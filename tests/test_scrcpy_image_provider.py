import unittest

from PySide6.QtCore import QSize
from PySide6.QtGui import QImage

from iaa.application.qt.controllers.scrcpy_image_provider import ScrcpyImageProvider


class ScrcpyImageProviderTests(unittest.TestCase):
    def test_request_image_strips_frame_token_query(self) -> None:
        provider = ScrcpyImageProvider()
        image = QImage(4, 4, QImage.Format.Format_RGB32)
        image.fill(0xFF0000)
        provider.update_image('my-config', image)

        result = provider.requestImage('my-config?42', None, QSize())

        self.assertFalse(result.isNull())
        self.assertEqual(result.width(), 4)
        self.assertEqual(result.height(), 4)
        self.assertEqual(result.pixelColor(0, 0).red(), 255)

    def test_resolve_key(self) -> None:
        self.assertEqual(ScrcpyImageProvider._resolve_key('tab-a?99'), 'tab-a')
        self.assertEqual(ScrcpyImageProvider._resolve_key('tab-a'), 'tab-a')


if __name__ == '__main__':
    unittest.main()