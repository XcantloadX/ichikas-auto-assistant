// 实验 33：x64 dlsym(guestHandle, name) → 直接可调用的 trampoline？
'use strict';

const itf = Process.findModuleByName('libhoudini.so').getExportByName('NativeBridgeItf');
const pLoadLibExt = itf.add(0x70).readPointer();
const loadLibraryExt = new NativeFunction(pLoadLibExt, 'pointer', ['pointer', 'int', 'pointer']);
const IL2CPP = '/data/app/~~_AKbb6cXWFMNLiugNkCZ2g==/com.sega.pjsekai-iMjlP6Bt2jE7PmZPtB4dKA==/lib/arm64/libil2cpp.so';
const handle = loadLibraryExt(Memory.allocUtf8String(IL2CPP), 2, ptr(0));
console.log('handle:', handle);

const dlsymFn = new NativeFunction(Module.getGlobalExportByName ? Module.getGlobalExportByName('dlsym') : Module.findExportByName('libc.so', 'dlsym'), 'pointer', ['pointer', 'pointer']);

for (const name of ['il2cpp_domain_get', 'il2cpp_string_new', 'il2cpp_runtime_invoke']) {
    try {
        const p = dlsymFn(handle, Memory.allocUtf8String(name));
        console.log(name, '→', p);
        send({ name: name, addr: String(p) });
        if (!p.isNull()) {
            if (name === 'il2cpp_domain_get') {
                const fn = new NativeFunction(p, 'pointer', []);
                try {
                    const d = fn();
                    console.log('*** dlsym-path CALL OK, domain =', d);
                    send({ ok: true, domain: String(d) });
                } catch (e) {
                    console.log('call failed:', e);
                    send({ ok: false, err: String(e) });
                }
            }
        }
    } catch (e) {
        console.log(name, 'err:', e);
    }
}
