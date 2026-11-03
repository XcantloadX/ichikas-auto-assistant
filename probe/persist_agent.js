// 常驻 agent：rpc.exports 供 Python 调用
'use strict';

const trampCache = {};
const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const pGetTrampoline = itf.add(24).readPointer();
const getTrampolineFn = new NativeFunction(pGetTrampoline, 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);

function tramp(name, shorty) {
    const key = name + '|' + shorty;
    if (trampCache[key]) return trampCache[key];
    const t = getTrampolineFn(ptr(0), Memory.allocUtf8String(name), Memory.allocUtf8String(shorty), shorty.length, 0);
    if (t.isNull()) throw new Error('no trampoline for ' + name);
    trampCache[key] = t;
    return t;
}
function nf(name, shorty, ret, args) { return new NativeFunction(tramp(name, shorty), ret, args); }

let domainGet = null;
try {
    domainGet = nf('il2cpp_domain_get', 'L', 'pointer', []);
} catch (e) { }

rpc.exports = {
    ping: function () {
        try {
            const d = domainGet();
            return { ok: true, domain: String(d) };
        } catch (e) {
            return { ok: false, err: String(e) };
        }
    },
    stats: function () {
        return { cachedTramps: Object.keys(trampCache).length };
    }
};

send({ agentReady: true });
