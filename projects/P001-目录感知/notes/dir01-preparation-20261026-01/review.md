# DIR-01 准备审查记录

日期：2026-10-26，Asia/Hong_Kong。范围只包括 PROTO-01 的实现、准入门和正式运行准备；**未运行正式性能矩阵，未产生性能结论**。

## 1. 现场恢复与变更边界

- 项目及 `code/` 均不是 Git 仓库，不能用 Git 证明工作树状态；沿用源码快照和 SHA-256。
- 本轮开始时存在未登记的准备增量，其中 `bitmap.hpp` 被错误字符替换，`index.hpp`/`index.cpp` 含字面量 `` `r`n``，不能直接编译。这些文件不在已验证快照中。已从 `SNAP-dd12b2f5ac546566` 恢复受损文本，再单独实现可审查的统计/计数接口；没有重置或覆盖其他项目、数据、既有实验记录。
- 原有 PE-ONLINE、PE-OFFLINE、TrieHI 的 posting/Inc、查询集合计算和 MOVE/MERGE 算法未改。维护函数入口增加诊断计数清零，使拒绝操作不返回上一次操作的陈旧计数。
- `bitmap.hpp` 仅增加 CRoaring `roaring_bitmap_portable_size_in_bytes` 只读转发。未修改第三方源码。

## 2. 实现审查

- 默认 `directory_core` 不定义 `DIRECTORY_ENABLE_WORK_COUNTERS`，没有 `query_work_` 成员和查询计数路径。独立 `directory_core_instrumented` 使用相同源码和 Release 优化配置，查询计数仅用于诊断，绝不与默认时延混池。
- 查询计数区分路径段、实际访问目录、直接孩子、位图读取、返回副本、并/差 API 调用。空结果上的实际并/差调用也计数；它们是操作计数，不是耗时或复杂度证明。
- `IndexStatistics` 只含目录数、catalog 条目数、位图数、Roaring portable 大小。未伪造 allocator/live bytes。Windows 进程 working set/private bytes/peak working set 另由 `GetProcessMemoryInfo` 采集；系统可用内存由 `GlobalMemoryStatusEx` 采集。
- 构建、DSQ、DSM 主口径均围绕公开 API；结果 cardinality/逐 ID oracle、输出和统计在计时区外。构建包含 index 构造，旧对象析构不计入单次构建；DSM 每项操作从相同冻结状态连续执行，序列间重建。
- catalog 始终包含在公开维护调用总时延中；当前没有真实独立 catalog 计时，字段明确为 `included_in_total_not_separately_timed`。分阶段耗时为 `not_collected`，没有用计数或减法伪造。
- 拒绝 MOVE 单独标记 `accepted=false`，不并入成功操作分布。图 2 MOVE/MERGE 每个样本独立初始状态；时间 DSM 按冻结 MOVE→MERGE→拒绝 MOVE 顺序。

## 3. 冻结输入与正确性门

- `prepare-benchmark-fixtures.py` 校验时间输入 SHA-256 `9aa84f093dfd4e9c4e1633c22ae7a9df424809fee9f45fc22fb96f85c04f36b6`、10,000 个连续 ID 和路径约束，不读取向量。
- 查询路径为根优先、其余 UTF-8 字节字典序。预期由 Python 独立路径/绑定枚举生成，不调用 C++ 核心或 oracle。摘要为升序 uint32 ID 小端字节的 FNV-1a 64；同时保留逐 ID oracle 检查。
- 固定输出：`figure2` 9 条、11 目录、22 查询；`time` 10,000 条、34 目录、68 查询。DSM 数量锚点在每次操作后检查，所有目录两模式与 oracle 逐 ID 比较；拒绝操作要求拓扑/catalog 不变。
- `self-test` 覆盖三策略的图 2、时间初始状态、图 2 MOVE/MERGE、时间完整 DSM，以及普通零暴露/插桩计数和空间统计。既有 CTest 仍保持 7 项，基准自检另列，不把自检耗时当性能数据。

## 4. 正式矩阵与汇总核对

- 默认：5 run × 3 策略 × 7 子负载（figure2 build/dsq/move/merge；time build/dsq/dsm）= **105 进程**。插桩重复同矩阵另 **105 进程**，合计 **210**。
- 含预热预期原始行数：build 1,380；DSQ 62,100；DSM 3,450；space 1,380；process 210。汇总器缺行、多行、进程失败或计数状态错误会拒绝生成正常总结。
- 统计仅纳入 `warmup=false`，保留每 run 均值和 pooled 均值/P90/P95/P99/P99.9；nearest-rank 为 `x[max(1,ceil(pN))]`。小样本 P99.9 标为不稳定描述值。
- 运行器在启动前检查真实实验登记，创建新证据目录、源码/输入/协议快照和环境；强制单进程 120 秒、总计 30 分钟、内存和输出上限。`--plan-only` 只输出矩阵，不创建实验或测量。

## 5. 验证结果与未决项

验证命令、退出码和日志见本目录 `validation-record.json`。最终只读复核确认 32 个清单内当前文件、ZIP 成员及逐成员 SHA-256 全部一致，ZIP 可完整读取；ZIP 容器自身 SHA-256 为 `b99cb307ad56dda2b6c7faa2a47c3e6ea9e5075eee7959dc0de6602a26b2605b`，与快照内容标识分开记录。正式实验尚未登记，`EXPERIMENTS.md` 只记录准备状态；没有 `experiments/<DIR-01>` 输出。

准备完成不等于 DIR-01 完成。下一步是审查本快照后登记唯一实验编号，再按用户指令运行正式矩阵；任何失败、中断或资源停止必须保留，不得减少重复数或改小输入冒充原协议。真实类别、多归属、WIKI、ANN 和全库缺口不变。
