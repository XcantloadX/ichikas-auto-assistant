from kotonebot import device, input, sleep
from kotonebot.client.device import AndroidDevice

class Joystick:
    CONTROL_POINT = (150, 600)

    def __init__(self):
        pass

    def raw_move(self, dx: int, dy: int, duration_sec: float):
        start = self.CONTROL_POINT
        d = input.touch_driver
        d.touch_down(start[0], start[1], 1)
        d.touch_move(start[0] + dx, start[1] + dy, 1)
        sleep(duration_sec)
        d.touch_up(start[0] + dx, start[1] + dy, 1)

    def move_forward(self, distance: int):
        # self.raw_move(0, -distance)
        pass


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
        j = Joystick()
        j.raw_move(-100, 100, 4)
        sleep(1)
        j.raw_move(100, 0, 4)
        sleep(1)
        j.raw_move(0, -100, 4)
        sleep(1)
        j.raw_move(-100, 0, 4)
        sleep(1)
        j.raw_move(0, 100, 4)