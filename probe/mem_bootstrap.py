"""按进程内存元数据 header 的完整 bootstrap：klass 定位 + fields 数组解码"""
import json
import struct
import subprocess
import sys
import time

from harness import get_device, find_game

ADB = ['adb', '-s', '127.0.0.1:5555', 'shell']

HEADER_NAMES = ['stringLiteralOffset', 'stringLiteralSize', 'stringLiteralDataOffset', 'stringLiteralDataSize',
                'stringOffset', 'stringSize', 'eventsOffset', 'eventsSize', 'propertiesOffset', 'propertiesSize',
                'methodsOffset', 'methodsSize', 'parameterDefaultValuesOffset', 'parameterDefaultValuesSize',
                'fieldDefaultValuesOffset', 'fieldDefaultValuesSize', 'fieldAndParameterDefaultValueDataOffset',
                'fieldAndParameterDefaultValueDataSize', 'fieldMarshaledSizesOffset', 'fieldMarshaledSizesSize',
                'parametersOffset', 'parametersSize', 'fieldsOffset', 'fieldsSize',
                'genericParametersOffset', 'genericParametersSize', 'genericParameterConstraintsOffset',
                'genericParameterConstraintsSize', 'genericContainersOffset', 'genericContainersSize',
                'nestedTypesOffset', 'nestedTypesSize', 'interfacesOffset', 'interfacesSize',
                'vtableMethodsOffset', 'vtableMethodsSize', 'interfaceOffsetsOffset', 'interfaceOffsetsSize',
                'typeDefinitionsOffset', 'typeDefinitionsSize', 'imagesOffset', 'imagesSize',
                'assembliesOffset', 'assembliesSize', 'fieldRefsOffset', 'fieldRefsSize',
                'referencedAssembliesOffset', 'referencedAssembliesSize', 'attributeDataOffset', 'attributeDataSize',
                'attributeDataRangeOffset', 'attributeDataRangeSize']

WANT_CLASSES = ['UnityEngine.GameObject', 'UnityEngine.Object', 'UnityEngine.Transform', 'UnityEngine.RectTransform',
                'UnityEngine.Component', 'UnityEngine.Behaviour', 'UnityEngine.Canvas', 'UnityEngine.CanvasGroup',
                'UnityEngine.CanvasRenderer', 'UnityEngine.UI.Button', 'UnityEngine.UI.Selectable',
                'UnityEngine.UI.Graphic', 'TMPro.TMP_Text', 'TMPro.TextMeshProUGUI']


def sh(cmd):
    return subprocess.run(ADB + [cmd], capture_output=True, text=True).stdout


def parse_maps(pid):
    out = sh(f'su -c "cat /proc/{pid}/maps"')
    meta = None
    for line in out.splitlines():
        if 'global-metadata.dat' in line and ' rw-p ' in line:
            meta = int(line.split('-')[0], 16)
    return meta


def parse_header(head_bytes):
    """head_bytes: 前 0x110 字节。尝试两种槽位对齐，返回 (header dict, shift)。"""
    vals = struct.unpack_from('<' + 'I' * 66, head_bytes, 0)
    assert vals[0] == 0xFAB11BAF
    for shift in (0, 1, 2, 3):
        idx = 2 + shift  # 跳过 sanity+version
        pairs = vals[idx: idx + len(HEADER_NAMES)]
        if len(pairs) < len(HEADER_NAMES):
            break
        H = dict(zip(HEADER_NAMES, pairs))
        # 一致性：相邻区域 [off, off+size) 首尾相接（对 size>0 的项）
        order = HEADER_NAMES
        ok = 0, 0
        bad = 0
        for i in range(0, len(order) - 2, 2):
            a, sa, b = H[order[i]], H[order[i + 1]], H[order[i + 2]]
            if sa == 0:
                continue
            if a + sa == b:
                ok = ok[0] + 1, ok[1]
            else:
                bad += 1
        if bad == 0 and H['typeDefinitionsSize'] % 0x58 == 0:
            return H, shift
    return None, None


def read_meta_strings(H, data):
    def getstr(idx):
        start = H['stringOffset'] + idx
        end = data.index(b'\x00', start)
        return data[start:end].decode('utf-8', 'replace')

    td_off, td_size = H['typeDefinitionsOffset'], H['typeDefinitionsSize']
    fmt = '<IIiiiiiIiiiiiiii8HII'
    assert struct.calcsize(fmt) == 0x58
    result = {}
    for i in range(td_size // 0x58):
        o = td_off + i * 0x58
        vals = struct.unpack_from(fmt, data, o)
        name_idx, ns_idx = vals[0], vals[1]
        field_start, f_cnt = vals[8], vals[18]
        name, ns = getstr(name_idx), getstr(ns_idx)
        result[f'{ns}.{name}'] = {'idx': i, 'name_idx': name_idx, 'ns_idx': ns_idx,
                                  'field_start': field_start, 'field_count': f_cnt, 'token': vals[25]}
    return result


def main():
    dev = get_device()
    proc = find_game(dev)
    pid = proc.pid
    meta = parse_maps(pid)
    print(f'pid={pid} meta_base={hex(meta)}')

    # 1. 从内存读 header
    session = dev.attach(pid)
    out = {}
    s1 = session.create_script(f'''
const mb = ptr('{hex(meta)}');
send({{ head: Array.from(new Uint8Array(mb.readByteArray(0x110))).map(x => x.toString(16).padStart(2, '0')).join(' ') }});
''')
    s1.on('message', lambda m, d: out.update(m.get('payload', {})) if m['type'] == 'send' else print('[e1]', str(m)[:150]))
    s1.load()
    time.sleep(3)
    head = bytes(int(x, 16) for x in out['head'].split())
    H, shift = parse_header(head)
    if not H:
        print('header parse failed (no consistent alignment)')
        return
    print(f'header ok, shift={shift}, stringOffset={hex(H["stringOffset"])} td={hex(H["typeDefinitionsOffset"])}')

    # 2. dump 内存元数据（解密后）到本地，解析类型
    dump_size = 28305260  # 映射大小可能略不同，用 maps 实际值
    maps_out = sh(f'su -c "cat /proc/{pid}/maps"')
    for line in maps_out.splitlines():
        if 'global-metadata.dat' in line and ' rw-p ' in line:
            a, b = line.split()[0].split('-')
            dump_size = int(b, 16) - int(a, 16)
    print('meta size:', dump_size)
    data = bytearray()
    s2 = session.create_script(f'''
const mb = ptr('{hex(meta)}');
const CHUNK = 0x100000;
for (let off = 0; off < {dump_size}; off += CHUNK) {{
    const n = Math.min(CHUNK, {dump_size} - off);
    send({{ off: off }}, mb.add(off).readByteArray(n));
}}
send({{ done: true }});
''')
    s2.on('message', lambda m, d: (data.extend(d), print('chunk', len(data))) if (m['type'] == 'send' and d) else None)
    s2.load()
    t0 = time.time()
    while len(data) < dump_size and time.time() - t0 < 60:
        time.sleep(0.5)
    data = bytes(data)
    open(f'meta_{pid}.bin', 'wb').write(data)
    print('metadata dumped:', len(data))

    types = read_meta_strings(H, data)
    print('types parsed:', len(types))

    # 3. 计算目标类的 name/ns 绝对指针
    anchors = {}
    for cn in WANT_CLASSES:
        t = types.get(cn)
        if not t:
            print('MISSING', cn)
            continue
        anchors[cn] = {
            'name_ptr': meta + H['stringOffset'] + t['name_idx'],
            'ns_ptr': meta + H['stringOffset'] + t['ns_idx'],
            'token': t['token'],
        }
    print('anchors:', json.dumps({k: [hex(v['name_ptr']), hex(v['ns_ptr'])] for k, v in anchors.items()}, indent=0))

    # 4. agent 内扫描定位 klass（每个类一个 name-ptr 单值扫描，合并成多 pattern）
    anchors_js = json.dumps({k: {'name': hex(v['name_ptr']), 'ns': hex(v['ns_ptr'])} for k, v in anchors.items()})
    s3 = session.create_script(f'''
const anchors = {anchors_js};
// 一次遍历：收集所有指向任何 name_ptr 的 qword
const patterns = [];
const nameToClass = {{}};
for (const [cn, a] of Object.entries(anchors)) {{
    const hexs = a.name.slice(2).padStart(16, '0');
    patterns.push(hexs.match(/../g).reverse().join(' '));
    nameToClass[hexs.match(/../g).reverse().join(' ')] = cn;
}}
const ranges = Process.enumerateRangesSync('rw-').filter(r => !r.file && r.size >= 0x8000 && r.size <= 512*1024*1024);
console.log('ranges:', ranges.length);
const klasses = {{}};
const METALO = ptr('{hex(meta)}'), METAHI = ptr('{hex(meta + dump_size)}');
for (const r of ranges) {{
    for (const pat of patterns) {{
        let hits = [];
        try {{ hits = Memory.scanSync(r.base, r.size, pat); }} catch (e) {{ continue; }}
        for (const h of hits) {{
            try {{
                const nsPtr = h.add(8).readPointer();
                const cls = nameToClass[pat];
                const wantNs = ptr(anchors[cls].ns);
                if (nsPtr.equals(wantNs)) {{
                    klasses[cls] = String(h.sub(0x10));
                }}
            }} catch (e) {{ }}
        }}
    }}
}}
send({{ klasses: klasses }});
''')
    out3 = {}
    s3.on('message', lambda m, d: out3.update(m.get('payload', {})) if m['type'] == 'send' else print('[e3]', str(m)[:150]))
    s3.load()
    t0 = time.time()
    while 'klasses' not in out3 and time.time() - t0 < 300:
        time.sleep(2)
    klasses = out3.get('klasses', {})
    print('klasses found:', json.dumps(klasses, indent=1))
    json.dump({'H': H, 'shift': shift, 'klasses': klasses, 'meta_base': meta, 'meta_size': dump_size, 'pid': pid},
              open(f'bootstrap_mem_{pid}.json', 'w'), indent=1)
    session.detach()
    print('saved')


if __name__ == '__main__':
    main()
