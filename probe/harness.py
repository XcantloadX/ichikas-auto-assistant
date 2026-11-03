"""probe 复用小工具：attach 到游戏进程并加载 JS agent。"""
import sys
import time

import frida

REMOTE = '127.0.0.1:27042'


def get_device():
    return frida.get_device_manager().add_remote_device(REMOTE)


def find_game(device, keyword='sega', pid=None):
    if pid is not None:
        for p in device.enumerate_processes():
            if p.pid == pid:
                return p
        return None
    try:
        for app in device.enumerate_applications():
            if keyword in app.identifier:
                return app
    except Exception:
        pass
    for p in device.enumerate_processes():
        if keyword in p.name.lower() or keyword in str(p).lower():
            return p
    return None


def run_js(js, keyword='sega', seconds=5, spawn=False, pkg=None, globals_=None):
    dev = get_device()
    if spawn:
        pid = dev.spawn([pkg])
        dev.resume(pid)
        session = dev.attach(pid)
    else:
        proc = find_game(dev, keyword)
        if proc is None:
            raise RuntimeError('game process not found')
        pid = proc.pid
        session = dev.attach(pid)
    print(f'attached pid={pid}')

    out = []

    def on_message(message, data):
        if message['type'] == 'send':
            out.append(message['payload'])
            print('[send]', message['payload'])
        elif message['type'] == 'error':
            print('[error]', message.get('stack', message))
        else:
            print('[msg]', message)

    if globals_:
        for k, v in globals_.items():
            js = js.replace(f'__{k}__', repr(v))
    script = session.create_script(js)
    script.on('message', on_message)
    script.load()
    t0 = time.time()
    while time.time() - t0 < seconds:
        time.sleep(0.2)
    return out, session, script


if __name__ == '__main__':
    path = sys.argv[1]
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 5
    with open(path, encoding='utf-8') as f:
        js = f.read()
    run_js(js, seconds=secs)
