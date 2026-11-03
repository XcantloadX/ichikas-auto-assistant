// 实验 25：重试派发器 —— 测量完成 10 次成功调用所需时间
'use strict';

const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const pGetTrampoline = itf.add(24).readPointer();
const getTrampolineFn = new NativeFunction(pGetTrampoline, 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);

let callCount = 0;
let trampCount = 0;

function makeDomainGet() {
    const t = getTrampolineFn(ptr(0), Memory.allocUtf8String('il2cpp_domain_get'), Memory.allocUtf8String('L'), 1, 0);
    trampCount++;
    return new NativeFunction(t, 'pointer', []);
}

function callWithRetry() {
    let dg = makeDomainGet();
    for (let attempt = 0; attempt < 500; attempt++) {
        try {
            const d = dg();
            callCount++;
            return d;
        } catch (e) {
            if (attempt % 25 === 24) dg = makeDomainGet(); // 换新 trampoline
            Thread.sleep(0.05);
        }
    }
    throw new Error('callWithRetry exhausted');
}

const t0 = Date.now();
const results = [];
try {
    for (let i = 0; i < 10; i++) {
        const d = callWithRetry();
        results.push(String(d));
    }
    send({ done: true, elapsedMs: Date.now() - t0, callCount: callCount, trampCount: trampCount, results: results });
} catch (e) {
    send({ failed: String(e), elapsedMs: Date.now() - t0, callCount: callCount, trampCount: trampCount });
}
