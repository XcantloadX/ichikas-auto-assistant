import json
from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QObject, Slot

if TYPE_CHECKING:
    from iaa.application.service.iaa_service import IaaService


class HelpController(QObject):
    def __init__(
        self,
        iaa_service: 'IaaService',
        get_language: Callable[[], str],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._iaa = iaa_service
        self._get_language = get_language

    def on_language_changed(self) -> None:
        self._iaa.help.clear_cache()

    @Slot(result=str)
    def topicsJson(self) -> str:
        topics = self._iaa.help.scan_topics(self._get_language())
        return json.dumps(topics, ensure_ascii=False)

    @Slot(str, result=str)
    def contentHtml(self, topic_id: str) -> str:
        return self._iaa.help.get_content(topic_id, self._get_language())