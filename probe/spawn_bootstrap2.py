"""spawn 模式 bootstrap v2：等元数据映射后再 ping"""
import json
import subprocess
import time

from harness import get_device

ADB = ['adb', '-s', '127.0.0.1:5555', 'shell']

poll_js = '''
'use strict';
const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const getTrampolineFn = new NativeFunction(itf.add(24).readPointer(), 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
let attempts = 0;
rpc.exports = {
    ping: function () {
        attempts++;
        try {
            const t = getTrampolineFn(ptr(0), Memory.allocUtf8String('il2cpp_domain_get'), Memory.allocUtf8String('L'), 1, 0);
            if (t.isNull()) return { ok: false, why: 'notramp', attempts: attempts };
            const dg = new NativeFunction(t, 'pointer', []);
            const d = dg();
            return { ok: true, domain: String(d), attempts: attempts };
        } catch (e) {
            return { ok: false, why: String(e).slice(0, 60), attempts: attempts };
        }
    }
};
send({ ready: true });
'''

bootstrap_js = open('bootstrap2.js', encoding='utf-8').read().replace('__PREV__', '{}')


def sh(cmd):
    return subprocess.run(ADB + [cmd], capture_output=True, text=True).stdout


def wait_for_metadata(pid, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        out = sh(f'su -c "cat /proc/{pid}/maps"')
        if 'global-metadata.dat' in out:
            return True
        time.sleep(0.3)
    return False


def main():
    dev = get_device()
    sh('am force-stop com.sega.pjsekai')
    time.sleep(2)
    pid = dev.spawn(['com.sega.pjsekai'])
    dev.resume(pid)
    print('spawned pid', pid)
    session = dev.attach(pid)

    box = {}

    def on(msg, data):
        if msg['type'] == 'send':
            box['payload'] = msg['payload']
        elif msg['type'] == 'error':
            box['error'] = msg.get('description', '') + ' | ' + str(msg.get('stack', ''))[:150]

    print('waiting for global-metadata mapping...')
    if not wait_for_metadata(pid):
        print('metadata never mapped')
        return
    print('metadata mapped, sleep 2s then attach script')
    time.sleep(2)

    sc2 = session.create_script(poll_js)
    sc2.on('message', on)
    sc2.load()
    api = sc2.exports_sync

    t0 = time.time()
    opened = False
    while time.time() - t0 < 120:
        try:
            r = api.ping()
        except Exception as e:
            print('process died during ping:', e)
            return
        if r['ok']:
            print(f'WINDOW at {time.time()-t0:.2f}s (attempt {r["attempts"]}) domain={r["domain"]}')
            opened = True
            break
        if r['attempts'] % 50 == 0:
            print(f'  {time.time()-t0:.1f}s attempt={r["attempts"]} why={r["why"]}')
        time.sleep(0.3)

    if opened:
        try:
            sc3 = session.create_script(bootstrap_js)
            sc3.on('message', on)
            sc3.load()
            payload = box.get('payload', {})
            print('bootstrap:', json.dumps(payload, ensure_ascii=False)[:2500])
            if 'bootstrap' in payload:
                json.dump(payload['bootstrap'], open('bootstrap_result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                print('SAVED bootstrap_result.json')
        except Exception as e:
            print('bootstrap err:', e)
    else:
        print('no window')
    try:
        session.detach()
    except Exception:
        pass


if __name__ == '__main__':
    main()
