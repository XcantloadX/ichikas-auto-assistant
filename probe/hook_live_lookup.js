// 实验 30：在 lookup 内部（lea r12 之后、cmp flag 之前）抓真实 r12/rbp
'use strict';
const itf = Process.findModuleByName('libhoudini.so').getExportByName('NativeBridgeItf');
const pGetTrampoline = itf.add(24).readPointer();
const getTrampolineFn = new NativeFunction(pGetTrampoline, 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
const t = getTrampolineFn(ptr(0), Memory.allocUtf8String('il2cpp_domain_get'), Memory.allocUtf8String('L'), 1, 0);
const arr = Array.from(new Uint8Array(t.readByteArray(24)));
function rd(off) { let v = 0n; for (let k = off + 7; k >= off; k--) v = (v << 8n) | BigInt(arr[k]); return v; }
const gw = ptr('0x' + rd(12).toString(16));
const myTicket = rd(2);
// 解析 lookup（同前链路）
const gwb = Array.from(new Uint8Array(gw.readByteArray(0x60)));
function callTarget(addr, off) {
    const b = Array.from(new Uint8Array(addr.add(off).readByteArray(5)));
    let rel = b[1] | (b[2] << 8) | (b[3] << 16) | (b[4] << 24);
    if (rel > 0x7fffffff) rel -= 0x100000000;
    return addr.add(off + 5 + rel);
}
let resolver = null;
for (let off = 0x30; off < 0x50; off++) if (gwb[off] === 0xe8) { resolver = callTarget(gw, off); break; }
const resb = Array.from(new Uint8Array(resolver.readByteArray(0x40)));
let lookup = null;
for (let off = 0x20; off < 0x38; off++) if (resb[off] === 0xe8) { lookup = callTarget(resolver, off); break; }
console.log('lookup:', lookup, 'myTicket:', myTicket.toString(16));
// 在 lookup+0x3c（cmp flag 前）挂点
const probeAt = lookup.add(0x3c);
const seen = {};
Interceptor.attach(probeAt, {
    onEnter: function () {
        const r12 = this.context.r12.toString(16);
        const rbp = Number(this.context.rbp.toString());
        const ticket = Math.floor(rbp / 16512);
        const key = r12.slice(-6) + '/t' + ticket.toString(16);
        seen[key] = (seen[key] || 0) + 1;
    }
});
// 我们的调用每 2s 一次
const dg = new NativeFunction(t, 'pointer', []);
let pingOk = 0, pingFail = 0;
const iv = setInterval(function () {
    try { dg(); pingOk++; } catch (e) { pingFail++; }
}, 2000);
setTimeout(function () {
    clearInterval(iv);
    const summary = { myTicket: '0x' + myTicket.toString(16), pingOk: pingOk, pingFail: pingFail, seen: seen };
    console.log(JSON.stringify(summary, null, 1));
    send(summary);
}, 12000);
