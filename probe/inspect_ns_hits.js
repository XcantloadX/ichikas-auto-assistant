'use strict';
// 检查 ns 指针命中的 [hit-8] 到底指向什么
const META_LO = ptr('0x788f219a3000'), META_HI = META_LO.add(0x1C00000);
const ranges = Process.enumerateRangesSync('rw-').filter(r => !r.file && r.size >= 0x4000 && r.size <= 512 * 1024 * 1024);
// metadata 中的 "UnityEngine\0"（唯一）
const unHits = Memory.scanSync(META_LO, 0x1C00000, '55 6e 69 74 79 45 6e 67 69 6e 65 00');
console.log('meta un instances:', unHits.map(h => String(h.address)).join(','));
const samples = [];
let total = 0;
for (const r of ranges) {
    for (const uh of unHits) {
        const hex = String(uh.address).slice(2).padStart(16, '0');
        const pat = hex.match(/../g).reverse().join(' ');
        let hits = [];
        try { hits = Memory.scanSync(r.base, r.size, pat); } catch (e) { continue; }
        for (const h of hits) {
            total++;
            if (samples.length < 20) {
                try {
                    const namePtr = h.sub(8).readPointer();
                    let s = null;
                    try { s = namePtr.readCString(24); } catch (e) { }
                    const inMeta = namePtr.compare(META_LO) >= 0 && namePtr.compare(META_HI) < 0;
                    samples.push({ at: String(h), namePtr: String(namePtr), inMeta: inMeta, name: s ? JSON.stringify(s.slice(0, 18)) : null });
                } catch (e) { }
            }
        }
    }
    if (total > 2000) break;
}
console.log('total ns-ptr hits:', total);
samples.forEach(s => console.log(JSON.stringify(s)));
send({ total: total, samples: samples });
