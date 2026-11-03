// 实验 16：验证 gateway 调用的线程预算
'use strict';

const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const getTrampolineFn = new NativeFunction(itf.add(24).readPointer(), 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
const t = getTrampolineFn(ptr(0), Memory.allocUtf8String('il2cpp_domain_get'), Memory.allocUtf8String('L'), 1, 0);
const domainGet = new NativeFunction(t, 'pointer', []);

// A: 同一线程第 2 次调用（预期失败）
try {
    const d1 = domainGet();
    send({ A1: String(d1) });
    const d2 = domainGet();
    send({ A2: String(d2), multi: true });
} catch (e) {
    send({ A2: 'ERR ' + e, multi: false });
}

// B: 新建 pthread，每线程调一次
const pthreadCreate = new NativeFunction(Module.getExportByName('libc.so', 'pthread_create'), 'int', ['pointer', 'pointer', 'pointer', 'pointer']);
const pthreadJoin = new NativeFunction(Module.getExportByName('libc.so', 'pthread_join'), 'int', ['pointer', 'pointer']);

const results = [];
for (let i = 0; i < 4; i++) {
    const cb = new NativeCallback(function () {
        try {
            const d = domainGet();
            results.push('T' + i + ':' + d);
            return 0;
        } catch (e) {
            results.push('T' + i + ':ERR');
            return 0;
        }
    }, 'pointer', ['pointer']);
    const tidBuf = Memory.alloc(8);
    const r = pthreadCreate(tidBuf, ptr(0), cb, ptr(0));
    if (r === 0) {
        pthreadJoin(tidBuf.readPointer(), ptr(0));
    } else {
        results.push('T' + i + ':create-fail');
    }
}
send({ B: results });
