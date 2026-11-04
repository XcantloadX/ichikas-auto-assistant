# iaa guest agent（arm64）

注入 Unity(il2cpp) 游戏进程的宿内代理：frida 经 Java 层 `System.load` 加载本
.so，houdini 以 guest 代码执行；agent 内 dlsym/UnityResolve 调用 il2cpp C API，
dump UI 树并通过 TCP 暴露给宿主（Python 侧见 `iaa/unity_ui/`）。

## 目录结构

```
guest_agent/
├── CMakeLists.txt            # NDK 构建（arm64-v8a, android-24, c++_static）
├── src/
│   ├── iaa_agent.cpp         # agent 主体（UnityResolve 解析层 + TCP 服务）
│   └── stubs.c               # guest libc 缺失符号空桩（必须参与链接）
├── third_party/UnityResolve/ # UnityResolve.hpp（MIT，vendored，勿随意改动）
├── iaa_agent.so              # 构建产物（提交进仓库，injector 按大小判断重推）
└── build/                    # cmake 构建目录（不提交）
```

## 构建

需要 Android NDK r27（`D:/SDK/Android/ndk/27.0.12077973`）：

```bash
cd guest_agent
cmake -B build \
  -DCMAKE_TOOLCHAIN_FILE=D:/SDK/Android/ndk/27.0.12077973/build/cmake/android.toolchain.cmake \
  -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-24 \
  -DANDROID_STL=c++_static -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

产物 `iaa_agent.so` 直接生成在本目录（`LIBRARY_OUTPUT_DIRECTORY` 指向源目录），
`iaa/unity_ui/injector.py` 的 `ensure_agent_so()` 会按文件大小自动重推到设备。

## 为什么这样编（MuMu/houdini 约束，勿随意改）

- **`ANDROID_STL=c++_static`**：agent 依赖静态 libc++（UnityResolve 用 STL），
  绝不能产生 `libc++_shared.so` 的 DT_NEEDED（游戏进程里没有）。
- **`src/stubs.c` 必须链接**：MuMu 的 arm64 guest libc 不导出
  `__register_atfork` / `__cxa_atexit`（NDK crt 默认引用它们），stubs 在本
  .so 内提供空桩，消除这些未定义导入——曾实测：仅此差异决定 houdini 能否
  加载（"failed to link"）。
- **max-page-size=4096 / soname 固定**：与 guest linker 与部署路径约定一致。

## 部署与验证（手动流程）

```bash
adb -s 127.0.0.1:5555 push iaa_agent.so /data/local/tmp/
adb -s 127.0.0.1:5555 shell "su -c 'chmod 644 /data/local/tmp/iaa_agent.so'"
# 游戏进到首页后（或让 iaa/unity_ui/client.py 的 ensure_ready 自动做）：
py -3 probe/inject_agent.py            # frida 注入
adb -s 127.0.0.1:5555 forward tcp:29170 tcp:29170
# TCP 行协议（每连接一请求一响应，单行 JSON，响应以 \n 结尾）：
#   {"cmd":"ping"}  {"cmd":"boot"}  {"cmd":"dbg"}  {"cmd":"dump","max":6000}
```

注意：agent 只能注入**运行中**的进程（spawn 会被反作弊杀）；游戏重启后
agent 失效，宿主 `UnityUITree.ensure_ready()` 会自动重注入。

## 与 UnityResolve 的关系

解析层基于 [UnityResolve.hpp](third_party/UnityResolve/UnityResolve.hpp)
（[issuimo/UnityResolve.hpp](https://github.com/issuimo/UnityResolve.hpp)，MIT）。
`Init()` 时全量枚举程序集/类/方法/字段，之后按名字取 `Method*` 直接调用。
**不依赖任何静态元数据**（dump.cs / script.json），游戏更新无需重新生成。

两处本仓库自有实现（不使用库内版本的原因写在函数注释里）：

- `mono_string_to_utf8()`：库的 `String::ToString()` 以 4 字节 `wchar_t` 读
  UTF-16 缓冲，仅 wchar_t==2 字节的平台（Windows）正确；且不处理代理对。
- 装箱值读取（`read_boxed_int/bool`）：`il2cpp_runtime_invoke` 对值类型返回
  装箱对象指针（值在 +0x10），不能直接当返回值用。
