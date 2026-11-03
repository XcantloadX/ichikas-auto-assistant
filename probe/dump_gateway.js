'use strict';
// 1) 造一个 trampoline 拿 gateway 地址
const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const pGetTrampoline = itf.add(24).readPointer();
const getTrampolineFn = new NativeFunction(pGetTrampoline, 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
const t = getTrampolineFn(ptr(0), Memory.allocUtf8String('il2cpp_domain_get'), Memory.allocUtf8String('L'), 1, 0);
console.log('tramp:', t);
if (t.isNull()) throw new Error('no tramp');
const bytes = t.readByteArray(32);
const arr = Array.from(new Uint8Array(bytes));
console.log('tramp bytes:', arr.map(b => b.toString(16).padStart(2, '0')).join(' '));
// movabs r11, imm64: 49 bb <8 bytes>
let gw = null;
for (let i = 0; i < 16; i++) {
    if (arr[i] === 0x49 && arr[i + 1] === 0xbb) {
        const lo = arr.slice(i + 2, i + 10);
        let v = 0n;
        for (let k = 7; k >= 0; k--) v = (v << 8n) | BigInt(lo[k]);
        gw = '0x' + v.toString(16);
        break;
    }
}
console.log('gateway:', gw);
send({ tramp: String(t), gateway: gw });

// 2) dump gateway 前后代码
if (gw) {
    const g = ptr(gw);
    const dump = g.readByteArray(512);
    send({ gwBytes: Array.from(new Uint8Array(dump)).map(x => x.toString(16).padStart(2, '0')).join(' ') });
    // 也 dump gateway 前一页找关联数据
}
