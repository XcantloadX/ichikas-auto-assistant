import tkinter as tk
from dataclasses import dataclass
from typing import TYPE_CHECKING

import cv2
from PIL import Image, ImageTk

if TYPE_CHECKING:
    from kotonebot.client.device import Device


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


class ScrcpyMirrorWindow:
    def __init__(self, root: tk.Misc):
        self.root = root
        self.window: tk.Toplevel | None = None
        self.canvas: tk.Canvas | None = None
        self._photo: ImageTk.PhotoImage | None = None
        self._canvas_image_id: int | None = None
        self._status_id: int | None = None
        self._device: Device | None = None
        self._mapping: DisplayMapping | None = None
        self._suppressed = False
        self._refresh_scheduled = False
        self._touch_active = False

    def ensure_open(self, device: 'Device') -> None:
        self._device = device
        if self._suppressed:
            return
        if self.window is not None and self.window.winfo_exists():
            return

        win = tk.Toplevel(self.root)
        win.title('Scrcpy 画面')
        win.geometry('960x600')
        win.configure(bg='black')
        win.protocol('WM_DELETE_WINDOW', self._on_manual_close)

        canvas = tk.Canvas(win, bg='black', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.bind('<ButtonPress-1>', self._on_button_press)
        canvas.bind('<B1-Motion>', self._on_button_drag)
        canvas.bind('<ButtonRelease-1>', self._on_button_release)

        self.window = win
        self.canvas = canvas
        self._canvas_image_id = None
        self._status_id = canvas.create_text(
            12,
            12,
            anchor=tk.NW,
            fill='white',
            text='等待画面...',
            font=('Microsoft YaHei UI', 10),
        )
        self._schedule_refresh()

    def close(self) -> None:
        self._touch_active = False
        self._device = None
        self._mapping = None
        self._photo = None
        self._canvas_image_id = None
        self._status_id = None
        self._refresh_scheduled = False
        if self.window is not None:
            try:
                if self.window.winfo_exists():
                    self.window.destroy()
            except tk.TclError:
                pass
        self.window = None
        self.canvas = None

    def notify_run_stopped(self) -> None:
        self._suppressed = False
        self.close()

    def _on_manual_close(self) -> None:
        self._suppressed = True
        self.close()

    def _schedule_refresh(self) -> None:
        if self._refresh_scheduled:
            return
        self._refresh_scheduled = True
        self.root.after(33, self._refresh_frame)

    def _refresh_frame(self) -> None:
        self._refresh_scheduled = False
        if self.window is None or not self.window.winfo_exists() or self.canvas is None or self._device is None:
            return

        try:
            frame = self._device.screenshot()
        except Exception as exc:  # noqa: BLE001
            self._update_status(f'等待画面... {exc}')
            self._schedule_refresh()
            return

        image_height, image_width = frame.shape[:2]
        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())

        scale = min(canvas_width / image_width, canvas_height / image_height)
        display_width = max(1, int(round(image_width * scale)))
        display_height = max(1, int(round(image_height * scale)))
        offset_x = max(0, (canvas_width - display_width) // 2)
        offset_y = max(0, (canvas_height - display_height) // 2)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if display_width != image_width or display_height != image_height:
            rgb = cv2.resize(rgb, (display_width, display_height), interpolation=cv2.INTER_AREA)

        photo = ImageTk.PhotoImage(Image.fromarray(rgb))
        self._photo = photo

        if self._canvas_image_id is None:
            self._canvas_image_id = self.canvas.create_image(offset_x, offset_y, anchor=tk.NW, image=photo)
        else:
            self.canvas.itemconfigure(self._canvas_image_id, image=photo)
            self.canvas.coords(self._canvas_image_id, offset_x, offset_y)

        self._mapping = DisplayMapping(
            offset_x=offset_x,
            offset_y=offset_y,
            display_width=display_width,
            display_height=display_height,
            image_width=image_width,
            image_height=image_height,
        )
        self._update_status(f'{image_width}x{image_height}')
        self._schedule_refresh()

    def _update_status(self, text: str) -> None:
        if self.canvas is not None and self._status_id is not None:
            self.canvas.itemconfigure(self._status_id, text=text)

    def _logic_to_physical(self, x: int, y: int) -> tuple[int, int]:
        if self._device is None:
            raise RuntimeError('No device bound to scrcpy viewer')
        real_x, real_y = self._device.scaler.logic_to_physical((x, y))
        return int(real_x), int(real_y)

    def _on_button_press(self, event: tk.Event) -> None:
        if self._device is None:
            return
        point = map_canvas_to_image(self._mapping, int(event.x), int(event.y))
        if point is None:
            return
        px, py = self._logic_to_physical(*point)
        self._device.input.touch_driver.touch_down(px, py, contact_id=0)
        self._touch_active = True

    def _on_button_drag(self, event: tk.Event) -> None:
        if self._device is None or not self._touch_active:
            return
        point = map_canvas_to_image(self._mapping, int(event.x), int(event.y))
        if point is None:
            return
        px, py = self._logic_to_physical(*point)
        self._device.input.touch_driver.touch_move(px, py, contact_id=0)

    def _on_button_release(self, event: tk.Event) -> None:
        if self._device is None or not self._touch_active:
            return
        point = map_canvas_to_image(self._mapping, int(event.x), int(event.y))
        if point is None:
            self._touch_active = False
            return
        px, py = self._logic_to_physical(*point)
        self._device.input.touch_driver.touch_up(px, py, contact_id=0)
        self._touch_active = False
