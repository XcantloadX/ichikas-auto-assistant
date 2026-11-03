"""把 agent 的 UI dump 叠加到截图上可视化（调试/映射用）。

支持两种输入：
- agent 原始 dump（``{"ok":true,"n":N,"nodes":[...]}``，平铺 + parent 指针）
- 已建树的 dump（``{"roots":[...]}``，每个节点带 ``children``）

坐标换算：agent 输出的是 Canvas 世界坐标（overlay 画布，原点在屏幕中心、
Y 向上），本工具按 ``screen_x = wx*S + W/2, screen_y = H/2 - wy*S`` 映射到
截图像素。S 默认 360（= H/2 / canvas_world_h），可按画布世界尺寸自动推算。

用法::

    py -3 tools/visualize_ui_dump.py <screenshot.png> <ui_dump.json> [out.png]
"""
from __future__ import annotations

import json
import sys

import cv2


def build_forest(nodes: list[dict]) -> list[dict]:
    """把平铺节点（parent 指针）组装为带 children 的森林。"""
    by_t = {nd['t']: nd for nd in nodes}
    for nd in nodes:
        nd.setdefault('children', [])
    roots = []
    for nd in nodes:
        p = by_t.get(nd['parent'])
        if p is None:
            roots.append(nd)
        else:
            p['children'].append(nd)
    return roots


def forest_from_dump(dump: dict) -> list[dict]:
    """兼容两种 dump 格式。"""
    if 'nodes' in dump:
        return build_forest(dump['nodes'])
    return dump.get('roots', [])


def canvas_scale(roots: list[dict], screen_w: int, screen_h: int) -> float:
    """从根画布的世界尺寸推算 world→pixel 比例；推不出时退回 H/720。"""
    for r in roots:
        rect = r.get('rect')
        if rect and rect[3] > 0.5:
            return screen_h / rect[3]
    return screen_h / 720.0


def draw(img, node: dict, scale: float, screen_w: int, screen_h: int, depth: int = 0) -> None:
    rect = node.get('rect')
    if rect:
        cx, cy, w, h = rect
        x1 = int(cx * scale + screen_w / 2 - w * scale / 2)
        y1 = int(screen_h / 2 - cy * scale - h * scale / 2)
        x2 = int(cx * scale + screen_w / 2 + w * scale / 2)
        y2 = int(screen_h / 2 - cy * scale + h * scale / 2)
        if 0 < x2 - x1 < screen_w * 2 and 0 < y2 - y1 < screen_h * 2:
            color = (0, 255, 0) if node.get('active', 1) else (0, 0, 255)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 1)
            label = node.get('name', '')[:28]
            if node.get('text'):
                label += '=' + node['text'][:16]
            cv2.putText(img, label, (x1 + 1, max(y1 - 2, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.32, (255, 255, 0), 1)
    for c in node.get('children', []):
        draw(img, c, scale, screen_w, screen_h, depth + 1)


if __name__ == '__main__':
    shot_path, dump_path = sys.argv[1], sys.argv[2]
    out_path = sys.argv[3] if len(sys.argv) > 3 else 'ui_dump_vis.png'
    img = cv2.imread(shot_path)
    dump = json.load(open(dump_path, encoding='utf-8'))
    roots = forest_from_dump(dump)
    h, w = img.shape[:2]
    scale = canvas_scale(roots, w, h)
    for r in roots:
        draw(img, r, scale, w, h)
    cv2.imwrite(out_path, img)
    print('saved', out_path, f'scale={scale:.2f}')
