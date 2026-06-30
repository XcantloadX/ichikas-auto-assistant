import json

from PySide6.QtCore import QObject, Slot

from iaa.application.service.help_service import HelpService


class HelpController(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._help = HelpService()

    @Slot(result=str)
    def topicsJson(self) -> str:
        return json.dumps(self._help.scan_topics(), ensure_ascii=False)

    @Slot(str, result=str)
    def contentHtml(self, topic_id: str) -> str:
        return self._help.get_content(topic_id)
