# Frida/注入获取 Unity UI 树 —— 研究全记录与交接文档

> 目标：注入获取 pjsk（Unity il2cpp）场景/UI 树，替换模板识别与 OCR（autolive 除外）。
> Worktree: `E:\GithubRepos\iaa-frida-uitree`，分支 `feat/frida-uitree`。
> **新 agent 从 §3「现状」开始读，§4 失败清单避免重复踩坑，§5 是已验证可用的主航线。**
>
> 最后更新：2026-11-03 深夜（方案 A 已打通 95%，剩最后一个 bug）

## 1. 环境事实（已验证）

| 项 | 值 |
|---|---|
| 模拟器 | MuMu 12 (NEMUX)，`127.0.0.1:5555`，Android 12，x86_64 + **libhoudini 12.0.1_z.Netease (Intel Bridge) ARM 转译** |
| 游戏 | `com.sega.pjsekai`（进程名「プロセカ」），Unity 2022.3.62f2，il2cpp metadata v31，**仅 arm64 原生库**（游戏库由 **NDK r23b** 编译） |
| 反作弊 | pcam/libchecker（app_pccache/libdCC*.so）；**frida spawn 模式 1.2s 被杀**，只能 attach；运行时外来 dlopen 不拦（见 §5） |
| frida | **17.25.2**（pip 装的客户端 + `/data/local/tmp/fs17`，root 启动，adb forward tcp:27042）。⚠️ frida 17 移除了内置 Java bridge，需 `frida-java-bridge` 经 frida-compile 打包（见 §5.3） |
| 编译链 | **NDK 27**：`D:/SDK/Android/ndk/27.0.12077973/toolchains/llvm/prebuilt/windows-x86_64/bin/aarch64-linux-android24-clang` |
| Java loader | `D:/tmp_iaa_npm/javaloader.js`（frida-compile 产物；源 `javaloader.ts`，用 `npx frida-compile` 重编） |
| 已知模拟器坑 | 模拟器**重启后**：fs17 要重新起、forward 要重做；游戏冷启动 60~70s 到 TAP TO START，点 (640,617) 后 ~70s 进首页 |

## 2. 技术图景速览（为什么走到方案 A）

- x64 frida **无法直接调用/hook arm64**（houdini 转译执行，text r--p）。
- 官方通道 `NativeBridgeItf.getTrampoline` 可创建 x64→arm64 跳板，**但 MuMu 门控**：跳板记录表 `TABLE + ticket*16512`，flag@`-0x4054` 为 0 → 调用解引用毒值 `0xdead1066`。ART 自己的 ticket flag=1。窗口期（偶发，~30 分钟一次）flag 会被批量置 1。
- 曾试图写 flag（mprotect 后成功写入）但记录其余字段（srcptr/size/scale）也没填，调用仍失败 → **放弃 x64 侧硬闯，转为方案 A：让我们的代码变成 guest 世界的 arm64 代码**。
- 方案 A 核心链条（**已全通**）：
  ```
  frida(x64) --Java.perform--> System.load("/data/local/tmp/iaa_agent.so")   [arm64]
    → ART → guest linker → houdini 正常加载（我们的 .so 是合法 guest 库）
      → JNI_OnLoad / constructor → dlsym(RTLD_DEFAULT, "il2cpp_*") 全部解析成功
      → 起 TCP 服务 → Python 直连（adb forward）→ dump UI 树
  ```

## 3. 现状（交接时点）

### ✅ 已打通
1. **arm64 agent.so 编译成功并可注入加载**（`guest_agent/iaa_agent.so` + `stubs.c`，见 §5.1 编译命令）
2. **JNI_OnLoad 触发、il2cpp 全部 12 个导出 dlsym 解析成功**、TCP 服务启动
3. Python 经 `adb forward tcp:29170` **ping 通过**：`{"ok":true,"agent":"iaa","il2cpp":true}`
4. **`dump` 命令成功返回 48 个节点**（FindObjectsOfType(Transform) 全链路 OK！）——但**名字只输出 1 个字符**（bug 未解，见 §6）
5. `boot`（bootstrap：解析 7 个类 + 14 个方法）返回 `{"ok":true}`

### ⚠️ 最后一个 bug（重启即修）
dump 出的节点名是单字符（疑似 get_name 返回的 String 只读到一个字符）。已加了 `dbg` 调试命令输出 nameobj/chars 指针、原始字节、slen 用于定位。**注意 §6 的双实例问题**。

### 🐛 已知小问题：agent.so 被加载了两个实例
JNI_OnLoad（System.load 触发）和 init_thread 都会尝试起服务器；若 .so 因 System.load 加载，**JNI_OnLoad 与 constructor 可能都跑**（constructor 在 System.load 路径也会被 linker 调用！）→ 两个 server 线程抢 bind（第二个 fallback 到 unix socket，日志可见）。**修复**：加一个 `static volatile int g_started` 原子标志，两入口先检查再启动。当前现象：inet 绑定成功的是第一个实例，功能正常；但 dbg 命令超时**可能**是请求打进了老进程残留的 forward——排查时先 `adb forward --remove tcp:29170` 再重 forward。

## 4. 失败清单（勿重复踩坑）

1. **x64 直接 NativeFunction/Interceptor arm64 地址** → SIGSEGV。
2. **gateway trampoline 硬闯**（handle=0）：受 §2 的 ticket 门控；窗口期虽存在但不可依赖。写 flag 无效（记录其他字段未填）。
3. **`realm='emulated'`**：frida 17 报 "process is not using emulation"（QEMU 专用，houdini 不识别）。
4. **frida spawn**：被 pcam 反作弊 1.2s 杀。
5. **纯内存解析 il2cpp 元数据**：内存元数据**按会话混淆**（11497 会话能解析，换进程 klass->name 指向乱码）；跨会话不可用，此路废弃。
6. **恢复被 hook 的原始字节**：houdini 代码缓存不刷新，无效。
7. **frida 16.7.19 的 `File('/proc/self/maps')`** 会卡死；frida 17 `Module.getExportByName` 静态方法被移除（用 `Process.findModuleByName(m).getExportByName()` 或 findGlobalExportByName）。
8. **NDK 27 默认链接产物 houdini 加载失败**（"failed to link"）——**根因已定位**：MuMu 的 arm64 guest libc 不导出 `__register_atfork` / `__cxa_atexit`（NDK crt 默认引用它们）。**解法**：`-nostdlib` + stubs.c 自带空桩（见 §5.1）。零导入的 NDK27 .so 能正常加载（ELF 结构没问题）。
9. 假线索排除记录：游戏运行时 System.load **不**被反作弊拦（加载游戏自己的库成功）、路径/SELinux 标签/文件名无关、16K/4K 页对齐无关、soname/ndk 版本/哈希格式无关——**唯一变量是导入符号**（v7=仅 liblog 符号→OK；v8=加 `__register_atfork`→失败；v9=`__cxa_atexit`→失败）。
10. **白屏事故**（已排除我们的嫌疑）：不注入重启也白屏，重启模拟器后恢复。原因不明（疑似模拟器状态问题）。教训：出问题先做基线对照。

## 5. 主航线操作手册（已验证）

### 5.1 编译 agent.so（改代码后执行）
```bash
cd E:/GithubRepos/iaa-frida-uitree/guest_agent
D:/SDK/Android/ndk/27.0.12077973/toolchains/llvm/prebuilt/windows-x86_64/bin/aarch64-linux-android24-clang \
  -shared -O2 -fPIC -nostdlib -fno-stack-protector \
  -Wl,-z,max-page-size=4096 -Wl,-soname,iaa_agent.so -llog \
  iaa_agent.c stubs.c -o iaa_agent.so
```
要点：`-nostdlib` 必须（绕开 crt 的缺失符号引用）；stub `__cxa_atexit/__cxa_finalize/__register_atfork` 在 stubs.c；剩余导入全是远古 bionic 符号（accept/bind/malloc/pthread_*/snprintf/socket/dlsym 等，已验证存在）。

### 5.2 部署 + 注入 + 连接
```bash
adb -s 127.0.0.1:5555 push iaa_agent.so /data/local/tmp/
adb -s 127.0.0.1:5555 shell "su -c 'chmod 644 /data/local/tmp/iaa_agent.so'"
# 游戏启动并进到首页后（TAP TO START 点 (640,617)，等 ~70s）：
cd probe && py -3 inject_agent.py          # frida Java Runtime.load0 注入
adb -s 127.0.0.1:5555 forward tcp:29170 tcp:29170
# TCP 行协议（每连接一请求一响应，响应以 \n 结尾）：
#   {"cmd":"ping"}   {"cmd":"boot"}   {"cmd":"dbg"}   {"cmd":"dump","max":6000}
```

### 5.3 frida Java bridge（17 必须）
- 源：`D:/tmp_iaa_npm/javaloader.ts`（`import Java from 'frida-java-bridge'`；用 `Runtime.load0(app.getClass(), path)` 绕开 System.load 的 caller-class NPE）
- 编译：`cd D:/tmp_iaa_npm && npx frida-compile javaloader.ts -o javaloader.js`
- probe/inject_agent.py 读该 js。E: 盘只剩 ~0.5G，npm 工作目录放 D: 了。

### 5.4 guest_agent/iaa_agent.c 结构
- `bootstrap()`：找 CoreModule/UI/TextMeshPro image → 解析 GameObject/Transform/RectTransform/Component/Behaviour/TMP_Text/Selectable 类 + get_name/FindObjectsOfType 等方法
- `dump_tree()`：FindObjectsOfType(Transform) → 逐节点 get_gameObject/get_name/get_activeInHierarchy/GetParent/childCount + RectTransform 的 position/lossyScale/sizeDelta（**只对 klass==RectTransform 调 sizeDelta**）+ TMP_Text/Selectable 全量映射表
- TCP 协议：ping / boot / dbg / dump；`{"cmd":"autodump"}` 未实现（可加）
- 输出格式：`{"ok":true,"n":N,"nodes":[{"t":"<ptr>","go":"<ptr>","name":"...","active":0/1,"parent":"<ptr>","cc":N,"text":"...","ia":0/1,"rect":[cx,cy,w,h]}...]}`（宿主侧建树）

## 6. 下一步（按序）

1. **修双实例问题**：`g_started` 标志（§3）。顺手把 `dbg` 超时查清（先 `adb forward --remove tcp:29170` 重 forward；确认请求进的是哪个实例——inet 在 29170 的实例功能正常）。
2. **修单字符名字 bug**：用 `dbg` 输出定位。怀疑点：a) `il2cpp_string_chars` 拿到的缓冲生命周期/编码；b) `get_name` 在该 Unity 版本返回的不是 String；c) `ob_put_json_str` 里的过滤逻辑（`ch >= 0x20` 以外全丢弃——若名字首字节就是非 ASCII？Unity 名字一般 ASCII，先看 raw 数组）。**最省事的替代方案**：不调 get_name，直接读 String 对象（`slen = *(int*)(str+0x10)`，字符 = UTF-16 @ +0x14，自己转 UTF-8），绕开 string_chars。
3. **名字修好后跑完整 dump**：`probe/ui_dump_guest.json` 已有一次 48 节点结果（名字坏）。dump 时游戏要已在首页（有 UI 可采）。
4. **接回框架**：`iaa/unity_ui/client.py` 把数据源从 frida RPC 换成本 TCP 客户端（send cmd/recv json），tree.py 的 `build_forest` 改为按 `parent` 指针建树（节点已有 t/go/parent 指针）。locator/element 不用动。
5. **坐标换算验证**：rect 是世界坐标（position/lossyScale/sizeDelta 近似），Screen Space Overlay 画布下≈屏幕坐标（游戏逻辑分辨率 1280x720）。截图叠加 `tools/visualize_ui_dump.py` 验证，偏了再做 pivot/画布修正。
6. **建 R.* → Unity 节点映射表**：在首页/礼物/活动页分别 dump，结合截图把 `iaa/tasks/R.py` 的 prefab 名映射到节点 path。之后逐 task 替换（autolive 除外）。
7. 可选增强：agent 加 autodump 循环/按名字查询命令；`/data/local/tmp/iaa_agent.so` 的 SELinux 上下文暂无问题。

## 7. 关键文件索引

| 文件 | 说明 |
|---|---|
| `guest_agent/iaa_agent.c` | arm64 guest agent（核心资产） |
| `guest_agent/stubs.c` | 缺失符号空桩（**必须一起链**） |
| `guest_agent/iaa_agent.so` | 已编译产物（NDK 27） |
| `probe/inject_agent.py` | 注入驱动（依赖 D:/tmp_iaa_npm/javaloader.js） |
| `probe/harness.py` | run_js/get_device/find_game（identifier 匹配） |
| `iaa/unity_ui/` | Python 侧框架（client/locator/element 待接 TCP 源） |
| `tools/visualize_ui_dump.py` | dump 叠加截图可视化 |
| `probe/ui_dump_guest.json` | 首次成功 dump（名字坏，结构对） |
| `doc/frida-uitree-findings.md` | 上一版研究文档（本文件取代之） |
| `D:/tmp_iaa_npm/` | frida-java-bridge + 编译环境（D 盘，E 盘满） |

## 8. git 提交记录（feat/frida-uitree）

- `3bb9eba` feat: frida UI 树方案调研与通用框架骨架（此前全部工作的压缩基线）
- 后续：agent.so 编译/注入/门控破译等尚未提交（guest_agent/ 目录与 probe 新脚本 untracked）——**交接后第一件事先 commit**

---

## 9. 2026-11-04 进展：框架全通 + 渐进迁移底座建成

### 9.1 已完成（全部实测验证）

1. **agent 修复**（`adb9849`、`bc6e2e7`）：
   - 单字符名字 bug → `mono_string_to_utf8()` 直接读 String 对象（len@0x10、UTF-16@0x14、代理对→UTF-8）
   - 双实例 bind 竞争 → `g_started` 原子标志
   - 装箱值 bug → `runtime_invoke` 值类型返回装箱指针，`childCount/active/interactable` 必须读 +0x10
   - **boot 前调 dump/dbg 会 `runtime_invoke(NULL)` 崩坏 GC 状态**（后续所有 runtime_invoke 挂死）→ 已加防护
2. **坐标映射**：`screen = (wx*S + 640, 360 - wy*S)`，`S = viewport_h / canvas_world_h`（CanvasRoot 世界高）。实测叠加截图完全对齐。
3. **TCP 框架**（`iaa/unity_ui/`）：`guest_agent.py`（行协议客户端）、`injector.py`（幂等注入，javaloader 收进仓库）、`client.py`（编排+失效重建）、`tree.py`（parent 指针建树+screen_rect）、`prefab.py`（kotonebot Prefab 协议接入）、`locator/element`（Playwright 风格）。
   - dump 285 节点 0.05s；点击闭环验证（新闻弹窗关闭按钮）；游戏重启自动重注入。
4. **渐进迁移底座**：`make_resources.py` 产物 R.py 保留为 fallback；`iaa/unity_ui/uimap.py` 的 `MAP` dict 逐名覆盖 → UI 树驱动；`iaa/tasks/__init__.py` 导入即安装（`IAA_UI_TREE=0` 禁用）。未映射的名字自动回退模板匹配，**所有 task 当前都能跑**。
5. **已迁移并端到端验证**：`common.py`（at_home/go_home 零改动）、`gift.py`（colored→interactable，实跑领到金币）、`mission_rewards.py`（实跑）、`start_game.py`（force-stop→launch→自动注入→关新闻→at_home）、`_fragments.handle_notification`（点 UIPartsCloseButton）。

### 9.2 已知映射（uimap.MAP）

ButtonLive/MySekai/Story/Gacha/Member（底栏 MainMenu/Base/*）、ButtonGoBack（`/UIPartsBackButton$`）、ButtonClaimAll（Present/Mission 页 footer UIPartsCommonButton）、Login.IconNotification（NewsDialog 关闭钮）。

### 9.3 关键坑与约定

- **Unity 重名加后缀**：`UIPartsMenuButton (1)`——正则要容忍 `( \(\d+\))?`
- **FindObjectsOfType 只返回激活节点**（active 恒 1），隐藏 UI 不可见；inactive 需 FindObjectsOfTypeAll 或层级遍历（未做）
- **3D 世界地图对象不在 UI 树**（世界地图建筑/图标是场景 mesh）→ cm.py 的地图导航部分保留模板匹配（fallback 自动生效）
- **`(Clone)` 后缀**：实例化节点路径带 `(Clone)`，正则需转义
- **开发环境**：worktree venv 在 `D:/iaa_frida_venv`（E 盘满）；`uv sync` + `UV_PROJECT_ENVIRONMENT`；probe 用 `logs/probe_boot.py`（顶层直线执行，**勿包进函数**——exec+函数+contextvar 有坑：getter 会丢，原因未查明）
- **probe 注意**：UI 树优先路径不走截图，须先 `device.screenshot()` 一次初始化 scaler 物理分辨率（probe_boot 已做）
- **白屏**：偶发（不注入也复现），重启模拟器/重开游戏可恢复；UIPrefab find 已降级为"未找到"可自然重试
- **kotonebot @task/@action** 会自动管理 context；裸函数调 device 需 init_context 后使用

### 9.4 下一步

1. **live.py 迁移**（最大头）：LIVE 顶部页已 dump（`probe/ui_dump_songselect.json`，ScreenLayerLiveTop 的 FreeLive/MultiLive/ChallengeLive/MV/VirtualLive 按钮全可见）。待映射：ButtonDecide（选歌列表决定钮）、歌单 cell、ApMultiplierDialog（OCR 改读 TMP text `CurrencyText` 式节点）、AutoSetDialog、结算页。autolive（auto_live_core.py）不动。
2. **event_shop.py**：MenuDialog/ShopCell→CrystalShop 已探明；商品 cell（ShopCell(Clone)/ShopCellRootView）结构待研究——若 TMP 文本含商品名可整体替换 icon 模板匹配 + ListView walking。
3. **story/mysekai/area_convos**：skip_stories、Story.ButtonStoryMenu 等待映射（进剧情即可 dump）。
4. **NetworkError 弹窗**：等自然触发时 dump（今天出现 2 次：通信エラー/タイトルへ戻る）。
5. agent 可选增强：按名字查询命令、autodump 循环、FindObjectsOfTypeAll 支持隐藏 UI。

---

## 10. 2026-11-04（晚）：agent 迁移到 UnityResolve.hpp + CMake 规范化

### 10.1 结构

```
guest_agent/
├── CMakeLists.txt            # NDK 构建入口（arm64-v8a, android-24, ANDROID_STL=c++_static）
├── src/iaa_agent.cpp         # C++ agent（协议不变：ping/boot/dbg/dump）
├── src/stubs.c               # guest libc 缺失符号空桩（必须链接）
├── third_party/UnityResolve/ # UnityResolve.hpp（MIT，vendored）
├── README.md                 # 构建/部署/约束说明
└── iaa_agent.so              # 产物（提交，injector 按大小重推）
```

编译组合结论：**默认 crt + ANDROID_STL=c++_static + stubs 可被 houdini 加载**
（stubs 内联消化 `__register_atfork/__cxa_atexit` 后产物无未定义导入；
DT_NEEDED 仅 liblog/libm/libdl/libc）。不再需要 -nostdlib。

### 10.2 踩坑记录（都很贵，别重复）

1. **`String::ToString()` 在 Android 是错的**：以 4 字节 wchar_t 读 UTF-16 缓冲
   （wchar_t 只有 Windows 是 2 字节），且不处理代理对 → 保留自有
   `mono_string_to_utf8()`。
2. **`Method::Invoke` 是直接调函数指针**（il2cpp methodInfo 首指针、无尾随
   MethodInfo*、不走 runtime_invoke）——本环境实测 FindObjectsOfType 挂死。
   **必须走 `il2cpp_runtime_invoke`**，且 params 语义要对：本环境引用类型
   参数按值放 params[i]（`params[0]=type_obj`，旧 C agent 验证过的形态），
   `Method::RuntimeInvoke` 的 `&arg` 形态会导致收到栈地址 → 挂死。
   → 统一用 `rt_invoke()` 辅助（见 iaa_agent.cpp 注释）。
3. **`Class::Get` 只搜本类方法**：`get_name` 等声明在 UnityEngine.Object 上，
   必须**沿继承链向上搜**（`resolve_in_hierarchy`，对齐
   il2cpp_class_get_method_from_name 的行为）。
4. **boot 前不能 `UR::ThreadAttach()`**：依赖 Init 缓存的 pDomain，boot 前
   调用 = il2cpp_thread_attach(NULL) 挂死整个 handler 线程（ping 都不回）。
5. 诊断手法：反作弊环境下 logcat 看不到 agent 日志 → 错误原因必须走协议
   返回（boot 响应带 err 字段）。

### 10.3 回归

boot ~10s（全量枚举程序集/类/方法，一次性），dump 281 节点 0.03s，
名字/文本/交互性/矩形与旧 C agent 输出一致；宿主 iaa/unity_ui 无改动直接可用。
