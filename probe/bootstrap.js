// 实验 24：加载期一次性 bootstrap burst —— 解析类/方法/字段，测试 invoke
'use strict';

const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const getTrampolineFn = new NativeFunction(itf.add(24).readPointer(), 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
const tramps = {};
function T(name, shorty) {
    const key = name + '|' + shorty;
    if (!tramps[key]) {
        const t = getTrampolineFn(ptr(0), Memory.allocUtf8String(name), Memory.allocUtf8String(shorty), shorty.length, 0);
        if (t.isNull()) throw new Error('no tramp ' + name);
        tramps[key] = t;
    }
    return tramps[key];
}
function NF(name, shorty, ret, args) { return new NativeFunction(T(name, shorty), ret, args); }

const F = {
    domain_get: NF('il2cpp_domain_get', 'L', 'pointer', []),
    domain_get_assemblies: NF('il2cpp_domain_get_assemblies', 'LL', 'pointer', ['pointer', 'pointer']),
    assembly_get_image: NF('il2cpp_assembly_get_image', 'LL', 'pointer', ['pointer']),
    image_get_name: NF('il2cpp_image_get_name', 'LL', 'pointer', ['pointer']),
    class_from_name: NF('il2cpp_class_from_name', 'LLL', 'pointer', ['pointer', 'pointer', 'pointer']),
    class_get_method_from_name: NF('il2cpp_class_get_method_from_name', 'LLLI', 'pointer', ['pointer', 'pointer', 'int']),
    class_get_field_from_name: NF('il2cpp_class_get_field_from_name', 'LLL', 'pointer', ['pointer', 'pointer']),
    field_get_offset: NF('il2cpp_field_get_offset', 'LL', 'int', ['pointer']),
    field_get_name: NF('il2cpp_field_get_name', 'LL', 'pointer', ['pointer']),
    method_get_name: NF('il2cpp_method_get_name', 'LL', 'pointer', ['pointer']),
    runtime_invoke: NF('il2cpp_runtime_invoke', 'LLPLP', 'pointer', ['pointer', 'pointer', 'pointer', 'pointer']),
    string_chars: NF('il2cpp_string_chars', 'LL', 'pointer', ['pointer']),
    string_new: NF('il2cpp_string_new', 'LL', 'pointer', ['pointer']),
    is_vm_thread: NF('il2cpp_is_vm_thread', 'LI', 'int', []),
};

function cstr(p) { return p.isNull() ? null : p.readCString(); }
function istr(p) { return p.isNull() ? null : cstr(F.string_chars(p)); }

const report = { steps: [] };
function step(name, fn) {
    try {
        report.steps.push({ name: name, ok: true, result: fn() });
    } catch (e) {
        report.steps.push({ name: name, ok: false, err: String(e) });
        throw e;
    }
}

let done = false;

function bootstrap() {
    const t0 = Date.now();
    const domain = F.domain_get();
    const R = { domain: String(domain) };

    // 1. 找 CoreModule image
    const sizeBuf = Memory.alloc(8);
    const assemblies = F.domain_get_assemblies(domain, sizeBuf);
    const count = sizeBuf.readULong().toNumber();
    let core = null;
    for (let i = 0; i < count; i++) {
        const img = F.assembly_get_image(assemblies.add(i * Process.pointerSize).readPointer());
        if (cstr(F.image_get_name(img)) === 'UnityEngine.CoreModule.dll') { core = img; break; }
    }
    if (!core) throw new Error('CoreModule not found');
    R.coreImage = String(core);

    // 2. 解析类
    const nsU = Memory.allocUtf8String('UnityEngine');
    const nsUG = Memory.allocUtf8String('UnityEngine.UI');
    const nsTM = Memory.allocUtf8String('TMPro');
    const classes = {};
    const wantCore = {
        GameObject: [nsU, 'GameObject'], Transform: [nsU, 'Transform'], RectTransform: [nsU, 'RectTransform'],
        Component: [nsU, 'Component'], Canvas: [nsU, 'Canvas'], Behaviour: [nsU, 'Behaviour'],
        Object: [nsU, 'Object'], SceneManager: [nsU, 'SceneManager'], Scene: [nsU, 'Scene'],
        Text: [nsU, 'Text'], Button: [nsUG, 'Button'], TMP_Text: [nsTM, 'TMP_Text'],
        CanvasGroup: [nsU, 'CanvasGroup'],
    };
    for (const [k, [nsPtr, nm]] of Object.entries(wantCore)) {
        const kl = F.class_from_name(core, nsPtr, Memory.allocUtf8String(nm));
        if (!kl.isNull()) classes[k] = String(kl);
    }
    // UI 模块可能在另一个 image（UnityEngine.UI.dll）
    R.classes = classes;

    const coreKl = {};
    for (const [k, v] of Object.entries(classes)) coreKl[k] = ptr(v);

    // 3. GameObject 字段偏移
    const goFields = {};
    for (const fn of ['m_CachedPtr', 'm_ComponentList', 'm_CanvasRenderer', 'm_Canvas', 'm_TagString', 'm_IsActive', 'm_Name']) {
        const f = F.class_get_field_from_name(coreKl.GameObject, Memory.allocUtf8String(fn));
        goFields[fn] = f.isNull() ? null : F.field_get_offset(f);
    }
    R.goFields = goFields;

    // Transform/RectTransform/Component 字段
    const tFields = {};
    for (const fn of ['m_CachedPtr']) {
        const f = F.class_get_field_from_name(coreKl.Transform, Memory.allocUtf8String(fn));
        tFields[fn] = f.isNull() ? null : F.field_get_offset(f);
    }
    R.tFields = tFields;

    // 4. 方法解析（后面 invoke 用）
    const methods = {};
    function gm(cls, name, argc) {
        const m = F.class_get_method_from_name(cls, Memory.allocUtf8String(name), argc);
        return m.isNull() ? null : String(m);
    }
    methods.go_get_name = gm(coreKl.GameObject, 'get_name', 0);
    methods.go_get_activeInHierarchy = gm(coreKl.GameObject, 'get_activeInHierarchy', 0);
    methods.go_get_transform = gm(coreKl.GameObject, 'get_transform', 0);
    methods.t_get_parent = gm(coreKl.Transform, 'GetParent', 0);
    methods.t_get_childCount = gm(coreKl.Transform, 'get_childCount', 0);
    methods.t_get_child = gm(coreKl.Transform, 'GetChild', 1);
    methods.rt_get_anchoredPosition = gm(coreKl.RectTransform, 'get_anchoredPosition', 0);
    methods.rt_get_sizeDelta = gm(coreKl.RectTransform, 'get_sizeDelta', 0);
    methods.go_get_component_button = gm(coreKl.GameObject, 'GetComponent', 1);
    R.methods = methods;

    // 5. invoke 测试：创建一个 string（string_new 不走 runtime_invoke）
    // 读端到端：string_new + string_chars
    const testStr = F.string_new(Memory.allocUtf8String('IAA_TEST_1234'));
    R.stringRoundtrip = istr(testStr);

    R.elapsedMs = Date.now() - t0;
    return R;
}

// 轮询等待可用窗口
function poll() {
    if (done) return;
    try {
        const d = F.domain_get();
        if (!d.isNull()) {
            done = true;
            try {
                send({ bootstrap: bootstrap() });
            } catch (e) {
                send({ bootstrapErr: String(e), steps: report.steps });
            }
            return;
        }
    } catch (e) {
        // 还在 OFF
    }
    setTimeout(poll, 300);
}
poll();
send({ polling: true });
