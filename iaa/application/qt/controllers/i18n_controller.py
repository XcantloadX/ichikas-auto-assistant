from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from iaa.application.qt.i18n import normalize_language, translate


class I18nController(QObject):
    languageChanged = Signal()

    def __init__(self, language: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._language = normalize_language(language)

    def _get_language(self) -> str:
        return self._language

    language = Property(str, _get_language, notify=languageChanged)

    @Slot(str)
    def setLanguage(self, language: str) -> None:
        normalized = normalize_language(language)
        if normalized == self._language:
            return
        self._language = normalized
        self.languageChanged.emit()

    @Slot(str, result=str)
    def t(self, key: str) -> str:
        return translate(self._language, key)
