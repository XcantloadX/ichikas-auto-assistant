"""框架猎手：用 iaa.unity_ui 客户端轮询窗口，窗口一开完成 bootstrap + dump。

用法：py -3 framework_hunter.py [最长等待秒数]
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(line_buffering=True)

from iaa.unity_ui.client import UnityUITree  # noqa: E402

OUT = Path(__file__).parent / 'ui_dump.json'


def main():
    max_wait = float(sys.argv[1]) if len(sys.argv) > 1 else 3600
    tap_interval = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
    ui = UnityUITree('com.sega.pjsekai', on_message=lambda p: print('[agent]', str(p)[:120]))
    t0 = time.time()
    pings = 0
    last_tap = 0.0
    print('hunting for window...')
    while time.time() - t0 < max_wait:
        pings += 1
        if ui.ping():
            print(f'*** WINDOW at {time.time() - t0:.0f}s (ping {pings}) ***')
            t1 = time.time()
            boot = ui.ensure_bootstrap(max_wait_s=120)
            print('bootstrap:', json.dumps(boot), f'{time.time() - t1:.1f}s')
            t1 = time.time()
            roots = ui.snapshot()
            print(f'dump ok: {time.time() - t1:.1f}s')
            total = len(roots)
            def count(nodes):
                return sum(1 + count(c.children) for c in nodes) if nodes else 0
            print('roots:', total, 'nodes:', count(roots))
            raw = ui._session.call('dump', 8000)
            OUT.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding='utf-8')
            print('saved', OUT)
            with open(Path(__file__).parent / 'hunter_done.flag', 'w') as f:
                f.write('ok')
            return
        # 周期点击触发过渡/输入处理（左上角安全点）
        if tap_interval > 0 and time.time() - last_tap > tap_interval:
            import subprocess
            subprocess.run(['adb', '-s', '127.0.0.1:5555', 'shell', 'input', 'tap', '8', '360'],
                           capture_output=True)
            last_tap = time.time()
        time.sleep(1.0)
    print('no window')


if __name__ == '__main__':
    main()
