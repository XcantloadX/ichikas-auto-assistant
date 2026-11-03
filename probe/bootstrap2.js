// 实验 26：同步 load 期 bootstrap，支持部分结果续传
'use strict';

const PREV = __PREV__; // 上次的部分结果 { classes: {...}, goFields: {...}, methods: {...}, domain: "0x..." }

const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const getTrampolineFn = new NativeFunction(itf.add(24).readPointer(), 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
const tramps = {};
let trampCreations = 0;

function T(name, shorty) {
    const key = name + '|' + shorty;
    if (!tramps[key]) {
        const t = getTrampolineFn(ptr(0), Memory.allocUtf8String(name), Memory.allocUtf8String(shorty), shorty.length, 0);
        if (t.isNull()) throw new Error('no tramp ' + name);
        tramps[key] = t;
    }
    return tramps[key];
}
function freshT(name, shorty) {
    // 强制新建（换 ticket）
    delete tramps[name + '|' + shorty];
    trampCreations++;
    return T(name, shorty);
}
function NF(name, shorty, ret, args) { return new NativeFunction(T(name, shorty), ret, args); }

const defs = {
    domain_get: ['L', 'pointer', []],
    domain_get_assemblies: ['LL', 'pointer', ['pointer', 'pointer']],
    assembly_get_image: ['LL', 'pointer', ['pointer']],
    image_get_name: ['LL', 'pointer', ['pointer']],
    class_from_name: ['LLL', 'pointer', ['pointer', 'pointer', 'pointer']],
    class_get_method_from_name: ['LLLI', 'pointer', ['pointer', 'pointer', 'int']],
    class_get_field_from_name: ['LLL', 'pointer', ['pointer', 'pointer']],
    field_get_offset: ['LL', 'int', ['pointer']],
    field_get_name: ['LL', 'pointer', ['pointer']],
    method_get_name: ['LL', 'pointer', ['pointer']],
    runtime_invoke: ['LLPLP', 'pointer', ['pointer', 'pointer', 'pointer', 'pointer']],
    string_chars: ['LL', 'pointer', ['pointer']],
    string_new: ['LL', 'pointer', ['pointer']],
    is_vm_thread: ['LI', 'int', []],
    gc_disable: ['V', 'void', []],
    gc_enable: ['V', 'void', []],
};

const F = {};
for (const [name, [shorty, ret, args]] of Object.entries(defs)) {
    F[name] = NF(name, shorty, ret, args);
}

function cstr(p) { return p.isNull() ? null : p.readCString(); }
function istr(p) { return p.isNull() ? null : cstr(F.string_chars(p)); }

const result = { classes: {}, goFields: {}, methods: {}, meta: {} };

// 带重试的一次调用（load 期总时长受限）
let budgetDeadline = Date.now() + 25000;
function call1(fn, args) {
    let lastErr = null;
    for (let attempt = 0; attempt < 400; attempt++) {
        try {
            return fn.apply(null, args);
        } catch (e) {
            lastErr = e;
            if (Date.now() > budgetDeadline) throw new Error('budget exceeded: ' + lastErr);
            Thread.sleep(0.02);
        }
    }
    throw new Error('retries exhausted: ' + lastErr);
}

function bootstrap() {
    const t0 = Date.now();
    const domain = call1(F.domain_get, []);
    result.meta.domain = String(domain);
    result.meta.vmThread = F.is_vm_thread();

    if (!PREV.coreImage) {
        const sizeBuf = Memory.alloc(8);
        const assemblies = call1(F.domain_get_assemblies, [domain, sizeBuf]);
        const count = sizeBuf.readULong().toNumber();
        let core = null;
        for (let i = 0; i < count; i++) {
            const img = call1(F.assembly_get_image, [assemblies.add(i * Process.pointerSize).readPointer()]);
            if (cstr(F.image_get_name(img)) === 'UnityEngine.CoreModule.dll') { core = img; break; }
        }
        if (!core) throw new Error('CoreModule not found');
        result.coreImage = String(core);
    } else {
        result.coreImage = PREV.coreImage;
    }
    const core = ptr(result.coreImage);

    // 类解析
    const wantCore = {
        GameObject: ['UnityEngine', 'GameObject'], Transform: ['UnityEngine', 'Transform'],
        RectTransform: ['UnityEngine', 'RectTransform'], Component: ['UnityEngine', 'Component'],
        Canvas: ['UnityEngine', 'Canvas'], Behaviour: ['UnityEngine', 'Behaviour'],
        Object: ['UnityEngine', 'Object'], Text: ['UnityEngine', 'Text'],
        CanvasGroup: ['UnityEngine', 'CanvasGroup'],
        Button: ['UnityEngine.UI', 'Button'], TMP_Text: ['TMPro', 'TMP_Text'],
    };
    for (const [k, [ns, nm]] of Object.entries(wantCore)) {
        if (PREV.classes && PREV.classes[k]) { result.classes[k] = PREV.classes[k]; continue; }
        const kl = call1(F.class_from_name, [core, Memory.allocUtf8String(ns), Memory.allocUtf8String(nm)]);
        if (!kl.isNull()) result.classes[k] = String(kl);
    }

    // GameObject 字段
    const go = ptr(result.classes.GameObject);
    for (const fn of ['m_CachedPtr', 'm_ComponentList', 'm_CanvasRenderer', 'm_Canvas', 'm_TagString', 'm_IsActive', 'm_Name']) {
        if (PREV.goFields && PREV.goFields[fn] !== undefined && PREV.goFields[fn] !== null) { result.goFields[fn] = PREV.goFields[fn]; continue; }
        const f = call1(F.class_get_field_from_name, [go, Memory.allocUtf8String(fn)]);
        result.goFields[fn] = f.isNull() ? null : F.field_get_offset(f);
    }

    // 方法
    const gm = (cls, name, argc) => {
        const key = name + '/' + argc;
        if (PREV.methods && PREV.methods[clsName(cls) + '.' + key]) return ptr(PREV.methods[clsName(cls) + '.' + key]);
        const m = call1(F.class_get_method_from_name, [cls, Memory.allocUtf8String(name), argc]);
        return m.isNull() ? null : m;
    };
    function clsName(c) { return Object.entries(result.classes).find(([k, v]) => v === String(c))?.[0] || String(c); }

    const C = {};
    for (const [k, v] of Object.entries(result.classes)) C[k] = ptr(v);

    const methodDefs = [
        ['GameObject', 'get_name', 0], ['GameObject', 'get_activeInHierarchy', 0],
        ['GameObject', 'get_transform', 0], ['GameObject', 'get_activeSelf', 0],
        ['Transform', 'GetParent', 0], ['Transform', 'get_childCount', 0], ['Transform', 'GetChild', 1],
        ['Transform', 'get_gameObject', 0],
        ['RectTransform', 'get_anchoredPosition', 0], ['RectTransform', 'get_sizeDelta', 0],
        ['Behaviour', 'get_isEnabled', 0], ['CanvasGroup', 'get_alpha', 0],
    ];
    result.methodPtrs = {};
    for (const [cls, name, argc] of methodDefs) {
        if (!C[cls]) continue;
        const m = gm(C[cls], name, argc);
        if (m) result.methodPtrs[cls + '.' + name + '/' + argc] = String(m);
    }

    // string roundtrip
    const s = call1(F.string_new, [Memory.allocUtf8String('IAA_OK')]);
    result.meta.stringRoundtrip = istr(s);
    result.meta.trampCreations = trampCreations;
    result.meta.elapsedMs = Date.now() - t0;
    return result;
}

send({ bootstrap: bootstrap() });
