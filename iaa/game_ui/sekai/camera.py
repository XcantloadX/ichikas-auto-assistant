from kotonebot import device, input, sleep
from kotonebot.client.device import AndroidDevice

class Camera:
    CONTROL_POINT = (733, 400)
    X_PX_PER_DEGREE = 4950 / 360 # 完整转一圈
    Y_PX_PER_DEGREE = 836 / 90 # 直视~接近 90° 俯视。实际值会更大，因为做不到绝对俯视

    def __init__(self):
        pass

    def rotate(self, pan: int, tilt: int, *, duration_sec: float = 4):
        """旋转镜头

        :param pan: 水平角度。
        :param tilt: 垂直角度。
        :param duration_sec: 持续时间（秒）, defaults to 4
        """
        start = self.CONTROL_POINT
        end = (
            start[0] + int(pan * self.X_PX_PER_DEGREE),
            start[1] + int(tilt * self.Y_PX_PER_DEGREE)
        )
        input.drag(start, end, duration=duration_sec)


if __name__ == '__main__':
    import json
    from pathlib import Path

    from kotonebot.backend.context.context import init_context, manual_context
    from kotonebot.client.host import Mumu12V5Host
    from kotonebot.client.host.mumu12_host import MuMu12HostConfig

    from iaa.config.base import IaaConfig

    config_path = Path('conf/default.json')
    config = IaaConfig.model_validate(json.loads(config_path.read_text(encoding='utf-8')))
    hosts = Mumu12V5Host.list()
    if not hosts:
        raise RuntimeError('No MuMu v5 instance found.')

    host = hosts[0]
    if not host.running() and config.game.check_emulator:
        host.start()
        host.wait_available()

    debug_device = host.create_device('nemu_ipc', MuMu12HostConfig())
    debug_device.orientation = 'landscape'
    debug_device.start()
    debug_device.scaler
    init_context(target_device=debug_device, force=True)

    print('Connected device screen size:', debug_device.screen_size)

    with manual_context('manual'):
        cam = Camera()
        cam.rotate(360, 0)
        # start = (733, 400)
        # end = (start[0], start[1] + 836)
        # input.drag(start, end, duration=5)
        # sleep(1)
        # input.drag(end, start, duration=5)