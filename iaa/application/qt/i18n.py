from __future__ import annotations

from typing import Literal

GuiLanguage = Literal['zh_CN', 'en_US']

DEFAULT_LANGUAGE: GuiLanguage = 'zh_CN'
SUPPORTED_LANGUAGES: tuple[GuiLanguage, ...] = ('zh_CN', 'en_US')

_TRANSLATIONS: dict[GuiLanguage, dict[str, str]] = {
    'zh_CN': {
        'nav.control': '控制',
        'nav.config': '配置',
        'nav.preferences': '偏好',
        'nav.logs': '日志',
        'nav.about': '关于',
        'common.save': '保存',
        'common.unsaved_changes': '有未保存改动',
        'preferences.title': '设置',
        'preferences.group.interface': '界面',
        'preferences.field.language': '界面语言',
        'preferences.language.zh_CN': '简体中文',
        'preferences.language.en_US': 'English',
    },
    'en_US': {
        'nav.control': 'Control',
        'nav.config': 'Config',
        'nav.preferences': 'Preferences',
        'nav.logs': 'Logs',
        'nav.about': 'About',
        'common.save': 'Save',
        'common.unsaved_changes': 'Unsaved changes',
        'preferences.title': 'Preferences',
        'preferences.group.interface': 'Interface',
        'preferences.field.language': 'Interface language',
        'preferences.language.zh_CN': 'Simplified Chinese',
        'preferences.language.en_US': 'English',
    },
}


def normalize_language(value: object) -> GuiLanguage:
    if value in ('zh', 'zh_CN', 'cn'):
        return 'zh_CN'
    if value in ('en', 'en_US'):
        return 'en_US'
    return DEFAULT_LANGUAGE


def translate(language: str, key: str) -> str:
    normalized = normalize_language(language)
    return (
        _TRANSLATIONS.get(normalized, {}).get(key)
        or _TRANSLATIONS[DEFAULT_LANGUAGE].get(key)
        or key
    )
