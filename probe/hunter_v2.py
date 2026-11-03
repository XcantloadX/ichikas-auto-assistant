"""窗口猎手 v2：重启循环 + 启动期高频 ping + 即时 bootstrap burst"""
import json
import subprocess
import time

from harness import get_device

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
            return { ok: false, why: 'dead1066' };
        }
    }
};
'''

bootstrap_js = open('bootstrap2.js', encoding='utf-8').read().replace('__PREV__', '{}')


def sh(cmd):
    return subprocess.run(ADB + [cmd], capture_output=True, text=True).stdout


def wait_process(dev, timeout=40):
    t0 = time.time()
    while time.time() - t0 < timeout:
        out = sh('pgrep -f com.sega.pjsekai').strip()
        if out:
            return int(out.splitlines()[0])
        time.sleep(0.5)
    return None


def try_cycle(dev, cycle_idx):
    """一次重启-狩猎周期"""
    sh('am force-stop com.sega.pjsekai')
    time.sleep(2)
    sh('monkey -p com.sega.pjsekai -c android.intent.category.LAUNCHER 1')
    t_launch = time.time()
    pid = wait_process(dev)
    if not pid:
        print(f'cycle {cycle_idx}: no process')
        return False
    print(f'cycle {cycle_idx}: pid={pid}')

    # 启动期高频 ping（0-60s，300ms 间隔）
    session = None
    api = None
    t0 = time.time()
    while time.time() - t0 < 75:
        try:
            if session is None:
                session = dev.attach(pid)
                sc = session.create_script(ping_js)
                sc.load()
                api = sc.exports_sync
            r = api.ping()
            el = time.time() - t_launch
            if r['ok']:
                print(f'*** WINDOW at {el:.1f}s domain={r["domain"]} ***')
                box = {}
                try:
                    bsc = session.create_script(bootstrap_js)
                    bsc.on('message', lambda m, d: box.update(payload=m.get('payload', {})) if m['type'] == 'send' else None)
                    bsc.load()
                    time.sleep(1)
                    payload = box.get('payload', {})
                    if 'bootstrap' in payload:
                        json.dump(payload['bootstrap'], open('bootstrap_result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                        print('SAVED bootstrap_result.json')
                        with open('hunter_done.flag', 'w') as f:
                            f.write('ok')
                        return True
                    else:
                        print('bootstrap incomplete:', str(payload)[:150])
                except Exception as e:
                    print('bootstrap err:', str(e)[:120])
                return False
        except Exception as e:
            # 进程可能尚未可 attach 或已死
            if 'not attached' not in str(e) and 'process' not in str(e).lower():
                pass
            session = None
            api = None
            if not sh(f'ls /proc/{pid}/cmdline').strip() or 'No such' in sh(f'cat /proc/{pid}/cmdline 2>/dev/null'):
                print(f'cycle {cycle_idx}: process died at {time.time()-t_launch:.0f}s')
                return False
        time.sleep(0.3)
    try:
        if session:
            session.detach()
    except Exception:
        pass
    print(f'cycle {cycle_idx}: no window in 75s')
    return False


def main():
    dev = get_device()
    for i in range(40):
        if try_cycle(dev, i):
            return
        time.sleep(3)
    print('hunter v2 ended: no window')


if __name__ == '__main__':
    main()
