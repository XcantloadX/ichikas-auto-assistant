// 实验 10：直接调 libnb 内部 resolver(idx) 拿函数表
'use strict';

const NB_BASE = ptr('0x788f65b83000'); // libnb.so base (当前进程，需验证)
const IL2CPP_PATH = '/data/app/~~_AKbb6cXWFMNLiugNkCZ2g==/com.sega.pjsekai-iMjlP6Bt2jE7PmZPtB4dKA==/lib/arm64/libil2cpp.so';

// 验证 libnb base
const nb = Process.getModuleByName('libnb.so');
console.log('libnb:', nb.base, nb.size);
const itf = Module.getExportByName('libnb.so', 'NativeBridgeItf');
console.log('NativeBridgeItf =', itf);

const resolver = nb.base.add(0x22d0);
const resolv = new NativeFunction(resolver, 'pointer', ['int']);
for (const idx of [1, 2, 3, 4, 5]) {
    let t = null, err = null;
    try { t = resolv(idx); } catch (e) { err = String(e); }
    console.log('resolver(' + idx + ') =', t, err || '');
    if (t && !t.isNull()) {
        const entries = [];
        for (let k = 0; k < 0x40; k += 8) {
            entries.push(k + ': ' + t.add(k).readPointer());
        }
        console.log(entries.join(' | '));
        send({ idx: idx, table: String(t), entries: entries });
    }
}
