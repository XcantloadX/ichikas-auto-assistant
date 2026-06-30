"""
QEMU gRPC 截图预览镜。
基于 QemuGrpcImpl 后台线程，实时展示 AVD 画面。
"""
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from iaa.application.service.qemu_grpc import QemuGrpcImpl


def main():
    import subprocess, sys

    # 确保 AVD 运行中
    serial = None
    r = subprocess.run(
        ['D:\\SDK\\Android\\platform-tools\\adb.exe', 'devices'],
        capture_output=True, text=True, timeout=10,
    )
    for line in r.stdout.splitlines():
        if 'emulator-' in line and 'device' in line:
            serial = line.split()[0]
            break

    if serial is None:
        print('AVD 未运行，正在启动...')
        subprocess.Popen(
            ['D:\\SDK\\Android\\emulator\\emulator.exe',
             '-avd', 'Pixel_Tablet', '-grpc', '8554',
             '-no-snapshot', '-no-boot-anim'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for i in range(60):
            r = subprocess.run(
                ['D:\\SDK\\Android\\platform-tools\\adb.exe', 'devices'],
                capture_output=True, text=True, timeout=10,
            )
            for line in r.stdout.splitlines():
                if 'emulator-' in line and 'device' in line:
                    serial = line.split()[0]
                    break
            if serial:
                break
            time.sleep(5)
        else:
            print('AVD 未能在 5 分钟内上线')
            sys.exit(1)
        for i in range(30):
            r = subprocess.run(
                ['netstat', '-ano'], capture_output=True, text=True, timeout=5,
            )
            if ':8554' in r.stdout and 'LISTENING' in r.stdout:
                break
            time.sleep(2)

    print(f'连接 AVD: {serial}')
    impl = QemuGrpcImpl(grpc_port=8554, adb_serial=serial)
    impl.start()

    # 等待首帧
    print('等待首帧...')
    try:
        bgr = impl.screenshot()
    except RuntimeError as e:
        print('错误:', e)
        impl.stop()
        sys.exit(1)

    h, w = bgr.shape[:2]
    print(f'画面: {w}x{h}, 按 q / ESC 退出')

    fps_counter = {'count': 0, 't0': time.perf_counter(), 'fps': 0}
    cv2.namedWindow('QEMU gRPC Mirror', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('QEMU gRPC Mirror', w // 2, h // 2)

    while True:
        # 读取最新帧（零阻塞，0.7ms）
        bgr = impl.screenshot()

        # FPS
        fps_counter['count'] += 1
        elapsed = time.perf_counter() - fps_counter['t0']
        if elapsed >= 1.0:
            fps_counter['fps'] = fps_counter['count'] / elapsed
            fps_counter['count'] = 0
            fps_counter['t0'] = time.perf_counter()

        # 叠加信息
        overlay = bgr.copy()
        cv2.rectangle(overlay, (0, 0), (w, 24), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, bgr, 0.5, 0, bgr)
        cv2.putText(
            bgr,
            f'{w}x{h}  FPS={fps_counter["fps"]:.1f}  screen_size={impl.screen_size}',
            (8, 18),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1,
        )

        cv2.imshow('QEMU gRPC Mirror', bgr)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27):
            break

    cv2.destroyAllWindows()
    impl.stop()
    print('退出')


if __name__ == '__main__':
    main()
