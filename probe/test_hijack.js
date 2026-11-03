// 实验 11：在游戏线程上（JniMethodStart 钩子内）调用 loadLibrary + getTrampoline
'use strict';

const IL2CPP_PATH = '/data/app/~~_AKbb6cXWFMNLiugNkCZ2g==/com.sega.pjsekai-iMjlP6Bt2jE7PmZPtB4dKA==/lib/arm64/libil2cpp.so';

const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const pLoadLibrary = itf.add(16).readPointer();
const pGetTrampoline = itf.add(24).readPointer();

const jniStart = Module.getExportByName('libart.so', '_ZN3art14JniMethodStartEPNS_6ThreadE');
console.log('JniMethodStart =', jniStart);

let done = false;
const listener = Interceptor.attach(jniStart, {
    onEnter: function () {
        if (done) return;
        done = true;
        console.log('[hijack] on game thread');
        try {
            const loadLibrary = new NativeFunction(pLoadLibrary, 'pointer', ['pointer', 'int']);
            const h = loadLibrary(Memory.allocUtf8String(IL2CPP_PATH), 2);
            console.log('[hijack] loadLibrary =', h);
            send({ hijack: true, handle: String(h) });
            if (!h.isNull()) {
                const getTrampoline = new NativeFunction(pGetTrampoline, 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
                const tramp = getTrampoline(h, Memory.allocUtf8String('il2cpp_domain_get'), Memory.allocUtf8String('L'), 1, 0);
                console.log('[hijack] trampoline =', tramp);
                send({ tramp: String(tramp) });
                if (!tramp.isNull()) {
                    const domainGet = new NativeFunction(tramp, 'pointer', []);
                    const dom = domainGet();
                    console.log('[hijack] il2cpp_domain_get() =', dom);
                    send({ callOk: true, domain: String(dom) });
                }
            }
        } catch (e) {
            console.log('[hijack] error:', e);
            send({ hijackErr: String(e) });
        } finally {
            // 钩子只触发一次，之后移除
            setTimeout(function () {}, 0);
        }
    }
});

send({ armed: true });
