'use strict';
const itf = Process.findModuleByName('libhoudini.so').getExportByName('NativeBridgeItf');
const loadLibraryExt = new NativeFunction(itf.add(0x70).readPointer(), 'pointer', ['pointer', 'int', 'pointer']);
const getError = new NativeFunction(itf.add(0x48).readPointer(), 'pointer', []);
const pGetTrampoline = itf.add(0x18).readPointer();
const getTrampolineFn = new NativeFunction(pGetTrampoline, 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);

for (const p of ['/data/local/tmp/v1.so', '/data/local/tmp/nonexist.so']) {
    getError(); // 清空
    const h = loadLibraryExt(Memory.allocUtf8String(p), 2, ptr(0));
    let err = '?';
    try {
        const e = getError();
        err = e.isNull() ? '(null)' : e.readCString(200);
    } catch (x) { err = 'getErrErr ' + x; }
    console.log(p, '→ handle', h, '| error:', err);
    send({ path: p, handle: String(h), err: err });
}
