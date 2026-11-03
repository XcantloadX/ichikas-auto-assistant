"""bootstrap2 驱动：多次尝试直到完成，支持续传"""
import json
import subprocess
import time

from harness import get_device, find_game

ADB = ['adb', '-s', '127.0.0.1:5555', 'shell']


def sh(cmd):
    return subprocess.run(ADB + [cmd], capture_output=True, text=True).stdout


def attempt(session, prev):
    js = open('bootstrap2.js', encoding='utf-8').read().replace('__PREV__', json.dumps(prev))
    sc = session.create_script(js)
    box = {}

    def on(msg, data):
        if msg['type'] == 'send':
            box['payload'] = msg['payload']
        elif msg['type'] == 'error':
            box['error'] = msg.get('description', '') + ' | ' + str(msg.get('stack', ''))[:200]

    sc.on('message', on)
    try:
        sc.load()
    except Exception as e:
        return {'error': f'load failed: {e}'}
    return box


def main():
    prev = {}
    for round_ in range(8):
        # 每轮可选重启游戏
        if round_ in (0, 3, 6):
            sh('am force-stop com.sega.pjsekai')
            time.sleep(2)
            sh('monkey -p com.sega.pjsekai -c android.intent.category.LAUNCHER 1')
            time.sleep(15)
            if round_ == 3:
                time.sleep(20)
                sh('input tap 640 617')  # TAP TO START
                time.sleep(2)
        dev = get_device()
        proc = find_game(dev)
        session = dev.attach(proc.pid)
        r = attempt(session, prev)
        session.detach()
        if 'payload' in r and 'bootstrap' in r.get('payload', {}):
            print('SUCCESS on round', round_)
            print(json.dumps(r['payload']['bootstrap'], ensure_ascii=False, indent=1)[:2500])
            json.dump(r['payload']['bootstrap'], open('bootstrap_result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            return
        err = r.get('error') or str(r.get('payload', r))[:200]
        print(f'round {round_}: {err[:180]}')
        # 部分结果续传
        p = r.get('payload', {})
        if 'bootstrap' in p:
            prev = p['bootstrap']
        time.sleep(2)
    print('ALL ROUNDS FAILED')


if __name__ == '__main__':
    main()
