"""spawn 模式 bootstrap：进程一出生就 attach，抢在 hp12 hook 安装前完成引导"""
import json
import time

from harness import get_device

js = open('bootstrap2.js', encoding='utf-8').read().replace('__PREV__', '{}')

def main():
    dev = get_device()
    print('spawning...')
    pid = dev.spawn(['com.sega.pjsekai'])
    dev.resume(pid)
    session = dev.attach(pid)
    sc = session.create_script(js)
    box = {}

    def on(msg, data):
        if msg['type'] == 'send':
            box['payload'] = msg['payload']
            p = msg['payload']
            if 'ping' in str(p)[:40]:
                pass
        elif msg['type'] == 'error':
            box['error'] = msg.get('description', '') + ' | ' + str(msg.get('stack', ''))[:150]

    sc.on('message', on)

    # bootstrap2.js 是同步 load 的；改成: 先加载一个 polling 脚本
    # 简化：直接在这里手写 spawn 版逻辑
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
    sc2 = session.create_script(poll_js)
    sc2.on('message', on)
    sc2.load()
    api = sc2.exports_sync

    print('polling from birth...')
    t0 = time.time()
    opened = False
    while time.time() - t0 < 180:
        r = api.ping()
        if r['ok']:
            print(f'WINDOW at {time.time()-t0:.2f}s (attempt {r["attempts"]}) domain={r["domain"]}')
            opened = True
            break
        if r['attempts'] % 100 == 0:
            print(f'  {time.time()-t0:.1f}s attempt={r["attempts"]} why={r["why"]}')
        time.sleep(0.05)

    if opened:
        # 窗口已开，立即跑完整 bootstrap（同步 load，趁窗口没关）
        sc3 = session.create_script(js)
        sc3.on('message', on)
        try:
            sc3.load()
            print('bootstrap payload:', json.dumps(box.get('payload', {}), ensure_ascii=False)[:2000])
            if 'bootstrap' in box.get('payload', {}):
                json.dump(box['payload']['bootstrap'], open('bootstrap_result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                print('SAVED bootstrap_result.json')
        except Exception as e:
            print('bootstrap load err:', e)
    else:
        print('no window in 180s')
    session.detach()

if __name__ == '__main__':
    main()
