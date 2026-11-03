// 实验 29：hook lookup(gateway-resolver 链)，对比成功/失败调用的返回地址
// 偏移关系（同版本 libhoudini.so 恒定）：resolver = gateway - 0x3DBC; lookup = resolver - 0x1080
'use strict';

const itf = getExportH('libhoudini.so', 'NativeBridgeItf');
function getExportH(modName, exportName) {
    if (typeof Module.getExportByName === 'function') {
        try { return Module.getExportByName(modName, exportName); } catch (e) { }
    }
    const m = Process.findModuleByName(modName);
    if (m) return m.getExportByName(exportName);
    throw new Error('no export');
}

const pGetTrampoline = itf.add(24).readPointer();
const getTrampolineFn = new NativeFunction(pGetTrampoline, 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
const t = getTrampolineFn(ptr(0), Memory.allocUtf8String('il2cpp_domain_get'), Memory.allocUtf8String('L'), 1, 0);
if (t.isNull()) throw new Error('no tramp');
const arr = Array.from(new Uint8Array(t.readByteArray(24)));
function readU64(bytes, off) {
    let v = 0n;
    for (let k = off + 7; k >= off; k--) v = (v << 8n) | BigInt(bytes[k]);
    return v;
}
let gw = null, ticket = null;
for (let i = 0; i < 16; i++) {
    if (arr[i] === 0x48 && arr[i + 1] === 0xb8) ticket = '0x' + readU64(arr, i + 2).toString(16);
    if (arr[i] === 0x49 && arr[i + 1] === 0xbb) gw = ptr('0x' + readU64(arr, i + 2).toString(16));
}
// 动态解析: gateway+0x2d 处 e8 → resolver; resolver 内首个 e8（+0x2a 附近）→ lookup
function callTarget(addr, off) {
    const b = Array.from(new Uint8Array(addr.add(off).readByteArray(5)));
    if (b[0] !== 0xe8) throw new Error('no call at ' + addr.add(off));
    let rel = b[1] | (b[2] << 8) | (b[3] << 16) | (b[4] << 24);
    if (rel > 0x7fffffff) rel -= 0x100000000;
    return addr.add(off + 5 + rel);
}
const gwb = Array.from(new Uint8Array(gw.readByteArray(0x60)));
// 找 gateway 内第一个 call（跳过序言：在 0x30-0x50 范围找 0xe8）
let resolver = null;
for (let off = 0x30; off < 0x50; off++) {
    if (gwb[off] === 0xe8) { resolver = callTarget(gw, off); break; }
}
console.log('resolver:', resolver);
const resb = Array.from(new Uint8Array(resolver.readByteArray(0x40)));
let lookup = null;
for (let off = 0x20; off < 0x38; off++) {
    if (resb[off] === 0xe8) { lookup = callTarget(resolver, off); break; }
}
console.log('lookup:', lookup);
send({ gw: String(gw), resolver: String(resolver), lookup: String(lookup), ticket: ticket });

// 统计容器
const stats = { lookupCalls: 0, ok: 0, fail: 0, retAddrsOk: {}, retAddrsFail: {}, ticketsFail: {} };

Interceptor.attach(lookup, {
    onEnter: function (args) {
        this.ticket = args[0].toInt32();
        this.ret = this.returnAddress;
    },
    onLeave: function (retval) {
        stats.lookupCalls++;
        const ok = retval.toInt32() !== 0;
        const ra = this.ret.toString();
        if (ok) { stats.ok++; stats.retAddrsOk[ra] = (stats.retAddrsOk[ra] || 0) + 1; }
        else {
            stats.fail++;
            stats.retAddrsFail[ra] = (stats.retAddrsFail[ra] || 0) + 1;
            const tk = '0x' + this.ticket.toString(16);
            stats.ticketsFail[tk] = (stats.ticketsFail[tk] || 0) + 1;
        }
    }
});

// 我们的调用：每 2s ping 一次，共 6 次（预期失败）
const dg = new NativeFunction(t, 'pointer', []);
let pingOk = 0, pingFail = 0;
const iv = setInterval(function () {
    try { dg(); pingOk++; send({ ping: 'ok' }); }
    catch (e) { pingFail++; }
}, 2000);
setTimeout(function () {
    clearInterval(iv);
    // 归属返回地址到模块
    function mod(a) {
        try {
            const r = Process.findRangeByAddress(ptr(a));
            return r && r.file ? r.file.path.split('/').pop() : 'anon@' + a;
        } catch (e) { return '?'; }
    }
    const summary = {
        lookupCalls: stats.lookupCalls, ok: stats.ok, fail: stats.fail,
        pingOk: pingOk, pingFail: pingFail,
        okRet: Object.fromEntries(Object.entries(stats.retAddrsOk).map(([k, v]) => [mod(k) + '|' + k, v])),
        failRet: Object.fromEntries(Object.entries(stats.retAddrsFail).map(([k, v]) => [mod(k) + '|' + k, v])),
        failTickets: stats.ticketsFail,
    };
    console.log(JSON.stringify(summary, null, 1));
    send(summary);
}, 13000);
