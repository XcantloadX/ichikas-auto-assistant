"""窗口猎手：干净会话 + 耐心轮询，抓 gateway 可用窗口"""
import time

from harness import get_device, find_game

js = '''
'use strict';
const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const getTrampolineFn = new NativeFunction(itf.add(24).readPointer(), 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
const t = getTrampolineFn(ptr(0), Memory.allocUtf8String('il2cpp_domain_get'), Memory.allocUtf8String('L'), 1, 0);
const dg = new NativeFunction(t, 'pointer', []);

rpc.exports = {
    ping: function () {
        try { return { ok: true, domain: String(dg()) }; }
        catch (e) { return { ok: false }; }
    }
};
send({ ready: true });
'''

def main():
    dev = get_device()
    proc = find_game(dev)
    session = dev.attach(proc.pid)
    sc = session.create_script(js)
    sc.on('message', lambda m, d: print('[msg]', str(m)[:100]) if m['type'] == 'error' else None)
    sc.load()
    api = sc.exports_sync
    results = []
    t0 = time.time()
    while time.time() - t0 < 480:
        r = api.ping()
        results.append(1 if r['ok'] else 0)
        if r['ok'] and sum(results) == 1:
            print(f'FIRST WINDOW at {time.time()-t0:.1f}s')
        time.sleep(0.5)
    s = ''.join('O' if x else '.' for x in results)
    print('timeline:', s)
    print('ok count:', sum(results), '/', len(results))
    session.detach()

if __name__ == '__main__':
    main()
