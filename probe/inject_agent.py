"""通过 frida Java 层把 iaa_agent.so 注入游戏（System.load 合法路径）"""
import sys
import time

sys.path.insert(0, '.')
from harness import get_device, find_game

JS = open('D:/tmp_iaa_npm/javaloader.js', encoding='utf-8').read()


def main():
    so_path = sys.argv[1] if len(sys.argv) > 1 else '/data/local/tmp/iaa_agent.so'
    dev = get_device()
    proc = find_game(dev)
    print('game pid:', proc.pid)
    session = dev.attach(proc.pid)
    sc = session.create_script(JS)
    sc.on('message', lambda m, d: print('[msg]', m) if m['type'] == 'error' else None)
    sc.load()
    r = sc.exports_sync.load(so_path)
    print('System.load:', r)
    time.sleep(2)
    session.detach()


if __name__ == '__main__':
    main()
