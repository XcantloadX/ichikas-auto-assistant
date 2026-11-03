"""重启游戏并在加载期运行 bootstrap burst"""
import subprocess
import time

from harness import get_device, find_game

ADB = ['adb', '-s', '127.0.0.1:5555', 'shell']


def sh(cmd):
    return subprocess.run(ADB + [cmd], capture_output=True, text=True).stdout


def main():
    sh('am force-stop com.sega.pjsekai')
    time.sleep(2)
    sh('monkey -p com.sega.pjsekai -c android.intent.category.LAUNCHER 1')
    print('game launching...')
    time.sleep(12)

    dev = get_device()
    proc = find_game(dev)
    print('pid:', proc.pid)
    session = dev.attach(proc.pid)
    js = open('bootstrap.js', encoding='utf-8').read()
    sc = session.create_script(js)

    events = []

    def on(msg, data):
        if msg['type'] == 'send':
            events.append(msg['payload'])
            print('[send]', str(msg['payload'])[:300])
        elif msg['type'] == 'error':
            print('[error]', msg.get('stack', msg)[:400])

    sc.on('message', on)
    sc.load()

    # 等待 bootstrap 完成（游戏加载 1-2 分钟）
    t0 = time.time()
    got = None
    while time.time() - t0 < 240:
        for e in events:
            if isinstance(e, dict) and ('bootstrap' in e or 'bootstrapErr' in e):
                got = e
        if got:
            break
        # 期间点一下屏幕尝试触发状态（TAP TO START 出现时）
        elapsed = time.time() - t0
        if 45 < elapsed < 48:
            sh('input tap 640 617')  # TAP TO START
        time.sleep(1)
    import json
    if got:
        with open('bootstrap_result.json', 'w', encoding='utf-8') as f:
            json.dump(got, f, ensure_ascii=False, indent=1)
        print('saved bootstrap_result.json')
    else:
        print('TIMEOUT: no bootstrap result')
    session.detach()


if __name__ == '__main__':
    main()
