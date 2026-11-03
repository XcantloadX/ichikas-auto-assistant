// 实验 13：扫描指向 "libil2cpp.so" 字符串的指针 & libil2cpp 基址值，找注册表
'use strict';

const LIB_BASE = ptr('0x788f30d0b000'); // 当前进程 libil2cpp guest 基址
const ranges = Process.enumerateRangesSync('rw-');
console.log('rw ranges:', ranges.length);

// 先找字符串实例（限制在扫描时顺带做太多；直接扫基址值 + 字符串指针分两轮）
// 轮 1：扫描 LIB_BASE 这个 8 字节值
const patternBase = LIB_BASE.toString(16).replace(/(..)/g, '$1 ').trim().split(' ').reverse().join(' ');
console.log('base pattern:', patternBase);

let hitsBase = [];
for (const r of ranges) {
    if (r.size > 512 * 1024 * 1024) continue;
    try {
        const m = Memory.scanSync(r.base, r.size, patternBase);
        hitsBase = hitsBase.concat(m.map(x => x.address));
    } catch (e) { }
    if (hitsBase.length > 100) break;
}
console.log('base value hits:', hitsBase.length);
send({ hitsBase: hitsBase.map(String) });

// 轮 2：扫描指向之前找到的字符串实例的指针
const strAddrs = ['0x788f1001ca79', '0x788f50750a3c', '0x788f50751afe', '0x788f5076c8c6'];
for (const sa of strAddrs) {
    const p = ptr(sa);
    const pat = p.toString(16).replace(/(..)/g, '$1 ').trim().split(' ').reverse().join(' ');
    let hits = [];
    for (const r of ranges) {
        if (r.size > 512 * 1024 * 1024) continue;
        try {
            const m = Memory.scanSync(r.base, r.size, pat);
            hits = hits.concat(m.map(x => x.address));
        } catch (e) { }
        if (hits.length > 50) break;
    }
    console.log('ptrs to', sa, ':', hits.length);
    for (const h of hits.slice(0, 10)) {
        // dump 周围 64 字节
        try {
            const start = h.sub(0x20);
            const vals = [];
            for (let k = 0; k < 8; k++) {
                vals.push(start.add(k * 8).readPointer().toString());
            }
            console.log('  @' + h + ': ' + vals.join(' '));
            send({ near: String(h), vals: vals });
        } catch (e) { }
    }
}
