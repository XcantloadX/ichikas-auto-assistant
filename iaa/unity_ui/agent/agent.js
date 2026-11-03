/**
 * Unity UI-Tree Agent (frida-il2cpp gateway 版)
 *
 * 通过 houdini native-bridge trampoline 调用 il2cpp C API（x64 宿主 → arm64 guest）。
 * MuMu 的 libhp12 会间歇性门控调用（0xdead1066 / no-tramp），因此所有 guest 调用
 * 都经过 call() 重试器；dump 等长任务在单个窗口内完成，失败可整块重试。
 *
 * 该文件对 Unity(il2cpp) 游戏通用；游戏相关的查询由宿主（Python 定位器）完成。
 */
'use strict';

// ---------------------------------------------------------------------------
// 基础设施
// ---------------------------------------------------------------------------

const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const pGetTrampoline = itf.add(24).readPointer();
const getTrampolineFn = new NativeFunction(pGetTrampoline, 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);

/** trampoline/NativeFunction 缓存: name|shorty -> NativeFunction */
const _nfCache = {};
/** 防止 getTrampoline 的参数字符串被 GC */
const _keepAlive = [];

/**
 * 创建（或取缓存）il2cpp 导出的可调用包装。
 *
 * :param name: 导出符号名，如 ``il2cpp_domain_get``
 * :param shorty: JNI shorty（返回值+参数类型），如 ``'LLP'``
 * :param ret: frida NativeFunction 返回类型
 * :param args: frida NativeFunction 参数类型数组
 * :return: NativeFunction
 */
function NF(name, shorty, ret, args) {
    const key = name + '|' + shorty;
    let fn = _nfCache[key];
    if (fn) return fn;
    const t = getTrampolineFn(ptr(0), Memory.allocUtf8String(name), Memory.allocUtf8String(shorty), shorty.length, 0);
    if (t.isNull()) throw new Error('no trampoline for ' + name);
    _keepAlive.push(t);
    fn = new NativeFunction(t, ret, args);
    _nfCache[key] = fn;
    return fn;
}

/** 重试参数：窗口期 <1ms/次，非窗口期持续等待 */
const RETRY_MAX_MS = 30000;
const RETRY_SLEEP = 0.05;

/**
 * 带重试的 guest 调用。
 *
 * :param fn: NativeFunction
 * :param args: 参数数组
 * :param maxMs: 重试时限毫秒
 * :return: fn 返回值
 * :raises Error: 超时仍未成功
 */
function call(fn, args, maxMs) {
    const deadline = Date.now() + (maxMs || RETRY_MAX_MS);
    let lastErr = null;
    for (;;) {
        try {
            return fn.apply(null, args);
        } catch (e) {
            lastErr = e;
            if (Date.now() > deadline) {
                throw new Error('guest call failed after retry: ' + lastErr);
            }
            Thread.sleep(RETRY_SLEEP);
        }
    }
}

function cstr(p) { return p.isNull() ? null : p.readCString(); }

// ---------------------------------------------------------------------------
// il2cpp C API
// ---------------------------------------------------------------------------

const F = {};
function initApi() {
    if (F.domain_get) return;
    F.domain_get = NF('il2cpp_domain_get', 'L', 'pointer', []);
    F.domain_get_assemblies = NF('il2cpp_domain_get_assemblies', 'LL', 'pointer', ['pointer', 'pointer']);
    F.assembly_get_image = NF('il2cpp_assembly_get_image', 'LL', 'pointer', ['pointer']);
    F.image_get_name = NF('il2cpp_image_get_name', 'LL', 'pointer', ['pointer']);
    F.class_from_name = NF('il2cpp_class_from_name', 'LLL', 'pointer', ['pointer', 'pointer', 'pointer']);
    F.class_get_method_from_name = NF('il2cpp_class_get_method_from_name', 'LLLI', 'pointer', ['pointer', 'pointer', 'int']);
    F.class_get_type = NF('il2cpp_class_get_type', 'LL', 'pointer', ['pointer']);
    F.type_get_object = NF('il2cpp_type_get_object', 'LL', 'pointer', ['pointer']);
    F.runtime_invoke = NF('il2cpp_runtime_invoke', 'LLPLP', 'pointer', ['pointer', 'pointer', 'pointer', 'pointer']);
    F.string_chars = NF('il2cpp_string_chars', 'LL', 'pointer', ['pointer']);
    F.array_length = NF('il2cpp_array_length', 'LL', 'uint64', ['pointer']);
}

/** 读取 il2cpp System.String 内容 */
function istr(p) { return p.isNull() ? null : cstr(F.string_chars(p)); }

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

/** 引导结果（dump 依赖） */
const B = {
    ready: false,
    klass: {},    // shortName -> klass ptr 字符串
    typeObj: {},  // shortName -> System.Type 对象指针字符串
    method: {},   // 'Class.name/argc' -> MethodInfo ptr 字符串
};

function findImages(domain) {
    const sizeBuf = Memory.alloc(8);
    const assemblies = F.domain_get_assemblies(domain, sizeBuf);
    const count = sizeBuf.readULong().toNumber();
    const images = {};
    for (let i = 0; i < count; i++) {
        const asm = assemblies.add(i * Process.pointerSize).readPointer();
        const img = F.assembly_get_image(asm);
        images[cstr(F.image_get_name(img))] = img;
    }
    return images;
}

/**
 * 执行 bootstrap：解析 Unity 核心类、System.Type 对象与所需方法。
 * 任何一步失败抛错（由上层在窗口内重试）。
 *
 * :return: 引导摘要
 */
function bootstrap() {
    initApi();
    const t0 = Date.now();
    const domain = F.domain_get();
    const images = findImages(domain);
    const core = images['UnityEngine.CoreModule.dll'];
    if (!core) throw new Error('CoreModule image not found');
    const ui = images['UnityEngine.UI.dll'] || core;
    const tmp = images['Unity.TextMeshPro.dll'] || core;

    const nsU = Memory.allocUtf8String('UnityEngine');
    const nsUI = Memory.allocUtf8String('UnityEngine.UI');
    const nsTM = Memory.allocUtf8String('TMPro');

    const classDefs = [
        ['GameObject', core, nsU, 'GameObject'],
        ['Transform', core, nsU, 'Transform'],
        ['RectTransform', core, nsU, 'RectTransform'],
        ['Component', core, nsU, 'Component'],
        ['Behaviour', core, nsU, 'Behaviour'],
        ['Canvas', core, nsU, 'Canvas'],
        ['CanvasGroup', core, nsU, 'CanvasGroup'],
        ['Text', core, nsU, 'Text'],
        ['Object', core, nsU, 'Object'],
        ['Selectable', ui, nsUI, 'Selectable'],
        ['Button', ui, nsUI, 'Button'],
        ['TMP_Text', tmp, nsTM, 'TMP_Text'],
    ];
    for (const [short, img, nsPtr, nm] of classDefs) {
        const k = F.class_from_name(img, nsPtr, Memory.allocUtf8String(nm));
        if (k.isNull()) throw new Error('class not found: ' + nm);
        B.klass[short] = String(k);
        B.typeObj[short] = String(F.type_get_object(F.class_get_type(k)));
    }

    const K = {};
    for (const [k, v] of Object.entries(B.klass)) K[k] = ptr(v);

    const methodDefs = [
        ['GameObject.get_name/0', K.GameObject, 'get_name', 0],
        ['GameObject.get_activeSelf/0', K.GameObject, 'get_activeSelf', 0],
        ['GameObject.get_activeInHierarchy/0', K.GameObject, 'get_activeInHierarchy', 0],
        ['GameObject.get_transform/0', K.GameObject, 'get_transform', 0],
        ['GameObject.GetComponent/1', K.GameObject, 'GetComponent', 1],
        ['Transform.GetParent/0', K.Transform, 'GetParent', 0],
        ['Transform.get_childCount/0', K.Transform, 'get_childCount', 0],
        ['Transform.GetChild/1', K.Transform, 'GetChild', 1],
        ['Component.get_gameObject/0', K.Component, 'get_gameObject', 0],
        ['Transform.get_position/0', K.Transform, 'get_position', 0],
        ['Transform.get_lossyScale/0', K.Transform, 'get_lossyScale', 0],
        ['RectTransform.get_sizeDelta/0', K.RectTransform, 'get_sizeDelta', 0],
        ['RectTransform.get_pivot/0', K.RectTransform, 'get_pivot', 0],
        ['Behaviour.get_enabled/0', K.Behaviour, 'get_enabled', 0],
        ['Selectable.get_interactable/0', K.Selectable, 'get_interactable', 0],
        ['TMP_Text.get_text/0', K.TMP_Text, 'get_text', 0],
        ['Object.FindObjectsOfType/1', K.Object, 'FindObjectsOfType', 1],
    ];
    for (const [key, cls, nm, argc] of methodDefs) {
        const m = F.class_get_method_from_name(cls, Memory.allocUtf8String(nm), argc);
        if (m.isNull()) throw new Error('method not found: ' + key);
        B.method[key] = String(m);
    }

    B.ready = true;
    return { elapsedMs: Date.now() - t0, classes: Object.keys(B.klass).length, methods: Object.keys(B.method).length };
}

// ---------------------------------------------------------------------------
// Dump
// ---------------------------------------------------------------------------

/**
 * invoke 封装。
 *
 * :param methodKey: B.method 的 key
 * :param obj: 实例（静态传 null）
 * :param args: 托管对象指针数组（无参传 null）
 * :return: 返回的 Il2CppObject*（值类型为 boxed）
 */
function invoke(methodKey, obj, args) {
    const m = ptr(B.method[methodKey]);
    let argv = ptr(0);
    if (args && args.length) {
        const argBuf = Memory.alloc(8 * args.length);
        args.forEach((a, i) => argBuf.add(i * 8).writePointer(a));
        argv = argBuf;
    }
    const exc = Memory.alloc(8);
    exc.writePointer(ptr(0));
    return F.runtime_invoke(m, obj, argv, exc);
}

/** 读取 boxed Vector3 的 x/y/z（[klass][monitor][x][y][z]） */
function readBoxedVec3(p) {
    if (p.isNull()) return null;
    return [p.add(0x10).readFloat(), p.add(0x14).readFloat(), p.add(0x18).readFloat()];
}

/** 读取 il2cpp 数组元素（引用类型数组 data 起始 +0x20） */
function readArray(p) {
    if (p.isNull()) return [];
    const n = Number(F.array_length(p));
    const out = [];
    for (let i = 0; i < n; i++) {
        out.push(p.add(0x20 + i * 8).readPointer());
    }
    return out;
}

/**
 * Object.FindObjectsOfType(typeObj)：一次调用抓取某类型的全部激活实例。
 *
 * :param typeShort: B.typeObj 的 shortName
 * :return: 组件对象指针数组
 */
function findAll(typeShort) {
    const arr = invoke('Object.FindObjectsOfType/1', null, [ptr(B.typeObj[typeShort])]);
    return readArray(arr);
}

/**
 * 全量 dump UI 树。
 *
 * 流程：
 *  1. FindObjectsOfType(Transform) 得到全部激活节点（1 次调用 + 内存直读）
 *  2. 逐节点：gameObject / name / activeInHierarchy / parent / childCount（只读调用）
 *  3. 文本与可交互性：FindObjectsOfType(TMP_Text/Selectable) 后按 gameObject 关联
 *  4. 矩形：position/lossyScale/sizeDelta/pivot（boxed，值类型返回会分配少量内存）
 *
 * :param maxNodes: 节点上限
 * :return: dump JSON（roots 为森林）
 */
function dumpTree(maxNodes) {
    if (!B.ready) throw new Error('not bootstrapped');
    const t0 = Date.now();
    maxNodes = maxNodes || 6000;

    // 1) 全部激活 Transform
    const transforms = findAll('Transform').slice(0, maxNodes);

    // 2) 文本组件表: go -> text
    const textMap = {};
    try {
        for (const c of findAll('TMP_Text')) {
            const go = invoke('Component.get_gameObject/0', c, null);
            const text = invoke('TMP_Text.get_text/0', c, null);
            textMap[String(go)] = istr(text);
        }
    } catch (e) { }

    // 3) Selectable 表: go -> interactable
    const selMap = {};
    try {
        for (const c of findAll('Selectable')) {
            const go = invoke('Component.get_gameObject/0', c, null);
            const ok = invoke('Selectable.get_interactable/0', c, null);
            selMap[String(go)] = ok.toInt32() !== 0;
        }
    } catch (e) { }

    // 4) 节点信息
    const nodes = {};
    const list = [];
    for (const t of transforms) {
        try {
            const go = invoke('Component.get_gameObject/0', t, null);
            const name = istr(invoke('GameObject.get_name/0', go, null)) || '';
            const active = invoke('GameObject.get_activeInHierarchy/0', go, null).toInt32() !== 0;
            const parent = invoke('Transform.GetParent/0', t, null);
            let rect = null;
            // 世界坐标 + 缩放 + sizeDelta → 中心/宽高（pivot≈0.5 时近似成立）
            // ⚠️ 仅对真正的 RectTransform 调用 get_sizeDelta（否则 native 侧未定义行为）
            const pos = readBoxedVec3(invoke('Transform.get_position/0', t, null));
            const scale = readBoxedVec3(invoke('Transform.get_lossyScale/0', t, null));
            if (pos && scale) {
                let size = null;
                const klassOfT = t.readPointer();
                if (klassOfT.equals(ptr(B.klass.RectTransform))) {
                    size = readBoxedVec3(invoke('RectTransform.get_sizeDelta/0', t, null));
                }
                rect = {
                    cx: pos[0], cy: pos[1],
                    w: size ? size[0] * scale[0] : 0,
                    h: size ? size[1] * scale[1] : 0,
                };
            }
            const e = {
                t: String(t), go: String(go),
                name: name,
                active: active,
                parent: parent.isNull() ? null : String(parent),
                children: [],
                text: textMap[String(go)] ?? null,
                interactable: (String(go) in selMap) ? selMap[String(go)] : null,
                rect: rect,
            };
            nodes[String(t)] = e;
            list.push(e);
        } catch (e) {
            // 单节点失败不致命
        }
    }

    // 5) 建森林
    const roots = [];
    for (const e of list) {
        if (e.parent && nodes[e.parent]) {
            nodes[e.parent].children.push(e);
        } else {
            roots.push(e);
        }
    }

    return {
        elapsedMs: Date.now() - t0,
        nodeCount: list.length,
        rootCount: roots.length,
        roots: roots,
    };
}

// ---------------------------------------------------------------------------
// RPC
// ---------------------------------------------------------------------------

rpc.exports = {
    /** 存活探测 + 窗口检测 */
    ping: function () {
        try {
            initApi();
            const d = F.domain_get();
            return { ok: true, domain: String(d) };
        } catch (e) {
            return { ok: false, why: String(e).slice(0, 60) };
        }
    },

    /** 执行 bootstrap（窗口内重试，整体超时 2 分钟） */
    bootstrap: function () {
        try {
            return { ok: true, result: call(bootstrap, [], 120000) };
        } catch (e) {
            return { ok: false, err: String(e).slice(0, 200) };
        }
    },

    /** 全量 dump UI 树 */
    dump: function (maxNodes) {
        try {
            return { ok: true, tree: call(dumpTree, [maxNodes], 120000) };
        } catch (e) {
            return { ok: false, err: String(e).slice(0, 200) };
        }
    },

    /** 引导状态 */
    state: function () {
        return { ready: B.ready, classes: B.klass, methods: B.method };
    },
};

send({ agentLoaded: true });
