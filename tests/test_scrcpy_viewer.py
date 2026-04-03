import unittest

from iaa.application.desktop.scrcpy_viewer import DisplayMapping, map_canvas_to_image


class ScrcpyViewerMappingTests(unittest.TestCase):
    def test_map_canvas_to_image_inside_content(self):
        mapping = DisplayMapping(
            offset_x=10,
            offset_y=20,
            display_width=640,
            display_height=360,
            image_width=1280,
            image_height=720,
        )

        point = map_canvas_to_image(mapping, 330, 200)

        self.assertEqual(point, (640, 360))

    def test_map_canvas_to_image_outside_content_returns_none(self):
        mapping = DisplayMapping(
            offset_x=10,
            offset_y=20,
            display_width=640,
            display_height=360,
            image_width=1280,
            image_height=720,
        )

        self.assertIsNone(map_canvas_to_image(mapping, 5, 200))
        self.assertIsNone(map_canvas_to_image(mapping, 330, 10))
        self.assertIsNone(map_canvas_to_image(mapping, 700, 200))
        self.assertIsNone(map_canvas_to_image(mapping, 330, 500))


if __name__ == '__main__':
    unittest.main()
