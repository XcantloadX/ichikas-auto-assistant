"""耐心猎手（后台跑）：ping + 偶尔点击触发过渡，窗口一开就完整 bootstrap"""
import json
import subprocess
import time

from harness import get_device, find_game

ADB = ['adb', '-s', '127.0.0.1:5555', 'shell']

ping_js = '''
'use strict';
const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const getTrampolineFn = new NativeFunction(itf.add(24).readPointer(), 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
let attempts = 0;
rpc.exports = {
    ping: function () {
        attempts++;
        try {
            const t = getTrampolineFn(ptr(0), Memory.allocUtf8String('il2cpp_domain_get'), Memory.allocUtf8String('L'), 1, 0);
            if (t.isNull()) return { ok: false, why: 'notramp' };
            const dg = new NativeFunction(t, 'pointer', []);
            const d = dg();
            return { ok: true, domain: String(d) };
        } catch (e) {
            return { ok: false, why: String(e).slice(0, 40) };
        }
    }
};
'''

bootstrap_js = open('bootstrap2.js', encoding='utf-8').read().replace('__PREV__', '{}')


def sh(cmd):
    return subprocess.run(ADB + [cmd], capture_output=True, text=True).stdout


def main():
    dev = get_device()
    proc = find_game(dev)
    session = dev.attach(proc.pid)
    sc = session.create_script(ping_js)
    sc.load()
    api = sc.exports_sync

    box = {}
    bsc_loaded = False
    t0 = time.time()
    pings = 0
    last_tap = 0
    print(f'hunting on pid={proc.pid}')
    while time.time() - t0 < 5400:
        try:
            r = api.ping()
        except Exception as e:
            print('session dead:', str(e)[:80])
            return
        pings += 1
        if r['ok']:
            print(f'*** WINDOW at {time.time()-t0:.0f}s (ping {pings}) domain={r["domain"]} ***')
            if not bsc_loaded:
                try:
                    bsc = session.create_script(bootstrap_js)
                    bsc.on('message', lambda m, d: box.update(payload=m.get('payload', {})) if m['type'] == 'send' else None)
                    bsc.load()
                    bsc_loaded = True
                except Exception as e:
                    print('bootstrap load err:', str(e)[:100])
            time.sleep(0.5)
            payload = box.get('payload', {})
            if 'bootstrap' in payload:
                json.dump(payload['bootstrap'], open('bootstrap_result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                print('SAVED bootstrap_result.json')
                with open('hunter_done.flag', 'w') as f:
                    f.write('ok')
                return
        # 每 45s 点一下屏幕左上角（避免按钮）触发过渡
        if time.time() - last_tap > 45:
            sh('input tap 8 8')
            last_tap = time.time()
        time.sleep(1.0)
    print(f'hunt ended: {pings} pings, no window')


if __name__ == '__main__':
    main()
