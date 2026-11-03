"""纯内存引导驱动：解析 maps、扫描 metadata 字符串、运行 agent 行走"""
import json
import subprocess
import sys
import time

from harness import get_device, find_game

ADB = ['adb', '-s', '127.0.0.1:5555', 'shell']


def sh(cmd):
    return subprocess.run(ADB + [cmd], capture_output=True, text=True).stdout


def parse_maps(pid):
    out = sh(f'su -c "cat /proc/{pid}/maps"')
    info = {'guest_base': None, 'meta_base': None}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue
        rng, perms, off, path = parts[0], parts[1], parts[2], parts[5]
        if 'libil2cpp.so' in path and perms == 'r--p' and off == '00000000':
            if info['guest_base'] is None:
                info['guest_base'] = int(rng.split('-')[0], 16)  # 第一个：保护壳副本
            else:
                info['guest_base_real'] = int(rng.split('-')[0], 16)  # 第二个：真实加载
        if 'global-metadata.dat' in path and perms == 'rw-p':
            info['meta_base'] = int(rng.split('-')[0], 16)
    return info


def main():
    dev = get_device()
    proc = find_game(dev)
    pid = proc.pid
    info = parse_maps(pid)
    print('maps:', {k: hex(v) if v else v for k, v in info.items()})
    meta_base = info['meta_base']
    meta_size = 28305260

    # 扫 metadata 找 "GameObject\0" / "UnityEngine\0"
    js = f'''
const mb = ptr('{hex(meta_base)}');
const size = {meta_size};
function findStr(pat) {{
    const m = Memory.scanSync(mb, size, pat);
    return m.map(h => String(h.address));
}}
const go = findStr('47 61 6d 65 4f 62 6a 65 63 74 00');
const un = findStr('55 6e 69 74 79 45 6e 67 69 6e 65 00');
send({{ go: go, un: un }});
'''
    sc = dev.attach(pid) if False else None
    session = dev.attach(pid)
    s1 = session.create_script(js)
    out1 = {}
    s1.on('message', lambda m, d: out1.update(m.get('payload', {})) if m['type'] == 'send' else print('[e1]', str(m)[:120]))
    s1.load()
    time.sleep(3)
    go_strs, un_strs = out1.get('go', []), out1.get('un', [])
    print('go strs:', len(go_strs), 'un strs:', len(un_strs))
    if not un_strs:
        print('no UnityEngine string found')
        return

    js2 = (open('memonly_bootstrap.js', encoding='utf-8').read()
           .replace('__META_BASE__', hex(meta_base))
           .replace('__GO_STRS__', json.dumps(go_strs))
           .replace('__UN_STRS__', json.dumps(un_strs[:1])))
    out2 = {}
    s2 = session.create_script(js2)
    s2.on('message', lambda m, d: out2.update(m.get('payload', {})) if m['type'] == 'send' else print('[e2]', str(m)[:200]))
    s2.load()
    t0 = time.time()
    while time.time() - t0 < 180:
        if 'table' in out2:
            break
        time.sleep(1)
    print('klass:', out2.get('klass'))
    print('walked:', out2.get('tableCount'))
    table = out2.get('table', {})
    for k, v in sorted(table.items()):
        print(f'  {k}: {v}')
    json.dump({'info': {k: v for k, v in info.items()}, 'klass': out2.get('klass'), 'table': table},
              open('memonly_result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    session.detach()


if __name__ == '__main__':
    main()
