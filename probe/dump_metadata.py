"""从进程内存 dump 解密后的 global-metadata.dat"""
import time

from harness import get_device, find_game

META_BASE = '0x788e9e501000'
META_SIZE = 28305260

js_tpl = '''
const base = ptr('__META_BASE__');
const size = __META_SIZE__;
const CHUNK = 0x100000;
for (let off = 0; off < size; off += CHUNK) {
    const n = Math.min(CHUNK, size - off);
    send({ off: off }, base.add(off).readByteArray(n));
}
send({ done: true });
'''

def main():
    dev = get_device()
    proc = find_game(dev)
    session = dev.attach(proc.pid)
    data = bytearray()

    def on_message(message, data_bytes):
        if message['type'] == 'send':
            p = message['payload']
            if 'off' in p and data_bytes:
                expected = p['off']
                if len(data) != expected:
                    raise RuntimeError(f'chunk mismatch at {expected} (have {len(data)})')
                data.extend(data_bytes)
            elif p.get('done'):
                print('done')
        elif message['type'] == 'error':
            print('[error]', message.get('stack', message))

    sc = session.create_script(js_tpl.replace('__META_BASE__', META_BASE).replace('__META_SIZE__', str(META_SIZE)))
    sc.on('message', on_message)
    sc.load()
    t0 = time.time()
    while len(data) < META_SIZE and time.time() - t0 < 120:
        time.sleep(0.5)
    with open('global-metadata.mem', 'wb') as f:
        f.write(bytes(data))
    print('saved', len(data), 'bytes in', round(time.time() - t0, 1), 's')
    session.detach()

if __name__ == '__main__':
    main()
