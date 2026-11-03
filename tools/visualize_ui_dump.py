"""把 agent 的 UI dump 叠加到截图上可视化（调试/映射用）。

用法::

    py -3 tools/visualize_ui_dump.py <screenshot.png> <ui_dump.json> [out.png]

在截图上绘制每个带 rect 的节点矩形与名称，便于把 R.* 模板 prefab
映射到真实 Unity 节点。
"""
from __future__ import annotations

import json
import sys

import cv2


def walk(node: dict, depth: int = 0) -> None:
    """先序遍历并绘制。"""
    rect = node.get('rect')
    if rect and rect.get('w', 0) > 1:
        x1, y1 = int(rect['cx'] - rect['w'] / 2), int(rect['cy'] - rect['h'] / 2)
        x2, y2 = int(rect['cx'] + rect['w'] / 2), int(rect['cy'] + rect['h'] / 2)
        color = (0, 255, 0) if node.get('active') else (0, 0, 255)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 1)
        cv2.putText(img, node.get('name', '')[:28], (x1 + 1, max(y1 - 2, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, (255, 255, 0), 1)
    for c in node.get('children', []):
        walk(c, depth + 1)


if __name__ == '__main__':
    img = cv2.imread(sys.argv[1])
    dump = json.load(open(sys.argv[2], encoding='utf-8'))
    out_path = sys.argv[3] if len(sys.argv) > 3 else 'ui_dump_vis.png'
    tree = dump.get('tree', dump)
    for root in tree.get('roots', []):
        walk(root)
    cv2.imwrite(out_path, img)
    print('saved', out_path)
