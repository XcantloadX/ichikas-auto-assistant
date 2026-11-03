// 实验 8：直接取 libhoudini 的 NativeBridgeItf 并调用 getTrampoline
'use strict';

const IL2CPP_PATH = '/data/app/~~_AKbb6cXWFMNLiugNkCZ2g==/com.sega.pjsekai-iMjlP6Bt2jE7PmZPtB4dKA==/lib/arm64/libil2cpp.so';

const itfAddr = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
console.log('houdini NativeBridgeItf =', itfAddr);
const slots = [];
for (let k = 0; k <= 128; k += 8) slots.push(k + ': ' + itfAddr.add(k).readPointer());
console.log(slots.join('\n'));
send({ itf: String(itfAddr), slots: slots });

// +0: version, +8 initialize, +16 loadLibrary, +24 getTrampoline, +32 isSupported
const loadLibrary = new NativeFunction(itfAddr.add(16).readPointer(), 'pointer', ['pointer', 'int']);
const isSupportedFn = new NativeFunction(itfAddr.add(32).readPointer(), 'int', ['pointer']);

send({ isSupported: isSupportedFn(Memory.allocUtf8String(IL2CPP_PATH)) });

const handle = loadLibrary(Memory.allocUtf8String(IL2CPP_PATH), 2);
console.log('handle =', handle);
send({ handle: String(handle) });

if (!handle.isNull()) {
    const getTrampoline = new NativeFunction(itfAddr.add(24).readPointer(), 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
    const tramp = getTrampoline(handle, Memory.allocUtf8String('il2cpp_domain_get'), Memory.allocUtf8String('L'), 1, 0);
    console.log('trampoline =', tramp);
    send({ tramp: String(tramp) });
    if (!tramp.isNull()) {
        const domainGet = new NativeFunction(tramp, 'pointer', []);
        const dom = domainGet();
        console.log('il2cpp_domain_get() =', dom);
        send({ callOk: true, domain: String(dom) });
    }
}
