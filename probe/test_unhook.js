// 实验 20：恢复被 hook 函数的原始字节，测试调用是否恢复
'use strict';

const BASE = ptr(__BASE__);
const FUNCS = __FUNCS__; // [{name, off, fileBytes(16)}]

function unhook(e) {
    const addr = BASE.add(e.off);
    Memory.protect(addr, 64, 'rwx');
    const orig = new Uint8Array(e.fileBytes);
    addr.writeByteArray(orig.buffer);
}

const results = {};
for (const e of FUNCS) {
    try { unhook(e); results[e.name] = 'unhooked'; } catch (err) { results[e.name] = 'ERR ' + err; }
}
send({ results: results });

// 然后连续调用 domain_get 30 次
const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const getTrampolineFn = new NativeFunction(itf.add(24).readPointer(), 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
const t = getTrampolineFn(ptr(0), Memory.allocUtf8String('il2cpp_domain_get'), Memory.allocUtf8String('L'), 1, 0);
const dg = new NativeFunction(t, 'pointer', []);
let ok = 0, err = 0, firstErr = null;
for (let i = 0; i < 30; i++) {
    try { dg(); ok++; } catch (e) { err++; if (!firstErr) firstErr = String(e); }
}
send({ afterUnhook: { ok: ok, err: err, firstErr: firstErr } });
