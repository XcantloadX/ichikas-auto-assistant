"""dump libhp12 内存到 probe/libhp12_mem.so"""
import time

from probe.harness import get_device, find_game

js = '''
const base = ptr('0x788f50611000');
const size = 1105920;
const buf = base.readByteArray(size);
const u8 = new Uint8Array(buf);
const CHUNK = 0x40000;
for (let off = 0; off < size; off += CHUNK) {
    send({ part: off, total: size }, u8.slice(off, Math.min(off + CHUNK, size)).buffer);
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
            if 'part' in p:
                data.extend(data_bytes)
        elif message['type'] == 'error':
            print('[error]', message)

    sc = session.create_script(js)
    sc.on('message', on_message)
    sc.load()
    time.sleep(6)
    with open('probe/libhp12_mem.so', 'wb') as f:
        f.write(bytes(data))
    print('saved', len(data))
    session.detach()

if __name__ == '__main__':
    main()
