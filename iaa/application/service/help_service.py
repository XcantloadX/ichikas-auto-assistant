import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from iaa.i18n import _detect_system_language

if TYPE_CHECKING:
    from .iaa_service import IaaService


class HelpService:
    def __init__(self, iaa_service: 'IaaService'):
        self._iaa = iaa_service
        self._topics_cache: dict[str, list[dict]] = {}

    @property
    def help_dir(self) -> str:
        return os.path.join(self._iaa.assets.assets_root_path, 'help')

    def _resolve_language(self, language: str) -> str:
        if language == 'auto':
            language = _detect_system_language()
        return language

    def _language_dir(self, language: str) -> Path:
        root = Path(self.help_dir)
        lang = self._resolve_language(language)
        lang_dir = root / lang
        if lang_dir.is_dir():
            return lang_dir
        fallback = root / 'zh_CN'
        if fallback.is_dir():
            return fallback
        return root

    def clear_cache(self) -> None:
        self._topics_cache.clear()

    def scan_topics(self, language: str = 'auto') -> list[dict]:
        lang = self._resolve_language(language)
        cached = self._topics_cache.get(lang)
        if cached is not None:
            return cached

        topics: list[dict] = []
        help_path = self._language_dir(language)
        if not help_path.exists():
            self._topics_cache[lang] = topics
            return topics

        html_files = sorted(help_path.glob('*.html'))
        for html_file in html_files:
            if html_file.name == 'index.html':
                continue
            topic_id = html_file.stem
            title = self._extract_title(html_file) or topic_id
            topics.append({
                'id': topic_id,
                'title': title,
            })
        self._topics_cache[lang] = topics
        return topics

    def _extract_title(self, file_path: Path) -> str | None:
        try:
            content = file_path.read_text(encoding='utf-8')
            match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        except Exception:
            pass
        return None

    def get_content(self, topic_id: str, language: str = 'auto') -> str:
        file_path = self._language_dir(language) / f'{topic_id}.html'
        if not file_path.exists():
            return ''
        try:
            content = file_path.read_text(encoding='utf-8')
            return self._preprocess_html(content)
        except Exception:
            return ''

    def _preprocess_html(self, html: str) -> str:
        def add_font_weight(match: re.Match) -> str:
            tag = match.group(1)
            attrs = match.group(2) or ''
            if 'style=' in attrs.lower():
                attrs = re.sub(r'style="([^"]*)"', r'style="\1; font-weight: normal"', attrs, flags=re.IGNORECASE)
                attrs = re.sub(r"style='([^']*)'", r"style='\1; font-weight: normal'", attrs, flags=re.IGNORECASE)
            else:
                attrs = f' style="font-weight: normal"{attrs}'
            return f'<{tag}{attrs}>'

        html = re.sub(r'<(h[1-6])((?:\s+[^>]*)?)>', add_font_weight, html)
        return html