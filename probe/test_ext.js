// 实验 31：loadLibraryExt(path, RTLD_NOW, ns=3) 拿 libil2cpp 真实 handle → getTrampoline(handle,...)
'use strict';

const itf = Process.findModuleByName('libhoudini.so').getExportByName('NativeBridgeItf');
console.log('Itf:', itf);
// v6 布局（看雪/Perfare 确认）：+0x10 loadLibrary, +0x18 getTrampoline, +0x20 isSupported, +0x70 loadLibraryExt
const pLoadLibExt = itf.add(0x70).readPointer();
const pGetTrampoline = itf.add(0x18).readPointer();
console.log('loadLibraryExt:', pLoadLibExt, 'getTrampoline:', pGetTrampoline);

const IL2CPP = '/data/app/~~_AKbb6cXWFMNLiugNkCZ2g==/com.sega.pjsekai-iMjlP6Bt2jE7PmZPtB4dKA==/lib/arm64/libil2cpp.so';

// loadLibraryExt(handle, const char* path, int flag, void* namespace)
// 注意 AOSP 签名: void* (*loadLibraryExt)(const char* libpath, int flag, void* extinfo)
const loadLibraryExt = new NativeFunction(pLoadLibExt, 'pointer', ['pointer', 'int', 'pointer']);
const getTrampolineFn = new NativeFunction(pGetTrampoline, 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);

let handle = null;
for (const ns of [ptr(3), ptr(0), ptr(-1)]) {
    try {
        const h = loadLibraryExt(Memory.allocUtf8String(IL2CPP), 2 /*RTLD_NOW*/, ns);
        console.log('loadLibraryExt ns=' + ns + ' → ' + h);
        send({ ns: String(ns), handle: String(h) });
        if (!h.isNull()) { handle = h; break; }
    } catch (e) {
        console.log('ns=' + ns + ' err: ' + e);
    }
}
if (!handle) throw new Error('loadLibraryExt all failed');

// 用真实 handle 建 trampoline
for (const name of ['il2cpp_domain_get']) {
    const t = getTrampolineFn(handle, Memory.allocUtf8String(name), Memory.allocUtf8String('L'), 1, 0);
    console.log(name, 'tramp:', t);
    if (t.isNull()) continue;
    const fn = new NativeFunction(t, 'pointer', []);
    try {
        const d = fn();
        console.log('*** CALL OK:', name, '=', d);
        send({ ok: true, name: name, result: String(d) });
    } catch (e) {
        console.log('call failed:', e);
        send({ ok: false, name: name, err: String(e) });
    }
}
