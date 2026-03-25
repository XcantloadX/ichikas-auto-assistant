from __future__ import annotations

import webbrowser
import tkinter as tk
from dataclasses import dataclass

import ttkbootstrap as tb

from .renderer import RenderContext


@dataclass(frozen=True, slots=True)
class AboutLink:
    """Metadata for one about-page hyperlink."""

    text: str
    url: str


ABOUT_LINKS: tuple[AboutLink, ...] = (
    AboutLink('GitHub', 'https://github.com/XcantloadX/ichikas-auto-assistant'),
    AboutLink('Bilibili', 'https://space.bilibili.com/3546853903698457'),
    AboutLink('教程文档', 'https://p.kdocs.cn/s/AGBH56RBAAAFS'),
    AboutLink('QQ 群', 'https://qm.qq.com/q/Mu1SSfK1Gg'),
)


def build_about_tab(parent: tk.Misc, *, context: RenderContext) -> None:
    """Render about tab from static metadata.

    :param parent: Parent widget.
    :param context: Render context carrying app reference.
    """

    app = context.app

    container = tb.Frame(parent)
    container.pack(fill=tk.BOTH, expand=True)

    inner = tb.Frame(container)
    inner.pack(expand=True)

    try:
        from iaa.application.desktop.tooltip import _HoverTooltip

        app.store.logo_image = tk.PhotoImage(file=app.service.assets.logo_path)
        logo_label = tk.Label(inner, image=app.store.logo_image)
        logo_label.pack(pady=(20, 8))
        _HoverTooltip(logo_label, '我同时和六个初音未来结婚')
    except Exception:
        pass

    tb.Label(inner, text='一歌小助手 iaa', font=('Microsoft YaHei UI', 20, 'bold')).pack(pady=(0, 6))
    tb.Label(inner, text=f'版本 v{app.service.version}', font=('Microsoft YaHei UI', 10)).pack(pady=(0, 12))

    links = tb.Frame(inner)
    links.pack()

    for link in ABOUT_LINKS:
        label = tk.Label(links, text=link.text, fg='#0d6efd', cursor='hand2', font=('Microsoft YaHei UI', 10, 'underline'))
        label.pack(side=tk.LEFT, padx=10)
        label.bind('<Button-1>', lambda _event, url=link.url: webbrowser.open(url))
