// 实验 17：JniMethodStart 钩子内（游戏线程 host 模式）调用 gateway
'use strict';

const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const getTrampolineFn = new NativeFunction(itf.add(24).readPointer(), 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
const t = getTrampolineFn(ptr(0), Memory.allocUtf8String('il2cpp_domain_get'), Memory.allocUtf8String('L'), 1, 0);
const dg = new NativeFunction(t, 'pointer', []);

const jniStart = Module.getExportByName('libart.so', '_ZN3art14JniMethodStartEPNS_6ThreadE');
console.log('JniMethodStart =', jniStart);

let fired = 0;
const listener = Interceptor.attach(jniStart, {
    onEnter: function () {
        fired++;
        if (fired > 10) return;
        try {
            const d = dg();
            send({ ride: fired, ok: true, domain: String(d), tid: Process.getCurrentThreadId() });
        } catch (e) {
            send({ ride: fired, ok: false, err: String(e), tid: Process.getCurrentThreadId() });
        }
    }
});
send({ armed: true });
