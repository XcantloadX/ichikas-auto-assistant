cmake_minimum_required(VERSION 3.22)
project(iaa_guest_agent C CXX)

# guest agent（arm64 .so）：经 frida System.load 注入 Unity(il2cpp) 游戏进程，
# 由 houdini 以 guest 代码执行。构建目标固定为 android arm64。
#
# 构建（在仓库根目录或本目录执行）：
#   cmake -B build \
#     -DCMAKE_TOOLCHAIN_FILE=$NDK/build/cmake/android.toolchain.cmake \
#     -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-24 \
#     -DANDROID_STL=c++_static -DCMAKE_BUILD_TYPE=Release
#   cmake --build build
#
# 产物自动落到本目录 iaa_agent.so（iaa.unity_ui.injector 按该路径部署）。

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

add_library(iaa_agent SHARED
    src/iaa_agent.cpp
    src/stubs.c
)

target_include_directories(iaa_agent PRIVATE third_party)

find_library(log-lib log)
target_link_libraries(iaa_agent PRIVATE ${log-lib})

# houdini 加载约束：
#  - max-page-size=4096（MuMu guest linker 4K 页）
#  - soname 固定（宿主 injector 按固定路径部署/加载）
#  - guest arm64 libc 缺 __register_atfork/__cxa_atexit 等：
#    src/stubs.c 在本 .so 内提供空桩，使最终产物不产生这些未定义导入
target_link_options(iaa_agent PRIVATE
    -Wl,-z,max-page-size=4096
    -Wl,-soname,iaa_agent.so
)

# 产物直接输出到源目录，供 iaa/unity_ui/injector.py 部署
set_target_properties(iaa_agent PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    OUTPUT_NAME iaa_agent
    PREFIX ""
)
