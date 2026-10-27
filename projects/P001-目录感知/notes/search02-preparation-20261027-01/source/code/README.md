# 单父目录核心实现

## DIR-01-COST-02 独立诊断工具

2026-10-27：独立阶段计时和请求分配追踪已实施；准入证据见 `../notes/cost02-preparation-20261027-01/`。正式补测协议为 `../notes/benchmark-cost-protocol-20261027.md`。原默认性能输入/输出和 build-Release 二进制保持不变。

```powershell
& 'D:\NewWorkspace\projects\P001-目录感知\code\scripts\build-test.cmd' Release normal cost
& 'D:\NewWorkspace\projects\P001-目录感知\code\scripts\build-test.cmd' RelWithDebInfo asan cost
python code/scripts/run-cost02.py --plan-only
```

cost 构建位于独立的 build-Release-Cost / build-RelWithDebInfo-ASan-Cost，包含原7项、phase7项、allocation7项及两项准入自检，共23项 CTest。第四参数 `build-only` 只构建，`admission-only` 只跑两项诊断准入门；不得以准入自检记录替代正式性能。

- `include/directory/diagnostics.hpp`、`src/diagnostics.cpp`：默认构建宏展开为空；阶段构建记录互斥的直接时间区间，allocation 构建记录实际请求字节及指针归属，两者不同时开启。
- `tests/cost_diagnostics.cpp`：复用冻结输入和独立判定器，维护/查询逐ID核验；内存采样先于 oracle，拒绝不变、销毁归零。
- `scripts/verify-cost-fixtures.py`：只读校验冻结输入，避免构建时反复生成共享别名。
- `scripts/run-cost02.py`：135进程矩阵计划、准入快照/二进制核对、早期失败记录与资源停止；`--plan-only` 不测量。
- `scripts/summarize-cost02.py`：严格完整性门与逐阶段/状态统计；缺行或失败不生成正常总结。
- `scripts/add-cost-scopes.py`：本次一次性开发注解脚本，只能用于原基线，已有注解时会拒绝，不是日常构建入口。

后续用户明确指定正式运行后，先登记唯一实际 EXP，再执行 `python code/scripts/run-cost02.py --project . --experiment-id <真实编号>`；当前没有新实验编号或135进程结果。诊断时间不是默认时间，requested bytes 不是物理堆/序列化大小；拒绝异常传播阶段覆盖不完整的限制见正式协议。

这里是依据论文 §III/IV 独立编写的 C++17 目录元数据层，不是作者源码，也不是完整向量数据库。接口输入是 entry ID 与目录，输出为合法 ID 位图；不加载向量、训练模型或执行 ANN。

实现包括 PE-ONLINE、PE-OFFLINE、TrieHI，以及与索引结构独立的测试判定器。当前范围是一条目一个逻辑父目录、串行合法 MOVE/MERGE。真实类别多归属协议仍见项目 STATE/GAP 清单。

## 构建与验证

本机已安装的 Visual Studio、CMake、Ninja、Python 路径写在 Windows 辅助脚本中；不安装系统工具，不联网获取构建依赖：

```powershell
& 'D:\NewWorkspace\projects\P001-目录感知\code\scripts\build-test.cmd' Release
& 'D:\NewWorkspace\projects\P001-目录感知\code\scripts\build-test.cmd' RelWithDebInfo asan
```

第一条构建普通 Release，第二条在独立目录为核心、测试与 CRoaring 启用 AddressSanitizer。均限制编译并行为 2，并通过 CTest 执行所有正确性测试。ASan 运行须保留 MSVC 运行库 PATH，因此使用此脚本加载现有开发环境。

脚本会校验已冻结的 `../notes/time-pilot-20261026-01/bindings.jsonl` 并生成构建目录内 TSV；样本缺失或哈希不符会停止，不自动重新选择数据。默认 CTest 包括位图所有权、固定语义、四种子各 1,000 步和时间样本正确性。脚本随后分别运行普通与插桩基准驱动的 `self-test`，覆盖三策略全目录/逐 ID oracle、固定查询摘要、DSM 锚点、拒绝不变性、计数和空间接口。所有检查使用显式 require，不依赖 Release 中会消失的 assert。

可直接运行已构建测试程序的模式为 `bitmap`、`fixed`、`random <seed> <steps>`、`pilot <bindings.tsv>`。编译/CTest 耗时仅用于开发日志，不是论文性能结果。

## 文件职责

- `include/directory/index.hpp`：统一目录接口、错误码、维护/查询诊断计数和只读空间统计。
- `tests/benchmark.cpp`：DIR-01 驱动；公开 API 计时、逐查询/操作 JSONL、独立 oracle 校验和进程资源采集。
- `scripts/prepare-benchmark-fixtures.py`：从冻结输入独立生成绑定、操作、查询基数/FNV-1a 摘要；哈希不符或已有文件不同即拒绝覆盖。
- `scripts/run-dir01.py`：正式矩阵/资源停止/证据目录；`--plan-only` 只展开计划，不测量。
- `scripts/summarize-dir01.py`：过滤预热，按进程和 pooled 样本汇总，nearest-rank 分位数；不完整记录直接失败。
- `include/directory/bitmap.hpp`：CRoaring C API 的小型内存所有权适配，不实现新位图算法。
- `src/path.cpp`：项目已明确的路径合法域与边界规则。
- `src/index.cpp`：两个路径展开方案和 TrieHI；两种 PE 共用辅助结构但保留不同 posting/查询/维护策略。
- `tests/oracle.*`：独立的路径/ID 枚举判定器，不调用生产路径助手、posting 或 Trie。
- `tests/core_tests.cpp`：论文图 2 手工预期、拒绝操作、稳定节点身份、随机状态核验和时间目录样本。
- `third_party/croaring/LOCK.json`：官方 v5.3.2 文件/许可证来源与 SHA-256；C/h 与官方 release digest 对齐。作者使用的版本未知。


## DIR-01 准备状态与正式入口

冻结输入和独立预期位于 `../notes/benchmark-fixtures-20261026-01/`。摘要定义为：对升序 uint32 ID 的小端四字节序列执行 FNV-1a 64；空集合为 offset basis。摘要用于发现意外变化，逐 ID 正确性仍由独立 oracle 判定，不以摘要碰撞概率代替集合核验。

`directory_benchmark` 链接默认核心，不在范围查询路径维护查询计数；`directory_benchmark_instrumented` 从同一源码单独编译并定义 `DIRECTORY_ENABLE_WORK_COUNTERS`。后者只用于诊断，其计数是位图 API 调用/访问次数，不与默认时延混池。默认核心的 `last_query_work()` 返回零值，驱动依据 `instrumented` 明确标记 `not_collected_in_default_core`，不能把零解释为真实工作量。

`statistics()` 只报告真实可取得的目录数、catalog 条目数、位图数和 CRoaring portable 大小。它不是堆容量、live bytes 或完整序列化索引大小。Windows working set/private bytes/peak working set 由进程 API 另行记录；不向量化，`vector_bytes=0`。

准备自检命令：

```powershell
& 'D:\NewWorkspace\projects\P001-目录感知\code\build-Release\directory_benchmark.exe' self-test 'D:\NewWorkspace\projects\P001-目录感知\notes\benchmark-fixtures-20261026-01'
& 'D:\NewWorkspace\projects\P001-目录感知\code\build-Release\directory_benchmark_instrumented.exe' self-test 'D:\NewWorkspace\projects\P001-目录感知\notes\benchmark-fixtures-20261026-01'
python 'D:\NewWorkspace\projects\P001-目录感知\code\scripts\run-dir01.py' --project 'D:\NewWorkspace\projects\P001-目录感知' --plan-only
```

正式 DIR-01 为 5 run × 3 策略 × 7 子负载 = 105 个默认进程，另有 105 个插桩进程；每个进程 3 预热 + 20 测量。正式运行前必须先在 `EXPERIMENTS.md` 登记唯一真实实验编号，然后执行：

```powershell
python 'D:\NewWorkspace\projects\P001-目录感知\code\scripts\run-dir01.py' --project 'D:\NewWorkspace\projects\P001-目录感知' --experiment-id '<已登记实验编号>'
```

运行器会新建证据目录并复制协议、源码、输入和哈希，不会在已有目录混合重跑。完成条件仍以 `../notes/benchmark-protocol.md` §11 为准。准备自检和 `--plan-only` 不产生性能结果；本轮未执行上述正式矩阵。

## 接口与语义

`make_index(Strategy)` 创建方案；`mkdir`/`insert` 准备目录和唯一 uint32 ID；`query(path, recursive)` 返回 exists 与独立所有权的 Bitmap；`move(source,new_parent)` 把源根挂到新父目录；`merge(source,target)` 合入目标根。详细错误/no-op 约定和原文依据以 `../notes/operation-spec.md` 为准。

查询路径按完整段区分，规范形式为 `/a/b/`；根为 `/`。非法路径、重复 ID、成环移动、同名目标移动和包含关系合并被明确拒绝。`directories`、`bindings`、`validate`、`identity` 是验证/审查入口，不在被测范围查询中使用。

PE-OFFLINE/TrieHI 非递归查询按总集合减直接孩子子树并集实现，没有添加 Local 查询缓存。Trie MOVE 保留节点身份、只重连源根并更新受影响祖先；MERGE 对同名目录递归协调，不冲突子树整体挂接。源根直接条目的 catalog 也必须转到目标，避免漏条目。

## 当前工程边界

公共 catalog 用稳定目录对象记录逻辑父目录；冲突合并的直接绑定刷新采用扫描 catalog 的简单实现，扫描次数单列在 MaintenanceWork 中。查询不使用 catalog 计算范围，也不借用它绕过论文集合差。

因此当前可以审查语义，但不能直接用整段 wall-clock 维护时间宣称论文复杂度或速度复现。后续计时须区分目录元数据与公共 catalog，并统一口径。预条件拒绝保证无逻辑状态变化；内存分配失败的事务回滚、并发读写和持久化不在本轮范围。

原文对应关系、代码审查和真实测试证据见 `../notes/core-review.md`。数据缺口不因本实现通过而关闭。
