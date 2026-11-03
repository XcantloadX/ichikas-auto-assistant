// 实验 27：纯内存引导 v1 —— klass 定位 + 相邻行走建类表
'use strict';

// 宿主机注入参数
const META_BASE = ptr(__META_BASE__);
const GO_STRS = __GO_STRS__;     // metadata 内 "GameObject\0" 地址
const UN_STRS = __UN_STRS__;     // "UnityEngine\0"

function readMetaStr(p) {
    try {
        // metadata 字符串区域安全读取（限制长度）
        return p.readCString(64);
    } catch (e) { return null; }
}

// 1) 定位 GameObject klass：扫 anon rw 中指向 "UnityEngine" 字符串的 qword
const unAddr = ptr(UN_STRS[0]);
const goSet = new Set(GO_STRS);
const pat = (() => {
    const hex = UN_STRS[0].slice(2).padStart(16, '0');
    return hex.match(/../g).reverse().join(' ');
})();

const ranges = Process.enumerateRangesSync('rw-').filter(r => !r.file && r.size >= 0x10000);
console.log('scanning', ranges.length, 'anon ranges');
let klass = null;
for (const r of ranges) {
    let hits = [];
    try { hits = Memory.scanSync(r.base, r.size, pat); } catch (e) { continue; }
    for (const h of hits) {
        try {
            const namePtr = h.sub(8).readPointer();
            if (goSet.has(String(namePtr))) { klass = h.sub(0x18); break; }
        } catch (e) { }
    }
    if (klass) break;
}
console.log('GameObject klass:', klass);
send({ klass: String(klass) });

// 2) 以 0x180 步进行走，读 name/ns 建表
function tryKlass(k) {
    try {
        const namePtr = k.add(0x10).readPointer();
        const nsPtr = k.add(0x18).readPointer();
        // 都必须落在 metadata 映射内
        const inMeta = (p) => p.compare(META_BASE) >= 0 && p.compare(META_BASE.add(28305260)) < 0;
        if (!inMeta(namePtr) || !inMeta(nsPtr)) return null;
        const name = readMetaStr(namePtr), ns = readMetaStr(nsPtr);
        if (!name || !/^[A-Za-z_`][A-Za-z0-9_.`<>+\[\]]*$/.test(name)) return null;
        if (!ns || !/^[A-Za-z0-9_.]+$/.test(ns)) return null;
        // token 在 0x118-0x120 附近应为 0x02xxxxxx
        return { name: name, ns: ns };
    } catch (e) { return null; }
}

const table = {};
if (klass) {
    for (let delta = -0x180 * 40; delta <= 0x180 * 120; delta += 0x180) {
        const k = klass.add(delta);
        const info = tryKlass(k);
        if (info) {
            const key = info.ns + '.' + info.name;
            table[key] = '0x' + delta.toString(16); // 相对 GameObject 的偏移
        }
    }
}
console.log('walked classes:', Object.keys(table).length);
const interesting = Object.entries(table).filter(([k]) => /GameObject|Transform|Component|Canvas|Button|Text|RectTransform|Behaviour|Object|Renderer|Image/.test(k));
console.log(JSON.stringify(interesting, null, 1));
send({ tableCount: Object.keys(table).length, table: table });
