// 实验 12：全进程扫描 "libil2cpp" 字符串，定位 houdini 注册表
'use strict';

const pattern = '6c 69 62 69 6c 32 63 70 70'; // "libil2cpp"
const ranges = Process.enumerateRangesSync('rw-');
console.log('rw ranges:', ranges.length);

let hits = [];
let scanned = 0;
for (const r of ranges) {
    // 跳过超大匿名堆以外的区域不必要；直接全扫，但限制单次 range 大小 <= 512MB
    if (r.size > 512 * 1024 * 1024) continue;
    try {
        const matches = Memory.scanSync(r.base, r.size, pattern);
        for (const m of matches) {
            hits.push(m.address);
        }
    } catch (e) { }
    scanned += r.size;
    if (hits.length > 200) break;
}
console.log('scanned bytes ~', scanned, 'hits:', hits.length);
send({ count: hits.length });

// 对每个命中读取周围 96 字符
const report = [];
for (const h of hits.slice(0, 60)) {
    try {
        const s = h.sub(0).readCString(160);
        report.push(String(h) + ' | ' + s.replace(/[^\x20-\x7e]/g, '.'));
    } catch (e) { }
}
console.log(report.join('\n'));
send({ report: report });
