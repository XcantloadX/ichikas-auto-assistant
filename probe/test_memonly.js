// 实验 21：纯内存定位 Il2CppClass + dump 原始结构
'use strict';

// 1) 扫描所有 rw 内存找字符串 "GameObject\0" 的实例
const ranges = Process.enumerateRangesSync('rw-').filter(r => r.size <= 512 * 1024 * 1024);
console.log('rw ranges:', ranges.length);

function scanAll(pattern, limit) {
    const hits = [];
    for (const r of ranges) {
        try {
            const m = Memory.scanSync(r.base, r.size, pattern);
            for (const h of m) hits.push(h.address);
        } catch (e) { }
        if (hits.length >= limit) break;
    }
    return hits;
}

const goStrPattern = '47 61 6d 65 4f 62 6a 65 63 74 00'; // "GameObject\0"
const goStrs = scanAll(goStrPattern, 50);
console.log('"GameObject" string instances:', goStrs.length);
send({ goStrs: goStrs.map(String) });

// 2) 对每个字符串地址，找指向它的 qword，并检查 +8 是否指向 "UnityEngine\0"
const unStrPattern = '55 6e 69 74 79 45 6e 67 69 6e 65 00'; // "UnityEngine\0"
const unStrs = scanAll(unStrPattern, 50);
const unSet = new Set(unStrs.map(String));
console.log('"UnityEngine" instances:', unStrs.length);

const klassCandidates = [];
for (const sa of goStrs) {
    // 扫描指向该字符串的指针：限定在 rw 段（klass 都在堆/数据段）
    const pat = sa.toString(16).replace(/^0x/, '').padStart(16, '0').match(/../g).reverse().join(' ');
    for (const r of ranges) {
        try {
            const m = Memory.scanSync(r.base, r.size, pat);
            for (const h of m) {
                // h 是存有字符串指针的位置；klass->name 应在 klass+0x10 → klass = h - 0x10
                try {
                    const ns = h.add(8).readPointer();
                    if (unSet.has(String(ns))) {
                        klassCandidates.push({ klass: String(h.sub(0x10)), nameAt: String(h) });
                    }
                } catch (e) { }
            }
        } catch (e) { }
        if (klassCandidates.length > 20) break;
    }
}
console.log('klass candidates:', klassCandidates.length);
klassCandidates.slice(0, 5).forEach(k => console.log('  ', JSON.stringify(k)));
send({ klassCandidates: klassCandidates });

// 3) dump GameObject klass 的原始 0x140 字节
if (klassCandidates.length > 0) {
    const k = ptr(klassCandidates[0].klass);
    const dump = k.readByteArray(0x140);
    send({ klassDump: Array.from(new Uint8Array(dump)).map(b => b.toString(16).padStart(2, '0')).join(' ') });
    console.log('klass dumped');
}
