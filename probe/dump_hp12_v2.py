"""dump libhp12 全部映射段"""
import time

from harness import get_device, find_game

js = '''
const ranges = Process.enumerateRangesSync('r--')
    .concat(Process.enumerateRangesSync('rw-'))
    .concat(Process.enumerateRangesSync('r-x'))
    .filter(function (r) {
        return r.file && r.file.path && r.file.path.indexOf('libhp12') !== -1;
    });
send({ count: ranges.length });
ranges.forEach(function (r, i) {
    console.log('range', i, r.base, r.size, r.protection);
});
// 逐段分块发送
for (let i = 0; i < ranges.length; i++) {
    const r = ranges[i];
    const CHUNK = 0x40000;
    for (let off = 0; off < r.size; off += CHUNK) {
        const n = Math.min(CHUNK, r.size - off);
        send({ idx: i, base: String(r.base), off: off, size: n }, r.base.add(off).readByteArray(n));
    }
}
send({ done: true });
'''

def main():
    dev = get_device()
    proc = find_game(dev)
    session = dev.attach(proc.pid)
    parts = {}

    def on_message(message, data_bytes):
        if message['type'] == 'send':
            p = message['payload']
            if 'idx' in p and data_bytes:
                parts.setdefault(p['idx'], {'base': int(p['base'], 16), 'chunks': {}})
                parts[p['idx']]['chunks'][p['off']] = data_bytes
            elif 'count' in p:
                print('ranges:', p['count'])
        elif message['type'] == 'error':
            print('[error]', message.get('stack', message))

    sc = session.create_script(js)
    sc.on('message', on_message)
    sc.load()
    time.sleep(10)
    import json
    meta = {}
    for idx, info in sorted(parts.items()):
        buf = bytearray()
        for off in sorted(info['chunks']):
            buf.extend(info['chunks'][off])
        fn = f'hp12_range_{idx}_{info["base"]:x}.bin'
        with open(fn, 'wb') as f:
            f.write(bytes(buf))
        meta[fn] = {'base': hex(info['base']), 'size': len(buf)}
        print('saved', fn, hex(info['base']), len(buf))
    with open('probe/hp12_meta.json', 'w') as f:
        json.dump(meta, f)
    session.detach()

if __name__ == '__main__':
    main()
