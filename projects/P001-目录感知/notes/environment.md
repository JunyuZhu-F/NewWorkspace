# 当前电脑的最小 C++ 环境核验

日期：2026-10-26。用户已确定先用现有电脑、小规模检查。未安装 Linux/WSL、未购买资源、初始探针未下载依赖；后续只获取轻量 CRoaring 源码，未下载大型数据。

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

## 核心实现环境锁定与实际验证

2026-10-26 后续：ENV-01 已在当前目录核心范围完成。MSVC 实际版本 19.51.36260.0，64 位；C++17/C11，Release 与 RelWithDebInfo-ASan 分目录构建。现有 ASan 运行库可用，没有额外安装系统/工具。

- 依赖：官方 CRoaring v5.3.2 轻量 C/h 与许可证，来源/哈希见 `../code/third_party/croaring/LOCK.json`；C/h 与官方 release digest 对齐。作者版本未给，只是工程固定版本。
- 位图适配用 C API 与项目 RAII；核心、测试、CRoaring 均纳入 ASan 构建。
- 构建入口 `../code/scripts/build-test.cmd` 加载现有 vcvars64 子进程环境，CMake/Ninja 编译并行数 2；配置/编译/CTest 失败均返回非零。时间样本转换先验 hash，不访问向量。
- 实际结果：Release 7/7、RelWithDebInfo-ASan 7/7，退出码均 0；ASan 未报告地址内存错误。命令/审查/日志/快照见 core-review.md §5、core-implementation-20261026-01/validation-record.json。
- 上游 roaring.h:6110 的 C4702 警告已审查并保留，不宣称零警告。

## 尚未完成的环境或实验条件

ANN 未选定/接入；性能计时、全量峰值内存、正式预算未验证。WSL 发行版没有检查，本轮未启动 WSL。Linux/125GB 原文机器与当前 Windows/15.81GiB 不可视为同条件。ENV-01 完成只证明当前核心可构建测试，不解除 DATA/SPEC 或规模审批。
