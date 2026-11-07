import json
from typing import Callable

from PySide6.QtCore import QObject, Slot

from iaa.application.service.help_service import HelpService


class HelpController(QObject):
    def __init__(
        self,
        help_service: HelpService,
        get_language: Callable[[], str],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._help = help_service
        self._get_language = get_language

    def on_language_changed(self) -> None:
        self._help.clear_cache()

    @Slot(result=str)
    def topicsJson(self) -> str:
        topics = self._help.scan_topics(self._get_language())
        return json.dumps(topics, ensure_ascii=False)

    @Slot(str, result=str)
    def contentHtml(self, topic_id: str) -> str:
        return self._help.get_content(topic_id, self._get_language())
