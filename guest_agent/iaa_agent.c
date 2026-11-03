/**
 * iaa guest agent (arm64) — 注入 Unity il2cpp 游戏进程的宿内代理。
 *
 * 加载路径：frida(Java) → System.load() → ART → guest linker → houdini 转译执行。
 * 由于我们是 guest 代码，可直接调用 libil2cpp 导出，不经任何 trampoline 门控。
 *
 * 功能：
 *  1. il2cpp_domain_get + thread_attach
 *  2. 解析 UnityEngine.CoreModule / UI / TextMeshPro 的类与方法
 *  3. 按需 dump UI 树（FindObjectsOfType<Transform> + 父子/名字/文本/交互性/矩形）
 *  4. TCP 服务（127.0.0.1:29170），每连接一请求一响应，JSON 行协议：
 *       {"cmd":"ping"}                  → {"ok":true}
 *       {"cmd":"dump","max":6000}       → {"ok":true,"tree":{...}}
 *
 * 编译：zig cc -target aarch64-linux-android -shared ...
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <dlfcn.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/un.h>
#include <errno.h>
#include <jni.h>
#include <android/log.h>

#define LOG_TAG "iaa_agent"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

#define AGENT_PORT 29170

/* ------------------------------------------------------------------ */
/* il2cpp 导出类型与句柄                                                */
/* ------------------------------------------------------------------ */

typedef void *(*fn_domain_get)(void);
typedef void *(*fn_thread_attach)(void *domain);
typedef void *(*fn_domain_get_assemblies)(void *domain, size_t *size);
typedef void *(*fn_assembly_get_image)(void *assembly);
typedef const char *(*fn_image_get_name)(void *image);
typedef void *(*fn_class_from_name)(void *image, const char *ns, const char *name);
typedef void *(*fn_class_get_method)(void *klass, const char *name, int argc);
typedef void *(*fn_class_get_type)(void *klass);
typedef void *(*fn_type_get_object)(void *type);
typedef void *(*fn_runtime_invoke)(void *method, void *obj, void **params, void **exc);
typedef char *(*fn_string_chars)(void *str);
typedef size_t (*fn_array_length)(void *arr);

static fn_domain_get f_domain_get;
static fn_thread_attach f_thread_attach;
static fn_domain_get_assemblies f_domain_get_assemblies;
static fn_assembly_get_image f_assembly_get_image;
static fn_image_get_name f_image_get_name;
static fn_class_from_name f_class_from_name;
static fn_class_get_method f_class_get_method;
static fn_class_get_type f_class_get_type;
static fn_type_get_object f_type_get_object;
static fn_runtime_invoke f_runtime_invoke;
static fn_string_chars f_string_chars;
static fn_array_length f_array_length;

/* 类句柄 */
static void *K_GameObject, *K_Transform, *K_RectTransform, *K_Component,
    *K_Behaviour, *K_TmpText, *K_Selectable;
/* 方法句柄 */
static void *M_go_name, *M_go_active_h, *M_comp_go, *M_t_parent,
    *M_t_childcount, *M_t_child, *M_t_position, *M_t_scale, *M_rt_sizedelta,
    *M_behav_enabled, *M_sel_interactable, *M_tmp_text, *M_find_all;

/* ------------------------------------------------------------------ */
/* 小工具                                                              */
/* ------------------------------------------------------------------ */

static const char *istr(void *s) { return s ? f_string_chars(s) : NULL; }

static void *invoke(void *method, void *obj, void **args) {
    void *exc = NULL;
    return f_runtime_invoke(method, obj, args, &exc);
}

static void *arr_item(void *arr, size_t i) {
    return *(void **)((char *)arr + 0x20 + i * 8);
}

static void read_vec3(void *boxed, float *o) {
    if (!boxed) { o[0] = o[1] = o[2] = 0.f; return; }
    float *f = (float *)((char *)boxed + 0x10);
    o[0] = f[0]; o[1] = f[1]; o[2] = f[2];
}

/* 输出缓冲区（每连接独立；容量按 maxNodes 估算，node*~160B） */
struct obuf {
    char *data;
    size_t cap;
    size_t len;
};

static void ob_put(struct obuf *o, const char *s) {
    size_t n = strlen(s);
    if (o->len + n + 1 > o->cap) return;
    memcpy(o->data + o->len, s, n);
    o->len += n;
    o->data[o->len] = 0;
}

static void ob_put_json_str(struct obuf *o, const char *s) {
    if (o->len + 2 > o->cap) return;
    o->data[o->len++] = '"';
    for (const unsigned char *c = (const unsigned char *)(s ? s : ""); *c; c++) {
        if (o->len + 8 > o->cap) break;
        unsigned char ch = *c;
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

static void ob_put_int(struct obuf *o, long v) {
    char tmp[32];
    snprintf(tmp, sizeof(tmp), "%ld", v);
    ob_put(o, tmp);
}

static void ob_put_float(struct obuf *o, float v) {
    char tmp[32];
    snprintf(tmp, sizeof(tmp), "%.2f", v);
    ob_put(o, tmp);
}

/* ------------------------------------------------------------------ */
/* dump                                                                */
/* ------------------------------------------------------------------ */

struct node_rec {
    void *transform;
    void *gameobject;
    const char *name;
    int active;
    void *parent;
    int child_count;
    const char *text;      /* 可为 NULL */
    int interactable;      /* -1 未知 */
    float cx, cy, w, h;    /* 世界矩形；has_rect=0 时无效 */
    int has_rect;
};

static int find_all_transforms(void ***out, int max) {
    /* Object.FindObjectsOfType(typeof(Transform)) 静态调用 */
    void *type_obj = NULL;
    void *type = f_class_get_type(K_Transform);
    if (!type) return -1;
    type_obj = f_type_get_object(type);
    if (!type_obj) return -1;
    void *args[1] = { type_obj };
    void *arr = invoke(M_find_all, NULL, args);
    if (!arr) return -1;
    size_t n = f_array_length(arr);
    if (n > (size_t)max) n = max;
    for (size_t i = 0; i < n; i++) (*out)[i] = arr_item(arr, i);
    return (int)n;
}

static int dump_tree(struct obuf *o, int max_nodes) {
    void **transforms = (void **)malloc(sizeof(void *) * max_nodes);
    struct node_rec *recs = (struct node_rec *)malloc(sizeof(struct node_rec) * max_nodes);
    if (!transforms || !recs) { free(transforms); free(recs); return -1; }

    int n = find_all_transforms(&transforms, max_nodes);
    if (n < 0) { free(transforms); free(recs); return -1; }

    /* 逐节点收集 */
    int m = 0;
    for (int i = 0; i < n; i++) {
        void *t = transforms[i];
        struct node_rec *r = &recs[m];
        memset(r, 0, sizeof(*r));
        r->interactable = -1;
        r->transform = t;
        void *go = invoke(M_comp_go, t, NULL);
        if (!go) continue;
        r->gameobject = go;
        r->name = istr(invoke(M_go_name, go, NULL));
        r->active = invoke(M_go_active_h, go, NULL) ? 1 : 0;
        r->parent = invoke(M_t_parent, t, NULL);
        void *cc = invoke(M_t_childcount, t, NULL);
        r->child_count = cc ? (int)(long)cc : 0;
        /* 文本（TMP_Text 缓存表外直接尝试）*/
        /* 注：为省调用，文本/交互性用二次 FindObjectsOfType 的映射表，见下方 */
        /* 矩形 */
        float pos[3], scale[3], sd[3];
        read_vec3(invoke(M_t_position, t, NULL), pos);
        read_vec3(invoke(M_t_scale, t, NULL), scale);
        /* 判断是否 RectTransform：klass 指针比较 */
        void *klass = *(void **)t;
        if (klass == K_RectTransform) {
            read_vec3(invoke(M_rt_sizedelta, t, NULL), sd);
            r->has_rect = 1;
            r->cx = pos[0]; r->cy = pos[1];
            r->w = sd[0] * scale[0];
            r->h = sd[1] * scale[1];
        }
        m++;
    }

    /* 文本映射表：go ptr → text */
    /* 为控制调用量，这里只对 TMP_Text 全量建表 */
    {
        void *type = f_class_get_type(K_TmpText);
        void *args[1] = { type ? f_type_get_object(type) : NULL };
        void *arr = args[0] ? invoke(M_find_all, NULL, args) : NULL;
        if (arr) {
            size_t cnt = f_array_length(arr);
            for (size_t i = 0; i < cnt; i++) {
                void *c = arr_item(arr, i);
                void *go = invoke(M_comp_go, c, NULL);
                if (!go) continue;
                const char *txt = istr(invoke(M_tmp_text, c, NULL));
                for (int j = 0; j < m; j++) {
                    if (recs[j].gameobject == go) { recs[j].text = txt; break; }
                }
            }
        }
    }
    /* 交互性映射表 */
    {
        void *type = f_class_get_type(K_Selectable);
        void *args[1] = { type ? f_type_get_object(type) : NULL };
        void *arr = args[0] ? invoke(M_find_all, NULL, args) : NULL;
        if (arr) {
            size_t cnt = f_array_length(arr);
            for (size_t i = 0; i < cnt; i++) {
                void *c = arr_item(arr, i);
                void *go = invoke(M_comp_go, c, NULL);
                if (!go) continue;
                void *ok = invoke(M_sel_interactable, c, NULL);
                for (int j = 0; j < m; j++) {
                    if (recs[j].gameobject == go) { recs[j].interactable = ok ? 1 : 0; break; }
                }
            }
        }
    }

    /* 输出：nodes 数组（宿主侧建树） */
    ob_put(o, "{\"ok\":true,\"n\":");
    ob_put_int(o, m);
    ob_put(o, ",\"nodes\":[");
    for (int j = 0; j < m; j++) {
        struct node_rec *r = &recs[j];
        if (j) ob_put(o, ",");
        ob_put(o, "{\"t\":\"");
        ob_put_int(o, (long)r->transform);
        ob_put(o, "\",\"go\":\"");
        ob_put_int(o, (long)r->gameobject);
        ob_put(o, "\",\"name\":");
        ob_put_json_str(o, r->name);
        ob_put(o, ",\"active\":");
        ob_put_int(o, r->active);
        ob_put(o, ",\"parent\":\"");
        ob_put_int(o, (long)r->parent);
        ob_put(o, "\",\"cc\":");
        ob_put_int(o, r->child_count);
        if (r->text) { ob_put(o, ",\"text\":"); ob_put_json_str(o, r->text); }
        if (r->interactable >= 0) { ob_put(o, ",\"ia\":"); ob_put_int(o, r->interactable); }
        if (r->has_rect) {
            ob_put(o, ",\"rect\":[");
            ob_put_float(o, r->cx); ob_put(o, ",");
            ob_put_float(o, r->cy); ob_put(o, ",");
            ob_put_float(o, r->w); ob_put(o, ",");
            ob_put_float(o, r->h);
            ob_put(o, "]");
        }
        ob_put(o, "}");
    }
    ob_put(o, "]}");

    free(transforms);
    free(recs);
    return m;
}

/* ------------------------------------------------------------------ */
/* bootstrap                                                           */
/* ------------------------------------------------------------------ */

static int bootstrap(void) {
    void *domain = f_domain_get();
    if (!domain) { LOGE("no domain"); return -1; }
    void *thread = f_thread_attach(domain);
    if (!thread) { LOGE("thread attach failed"); return -1; }
    LOGI("attached, domain=%p", domain);

    /* 找 image */
    void *core = NULL, *ui = NULL, *tmp = NULL;
    size_t asize = 0;
    void *assemblies = f_domain_get_assemblies(domain, &asize);
    if (!assemblies) return -1;
    for (size_t i = 0; i < asize; i++) {
        void *asm_ = *(void **)((char *)assemblies + i * sizeof(void *));
        void *img = f_assembly_get_image(asm_);
        const char *nm = f_image_get_name(img);
        if (!nm) continue;
        if (!strcmp(nm, "UnityEngine.CoreModule.dll")) core = img;
        else if (!strcmp(nm, "UnityEngine.UI.dll")) ui = img;
        else if (!strcmp(nm, "Unity.TextMeshPro.dll")) tmp = img;
    }
    if (!core) { LOGE("CoreModule not found"); return -1; }
    if (!ui) ui = core;
    if (!tmp) tmp = core;

#define CLASS(var, img, ns, name)                                          \
    do {                                                                   \
        var = f_class_from_name(img, ns, name);                            \
        if (!var) { LOGE("class %s not found", name); return -1; }         \
    } while (0)

    CLASS(K_GameObject, core, "UnityEngine", "GameObject");
    CLASS(K_Transform, core, "UnityEngine", "Transform");
    CLASS(K_RectTransform, core, "UnityEngine", "RectTransform");
    CLASS(K_Component, core, "UnityEngine", "Component");
    CLASS(K_Behaviour, core, "UnityEngine", "Behaviour");
    CLASS(K_TmpText, tmp, "TMPro", "TMP_Text");
    CLASS(K_Selectable, ui, "UnityEngine.UI", "Selectable");
#undef CLASS

#define METHOD(var, klass, name, argc)                                     \
    do {                                                                   \
        var = f_class_get_method(klass, name, argc);                       \
        if (!var) { LOGE("method %s not found", name); return -1; }        \
    } while (0)

    METHOD(M_go_name, K_GameObject, "get_name", 0);
    METHOD(M_go_active_h, K_GameObject, "get_activeInHierarchy", 0);
    METHOD(M_comp_go, K_Component, "get_gameObject", 0);
    METHOD(M_t_parent, K_Transform, "GetParent", 0);
    METHOD(M_t_childcount, K_Transform, "get_childCount", 0);
    METHOD(M_t_child, K_Transform, "GetChild", 1);
    METHOD(M_t_position, K_Transform, "get_position", 0);
    METHOD(M_t_scale, K_Transform, "get_lossyScale", 0);
    METHOD(M_rt_sizedelta, K_RectTransform, "get_sizeDelta", 0);
    METHOD(M_behav_enabled, K_Behaviour, "get_enabled", 0);
    METHOD(M_sel_interactable, K_Selectable, "get_interactable", 0);
    METHOD(M_tmp_text, K_TmpText, "get_text", 0);
#undef METHOD

    /* FindObjectsOfType 是 UnityEngine.Object 的静态重载（带 Type 参数） */
    {
        void *kobject = f_class_from_name(core, "UnityEngine", "Object");
        if (!kobject) return -1;
        M_find_all = f_class_get_method(kobject, "FindObjectsOfType", 1);
        if (!M_find_all) { LOGE("FindObjectsOfType not found"); return -1; }
    }

    LOGI("bootstrap ok");
    return 0;
}

/* ------------------------------------------------------------------ */
/* TCP 服务                                                            */
/* ------------------------------------------------------------------ */

static void *handle_client(void *arg) {
    int fd = (int)(long)arg;
    char req[256];
    struct obuf o;
    o.cap = 4 * 1024 * 1024;
    o.data = (char *)malloc(o.cap);
    if (!o.data) { close(fd); return NULL; }

    ssize_t n = recv(fd, req, sizeof(req) - 1, 0);
    if (n <= 0) { free(o.data); close(fd); return NULL; }
    req[n] = 0;

    o.len = 0;
    o.data[0] = 0;

    if (strstr(req, "\"ping\"")) {
        ob_put(&o, "{\"ok\":true,\"agent\":\"iaa\",\"il2cpp\":true}");
    } else if (strstr(req, "\"dbg\"")) {
        /* 调试：字符串往返 + 第一个 Transform 的名字原始字节 */
        void *domain = f_domain_get();
        f_thread_attach(domain);
        ob_put(&o, "{\"ok\":true");
        void **ts = (void **)malloc(sizeof(void *) * 8);
        int n = find_all_transforms(&ts, 8);
        ob_put(&o, ",\"tn\":");
        ob_put_int(&o, n);
        if (n > 0) {
            void *go = invoke(M_comp_go, ts[0], NULL);
            void *nm = invoke(M_go_name, go, NULL);
            char tmp[512];
            snprintf(tmp, sizeof(tmp), ",\"nameobj\":\"%p\",\"chars\":\"%p\"", nm, nm ? f_string_chars(nm) : NULL);
            ob_put(&o, tmp);
            if (nm) {
                const unsigned char *raw = (const unsigned char *)f_string_chars(nm);
                ob_put(&o, ",\"raw\":[");
                for (int i = 0; i < 24 && raw[i]; i++) {
                    if (i) ob_put(&o, ",");
                    ob_put_int(&o, raw[i]);
                }
                ob_put(&o, "]");
                /* String 对象头：klass/monitor/length */
                int slen = *(int *)((char *)nm + 0x10);
                ob_put(&o, ",\"slen\":");
                ob_put_int(&o, slen);
            }
        }
        free(ts);
        ob_put(&o, "}");
    } else if (strstr(req, "\"dump\"")) {
        int max = 6000;
        const char *mp = strstr(req, "\"max\":");
        if (mp) max = atoi(mp + 6);
        if (max > 12000) max = 12000;
        if (dump_tree(&o, max) < 0) {
            o.len = 0;
            ob_put(&o, "{\"ok\":false,\"err\":\"dump failed\"}");
        }
    } else if (strstr(req, "\"boot\"")) {
        int r = bootstrap();
        char tmp[64];
        snprintf(tmp, sizeof(tmp), "{\"ok\":%s}", r == 0 ? "true" : "false");
        ob_put(&o, tmp);
    } else {
        ob_put(&o, "{\"ok\":false,\"err\":\"unknown cmd\"}");
    }

    ob_put(&o, "\n");
    send(fd, o.data, o.len, 0);
    free(o.data);
    close(fd);
    return NULL;
}

static void accept_loop(int srv) {
    for (;;) {
        int c = accept(srv, NULL, NULL);
        if (c < 0) continue;
        pthread_t th;
        pthread_create(&th, NULL, handle_client, (void *)(long)c);
        pthread_detach(th);
    }
}

static void *server_thread(void *arg) {
    (void)arg;
    int srv = socket(AF_INET, SOCK_STREAM, 0);
    if (srv >= 0) {
        int one = 1;
        setsockopt(srv, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
        struct sockaddr_in addr;
        memset(&addr, 0, sizeof(addr));
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = htonl(INADDR_ANY);
        addr.sin_port = htons(AGENT_PORT);
        if (bind(srv, (struct sockaddr *)&addr, sizeof(addr)) == 0 && listen(srv, 4) == 0) {
            LOGI("agent listening on 0.0.0.0:%d (inet)", AGENT_PORT);
            accept_loop(srv);
            return NULL;
        }
        LOGE("inet bind failed errno=%d", errno);
        close(srv);
    } else {
        LOGE("socket failed errno=%d", errno);
    }

    /* 回退：abstract unix socket "iaa_agent"（adb forward localabstract 支持） */
    srv = socket(AF_UNIX, SOCK_STREAM, 0);
    if (srv < 0) { LOGE("unix socket failed errno=%d", errno); return NULL; }
    struct sockaddr_un ua;
    memset(&ua, 0, sizeof(ua));
    ua.sun_family = AF_UNIX;
    ua.sun_path[0] = 0;
    memcpy(ua.sun_path + 1, "iaa_agent", 10);
    if (bind(srv, (struct sockaddr *)&ua, sizeof(sa_family_t) + 10) < 0 || listen(srv, 4) < 0) {
        LOGE("unix bind failed errno=%d", errno);
        return NULL;
    }
    LOGI("agent listening on @iaa_agent (unix)");
    accept_loop(srv);
    return NULL;
}

/* ------------------------------------------------------------------ */
/* 入口                                                                 */
/*   1) JNI_OnLoad：System.load 触发（反作弊环境下通常到不了这里）        */
/*   2) constructor：DT_NEEDED 劫持触发——guest linker 加载依赖库时执行，  */
/*      早于运行时完整性监控。此处 il2cpp 可能尚未加载，轮询等待。          */
/* ------------------------------------------------------------------ */

static void *init_thread(void *arg) {
    (void)arg;
    /* 等待 libil2cpp 加载（最多 10 分钟） */
    for (int i = 0; i < 600; i++) {
        void *sym = dlsym(RTLD_DEFAULT, "il2cpp_domain_get");
        if (sym) break;
        usleep(1000 * 1000);
    }
#define SYM(var, name)                                                     \
    do {                                                                   \
        var = (typeof(var))dlsym(RTLD_DEFAULT, name);                      \
        if (!var) { LOGE("dlsym %s failed", name); return NULL; }          \
    } while (0)

    SYM(f_domain_get, "il2cpp_domain_get");
    SYM(f_thread_attach, "il2cpp_thread_attach");
    SYM(f_domain_get_assemblies, "il2cpp_domain_get_assemblies");
    SYM(f_assembly_get_image, "il2cpp_assembly_get_image");
    SYM(f_image_get_name, "il2cpp_image_get_name");
    SYM(f_class_from_name, "il2cpp_class_from_name");
    SYM(f_class_get_method, "il2cpp_class_get_method_from_name");
    SYM(f_class_get_type, "il2cpp_class_get_type");
    SYM(f_type_get_object, "il2cpp_type_get_object");
    SYM(f_runtime_invoke, "il2cpp_runtime_invoke");
    SYM(f_string_chars, "il2cpp_string_chars");
    SYM(f_array_length, "il2cpp_array_length");
#undef SYM

    LOGI("il2cpp symbols resolved, starting server");
    server_thread(NULL);
    return NULL;
}

__attribute__((constructor)) static void iaa_agent_ctor(void) {
    LOGI("ctor: agent injected (DT_NEEDED path)");
    pthread_t th;
    pthread_create(&th, NULL, init_thread, NULL);
    pthread_detach(th);
}

jint JNI_OnLoad(JavaVM *vm, void *reserved) {
    (void)vm; (void)reserved;
    LOGI("JNI_OnLoad (System.load path)");
    pthread_t th;
    pthread_create(&th, NULL, init_thread, NULL);
    pthread_detach(th);
    return JNI_VERSION_1_6;
}
