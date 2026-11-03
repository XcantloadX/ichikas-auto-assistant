// 实验 5：直接在 libhoudini 的映射内扫描 NativeBridgeCallbacks 结构
'use strict';

const HOUDINI_BASE = ptr(__HOUDINI_BASE__);
const HOUDINI_SIZE = 12800000;
const IL2CPP_PATH = '/data/app/~~_AKbb6cXWFMNLiugNkCZ2g==/com.sega.pjsekai-iMjlP6Bt2jE7PmZPtB4dKA==/lib/arm64/libil2cpp.so';

function inHoudini(p) {
    return p.compare(HOUDINI_BASE) >= 0 && p.compare(HOUDINI_BASE.add(HOUDINI_SIZE)) < 0;
}

// 枚举 houdini 全部映射段（宿主机侧已给出基址；这里用 enumerateRanges 找出属于 houdini 范围内的段）
const ranges = Process.enumerateRangesSync({ protection: 'r--', coalesce: false })
    .concat(Process.enumerateRangesSync({ protection: 'rw-', coalesce: false }));
const houdiniRanges = ranges.filter(r => {
    const start = r.base, end = r.base.add(r.size);
    return start.compare(HOUDINI_BASE) >= 0 && end.compare(HOUDINI_BASE.add(HOUDINI_SIZE)) <= 0;
});
console.log('houdini ranges:', houdiniRanges.length);
houdiniRanges.forEach(r => console.log('  ', r.base, r.size, r.protection));

let callbacks = null;
for (const r of houdiniRanges) {
    const step = 8;
    for (let off = 0; off + 96 <= r.size; off += step) {
        const cand = r.base.add(off);
        try {
            const ver = cand.readU32();
            if (ver < 1 || ver > 10) continue;
            const loadLibrary = cand.add(16).readPointer();
            const getTramp = cand.add(24).readPointer();
            const isSupported = cand.add(32).readPointer();
            if (inHoudini(loadLibrary) && inHoudini(getTramp) && inHoudini(isSupported)) {
                console.log('callbacks at', cand, 'ver', ver);
                callbacks = cand;
                break;
            }
        } catch (e) { continue; }
    }
    if (callbacks) break;
}
send({ callbacks: String(callbacks) });

if (callbacks) {
    const isSupportedFn = new NativeFunction(callbacks.add(32).readPointer(), 'int', ['pointer']);
    send({ isSupportedIl2cpp: isSupportedFn(Memory.allocUtf8String(IL2CPP_PATH)) });

    const loadLibrary = new NativeFunction(callbacks.add(16).readPointer(), 'pointer', ['pointer', 'int']);
    const handle = loadLibrary(Memory.allocUtf8String(IL2CPP_PATH), 2);
    console.log('handle =', handle);
    send({ handle: String(handle) });

    if (!handle.isNull()) {
        const getTrampoline = new NativeFunction(callbacks.add(24).readPointer(), 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
        const tramp = getTrampoline(handle, Memory.allocUtf8String('il2cpp_domain_get'), Memory.allocUtf8String('L'), 1, 0);
        console.log('trampoline =', tramp);
        if (!tramp.isNull()) {
            const domainGet = new NativeFunction(tramp, 'pointer', []);
            const dom = domainGet();
            console.log('il2cpp_domain_get() =', dom);
            send({ callOk: true, domain: String(dom) });
        } else {
            send({ trampNull: true });
        }
    }
}
