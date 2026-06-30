from __future__ import annotations

from threading import Lock

from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider


class ScrcpyImageProvider(QQuickImageProvider):
    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._images: dict[str, QImage] = {}
        self._lock = Lock()

    def update_image(self, key: str, image: QImage) -> None:
        with self._lock:
            self._images[key] = image

    def remove_image(self, key: str) -> None:
        with self._lock:
            self._images.pop(key, None)

    @staticmethod
    def _resolve_key(image_id: str) -> str:
        # QML: image://scrcpy/<key>?<frameToken> → id 为 "<key>?<frameToken>"
        return image_id.split('?', 1)[0]

    def requestImage(self, _id: str, size, requested_size):  # type: ignore[override]
        key = self._resolve_key(_id)
        with self._lock:
            image = self._images.get(key)
            if image is None or image.isNull():
                result = QImage(2, 2, QImage.Format.Format_RGB32)
                result.fill(0)
            else:
                result = image.copy()
        if size is not None:
            size.setWidth(result.width())
            size.setHeight(result.height())
        if requested_size.width() > 0 and requested_size.height() > 0:
            result = result.scaled(requested_size)
        return result