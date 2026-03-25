import tkinter as tk
import ttkbootstrap as tb

from typing import Iterable, List


class Shuttle(tb.Frame):
    """A reusable dual-list shuttle widget with order controls.

    Usage:
      s = Shuttle(parent)
      s.set_selected([...])
      s.set_available([...])
      values = s.get_selected()
    """

    def __init__(self, parent: tk.Misc, selected_title: str = "已选项（上/下 可排序）",
                 available_title: str = "可选项", height: int = 8, btn_kw: dict | None = None):
        super().__init__(parent)

        if btn_kw is None:
            btn_kw = dict(width=3, padding=0, bootstyle="secondary-toolbutton")

        # Left: selected
        self.lb_selected_frame = tb.Frame(self)
        self.lb_selected_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tb.Label(self.lb_selected_frame, text=selected_title, anchor=tk.W).pack(fill=tk.X)
        self.selected_lb = tk.Listbox(self.lb_selected_frame, height=height, exportselection=False)
        self.selected_lb.pack(fill=tk.BOTH, expand=True)

        # Middle: control buttons (vertically centered)
        self.ctrl_frame = tb.Frame(self)
        self.ctrl_frame.pack(side=tk.LEFT, padx=8, fill=tk.Y)
        self.ctrl_frame.rowconfigure(0, weight=1)
        self.ctrl_frame.rowconfigure(5, weight=1)

        self.btn_add = tb.Button(self.ctrl_frame, text="→", **btn_kw)
        self.btn_remove = tb.Button(self.ctrl_frame, text="←", **btn_kw)
        self.btn_up = tb.Button(self.ctrl_frame, text="↑", **btn_kw)
        self.btn_down = tb.Button(self.ctrl_frame, text="↓", **btn_kw)
        self.btn_add.grid(row=1, column=0, padx=2, pady=2)
        self.btn_remove.grid(row=2, column=0, padx=2, pady=2)
        self.btn_up.grid(row=3, column=0, padx=2, pady=2)
        self.btn_down.grid(row=4, column=0, padx=2, pady=2)

        # Right: available
        self.lb_available_frame = tb.Frame(self)
        self.lb_available_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tb.Label(self.lb_available_frame, text=available_title, anchor=tk.W).pack(fill=tk.X)
        self.available_lb = tk.Listbox(self.lb_available_frame, height=height, exportselection=False)
        self.available_lb.pack(fill=tk.BOTH, expand=True)

        # Bind controls
        self.btn_add.configure(command=self._move_to_available)
        self.btn_remove.configure(command=self._move_to_selected)
        self.btn_up.configure(command=self._move_up)
        self.btn_down.configure(command=self._move_down)

        self.available_lb.bind('<Double-1>', lambda e: self._move_to_selected())
        self.selected_lb.bind('<Double-1>', lambda e: self._move_to_available())

        # Prevent outer scroll propagation by handling wheel events on each listbox
        self._bind_listbox_scroll(self.available_lb)
        self._bind_listbox_scroll(self.selected_lb)

    def _bind_listbox_scroll(self, lb: tk.Listbox) -> None:
        def _on_lb_mousewheel(event: tk.Event):
            lb.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        def _on_lb_mousewheel_up(event: tk.Event):
            lb.yview_scroll(-1, "units")
            return "break"

        def _on_lb_mousewheel_down(event: tk.Event):
            lb.yview_scroll(1, "units")
            return "break"

        lb.bind("<MouseWheel>", _on_lb_mousewheel)
        lb.bind("<Button-4>", _on_lb_mousewheel_up)
        lb.bind("<Button-5>", _on_lb_mousewheel_down)

    # Movement helpers
    def _move_to_selected(self) -> None:
        sel = self.available_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        val = self.available_lb.get(idx)
        self.available_lb.delete(idx)
        self.selected_lb.insert(tk.END, val)

    def _move_to_available(self) -> None:
        sel = self.selected_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        val = self.selected_lb.get(idx)
        self.selected_lb.delete(idx)
        self.available_lb.insert(tk.END, val)

    def _move_up(self) -> None:
        sel = self.selected_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx <= 0:
            return
        val = self.selected_lb.get(idx)
        self.selected_lb.delete(idx)
        self.selected_lb.insert(idx - 1, val)
        self.selected_lb.selection_set(idx - 1)

    def _move_down(self) -> None:
        sel = self.selected_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= self.selected_lb.size() - 1:
            return
        val = self.selected_lb.get(idx)
        self.selected_lb.delete(idx)
        self.selected_lb.insert(idx + 1, val)
        self.selected_lb.selection_set(idx + 1)

    # API
    def set_selected(self, items: Iterable[str]) -> None:
        self.selected_lb.delete(0, tk.END)
        for it in items:
            self.selected_lb.insert(tk.END, it)

    def set_available(self, items: Iterable[str]) -> None:
        self.available_lb.delete(0, tk.END)
        for it in items:
            self.available_lb.insert(tk.END, it)

    def get_selected(self) -> List[str]:
        return [self.selected_lb.get(i) for i in range(self.selected_lb.size())]

    def get_available(self) -> List[str]:
        return [self.available_lb.get(i) for i in range(self.available_lb.size())]
