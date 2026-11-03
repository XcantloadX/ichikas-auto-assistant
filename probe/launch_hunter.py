"""启动期窗口猎手：重启游戏后高频 attach 尝试"""
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
            if (t.isNull()) return { ok: false, why: 'notramp', attempts: attempts };
            const dg = new NativeFunction(t, 'pointer', []);
            const d = dg();
            return { ok: true, domain: String(d), attempts: attempts };
        } catch (e) {
            return { ok: false, why: String(e).slice(0, 60), attempts: attempts };
        }
    }
};
'''

bootstrap_js = open('bootstrap2.js', encoding='utf-8').read().replace('__PREV__', '{}')


def sh(cmd):
    return subprocess.run(ADB + [cmd], capture_output=True, text=True).stdout


def main():
    dev = get_device()
    sh('am force-stop com.sega.pjsekai')
    time.sleep(2)
    sh('monkey -p com.sega.pjsekai -c android.intent.category.LAUNCHER 1')
    t0 = time.time()
    launched = None

    while time.time() - t0 < 150:
        # 找进程
        out = sh('pgrep -f com.sega.pjsekai').strip()
        if not out:
            time.sleep(0.3)
            continue
        pid = int(out.splitlines()[0])
        if launched is None:
            print(f'process at {time.time()-t0:.1f}s pid={pid}')
            launched = pid
        # 检查元数据是否映射
        maps = sh(f'su -c "grep -c global-metadata /proc/{pid}/maps"').strip()
        meta = maps and maps != '0'
        if not meta:
            time.sleep(0.2)
            continue

        # 快速 attach + ping
        try:
            session = dev.attach(pid)
        except Exception as e:
            time.sleep(0.2)
            continue
        try:
            sc = session.create_script(ping_js)
            sc.load()
            r = sc.exports_sync.ping()
            el = time.time() - t0
            if r['ok']:
                print(f'*** WINDOW at {el:.1f}s domain={r["domain"]} ***')
                # 立刻跑完整 bootstrap
                try:
                    bsc = session.create_script(bootstrap_js)
                    bsc.load()
                except Exception as e:
                    print('bootstrap during window failed (script destroyed?):', str(e)[:80])
                time.sleep(1)
                box = {}
                # bootstrap2 通过 send 返回，重新建脚本收取结果
                try:
                    bsc2 = session.create_script(bootstrap_js)
                    bsc2.on('message', lambda m, d: box.update(payload=m.get('payload', {})) if m['type'] == 'send' else None)
                    bsc2.load()
                    print(json.dumps(box.get('payload', {}), ensure_ascii=False)[:1500])
                    if 'bootstrap' in box.get('payload', {}):
                        json.dump(box['payload']['bootstrap'], open('bootstrap_result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                        print('SAVED')
                        return
                except Exception as e:
                    print('second bootstrap err:', str(e)[:100])
                return
            else:
                print(f'{el:.1f}s ping fail: {r["why"]} (attempt {r["attempts"]})')
        except Exception as e:
            print(f'{time.time()-t0:.1f}s err: {str(e)[:80]}')
        finally:
            try:
                session.detach()
            except Exception:
                pass
        time.sleep(0.4)
    print('done')


if __name__ == '__main__':
    main()
