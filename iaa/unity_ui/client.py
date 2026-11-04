"""Unity UI 树客户端：注入 → bootstrap → dump → 定位。

用法::

    ui = UnityUITree('com.sega.pjsekai')
    ui.ensure_ready()
    roots = ui.snapshot()
    btn = ui.locator(name='UIPartsCloseButton').first()
    btn.click()
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from . import injector
from .guest_agent import AGENT_PORT, GuestAgentClient, GuestAgentError
from .tree import UINode, build_forest, flat_nodes


def detect_viewport(serial: str) -> tuple[int, int]:
    """查询设备屏幕分辨率（恒以横向为准，w >= h）。

    :param serial: adb 设备 serial
    :return: (w, h)
    """
    out = injector.adb_shell('wm size', serial)
    size = ''
    for line in out.splitlines():
        if 'Physical size' in line or 'Override size' in line:
            size = line.split(':')[-1].strip()
    w, h = (int(v) for v in size.split('x'))
    return (w, h) if w >= h else (h, w)


class UnityUITree:
    """Unity 游戏 UI 树客户端（guest agent TCP 链路）。

    生命周期：进程重启后 agent 失效，:meth:`ensure_ready` 会自动重注入；
    dump 期间进程死亡则抛出 :class:`GuestAgentError`，由调用方决定重建。
    """

    def __init__(self, package: str, serial: str = injector.ADB_SERIAL,
                 port: int = AGENT_PORT, viewport: tuple[int, int] | None = None) -> None:
        """创建客户端（不立即注入，首次 :meth:`ensure_ready` 时按需注入）。

        :param package: android 包名
        :param serial: adb 设备 serial
        :param port: agent TCP 端口
        :param viewport: 屏幕逻辑分辨率 (w, h)；缺省用 ``wm size`` 自动检测
        """
        self.package = package
        """android 包名。"""

        self.serial = serial
        """adb 设备 serial。"""

        self.viewport = viewport or detect_viewport(serial)
        """屏幕逻辑分辨率 (w, h)，横向。"""

        self._agent = GuestAgentClient(serial, port)
        self._bootstrapped = False

    # -- 连接管理 -----------------------------------------------------------

    def ping(self) -> bool:
        """探测 agent 是否存活。

        :return: agent 可响应时 True
        """
        return self._agent.ping()

    def ensure_ready(self) -> None:
        """确保 agent 已注入并完成 bootstrap（幂等；失效时自动重注入）。

        :raises RuntimeError: 游戏进程未运行或注入反复失败时
        """
        if self._bootstrapped and self.ping():
            return
        # 先试直连（agent 可能早已加载，只是 forward 丢了）
        self._agent.ensure_forward()
        if not self.ping():
            injector.ensure_agent_so(self.serial)
            injector.inject(self.serial, self.package)
            # 注入后 server 线程就绪可能慢一拍
            deadline = time.time() + 15
            while time.time() < deadline:
                if self.ping():
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError('agent did not come online after injection')
        self._agent.boot()
        self._bootstrapped = True

    # -- 快照 ---------------------------------------------------------------

    def snapshot(self, max_nodes: int = 8000) -> list[UINode]:
        """dump 当前 UI 树并还原为节点森林。

        :param max_nodes: 节点数上限
        :return: 根节点列表（每棵场景层级树一个根）
        :raises GuestAgentError: dump 失败时
        :raises RuntimeError: agent 失效且重注入后仍失败时
        """
        self.ensure_ready()
        try:
            r = self._agent.dump(max_nodes)
        except GuestAgentError:
            # 进程可能已重启：强制重注入一次
            self._bootstrapped = False
            self.ensure_ready()
            r = self._agent.dump(max_nodes)
        return build_forest(r, self.viewport)

    def snapshot_json(self, path: str, max_nodes: int = 8000) -> dict:
        """dump 并把原始 JSON 保存到文件（调试用）。

        :param path: 输出 json 路径
        :param max_nodes: 节点数上限
        :return: 原始 dump dict
        """
        self.ensure_ready()
        r = self._agent.dump(max_nodes)
        Path(path).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding='utf-8')
        return r

    # -- 定位 ---------------------------------------------------------------

    def locator(self, *, name: str | None = None, name_re: str | None = None,
                path: str | None = None, path_re: str | None = None,
                text: str | None = None, text_re: str | None = None,
                has_text: str | None = None, has_text_re: str | None = None,
                interactable: bool | None = None,
                include_inactive: bool = False,
                snapshot: list[UINode] | None = None):
        """创建 Playwright 风格定位器。

        :param name: GameObject 名精确匹配
        :param name_re: 名正则
        :param path: 完整路径精确匹配
        :param path_re: 路径正则
        :param text: TMP 文本精确匹配（节点自身）
        :param text_re: 节点自身文本正则
        :param has_text: 自身或任一子孙文本包含该子串
        :param has_text_re: 自身或任一子孙文本匹配该正则
        :param interactable: 可交互性过滤
        :param include_inactive: 含未激活节点
        :param snapshot: 复用已有快照（避免重复 dump）
        :return: :class:`Locator`
        """
        from .locator import Locator

        loc = Locator(self, name=name, name_re=name_re, path=path, path_re=path_re,
                      text=text, text_re=text_re, has_text=has_text,
                      has_text_re=has_text_re, interactable=interactable,
                      include_inactive=include_inactive)
        if snapshot is not None:
            loc.use_snapshot(snapshot)
        return loc
