// 实验 9：在 houdini 数据段找已加载 guest 库的注册表（含 handle token）
'use strict';

const H_BASE = ptr('0x788f4def2000');
const H_END = H_BASE.add(0x8D6000);

// 1) 枚举 houdini 的 rw 段
const rwRanges = Process.enumerateRangesSync('rw-').filter(r =>
    r.base.compare(H_BASE) >= 0 && r.base.add(r.size).compare(H_END) <= 0);
console.log('houdini rw ranges:', rwRanges.map(r => r.base + ' ' + r.size).join(', '));

// 2) 在其中搜索 "libil2cpp.so" 字符串
let hits = [];
for (const r of rwRanges) {
    try {
        const matches = Memory.scanSync(r.base, r.size, '6c 69 62 69 6c 32 63 70 70 2e 73 6f'); // "libil2cpp.so"
        hits = hits.concat(matches.map(m => m.address));
    } catch (e) { }
}
console.log('libil2cpp.so string hits:', hits.map(String).join(', '));
send({ hits: hits.map(String) });

// 3) dump 命中点周围内存，寻找结构（路径指针、handle 等）
for (const h of hits.slice(0, 8)) {
    try {
        const start = h.sub(0x40);
        const before = start.readCString(0x80);
        console.log('--- around', h);
        console.log(before.replace(/[^\x20-\x7e]/g, '.'));
        // 打印前后各 8 个指针
        const ptrs = [];
        for (let k = -0x40; k < 0x40; k += 8) {
            try { ptrs.push(k + ':' + h.add(k).readPointer()); } catch (e) { ptrs.push(k + ':?'); }
        }
        console.log(ptrs.join(' '));
        send({ around: String(h), ptrs: ptrs });
    } catch (e) {
        console.log('read fail at', h, e);
    }
}
