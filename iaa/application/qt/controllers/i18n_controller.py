from __future__ import annotations
from typing import cast

from PySide6.QtCore import QObject, Property, Signal, Slot

from iaa.i18n import translate


class I18nController(QObject):
    languageChanged = Signal()

    def __init__(self, language: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._language = language

    def _get_language(self) -> str:
        return self._language

    language: str = cast(str, Property(str, _get_language, notify=languageChanged))

    @Slot(str)
    def setLanguage(self, language: str) -> None:
        if language == self._language:
            return
        self._language = language
        self.languageChanged.emit()

    @Slot(str, result=str)
    def t(self, key: str) -> str:
        return translate(self._language, key)
