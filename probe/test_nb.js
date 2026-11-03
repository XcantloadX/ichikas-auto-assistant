// 实验 6：读取 libnb.so 的 NativeBridgeItf 回调表并测试 trampoline
'use strict';

const NB_ITF = ptr(__NB_ITF__); // NativeBridgeItf 符号运行时地址
const IL2CPP_PATH = '/data/app/~~_AKbb6cXWFMNLiugNkCZ2g==/com.sega.pjsekai-iMjlP6Bt2jE7PmZPtB4dKA==/lib/arm64/libil2cpp.so';

const version = NB_ITF.readU32();
console.log('NativeBridgeItf version =', version);
const slots = [];
for (let k = 8; k <= 128; k += 8) {
    slots.push(k + ': ' + NB_ITF.add(k).readPointer());
}
console.log(slots.join('\n'));
send({ version: version, slots: slots });

// AOSP 布局: +8 initialize, +16 loadLibrary, +24 getTrampoline, +32 isSupported, +40 getAppEnv,
// v2: +48 isPathSupported, +56 initAnonymousNamespace, +64 createNamespace, +72 getVendorNamespace
// v3: +80 loadLibraryExt, v4: +88 preZygoteFork, v5: +96 initializeCompanion, v6: +104 loadLibraryCompanion
const loadLibrary = new NativeFunction(NB_ITF.add(16).readPointer(), 'pointer', ['pointer', 'int']);
const isSupportedFn = new NativeFunction(NB_ITF.add(32).readPointer(), 'int', ['pointer']);

send({ isSupported: isSupportedFn(Memory.allocUtf8String(IL2CPP_PATH)) });

const handle = loadLibrary(Memory.allocUtf8String(IL2CPP_PATH), 2);
console.log('handle =', handle);
send({ handle: String(handle) });

if (!handle.isNull()) {
    const getTrampoline = new NativeFunction(NB_ITF.add(24).readPointer(), 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
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
