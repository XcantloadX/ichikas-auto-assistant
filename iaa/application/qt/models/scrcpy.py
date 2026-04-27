from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DisplayMapping:
    offset_x: int
    offset_y: int
    display_width: int
    display_height: int
    image_width: int
    image_height: int


def map_canvas_to_image(mapping: DisplayMapping | None, x: int, y: int) -> tuple[int, int] | None:
    if mapping is None:
        return None
    if x < mapping.offset_x or y < mapping.offset_y:
        return None
    if x >= mapping.offset_x + mapping.display_width or y >= mapping.offset_y + mapping.display_height:
        return None

    rel_x = x - mapping.offset_x
    rel_y = y - mapping.offset_y
    img_x = min(mapping.image_width - 1, max(0, int(round(rel_x * mapping.image_width / mapping.display_width))))
    img_y = min(mapping.image_height - 1, max(0, int(round(rel_y * mapping.image_height / mapping.display_height))))
    return img_x, img_y
