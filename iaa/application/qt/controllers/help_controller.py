import json
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot

if TYPE_CHECKING:
    from iaa.application.service.iaa_service import IaaService


class HelpController(QObject):
    def __init__(self, iaa_service: 'IaaService', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._iaa = iaa_service

    @Slot(result=str)
    def topicsJson(self) -> str:
        topics = self._iaa.help.scan_topics()
        return json.dumps(topics, ensure_ascii=False)

    @Slot(str, result=str)
    def contentHtml(self, topic_id: str) -> str:
        return self._iaa.help.get_content(topic_id)
