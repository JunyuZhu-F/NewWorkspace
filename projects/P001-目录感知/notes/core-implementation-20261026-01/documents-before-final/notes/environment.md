# 当前电脑的最小 C++ 环境核验

日期：2026-10-26。用户已确定先用现有电脑、小规模检查。未安装 Linux/WSL、未购买资源、未下载依赖或大型数据。

## 已验证

- Windows 11，约 15.81 GiB 可见内存；详细资源初始快照见 `reading-20261026/resource-snapshot.json`。
- 普通 PowerShell 的 PATH 上找不到 cl/CMake，但使用现有 VS Installer 的 vswhere 检查到 `D:/Microsoft Visual Studio` 下已有 C++ Build Tools。不能把 PATH 未发现误写成没有安装。
- MSVC 工具目录 `VC/Tools/MSVC/14.51.36231/`；通过现有 `VC/Auxiliary/Build/vcvars64.bat` 设置当前探针子进程环境后，实际完成 64 位 C++17 编译和运行。
- 探针输出：`{"cplusplus":201703,"msvc":1951,"pointer_bits":64,"ok":true}`，批处理退出码 0。
- 本地自带 CMake：`D:/Microsoft Visual Studio/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe`，实际 `--version` 输出 `4.3.1-msvc1`。
- 现有 Ninja：`D:/anaconda3/Scripts/ninja.exe`，实际 `--version` 输出 `1.13.2.git.kitware.jobserver-pipe-1`。

证据：`data-audit-20261026-01/environment-discovery.json` 是发现阶段清单；该清单中的“No compiler test”描述的是当时边界，后续真正编译证据在 `env-probe-20261026/`：

- `probe.cpp`：仅使用标准库 vector 和输出环境信息，不含目录或向量算法。
- `run-probe.cmd`：加载已安装 MSVC 的子进程环境、编译、运行。
- `vcvars.log` / `build.log`：真实工具输出。
- `probe-output.json`：真实运行结果。
- `probe.exe` / `probe.obj`：本轮生成的探针产物。

已实际执行的命令：

```powershell
& 'D:\NewWorkspace\projects\P001-目录感知\notes\env-probe-20261026\run-probe.cmd'
```

探针使用 `/std:c++17 /Zc:__cplusplus /EHsc /O2`。它只证明当前 C++ 标准库编译/执行可用，不证明 Roaring 或论文实现可编译，也不是性能基准。

## 仍未验证

- CRoaring/C++ wrapper 的版本、来源、Windows 构建与锁定方式。
- 三方案公共 bitmap 适配、真实源码工程、构建入口、单元/随机正确性检查。
- 目录/ANN 计时边界、可用峰值内存与完整运行预算。
- WSL 是否已有可用发行版未检查；本轮未启动 WSL。用户选择现有 Windows 电脑，不意味着必须转 Linux。

ENV-01 因此仍为进行中。下一步可以在既有 Windows 工具基础上核查和锁定轻量 bitmap 依赖；任何正式算法实现仍按 PLAN 的前置条件推进，不能将环境探针登记为论文实验。
