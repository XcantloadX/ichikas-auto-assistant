// 实验 3：通过 libnativebridge 的 NativeBridgeGetTrampoline 调用 arm64 il2cpp 导出
'use strict';

const LIBNB = 'libnativebridge.so';
const IL2CPP_PATH = '/data/app/~~_AKbb6cXWFMNLiugNkCZ2g==/com.sega.pjsekai-iMjlP6Bt2jE7PmZPtB4dKA==/lib/arm64/libil2cpp.so';

function nbFunc(name, ret, args) {
    const addr = Module.getExportByName(LIBNB, name);
    return new NativeFunction(addr, ret, args);
}

const isSupported = nbFunc('NativeBridgeIsSupported', 'int', ['pointer']);
const loadLibrary = nbFunc('NativeBridgeLoadLibrary', 'pointer', ['pointer', 'int']);
const getTrampoline = nbFunc('NativeBridgeGetTrampoline', 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);

const supported = isSupported(Memory.allocUtf8String(IL2CPP_PATH));
send({ supported: supported });

const hPath = Memory.allocUtf8String(IL2CPP_PATH);
const handle = loadLibrary(hPath, 2); // RTLD_NOW
console.log('il2cpp guest handle =', handle);
send({ handle: String(handle) });

if (!handle.isNull()) {
    // trampoline type: 先试 0 (kDefault)
    for (const tt of [0, 1]) {
        const tramp = getTrampoline(
            handle,
            Memory.allocUtf8String('il2cpp_domain_get'),
            Memory.allocUtf8String('L'), // shorty: 返回 L (对象/指针)，无参
            1,
            tt
        );
        console.log('trampoline type', tt, '=', tramp);
        if (tramp.isNull()) continue;
        try {
            const domainGet = new NativeFunction(tramp, 'pointer', []);
            const dom = domainGet();
            console.log('il2cpp_domain_get() =', dom);
            send({ callOk: true, tt: tt, domain: String(dom) });
            break;
        } catch (e) {
            console.log('call failed (tt=' + tt + '):', e);
            send({ callOk: false, tt: tt, err: String(e) });
        }
    }
}
