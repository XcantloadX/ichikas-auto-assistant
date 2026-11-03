// 实验 22：单遍扫描定位 GameObject klass（内存只读）
'use strict';

// 宿主机注入的字符串地址集合
const GO_ADDRS = __GO_ADDRS__;   // ["0x...", ...]
const UN_ADDRS = __UN_ADDRS__;

const goSet = new Set(GO_ADDRS);
const unSet = new Set(UN_ADDRS);
const strAddrs = new Set([...GO_ADDRS, ...UN_ADDRS]);

const ranges = Process.enumerateRangesSync('rw-').filter(r => !r.file && r.size >= 0x10000);
console.log('anon rw ranges:', ranges.length, 'total', (ranges.reduce((a, r) => a + r.size, 0) / 1048576).toFixed(0), 'MB');

const candidates = [];
const CHUNK = 0x800000; // 8MB
for (const r of ranges) {
    for (let off = 0; off < r.size; off += CHUNK - 0x10) {
        const n = Math.min(CHUNK, r.size - off);
        let buf;
        try { buf = r.base.add(off).readByteArray(n); } catch (e) { continue; }
        const dv = new DataView(buf);
        const baseAddr = Number(r.base.add(off));
        // 每 8 字节检查：val 在字符串集合内，且下一个 qword 也在集合内且属于另一集合
        for (let i = 0; i + 16 <= n; i += 8) {
            const lo = dv.getUint32(i, true), hi = dv.getUint32(i + 4, true);
            if (hi !== 0x788e) continue; // metadata mapping 在 0x788e9e...
            const addrStr = '0x' + (hi * 4294967296 + lo).toString(16);
            if (!strAddrs.has(addrStr)) continue;
            const lo2 = dv.getUint32(i + 8, true), hi2 = dv.getUint32(i + 12, true);
            if (hi2 !== 0x788e) continue;
            const addr2 = '0x' + (hi2 * 4294967296 + lo2).toString(16);
            const isFirstGo = goSet.has(addrStr), isSecondUn = unSet.has(addr2);
            if (isFirstGo && isSecondUn) {
                candidates.push({ klass: '0x' + (baseAddr + i - 0x10).toString(16), nameAt: addrStr });
            }
        }
    }
    if (candidates.length > 50) break;
}
console.log('klass candidates:', candidates.length);
candidates.slice(0, 10).forEach(c => console.log('  ', JSON.stringify(c)));
send({ candidates: candidates });

// dump 第一个 klass 的 0x140 字节
if (candidates.length > 0) {
    const k = ptr(candidates[0].klass);
    const dump = k.readByteArray(0x140);
    send({ klassDump: Array.from(new Uint8Array(dump)).map(b => b.toString(16).padStart(2, '0')).join(' ') });
}
