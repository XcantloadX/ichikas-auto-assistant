// 实验 18：在 ON 窗口内 attach 线程，验证此后调用是否稳定
'use strict';

const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const getTrampolineFn = new NativeFunction(itf.add(24).readPointer(), 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);

function mkTramp(name, shorty) {
    const t = getTrampolineFn(ptr(0), Memory.allocUtf8String(name), Memory.allocUtf8String(shorty), shorty.length, 0);
    if (t.isNull()) throw new Error('no trampoline for ' + name);
    return t;
}

const domainGet = new NativeFunction(mkTramp('il2cpp_domain_get', 'L'), 'pointer', []);
const threadAttach = new NativeFunction(mkTramp('il2cpp_thread_attach', 'LL'), 'pointer', ['pointer']);
const threadDetach = new NativeFunction(mkTramp('il2cpp_thread_detach', 'LL'), 'pointer', ['pointer']);
const isVmThread = new NativeFunction(mkTramp('il2cpp_is_vm_thread', 'LI'), 'int', []);

// 轮询等待 ON 窗口
let attached = false, domain = null;
const t0 = Date.now();
while (Date.now() - t0 < 60000) {
    try {
        domain = domainGet();
        // ON 窗口：立即 attach
        try {
            const th = threadAttach(domain);
            attached = true;
            send({ attached: true, thread: String(th), domain: String(domain), vmThread: isVmThread() });
        } catch (e) {
            send({ attached: false, attachErr: String(e), domain: String(domain) });
        }
        break;
    } catch (e) {
        send({ wait: true, err: String(e) });
        Thread.sleep(0.5);
    }
}

if (attached) {
    // attach 后连续调用 30 次
    let ok = 0, err = 0;
    for (let i = 0; i < 30; i++) {
        try { domainGet(); ok++; } catch (e) { err++; }
    }
    send({ afterAttach: { ok: ok, err: err } });
} else {
    send({ attached: false, domain: domain ? String(domain) : null });
}
