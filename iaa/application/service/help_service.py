import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .iaa_service import IaaService


class HelpService:
    def __init__(self, iaa_service: 'IaaService'):
        self._iaa = iaa_service
        self._topics: list[dict] | None = None

    @property
    def help_dir(self) -> str:
        return os.path.join(self._iaa.assets.assets_root_path, 'help')

    def scan_topics(self) -> list[dict]:
        if self._topics is not None:
            return self._topics

        self._topics = []
        help_path = Path(self.help_dir)
        if not help_path.exists():
            return self._topics

        html_files = sorted(help_path.glob('*.html'))
        for html_file in html_files:
            topic_id = html_file.stem
            title = self._extract_title(html_file) or topic_id
            self._topics.append({
                'id': topic_id,
                'title': title,
            })
        return self._topics

    def _extract_title(self, file_path: Path) -> str | None:
        try:
            content = file_path.read_text(encoding='utf-8')
            match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        except Exception:
            pass
        return None

    def get_content(self, topic_id: str) -> str:
        file_path = Path(self.help_dir) / f'{topic_id}.html'
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
