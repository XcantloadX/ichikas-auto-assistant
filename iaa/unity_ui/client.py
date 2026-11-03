"""agent RPC 的 Python 封装：bootstrap / snapshot / 窗口重试。

因为 MuMu 的 hook 门控，guest 调用呈"窗口"性：agent 内部已有逐调用重试，
这里再兜一层"整个操作重试"与"会话重建"。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from . import injector
from .tree import UINode, build_forest, flat_nodes

#: bootstrap 结果缓存路径（按进程 pid 区分）
_CACHE_DIR = Path(__file__).parent / '.cache'


class UnityUITree:
    """Unity 游戏 UI 树客户端。

    用法::

        ui = UnityUITree('com.sega.pjsekai')
        ui.ensure_bootstrap()
        roots = ui.snapshot()
        btn = ui.locator(name='StartButton').first()
        btn.click()
    """

    def __init__(self, package: str, on_message: Callable | None = None) -> None:
        """连接游戏进程并加载 agent。

        :param package: android 包名
        :param on_message: agent 消息回调
        :raises RuntimeError: 进程未运行时
        """
        self.package = package
        self._session = injector.AgentSession(package, on_message)
        self._bootstrapped = False

    # -- 基础 ---------------------------------------------------------------

    def ping(self) -> bool:
        """探测 agent 与窗口状态。

        :return: 窗口是否打开
        """
        return bool(self._session.call('ping').get('ok'))

    def ensure_bootstrap(self, max_wait_s: float = 600.0) -> dict:
        """确保 agent 完成 bootstrap（窗口内执行，失败时轮询重试）。

        :param max_wait_s: 最长等待窗口时间
        :return: bootstrap 摘要
        :raises TimeoutError: 等待窗口超时
        """
        if self._bootstrapped:
            return {}
        deadline = time.time() + max_wait_s
        last_err = None
        while time.time() < deadline:
            r = self._session.call('bootstrap')
            if r.get('ok'):
                self._bootstrapped = True
                return r['result']
            last_err = r.get('err')
            if not self._session.alive():
                self._rebuild()
            time.sleep(1.0)
        raise TimeoutError(f'bootstrap not completed: {last_err}')

    def snapshot(self, max_nodes: int = 6000) -> list[UINode]:
        """dump 当前 UI 树并还原为节点森林。

        :param max_nodes: 节点数上限
        :return: 根节点列表（每棵场景层级树一个根）
        :raises RuntimeError: dump 失败时
        """
        r = self._session.call('dump', max_nodes, timeout=180)
        if not r.get('ok'):
            raise RuntimeError(f"dump failed: {r.get('err')}")
        return build_forest(r['tree'])

    def snapshot_json(self, path: str, max_nodes: int = 6000) -> dict:
        """dump 并把原始 JSON 保存到文件（调试用）。

        :param path: 输出 json 路径
        :param max_nodes: 节点数上限
        :return: 原始 dump dict
        """
        r = self._session.call('dump', max_nodes, timeout=180)
        Path(path).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding='utf-8')
        return r

    def locator(self, *, name: str | None = None, name_re: str | None = None,
                path: str | None = None, path_re: str | None = None,
                text: str | None = None, text_re: str | None = None,
                interactable: bool | None = None,
                include_inactive: bool = False,
                snapshot: list[UINode] | None = None):
        """创建 Playwright 风格定位器。

        :param name: GameObject 名精确匹配
        :param name_re: 名正则
        :param path: 完整路径精确匹配
        :param path_re: 路径正则
        :param text: TMP 文本精确匹配
        :param text_re: 文本正则
        :param interactable: 可交互性过滤
        :param include_inactive: 含未激活节点
        :param snapshot: 复用已有快照（避免重复 dump）
        :return: :class:`Locator`
        """
        from .locator import Locator

        loc = Locator(self, name=name, name_re=name_re, path=path, path_re=path_re,
                      text=text, text_re=text_re, interactable=interactable,
                      include_inactive=include_inactive)
        if snapshot is not None:
            loc.use_snapshot(snapshot)
        return loc

    # -- 内部 ---------------------------------------------------------------

    def _rebuild(self) -> None:
        """目标进程已死或会话失效时重建会话（等待游戏重新运行）。"""
        try:
            self._session.detach()
        except Exception:  # noqa: BLE001
            pass
        for _ in range(120):
            try:
                self._session = injector.AgentSession(self.package)
                self._bootstrapped = False
                return
            except RuntimeError:
                time.sleep(1.0)
        raise RuntimeError('cannot rebuild agent session')
