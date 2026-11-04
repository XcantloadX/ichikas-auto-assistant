/**
 * iaa guest agent (arm64, C++) — 注入 Unity il2cpp 游戏进程的宿内代理。
 *
 * 加载路径：frida(Java) → System.load() → ART → guest linker → houdini 转译执行。
 * 由于我们是 guest 代码，可直接调用 libil2cpp 导出，不经任何 trampoline 门控。
 *
 * 解析层基于 UnityResolve.hpp（third_party/，MIT）：
 *   - Init 时枚举全部程序集/类/方法，之后按名字取 Method* 直接 Invoke
 *   - 不依赖任何静态元数据（dump.cs 等），游戏更新无需重新生成
 *
 * 功能：
 *  1. il2cpp domain attach + UnityResolve 初始化
 *  2. 按需 dump UI 树（FindObjectsOfType<Transform> + 父子/名字/文本/交互性/矩形）
 *  3. TCP 服务（0.0.0.0:29170），每连接一请求一响应，JSON 行协议：
 *       {"cmd":"ping"}                  → {"ok":true,"agent":"iaa","il2cpp":true}
 *       {"cmd":"boot"}                  → {"ok":true}   （幂等）
 *       {"cmd":"dbg"}                   → 调试：前几个 Transform 名字
 *       {"cmd":"dump","max":6000}       → {"ok":true,"n":N,"nodes":[...]}
 *
 * 产出节点字段（宿主侧 build_forest 建树 + 换算屏幕坐标）：
 *   t/go=对象指针, name, active, parent, cc, text?, ia?, rect=[cx,cy,w,h],
 *   px?=[x,y,w,h]（PixelAdjustRect 像素级屏幕矩形，y 自底部起；
 *   Screen Space-Camera 的 Canvas——如 Layer_Scenario——只有 px 可靠）
 */
#include <jni.h>
#include <android/log.h>

#include <cctype>
#include <unordered_map>
#include <vector>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <dlfcn.h>
#include <netinet/in.h>
#include <pthread.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#include "UnityResolve/UnityResolve.hpp"

#define LOG_TAG "iaa_agent"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

#define AGENT_PORT 29170

/* ------------------------------------------------------------------ */
/* 方法句柄缓存（UnityResolve::Init 枚举后按名字取用）                    */
/* ------------------------------------------------------------------ */

using UR = UnityResolve;

namespace {

UR::Assembly* core = nullptr;
UR::Method* M_go_name = nullptr;         // GameObject.get_name
UR::Method* M_go_active_h = nullptr;     // GameObject.get_activeInHierarchy
UR::Method* M_comp_go = nullptr;         // Component.get_gameObject
UR::Method* M_comp_transform = nullptr;  // Component.get_transform
UR::Method* M_t_parent = nullptr;        // Transform.GetParent
UR::Method* M_t_childcount = nullptr;    // Transform.get_childCount
UR::Method* M_t_position = nullptr;      // Transform.get_position
UR::Method* M_t_scale = nullptr;         // Transform.get_lossyScale
UR::Method* M_rt_sizedelta = nullptr;    // RectTransform.get_sizeDelta
UR::Method* M_tmp_text = nullptr;        // TMP_Text.get_text
UR::Method* M_sel_interactable = nullptr;// Selectable.get_interactable
UR::Method* M_find_all = nullptr;        // Object.FindObjectsOfType(Type)
UR::Method* M_get_world_corners = nullptr; // RectTransform.GetWorldCorners(Vector3[4])（可选）
UR::Method* M_canvas_render_mode = nullptr; // Canvas.get_renderMode（可选）
UR::Method* M_canvas_world_camera = nullptr; // Canvas.get_worldCamera（可选）
UR::Method* M_w2s = nullptr;             // Camera.WorldToScreenPoint(Vector3)（可选）
UR::Method* M_img_sprite = nullptr;      // Image.get_sprite（可选，UI 图标身份）
UR::Method* M_obj_name = nullptr;        // Object.get_name（Sprite 名等，可选）
UR::Method* M_renderer_bounds = nullptr; // Renderer.get_bounds（可选，3D 定位）
UR::Method* M_cam_main = nullptr;        // Camera.get_main（静态，可选）
UR::Class* K_RectTransform = nullptr;    // 用于 klass 指针比较
UR::Class* K_Transform = nullptr;
UR::Class* K_TmpText = nullptr;
UR::Class* K_Selectable = nullptr;
UR::Class* K_Canvas = nullptr;
UR::Class* K_Vector3 = nullptr;
UR::Class* K_Image = nullptr;            // UnityEngine.UI.Image
UR::Class* K_Renderer = nullptr;         // UnityEngine.Renderer
void* g_corners_arr = nullptr;           // Vector3[4] 复用缓冲（GetWorldCorners 出参）

/* bootstrap 完成后置 1：handle_client 依此决定是否 ThreadAttach */
volatile int g_bootstrapped = 0;

/**
 * 与旧 C agent 逐字节一致的 runtime_invoke 语义（本仓库实测验证过的路径）：
 * params[i] 直接作为引用类型实参（il2cpp 对引用类型不再解引用）、
 * exc 传有效槽位。不用 Method::RuntimeInvoke：其以 &arg（指向实参的指针）
 * 构造 params，对本环境的 il2cpp 会导致 FindObjectsOfType 收到栈地址。
 */
/* 最近一次 runtime_invoke 的异常对象（诊断用） */
void* g_last_exc = nullptr;

void* rt_invoke(UR::Method* m, void* obj, void** params) {
    if (!m) return nullptr;
    void* exc = nullptr;
    void* r = UR::Invoke<void*>("il2cpp_runtime_invoke", m->address, obj, params, &exc);
    g_last_exc = exc;
    return r;
}

/**
 * Camera.WorldToScreenPoint(Vector3)：值类型参数的传递约定在 il2cpp 上
 * 存在两种实现（指针到未装箱值 / 装箱对象）。先按 mono 约定传栈上值，
 * 失败自动改传装箱 Vector3 并记住结果。
 */
void* invoke_w2s(void* cam, const float* v) {
    static int boxed_conv = -1; /* -1 未知, 0 指针, 1 装箱 */
    if (boxed_conv != 1) {
        void* params[1] = { const_cast<float*>(v) };
        void* r = rt_invoke(M_w2s, cam, params);
        if (r) { boxed_conv = 0; return r; }
    }
    if (K_Vector3) {
        void* b = UR::Invoke<void*>("il2cpp_object_new", K_Vector3->address);
        if (b) {
            memcpy(reinterpret_cast<char*>(b) + 0x10, v, 12);
            void* params[1] = { b };
            void* r = rt_invoke(M_w2s, cam, params);
            if (r) { boxed_conv = 1; return r; }
        }
    }
    return nullptr;
}

/* runtime_invoke 对值类型返回装箱对象指针（klass/monitor 头 0x10B + 值），
   不能直接把指针当值用。 */
int read_boxed_int(void* boxed) {
    if (!boxed) return 0;
    return *reinterpret_cast<int*>(reinterpret_cast<char*>(boxed) + 0x10);
}

int read_boxed_bool(void* boxed) {
    if (!boxed) return 0;
    return *reinterpret_cast<unsigned char*>(reinterpret_cast<char*>(boxed) + 0x10) != 0;
}

void read_vec3(void* boxed, float* o) {
    if (!boxed) { o[0] = o[1] = o[2] = 0.f; return; }
    const float* f = reinterpret_cast<float*>(reinterpret_cast<char*>(boxed) + 0x10);
    o[0] = f[0]; o[1] = f[1]; o[2] = f[2];
}

/* 直接读 il2cpp String 对象（length@0x10, UTF-16 chars@0x14），自行转 UTF-8。
   不用 UnityResolve::String::ToString：其以 4 字节 wchar_t 读 UTF-16 缓冲，
   仅在 wchar_t==2 字节的平台（Windows）正确；且带抛弃代理对。
   返回 malloc 的 C 字符串（调用方 free），失败返回 NULL。 */
char* mono_string_to_utf8(void* str) {
    if (!str) return nullptr;
    const int slen = *reinterpret_cast<int*>(reinterpret_cast<char*>(str) + 0x10);
    if (slen < 0 || slen > 8192) return nullptr;
    const auto* u16 = reinterpret_cast<const unsigned short*>(reinterpret_cast<char*>(str) + 0x14);
    char* out = static_cast<char*>(malloc(static_cast<size_t>(slen) * 4 + 1));
    if (!out) return nullptr;
    size_t o = 0;
    for (int i = 0; i < slen; i++) {
        unsigned int c = u16[i];
        if (c >= 0xD800 && c < 0xDC00 && i + 1 < slen) {
            const unsigned int lo = u16[i + 1];
            if (lo >= 0xDC00 && lo < 0xE000) {
                c = 0x10000 + ((c - 0xD800) << 10) + (lo - 0xDC00);
                i++;
            }
        }
        if (c < 0x80) {
            out[o++] = static_cast<char>(c);
        } else if (c < 0x800) {
            out[o++] = static_cast<char>(0xC0 | (c >> 6));
            out[o++] = static_cast<char>(0x80 | (c & 0x3F));
        } else if (c < 0x10000) {
            out[o++] = static_cast<char>(0xE0 | (c >> 12));
            out[o++] = static_cast<char>(0x80 | ((c >> 6) & 0x3F));
            out[o++] = static_cast<char>(0x80 | (c & 0x3F));
        } else {
            out[o++] = static_cast<char>(0xF0 | (c >> 18));
            out[o++] = static_cast<char>(0x80 | ((c >> 12) & 0x3F));
            out[o++] = static_cast<char>(0x80 | ((c >> 6) & 0x3F));
            out[o++] = static_cast<char>(0x80 | (c & 0x3F));
        }
    }
    out[o] = 0;
    return out;
}

/* 输出缓冲区（每连接独立；容量按 maxNodes 估算） */
struct obuf {
    char* data;
    size_t cap;
    size_t len;
};

void ob_put(struct obuf* o, const char* s) {
    const size_t n = strlen(s);
    if (o->len + n + 1 > o->cap) return;
    memcpy(o->data + o->len, s, n);
    o->len += n;
    o->data[o->len] = 0;
}

void ob_put_json_str(struct obuf* o, const char* s) {
    if (o->len + 2 > o->cap) return;
    o->data[o->len++] = '"';
    for (const auto* c = reinterpret_cast<const unsigned char*>(s ? s : ""); *c; c++) {
        if (o->len + 8 > o->cap) break;
        const unsigned char ch = *c;
        if (ch == '"' || ch == '\\') {
            o->data[o->len++] = '\\';
            o->data[o->len++] = ch;
        } else if (ch == '\n') {
            memcpy(o->data + o->len, "\\n", 2);
            o->len += 2;
        } else if (ch == '\r' || ch == '\t') {
            o->data[o->len++] = ' ';
        } else if (ch >= 0x20) {
            /* UTF-8 字节透传（合法 JSON） */
            o->data[o->len++] = ch;
        }
    }
    o->data[o->len++] = '"';
}

void ob_put_int(struct obuf* o, const long v) {
    char tmp[32];
    snprintf(tmp, sizeof(tmp), "%ld", v);
    ob_put(o, tmp);
}

void ob_put_float(struct obuf* o, const float v) {
    char tmp[32];
    snprintf(tmp, sizeof(tmp), "%.2f", v);
    ob_put(o, tmp);
}

/* ------------------------------------------------------------------ */
/* bootstrap                                                            */
/* ------------------------------------------------------------------ */

/**
 * 沿继承链解析方法句柄（UnityResolve::Class::Get 只搜本类，而
 * il2cpp_class_get_method_from_name 会向上搜基类——get_name 等声明在
 * UnityEngine.Object 上，必须走继承链）。找不到返回 nullptr。
 */
UR::Method* resolve_in_hierarchy(UR::Assembly* asm_, UR::Class* klass, const char* name, const int argc) {
    if (!asm_ || !klass) return nullptr;
    UR::Class* c = klass;
    for (int depth = 0; c && depth < 8; depth++) {
        if (auto* m = c->Get<UR::Method>(name, argc ? std::vector<std::string>(static_cast<size_t>(argc), "*") : std::vector<std::string>{}))
            return m;
        if (c->parent.empty()) break;
        c = asm_->Get(c->parent);
    }
    return nullptr;
}

/* 最近一次 bootstrap 失败原因（协议可见，反作弊环境下 logcat 不可依赖） */
char g_boot_err[256] = {0};

/**
 * 跨全部程序集按 名字+命名空间 找类（类所在模块因 Unity 版本/裁剪而异，
 * 如 Canvas/RectTransformUtility 在 UnityEngine.UIModule 而非 CoreModule/UI）。
 */
UR::Class* find_class_all(const char* name, const char* ns) {
    for (auto* a : UR::assembly) {
        if (!a) continue;
        if (auto* k = a->Get(name, ns)) return k;
    }
    return nullptr;
}

/**
 * 可选句柄：Camera Canvas 的屏幕矩形（GetWorldCorners + WorldToScreenPoint）。
 * 幂等；解析失败仅降级（宿主对 Overlay 用世界坐标换算，本就正确）。
 *
 * .. NOTE:: il2cpp 裁剪会把游戏未调用的方法体 strip（metadata 在而
 *    methodInfo->address=0），故这里校验 address，避免 invoke 空指针。
 *    实测 PixelAdjustRect 返回的是节点本地 rect（pivot 居中），非屏幕空间，
 *    不可用；GetComponentInParent(Type) 也被本游戏裁剪。
 */
void ensure_pixel_handles() {
    if (M_get_world_corners && M_w2s && g_corners_arr) return;
    if (!core) return;
    if (!K_Vector3) K_Vector3 = find_class_all("Vector3", "UnityEngine");
    auto* K_camera = find_class_all("Camera", "UnityEngine");
    if (!K_Canvas) K_Canvas = find_class_all("Canvas", "UnityEngine");
    if (K_Vector3 && !g_corners_arr)
        g_corners_arr = UR::Invoke<void*>("il2cpp_array_new", K_Vector3->address, 4);
    if (K_RectTransform && !M_get_world_corners) {
        if (auto* m = resolve_in_hierarchy(core, K_RectTransform, "GetWorldCorners", 1))
            if (m->address) M_get_world_corners = m;
    }
    if (K_Canvas) {
        if (!M_canvas_render_mode) {
            if (auto* m = resolve_in_hierarchy(core, K_Canvas, "get_renderMode", 0))
                if (m->address) M_canvas_render_mode = m;
        }
        if (!M_canvas_world_camera) {
            if (auto* m = resolve_in_hierarchy(core, K_Canvas, "get_worldCamera", 0))
                if (m->address) M_canvas_world_camera = m;
        }
    }
    if (K_camera && !M_w2s) {
        if (auto* m = K_camera->Get<UR::Method>("WorldToScreenPoint", std::vector<std::string>{"*"}))
            if (m->address) M_w2s = m;
    }
    /* UI 图标身份（sprite 名）+ 3D 定位（Renderer bounds 投影）句柄。
       与 UI/3D 定位协议分离对应：spr 字段进 UI dump，3D 走 find3d 命令。 */
    if (!K_Image) {
        if (auto* ui_asm2 = UR::Get("UnityEngine.UI.dll")) K_Image = ui_asm2->Get("Image", "UnityEngine.UI");
        if (!K_Image && core) K_Image = core->Get("Image", "UnityEngine.UI");
    }
    if (K_Image && !M_img_sprite) {
        if (auto* m = resolve_in_hierarchy(core, K_Image, "get_sprite", 0))
            if (m->address) M_img_sprite = m;
    }
    if (core && !M_obj_name) {
        if (auto* K_obj = core->Get("Object", "UnityEngine")) {
            if (auto* m = resolve_in_hierarchy(core, K_obj, "get_name", 0))
                if (m->address) M_obj_name = m;
        }
    }
    if (!K_Renderer) K_Renderer = find_class_all("Renderer", "UnityEngine");
    if (K_Renderer && !M_renderer_bounds) {
        if (auto* m = resolve_in_hierarchy(core, K_Renderer, "get_bounds", 0))
            if (m->address) M_renderer_bounds = m;
    }
    if (K_camera && !M_cam_main) {
        if (auto* m = K_camera->Get<UR::Method>("get_main", std::vector<std::string>{}))
            if (m->address) M_cam_main = m;
    }
    LOGI("pixel handles: corners=%d arr=%d rmode=%d wcam=%d w2s=%d sprite=%d objname=%d bounds=%d cammain=%d",
         M_get_world_corners != nullptr, g_corners_arr != nullptr,
         M_canvas_render_mode != nullptr, M_canvas_world_camera != nullptr, M_w2s != nullptr,
         M_img_sprite != nullptr, M_obj_name != nullptr,
         M_renderer_bounds != nullptr, M_cam_main != nullptr);
}

#define BOOT_FAIL(msg)                                                                       \
    do {                                                                                     \
        LOGE("%s", msg);                                                                     \
        snprintf(g_boot_err, sizeof(g_boot_err), "%s", msg);                                  \
        g_boot_err[sizeof(g_boot_err) - 1] = 0;                                               \
        return -1;                                                                           \
    } while (0)

int bootstrap() {
    /* il2cpp 已加载（init_thread 轮询过 dlsym），拿句柄做全量枚举 */
    void* handle = dlopen("libil2cpp.so", RTLD_NOLOAD | RTLD_LAZY);
    if (!handle) {
        /* 兜底：某些设备上 so 名带变体 */
        handle = dlopen(nullptr, RTLD_LAZY); /* 全局句柄：导出表里也有 il2cpp_* */
    }
    if (!handle) BOOT_FAIL("libil2cpp handle not found");

    const auto t0 = time(nullptr);
    UR::Init(handle, UR::Mode::Il2Cpp);
    LOGI("UnityResolve::Init took %lds, %zu assemblies", static_cast<long>(time(nullptr) - t0), UR::assembly.size());
    if (UR::assembly.empty()) BOOT_FAIL("UnityResolve enumerated 0 assemblies");

    core = UR::Get("UnityEngine.CoreModule.dll");
    if (!core) BOOT_FAIL("UnityEngine.CoreModule.dll not found");

    auto* ui_asm = UR::Get("UnityEngine.UI.dll");
    if (!ui_asm) ui_asm = core;
    auto* tmp_asm = UR::Get("Unity.TextMeshPro.dll");
    if (!tmp_asm) tmp_asm = core;

    auto* K_GO = core->Get("GameObject", "UnityEngine");
    K_Transform = core->Get("Transform", "UnityEngine");
    K_RectTransform = core->Get("RectTransform", "UnityEngine");
    auto* K_Component = core->Get("Component", "UnityEngine");
    K_TmpText = tmp_asm->Get("TMP_Text", "TMPro");
    K_Selectable = ui_asm->Get("Selectable", "UnityEngine.UI");
    auto* K_Object = core->Get("Object", "UnityEngine");

    if (!K_GO || !K_Transform || !K_RectTransform || !K_Component || !K_TmpText || !K_Selectable || !K_Object) {
        snprintf(g_boot_err, sizeof(g_boot_err),
                 "class resolution failed: go=%d t=%d rt=%d comp=%d tmp=%d sel=%d obj=%d",
                 K_GO != nullptr, K_Transform != nullptr, K_RectTransform != nullptr,
                 K_Component != nullptr, K_TmpText != nullptr, K_Selectable != nullptr,
                 K_Object != nullptr);
        LOGE("%s", g_boot_err);
        return -1;
    }

    M_go_name = resolve_in_hierarchy(core, K_GO, "get_name", 0);
    M_go_active_h = resolve_in_hierarchy(core, K_GO, "get_activeInHierarchy", 0);
    M_comp_go = resolve_in_hierarchy(core, K_Component, "get_gameObject", 0);
    M_comp_transform = resolve_in_hierarchy(core, K_Component, "get_transform", 0);
    M_t_parent = resolve_in_hierarchy(core, K_Transform, "GetParent", 0);
    M_t_childcount = resolve_in_hierarchy(core, K_Transform, "get_childCount", 0);
    M_t_position = resolve_in_hierarchy(core, K_Transform, "get_position", 0);
    M_t_scale = resolve_in_hierarchy(core, K_Transform, "get_lossyScale", 0);
    M_rt_sizedelta = resolve_in_hierarchy(core, K_RectTransform, "get_sizeDelta", 0);
    M_tmp_text = resolve_in_hierarchy(tmp_asm, K_TmpText, "get_text", 0);
    M_sel_interactable = resolve_in_hierarchy(ui_asm, K_Selectable, "get_interactable", 0);
    M_find_all = resolve_in_hierarchy(core, K_Object, "FindObjectsOfType", 1);

    /* 可选句柄（失败不作 bootstrap 失败条件；dump 前会兜底重试） */
    ensure_pixel_handles();

    if (!M_go_name || !M_go_active_h || !M_comp_go || !M_comp_transform || !M_t_parent || !M_t_childcount
        || !M_t_position || !M_t_scale || !M_rt_sizedelta || !M_tmp_text
        || !M_sel_interactable || !M_find_all) {
        snprintf(g_boot_err, sizeof(g_boot_err),
                 "method resolution failed: name=%d active=%d go=%d parent=%d cc=%d pos=%d scale=%d sd=%d text=%d ia=%d findall=%d",
                 M_go_name != nullptr, M_go_active_h != nullptr, M_comp_go != nullptr,
                 M_t_parent != nullptr, M_t_childcount != nullptr, M_t_position != nullptr,
                 M_t_scale != nullptr, M_rt_sizedelta != nullptr, M_tmp_text != nullptr,
                 M_sel_interactable != nullptr, M_find_all != nullptr);
        LOGE("%s", g_boot_err);
        return -1;
    }

    LOGI("bootstrap ok");
    g_boot_err[0] = 0;
    g_bootstrapped = 1;
    return 0;
}

/* ------------------------------------------------------------------ */
/* dump                                                                */
/* ------------------------------------------------------------------ */

struct node_rec {
    void* transform;
    void* gameobject;
    char* name;            /* malloc 所有权归本结构 */
    int active;
    void* parent;
    int child_count;
    char* text;            /* 可为 NULL；malloc 所有权归本结构 */
    char* sprite;          /* Image.sprite 名（图标身份）；可为 NULL；malloc 归本结构 */
    int interactable;      /* -1 未知 */
    float cx, cy, w, h;    /* 世界矩形；has_rect=0 时无效 */
    int has_rect;
    float px_x, px_y, px_w, px_h; /* 像素级屏幕矩形（y 自底部起，PixelAdjustRect 语义）；has_px=1 时有效 */
    int has_px;
};

int find_all_transforms(void*** out, const int max) {
    /* Object.FindObjectsOfType(typeof(Transform)) 静态调用 */
    if (!M_find_all || !K_Transform) return -1;
    void* type_obj = K_Transform->GetType();
    if (!type_obj) return -1;
    void* params[1] = { type_obj };
    void* arr = rt_invoke(M_find_all, nullptr, params);
    if (!arr) return -1;
    /* il2cpp 数组布局：klass/monitor 头 0x10 + length@0x18? 
       实测稳定布局：max_length@0x18，数据从 0x20 开始 */
    const auto n = *reinterpret_cast<uintptr_t*>(reinterpret_cast<char*>(arr) + 0x18);
    const auto cnt = n < static_cast<uintptr_t>(max) ? n : static_cast<uintptr_t>(max);
    auto* items = reinterpret_cast<void**>(reinterpret_cast<char*>(arr) + 0x20);
    for (uintptr_t i = 0; i < cnt; i++) (*out)[i] = items[i];
    return static_cast<int>(cnt);
}

int dump_tree(struct obuf* o, const int max_nodes) {
    /* boot 时程序集可能未加载全（标题画面 158 个 vs 全量 2528 个），
       每次 dump 兜底重试可选句柄 */
    ensure_pixel_handles();

    auto** transforms = static_cast<void**>(malloc(sizeof(void*) * max_nodes));
    auto* recs = static_cast<node_rec*>(malloc(sizeof(node_rec) * max_nodes));
    if (!transforms || !recs) { free(transforms); free(recs); return -1; }
    memset(recs, 0, sizeof(node_rec) * max_nodes);

    const int n = find_all_transforms(&transforms, max_nodes);
    if (n < 0) { free(transforms); free(recs); return -1; }

    /* Canvas 组件表：FindObjectsOfType(Canvas) → 其 Transform 指针。
       GetComponentInParent(Type) 在本游戏被裁剪（address=0）不可用，
       改由节点沿 parent 链回溯查此表（见下方二次扫描）。 */
    void** canvas_ts = nullptr;
    void** canvas_cs = nullptr;
    int n_canvas = 0;
    void* type_canvas = K_Canvas ? K_Canvas->GetType() : nullptr;
    if (M_find_all && type_canvas) {
        void* find_params[1] = { type_canvas };
        if (void* arr = rt_invoke(M_find_all, nullptr, find_params)) {
            const auto cnt = *reinterpret_cast<uintptr_t*>(reinterpret_cast<char*>(arr) + 0x18);
            auto* items = reinterpret_cast<void**>(reinterpret_cast<char*>(arr) + 0x20);
            const auto cap = cnt < 32 ? cnt : 32;
            canvas_ts = static_cast<void**>(malloc(sizeof(void*) * cap));
            canvas_cs = static_cast<void**>(malloc(sizeof(void*) * cap));
            for (uintptr_t i = 0; i < cnt && n_canvas < static_cast<int>(cap); i++) {
                void* c = items[i];
                /* Component.get_transform：Canvas 组件自身即挂在该 GameObject 上 */
                void* t = rt_invoke(M_comp_transform, c, nullptr);
                if (!t) continue;
                canvas_ts[n_canvas] = t;
                canvas_cs[n_canvas] = c;
                n_canvas++;
            }
        }
    }

    /* 逐节点收集 */
    int m = 0;
    int gip_fail = 0, pa_fail = 0, px_ok = 0;
    for (int i = 0; i < n; i++) {
        void* t = transforms[i];
        node_rec* r = &recs[m];
        memset(r, 0, sizeof(*r));
        r->interactable = -1;
        r->transform = t;
        void* go = rt_invoke(M_comp_go, t, nullptr);
        if (!go) continue;
        r->gameobject = go;
        r->name = mono_string_to_utf8(rt_invoke(M_go_name, go, nullptr));
        r->active = read_boxed_bool(rt_invoke(M_go_active_h, go, nullptr));
        r->parent = rt_invoke(M_t_parent, t, nullptr);
        r->child_count = read_boxed_int(rt_invoke(M_t_childcount, t, nullptr));
        /* 矩形：仅对 klass==RectTransform 调 sizeDelta */
        const void* klass = *reinterpret_cast<void**>(t);
        if (klass == K_RectTransform->address) {
            float pos[3], scale[3], sd[3];
            read_vec3(rt_invoke(M_t_position, t, nullptr), pos);
            read_vec3(rt_invoke(M_t_scale, t, nullptr), scale);
            read_vec3(rt_invoke(M_rt_sizedelta, t, nullptr), sd);
            r->has_rect = 1;
            r->cx = pos[0]; r->cy = pos[1];
            r->w = sd[0] * scale[0];
            if (r->w < 0) r->w = -r->w;
            r->h = sd[1] * scale[1];
            if (r->h < 0) r->h = -r->h;
        }
        m++;
    }

    /* 像素级矩形二次扫描：transform→rec 索引 + Canvas transform→组件映射，
       节点沿 parent 链（已在 recs 内，零 invoke）找到所属 Canvas。
       - Camera Canvas（renderMode≠Overlay 且 worldCamera 可用）：四角
         GetWorldCorners 后逐角 WorldToScreenPoint，px=真实屏幕像素
         （y 自底部起）。Screen Space-Camera 的 Canvas——如 Layer_Scenario
         ——只有此路径可靠。
       - Overlay Canvas：不产出 px，宿主用世界坐标×画布比例换算（正确）。
     */
    if (M_get_world_corners && g_corners_arr && n_canvas > 0) {
        std::unordered_map<void*, int> t2i;
        t2i.reserve(static_cast<size_t>(m) * 2);
        for (int j = 0; j < m; j++) t2i[recs[j].transform] = j;
        std::unordered_map<void*, void*> t2canvas;
        t2canvas.reserve(static_cast<size_t>(n_canvas) * 2);
        for (int i = 0; i < n_canvas; i++) t2canvas[canvas_ts[i]] = canvas_cs[i];
        for (int j = 0; j < m; j++) {
            node_rec* r = &recs[j];
            if (!r->has_rect) continue;
            int idx = j;
            void* canvas = nullptr;
            for (int hops = 0; idx >= 0 && hops < 64; hops++) {
                const auto it = t2canvas.find(recs[idx].transform);
                if (it != t2canvas.end()) { canvas = it->second; break; }
                const auto pit = t2i.find(recs[idx].parent);
                if (pit == t2i.end()) break;
                idx = pit->second;
            }
            if (!canvas) { gip_fail++; continue; }
            /* Overlay：宿主启发式已正确，跳过 */
            if (M_canvas_render_mode) {
                const int rm = read_boxed_int(rt_invoke(M_canvas_render_mode, canvas, nullptr));
                if (rm == 0) continue;
            }
            if (!M_canvas_world_camera || !M_w2s) continue;
            void* cam = rt_invoke(M_canvas_world_camera, canvas, nullptr);
            if (!cam) continue;
            void* params[1] = { g_corners_arr };
            rt_invoke(M_get_world_corners, r->transform, params);
            const float* f = reinterpret_cast<const float*>(reinterpret_cast<char*>(g_corners_arr) + 0x20);
            float xmin = 0, xmax = 0, ymin = 0, ymax = 0;
            for (int c2 = 0; c2 < 4; c2++) {
                const float* p = &f[c2 * 3];
                void* boxed = invoke_w2s(cam, p);
                if (!boxed) { xmin = 0; xmax = -1; break; } /* 投影失败标记 */
                const float* s = reinterpret_cast<const float*>(reinterpret_cast<char*>(boxed) + 0x10);
                if (c2 == 0) { xmin = xmax = s[0]; ymin = ymax = s[1]; }
                else {
                    xmin = xmin < s[0] ? xmin : s[0];
                    xmax = xmax > s[0] ? xmax : s[0];
                    ymin = ymin < s[1] ? ymin : s[1];
                    ymax = ymax > s[1] ? ymax : s[1];
                }
            }
            if (xmax > xmin) {
                r->px_x = xmin; r->px_y = ymin;
                r->px_w = xmax - xmin; r->px_h = ymax - ymin;
                r->has_px = 1;
                px_ok++;
            } else {
                pa_fail++;
                if (pa_fail == 1 && g_last_exc) {
                    /* 诊断：投影失败的异常类名（只记第一次） */
                    void* klass = UR::Invoke<void*>("il2cpp_object_get_class", g_last_exc);
                    const char* nm = klass ? UR::Invoke<const char*>("il2cpp_class_get_name", klass) : nullptr;
                    LOGI("w2s exc: %s", nm ? nm : "(null)");
                }
            }
        }
    }
    free(canvas_ts);
    free(canvas_cs);

    /* 文本映射表：TMP_Text 全量建表 */
    if (K_TmpText) {
        if (void* type = K_TmpText->GetType()) {
        void* params[1] = { type };
                void* arr = rt_invoke(M_find_all, nullptr, params);
        if (arr) {
            const auto cnt = *reinterpret_cast<uintptr_t*>(reinterpret_cast<char*>(arr) + 0x18);
            auto* items = reinterpret_cast<void**>(reinterpret_cast<char*>(arr) + 0x20);
            for (uintptr_t i = 0; i < cnt; i++) {
                void* c = items[i];
                void* go = rt_invoke(M_comp_go, c, nullptr);
                if (!go) continue;
                char* txt = mono_string_to_utf8(rt_invoke(M_tmp_text, c, nullptr));
                int assigned = 0;
                for (int j = 0; j < m; j++) {
                    if (recs[j].gameobject == go && !recs[j].text) {
                        recs[j].text = txt;
                        assigned = 1;
                        break;
                    }
                }
                if (!assigned) free(txt);
            }
        }
        }
    }
    /* UI 图标身份映射表：Image → sprite 名（go 指针 → 名字，线性查找代价
       与 TMP 文本表同量级；sprite 名是重名图标节点唯一可区分的身份） */
    if (M_img_sprite && M_obj_name && K_Image) {
        if (void* type = K_Image->GetType()) {
            void* params[1] = { type };
            void* arr = rt_invoke(M_find_all, nullptr, params);
            if (arr) {
                const auto cnt = *reinterpret_cast<uintptr_t*>(reinterpret_cast<char*>(arr) + 0x18);
                auto* items = reinterpret_cast<void**>(reinterpret_cast<char*>(arr) + 0x20);
                for (uintptr_t i = 0; i < cnt; i++) {
                    void* c = items[i];
                    void* go = rt_invoke(M_comp_go, c, nullptr);
                    if (!go) continue;
                    void* sp = rt_invoke(M_img_sprite, c, nullptr);
                    if (!sp) continue;
                    char* nm = mono_string_to_utf8(rt_invoke(M_obj_name, sp, nullptr));
                    if (!nm) continue;
                    for (int j = 0; j < m; j++) {
                        if (recs[j].gameobject == go && !recs[j].sprite) {
                            recs[j].sprite = nm;
                            break;
                        }
                    }
                }
            }
        }
    }
    /* 交互性映射表 */
    if (K_Selectable) {
        if (void* type = K_Selectable->GetType()) {
                void* params[1] = { type };
                void* arr = rt_invoke(M_find_all, nullptr, params);
                if (arr) {
                    const auto cnt = *reinterpret_cast<uintptr_t*>(reinterpret_cast<char*>(arr) + 0x18);
                    auto* items = reinterpret_cast<void**>(reinterpret_cast<char*>(arr) + 0x20);
                    for (uintptr_t i = 0; i < cnt; i++) {
                        void* c = items[i];
                        void* go = rt_invoke(M_comp_go, c, nullptr);
                        if (!go) continue;
                        void* ok = rt_invoke(M_sel_interactable, c, nullptr);
                        for (int j = 0; j < m; j++) {
                            if (recs[j].gameobject == go) {
                                recs[j].interactable = read_boxed_bool(ok);
                                break;
                            }
                        }
                    }
                }
            }
        }

    /* 输出：nodes 数组（宿主侧建树） */
    ob_put(o, "{\"ok\":true,\"n\":");
    ob_put_int(o, m);
    ob_put(o, ",\"pxok\":");  ob_put_int(o, px_ok);
    ob_put(o, ",\"gipfail\":"); ob_put_int(o, gip_fail);
    ob_put(o, ",\"pafail\":"); ob_put_int(o, pa_fail);
    ob_put(o, ",\"nodes\":[");
    for (int j = 0; j < m; j++) {
        node_rec* r = &recs[j];
        if (j) ob_put(o, ",");
        ob_put(o, "{\"t\":\"");
        ob_put_int(o, reinterpret_cast<long>(r->transform));
        ob_put(o, "\",\"go\":\"");
        ob_put_int(o, reinterpret_cast<long>(r->gameobject));
        ob_put(o, "\",\"name\":");
        ob_put_json_str(o, r->name);
        ob_put(o, ",\"active\":");
        ob_put_int(o, r->active);
        ob_put(o, ",\"parent\":\"");
        ob_put_int(o, reinterpret_cast<long>(r->parent));
        ob_put(o, "\",\"cc\":");
        ob_put_int(o, r->child_count);
        if (r->text) { ob_put(o, ",\"text\":"); ob_put_json_str(o, r->text); }
        if (r->sprite) { ob_put(o, ",\"spr\":"); ob_put_json_str(o, r->sprite); }
        if (r->interactable >= 0) { ob_put(o, ",\"ia\":"); ob_put_int(o, r->interactable); }
        if (r->has_rect) {
            ob_put(o, ",\"rect\":[");
            ob_put_float(o, r->cx); ob_put(o, ",");
            ob_put_float(o, r->cy); ob_put(o, ",");
            ob_put_float(o, r->w); ob_put(o, ",");
            ob_put_float(o, r->h);
            ob_put(o, "]");
        }
        if (r->has_px) {
            ob_put(o, ",\"px\":[");
            ob_put_float(o, r->px_x); ob_put(o, ",");
            ob_put_float(o, r->px_y); ob_put(o, ",");
            ob_put_float(o, r->px_w); ob_put(o, ",");
            ob_put_float(o, r->px_h);
            ob_put(o, "]");
        }
        ob_put(o, "}");
    }
    ob_put(o, "]}");

    for (int j = 0; j < m; j++) {
        free(recs[j].name);
        free(recs[j].text);
        free(recs[j].sprite);
    }
    free(transforms);
    free(recs);
    return m;
}

/* ------------------------------------------------------------------ */
/* TCP 服务                                                            */
/* ------------------------------------------------------------------ */

void* handle_client(void* arg) {
    const int fd = static_cast<int>(reinterpret_cast<intptr_t>(arg));
    char req[256];
    /* 本线程要用 il2cpp_runtime_invoke，先挂到 il2cpp domain（幂等）。
       必须在 Init 之后：ThreadAttach 依赖 Init 缓存的 pDomain，
       boot 前调用会 il2cpp_thread_attach(NULL) 挂死。 */
    if (g_bootstrapped) UR::ThreadAttach();
    obuf o;
    o.cap = 4 * 1024 * 1024;
    o.data = static_cast<char*>(malloc(o.cap));
    if (!o.data) { close(fd); return nullptr; }

    const ssize_t n = recv(fd, req, sizeof(req) - 1, 0);
    if (n <= 0) { free(o.data); close(fd); return nullptr; }
    req[n] = 0;

    o.len = 0;
    o.data[0] = 0;

    if (strstr(req, "\"ping\"")) {
        ob_put(&o, "{\"ok\":true,\"agent\":\"iaa\",\"il2cpp\":true}");
    } else if (strstr(req, "\"dbg\"")) {
        /* 调试：直接读 String 对象，输出前几个 Transform 的名字 */
        if (!g_bootstrapped) {
            ob_put(&o, "{\"ok\":false,\"err\":\"not bootstrapped, send boot first\"}");
        } else {
            ob_put(&o, "{\"ok\":true");
            auto** ts = static_cast<void**>(malloc(sizeof(void*) * 8));
            const int nts = find_all_transforms(&ts, 8);
            ob_put(&o, ",\"tn\":");
            ob_put_int(&o, nts);
            if (nts > 0) {
                ob_put(&o, ",\"names\":[");
                for (int i = 0; i < nts && i < 4; i++) {
                    if (i) ob_put(&o, ",");
                    void* go = M_comp_go->RuntimeInvoke<void*>(ts[i]);
                    void* nm = go ? rt_invoke(M_go_name, go, nullptr) : nullptr;
                    ob_put_json_str(&o, mono_string_to_utf8(nm));
                }
                ob_put(&o, "]");
            }
            free(ts);
            ob_put(&o, "}");
        }
    } else if (strstr(req, "\"dump\"")) {
        if (!g_bootstrapped) {
            ob_put(&o, "{\"ok\":false,\"err\":\"not bootstrapped, send boot first\"}");
        } else {
            int max = 6000;
            const char* mp = strstr(req, "\"max\":");
            if (mp) max = atoi(mp + 6);
            if (max > 12000) max = 12000;
            if (dump_tree(&o, max) < 0) {
                o.len = 0;
                ob_put(&o, "{\"ok\":false,\"err\":\"dump failed\"}");
            }
        }
    } else if (strstr(req, "\"boot\"")) {
        /* 幂等：重复 boot 不得重新枚举（二次 UR::Init 有崩溃风险） */
        if (g_bootstrapped) {
            ob_put(&o, "{\"ok\":true,\"cached\":true}");
        } else {
        const int r = bootstrap();
        if (r == 0) {
            ob_put(&o, "{\"ok\":true}");
        } else {
            char tmp[320];
            snprintf(tmp, sizeof(tmp), "bootstrap failed: %s", g_boot_err);
            ob_put(&o, "{\"ok\":false,\"err\":");
            ob_put_json_str(&o, tmp);
            ob_put(&o, "}");
        }
        }
    } else if (strstr(req, "\"find3d\"")) {
        /* 3D 对象定位（独立于 UI dump 域）：FindObjectsOfType(Renderer)，
           按 GameObject 名子串过滤，bounds 8 角经相机投影出屏幕像素矩形。
           请求：{"cmd":"find3d","name":"子串","max":100}（name 可省=全部） */
        if (!g_bootstrapped || !M_renderer_bounds || !M_w2s || !g_corners_arr) {
            ob_put(&o, "{\"ok\":false,\"err\":\"find3d unavailable (not bootstrapped or handles missing)\"}");
        } else {
            ensure_pixel_handles();
            /* 解析 name/max（容忍冒号后空格；GO 名无转义字符） */
            char name[128] = {0};
            const char* np = strstr(req, "\"name\"");
            if (np) {
                np = strchr(np + 6, ':');
                if (np) {
                    while (*++np == ' ') {}
                    if (*np == '"') {
                        np++;
                        size_t ni = 0;
                        while (*np && *np != '"' && ni < sizeof(name) - 1) name[ni++] = *np++;
                        name[ni] = 0;
                    }
                }
            }
            int fmax = 100;
            const char* xp = strstr(req, "\"max\"");
            if (xp) fmax = atoi(strchr(xp + 5, ':') + 1);
            if (fmax > 500) fmax = 500;
            void* cam = nullptr;
            if (M_cam_main) cam = rt_invoke(M_cam_main, nullptr, nullptr);
            if (cam) {
                void* type_obj = K_Renderer ? K_Renderer->GetType() : nullptr;
                void* arr = nullptr;
                if (type_obj) {
                    void* params[1] = { type_obj };
                    arr = rt_invoke(M_find_all, nullptr, params);
                }
                ob_put(&o, "{\"ok\":true,\"items\":[");
                int emitted = 0;
                std::unordered_map<void*, int> seen_go;
                if (arr) {
                    const auto cnt = *reinterpret_cast<uintptr_t*>(reinterpret_cast<char*>(arr) + 0x18);
                    auto* items = reinterpret_cast<void**>(reinterpret_cast<char*>(arr) + 0x20);
                    for (uintptr_t i = 0; i < cnt && emitted < fmax; i++) {
                        void* c = items[i];
                        void* go = rt_invoke(M_comp_go, c, nullptr);
                        if (!go || seen_go.count(go)) continue;
                        seen_go[go] = 1;
                        char* nm = mono_string_to_utf8(rt_invoke(M_go_name, go, nullptr));
                        if (!nm) continue;
                        const bool hit = name[0] == 0 || strstr(nm, name) != nullptr;
                        if (!hit) { free(nm); continue; }
                        void* boxed_b = rt_invoke(M_renderer_bounds, c, nullptr);
                        if (!boxed_b) { free(nm); continue; }
                        const float* bf = reinterpret_cast<const float*>(reinterpret_cast<char*>(boxed_b) + 0x10);
                        const float ctr[3] = { bf[0], bf[1], bf[2] };
                        const float ext[3] = { bf[3], bf[4], bf[5] };
                        float xmin = 0, xmax = -1, ymin = 0, ymax = 0;
                        for (int ci = 0; ci < 8; ci++) {
                            const float p[3] = {
                                ctr[0] + ((ci & 1) ? ext[0] : -ext[0]),
                                ctr[1] + ((ci & 2) ? ext[1] : -ext[1]),
                                ctr[2] + ((ci & 4) ? ext[2] : -ext[2]),
                            };
                            void* boxed = invoke_w2s(cam, p);
                            if (!boxed) { xmin = 0; xmax = -1; break; }
                            const float* s = reinterpret_cast<const float*>(reinterpret_cast<char*>(boxed) + 0x10);
                            if (ci == 0) { xmin = xmax = s[0]; ymin = ymax = s[1]; }
                            else {
                                xmin = xmin < s[0] ? xmin : s[0];
                                xmax = xmax > s[0] ? xmax : s[0];
                                ymin = ymin < s[1] ? ymin : s[1];
                                ymax = ymax > s[1] ? ymax : s[1];
                            }
                        }
                        if (xmax > xmin) {
                            if (emitted) ob_put(&o, ",");
                            ob_put(&o, "{\"name\":");
                            ob_put_json_str(&o, nm);
                            ob_put(&o, ",\"px\":[");
                            ob_put_float(&o, xmin); ob_put(&o, ",");
                            ob_put_float(&o, ymin); ob_put(&o, ",");
                            ob_put_float(&o, xmax - xmin); ob_put(&o, ",");
                            ob_put_float(&o, ymax - ymin);
                            ob_put(&o, "],\"go\":\"");
                            ob_put_int(&o, reinterpret_cast<long>(go));
                            ob_put(&o, "\"}");
                            emitted++;
                        }
                        free(nm);
                    }
                }
                ob_put(&o, "],\"n\":");
                ob_put_int(&o, emitted);
                ob_put(&o, "}");
            } else {
                ob_put(&o, "{\"ok\":false,\"err\":\"no camera (get_main unavailable)\"}");
            }
        }
    } else {
        ob_put(&o, "{\"ok\":false,\"err\":\"unknown cmd\"}");
    }

    ob_put(&o, "\n");
    send(fd, o.data, o.len, 0);
    free(o.data);
    close(fd);
    return nullptr;
}

void accept_loop(const int srv) {
    for (;;) {
        const int c = accept(srv, nullptr, nullptr);
        if (c < 0) continue;
        pthread_t th;
        pthread_create(&th, nullptr, handle_client, reinterpret_cast<void*>(static_cast<intptr_t>(c)));
        pthread_detach(th);
    }
}

void* server_thread(void* /*arg*/) {
    int srv = socket(AF_INET, SOCK_STREAM, 0);
    if (srv >= 0) {
        int one = 1;
        setsockopt(srv, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = htonl(INADDR_ANY);
        addr.sin_port = htons(AGENT_PORT);
        if (bind(srv, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) == 0 && listen(srv, 4) == 0) {
            LOGI("agent listening on 0.0.0.0:%d (inet)", AGENT_PORT);
            accept_loop(srv);
            return nullptr;
        }
        LOGE("inet bind failed errno=%d", errno);
        close(srv);
    } else {
        LOGE("socket failed errno=%d", errno);
    }

    /* 回退：abstract unix socket "iaa_agent"（adb forward localabstract 支持） */
    srv = socket(AF_UNIX, SOCK_STREAM, 0);
    if (srv < 0) { LOGE("unix socket failed errno=%d", errno); return nullptr; }
    sockaddr_un ua{};
    ua.sun_family = AF_UNIX;
    ua.sun_path[0] = 0;
    memcpy(ua.sun_path + 1, "iaa_agent", 10);
    if (bind(srv, reinterpret_cast<sockaddr*>(&ua), sizeof(sa_family_t) + 10) < 0 || listen(srv, 4) < 0) {
        LOGE("unix bind failed errno=%d", errno);
        return nullptr;
    }
    LOGI("agent listening on @iaa_agent (unix)");
    accept_loop(srv);
    return nullptr;
}

} // namespace

/* ------------------------------------------------------------------ */
/* 入口                                                                 */
/*   1) JNI_OnLoad：System.load 触发（反作弊环境下通常到不了这里）        */
/*   2) constructor：DT_NEEDED 劫持触发——guest linker 加载依赖库时执行，  */
/*      早于运行时完整性监控。此处 il2cpp 可能尚未加载，轮询等待。          */
/* System.load 路径下 JNI_OnLoad 与 constructor 都会执行 → 用 g_started   */
/* 原子标志保证只有一个 server（否则两实例抢 bind，第二个 fallback unix）  */
/* ------------------------------------------------------------------ */

static volatile int g_started = 0;
static pthread_mutex_t g_start_mx = PTHREAD_MUTEX_INITIALIZER;

void* init_thread(void* /*arg*/) {
    pthread_mutex_lock(&g_start_mx);
    if (g_started) {
        pthread_mutex_unlock(&g_start_mx);
        LOGI("init_thread: already started, skip");
        return nullptr;
    }
    g_started = 1;
    pthread_mutex_unlock(&g_start_mx);

    /* 等待 libil2cpp 加载（最多 10 分钟） */
    for (int i = 0; i < 600; i++) {
        if (dlsym(RTLD_DEFAULT, "il2cpp_domain_get")) break;
        usleep(1000 * 1000);
    }
    if (!dlsym(RTLD_DEFAULT, "il2cpp_domain_get")) {
        LOGE("il2cpp not loaded within timeout");
        return nullptr;
    }

    LOGI("il2cpp available, starting server");
    server_thread(nullptr);
    return nullptr;
}

__attribute__((constructor)) static void iaa_agent_ctor() {
    LOGI("ctor: agent injected (DT_NEEDED path)");
    pthread_t th;
    pthread_create(&th, nullptr, init_thread, nullptr);
    pthread_detach(th);
}

jint JNI_OnLoad(JavaVM* vm, void* /*reserved*/) {
    (void)vm;
    LOGI("JNI_OnLoad (System.load path)");
    pthread_t th;
    pthread_create(&th, nullptr, init_thread, nullptr);
    pthread_detach(th);
    return JNI_VERSION_1_6;
}
