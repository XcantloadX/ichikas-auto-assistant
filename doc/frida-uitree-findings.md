# MuMu(x86_64+houdini) 上 pjsk(il2cpp/arm64) 的 Frida 注入研究

> 目标：用 Frida 注入获取游戏场景/UI 树，替换模板识别与 OCR（autolive 除外）。
> 本文档供后续 agent 快速接续研究。**先读 §3「现状」与 §5「失败清单」，避免重复踩坑。**
>
> 最后更新：2026-11-03（Worktree: E:\GithubRepos\iaa-frida-uitree，分支 feat/frida-uitree）

## 1. 环境事实（已验证）

| 项 | 值 |
|---|---|
| 模拟器 | MuMu 12 (NEMUX)，`127.0.0.1:5555`，Android 12，x86_64 + **libhoudini (Intel Bridge for Netease) ARM 转译** |
| 游戏 | `com.sega.pjsekai`（进程名显示「プロセカ」），Unity 2022.3，il2cpp metadata v31，**仅 arm64 原生库**（/lib/arm64/） |
| 反作弊 | pcam/libchecker（app_pccache/libdCC*.so）；**frida spawn 模式 1.2s 内被杀**，只能 attach 运行中的进程 |
| frida | 宿主与设备均已升级 **17.25.2**（设备 /data/local/tmp/fs17，root 启动；旧 frida-server16 仍在 /data/local/tmp）。adb forward tcp:27042 |
| 客户端 | `py -3`（Python 3.11），frida 17.25.2 已 pip 安装 |
| 游戏内关键进程事实 | x64 进程；arm64 库经 houdini 转译执行；**text 段映射为 r--p**（无 r-x）；arm64 库不出现在 frida 的 enumerateModules（x64 linker 命名空间） |
| 元数据 | `/storage/emulated/0/Android/data/com.sega.pjsekai/files/il2cpp/Metadata/global-metadata.dat` 磁盘加密、**内存中已解密**（rw-p 映射）。⚠️ **内存元数据布局按会话不同**（见 §4.4） |
| 转译链 | libnb.so(MuMu 壳, NativeBridgeItf@+0x4740 导出) → libhp12_x86_64.so(MuMu Unity 兼容层, 从宿主机注入, 设备 FS 不可见) → libhoudini.so(混淆, 零导出但 `NativeBridgeItf` 可被 frida getExportByName 找到) |

## 2. 核心技术图景（读懂再动手）

### 2.1 x64 → arm64 的官方调用通道（已打通，但被门控）

```
x64 代码 (frida agent)
  └ NativeFunction(NativeBridgeItf+0x18 = getTrampoline)
      handle=0, name="il2cpp_domain_get", shorty="L", len=1, type=0
      → 返回 22 字节 trampoline:  48 b8 <ticket:u64>  movabs rax, ticket
                                  49 bb <gateway:u64> movabs r11, gateway
                                  41 ff e3            jmp r11
  └ NativeFunction(trampoline) → houdini gateway(x64) → resolver(ticket 查表) → 执行 arm64 guest 函数
```

- **实测成功过**：`il2cpp_domain_get()` 返回合法 domain 指针；曾 10/10 连续调用、1ms 完成 10 次。
- ticket 每 getTrampoline 调用递增（如 0x53、0x5c...），gateway 地址每进程不同（从 trampoline 字节中解析 `49 bb` 后 8 字节可得）。
- `il2cpp_*` 全部导出可以用 `lief` 从磁盘上的 libil2cpp.so 解析偏移（probe/libil2cpp.so 已拉取，199MB）。

### 2.2 门控现象（未破解的核心问题）

- 窗口期：所有 guest 调用成功；非窗口期 100% 失败，两种症状：
  - `getTrampoline` 返回 NULL（"no tramp"）
  - 调用时报 `access violation accessing 0xdead1066`（毒值）
- 窗口与游戏状态/年龄/前后台切换/tap 均无稳定相关性；曾在会话 30 分钟处观察到 2 次窗口（相隔 6s）。
- 空闲标题画面 8 分钟 0/951 次成功；launch 高频 attach/detach 期间全失败（**怀疑频繁 attach/detach 会抑制窗口**）。
- 深挖结论（§4.6）：gateway resolver 查 ticket 注册表（`TABLE_B + ticket*16512`，有效标志在 `-0x4054`），标志清零 → 走 poison 路径。注册表稀疏映射（未分配 ticket 的地址不可读），静态 patch 未成功。

### 2.3 il2cpp 函数被内联 hook

libhp12 对 il2cpp C API（domain_get/resolve_icall/stats_get_value/is_vm_thread/thread_current/string_*/class_*/runtime_invoke/gc_* 等约 35+ 个）打了内联 hook：内存 prologue ≠ 磁盘文件，首指令变 `B <hook>`。hook 校验调用者上下文，未授权 → 0xdead1066。**恢复原始字节无效**（houdini 代码缓存仍执行旧翻译）。

### 2.4 frida 能力边界

- ✅ 全进程内存读写（含 arm64 代码/数据）、x64 模块的 Interceptor（libart/libnb/libhp12/libhoudini 的 x64 函数都可 hook）
- ❌ 直接 NativeFunction/Interceptor arm64 地址（SIGSEGV → access violation）
- ❌ `realm='emulated'`（frida 17 的 emulated realm 仅支持 QEMU 式模拟器，MuMu houdini 报 "process is not using emulation"，spawn 也一样——实测 17.25.2）
- ❌ frida `File('/proc/self/maps')` 读取卡死；`ptr()` 必须带 `0x` 前缀
- ⚠️ frida 客户端/服务端版本敏感（看雪同款环境 14.2.18 失败、16.0.11 可用；我们 16.7.19 长期使用正常）

## 3. 现状（截至本文更新）

1. **框架骨架已提交**（iaa/unity_ui/）：agent.js（gateway 调用器+窗口重试+bootstrap+dump）、injector/client/tree/locator/element。**未在真实游戏上完整验证**——卡在等窗口。
2. **后台窗口猎手**：probe/framework_hunter.py（ping→bootstrap→dump→存 probe/ui_dump.json）。注意：frida 升级 17.25.2 后旧猎手进程已死，**需要重启**（先 `py -3 -u probe/framework_hunter.py 7200 10`，它会自己 attach）。
3. **尚无成功的 dump**。tasks 业务重构未开始（需要第一次 dump 的真实节点名）。
4. 下一步最有价值的实验：**§6 的「观察 ART 自己的成功调用」**。

## 4. 失败清单（勿重复）

### 4.1 直接调用/hook arm64
`NativeFunction(guest_addr)` → access violation；Interceptor 无法作用（houdini 转译执行 + 代码缓存）。

### 4.2 恢复被 hook 的原始字节
Memory.protect+write 成功写入（游戏存活），但调用仍 0xdead1066——**houdini 翻译缓存不因宿主侧写内存而失效**。

### 4.3 realm='emulated'
frida 17 的 emulated realm 只认 QEMU 式模拟器；MuMu houdini（Netease 定制）不被识别。宿主+设备升级 17.25.2 后依旧。

### 4.4 纯内存解析 il2cpp 元数据 + 统计推导
- v31 header/TypeDefinition(0x58)/FieldDefinition(12B) 布局已逆向成功（probe/meta_parse.py、MetadataClass.cs），能离线解出 37112 个类型与全部字段名（Object.m_CachedPtr、Selectable.m_Interactable、TMP_Text.m_text 均为托管字段；GameObject/Transform 无托管实例字段，m_CachedPtr 恒在 offset 0x10）。
- **但内存元数据按会话混淆**：11497 进程的内存元数据可解析（klass->name 指向元数据 string 区验证成功），换进程（20522/25252）后 klass->name 指向的区域内容不可读（0x37640 处乱码），且 header 槽位有偏移。**跨会话不可复用，此路废弃**（除非逆向每会话解密，成本高）。
- Runtime Il2CppClass 布局部分确认：+0x10 name / +0x18 ns / +0x20 byval_type* / token@+0x11C / 大小 0x180 相邻分配；fields 数组位置未确证（+0x90/+0x98/+0xa8/+0xc8 均排除过常见布局）。

### 4.5 spawn 模式
被 pcam 反作弊 1.2 秒杀（AppCrash），无论是否 attach agent。

### 4.6 houdini 内部 patch（部分成功，未收官）
- gateway 入口 x64 反汇编完成：入口把寄存器打包 → `resolver(ticket)`。
- resolver(0x...ccd0)：`lookup(ticket)`(0x...bc50) 读 ticket 注册表（rwlock 保护，表 B 基址=`lea rip+0x3e93f1`，步长 16512=129<<7，valid 标志 @`-0x4054`）→ 失败走 poison（0xdead1066）。
- patch 尝试未完成：标志地址计算与实际映射不符（表稀疏提交，未分配 ticket 不可读），**需要用「已分配 ticket 的真实地址」做实验**（从新 getTrampoline 拿到 ticket 后按公式读，注意 r12 基址要按运行时 rip 精确计算）。

### 4.7 其它已验证细节
- 常量/坑：frida `ptr()` 必须带 `0x`；JS 里 `hex()` 不存在；rwx 匿名段 = frida 自己的；libhp12 在设备 FS 无文件（宿主注入），dump 用 frida 读内存。
- MuMu 的 hp12（libhp12_x86_64.so）含 il2cpp dumper 功能（'dump.cs'、'// RVA: 0x' 字符串）、Whale hook（WInlineHookFunction）、OAID getTrampoline 白名单、`can_houdini_hook`——**MuMu 自己有调用 guest 的能力**（仅内部使用）。

## 5. 已确认可用的构件（可直接复用）

- probe/harness.py — run_js(js, seconds, globals_)/get_device/find_game（注意进程名是日文，用 identifier 匹配）
- probe/test_trampoline2.js、test_nb.js — NativeBridgeItf 直调（houdini Itf：`Module.getExportByName('libhoudini.so','NativeBridgeItf')`；+0x10 loadLibrary、+0x18 getTrampoline、+0x20 isSupported；libhp12 把 +0x18 换成了它的 wrapper，原始 houdini getTrampoline 可从 wrapper 前几条指令的 `call [rip+disp]` 中提取）
- probe/bootstrap2.js — 窗口期一次性 bootstrap（类/方法/字段全解析，支持 PREV 续传）
- iaa/unity_ui/agent/agent.js — 整合版（RPC: ping/bootstrap/dump/state）
- probe/find_klass.js、inspect_*.js — 内存定位工具
- probe/global-metadata.mem（11497 会话的解密元数据）、probe/libil2cpp.so、probe/libhp12.so、probe/gateway.bin、probe/resolver.bin、probe/lookup.bin

## 6. 下一步路线（按优先级）

### A. 观察并复用 ART 自己的成功调用（最有希望，未做）
NativeBridgeItf 的 x64 函数可被 frida Interceptor 随意 hook（看雪文章验证过 loadLibraryExt）。
1. Hook houdini **真实 getTrampoline**（从 hp12 wrapper 提取的那个）+ hp12 wrapper：游戏运行时 ART 为 JNI native 持续创建 trampoline，记录它的 (handle, name, shorty) —— **我们一直传 handle=0，而 ART 有真实 handle**。
2. Hook gateway 入口（x64），统计成功/失败调用的 ticket 与上下文差异 → 定位门控标志位。
3. 用 ART 的真实 handle 重试 il2cpp 导出调用；若成功 → 门控绕过完成，框架立即可用。

### B. 继续窗口猎手（保底，已验证可命中）
`py -3 -u probe/framework_hunter.py 7200 10`，窗口命中即自动 bootstrap+dump 存 probe/ui_dump.json。历史命中率：~30 分钟 2 个窗口（相隔 6s）。注意避免频繁 attach/detach（疑似抑制窗口）。

### C. 换环境验证框架
在无 SEGA 反作弊的 arm-only Unity 游戏（或真机/ARM 模拟器）上先验证 iaa/unity_ui 全链路，再回头攻 pjsk。

### D. UI 树替代方案的另一个入口（不依赖 il2cpp 调用）
Unity 渲染层绕过：minicap/Accessibility 不可行，但 **Unity 的 UI 信event 不走 Android view**；若最终无法调用 guest，可考虑 hook houdini 的**渲染提交**（x64 侧 eglSwapBuffers 是 guest 调用……同样受限）——评估后基本不可行，列此存档。

## 7. 框架使用（一旦调用打通）

```python
from iaa.unity_ui.client import UnityUITree
ui = UnityUITree('com.sega.pjsekai')
ui.ensure_bootstrap(max_wait_s=600)
roots = ui.snapshot()
btn = ui.locator(name='ButtonLive').one()   # 具体节点名待第一次 dump 确认
btn.click()                                  # 走 kotonebot device.click（模拟点击，不走 hook）
```

tasks 重构计划：把 `R.<Group>.<Prefab>.find()/try_click()` 换成 `ui.locator(...)` 语义查询；autolive（auto_live*.py、live_presets、qt 的 AutoLiveDialog）不动。R.* → 节点名映射表等第一次 dump 后建立（tools/visualize_ui_dump.py 可把 dump 叠加到截图辅助映射）。

## 8. 提交记录（feat/frida-uitree 分支）

- probe: frida+il2cpp 调研结论与实验脚本
- feat(unity_ui): 通用 UI 树框架骨架
- feat(tools): UI dump 可视化工具 + 猎手点击触发实验
- fix(agent): rect 读取仅在 RectTransform 上调用 get_sizeDelta
