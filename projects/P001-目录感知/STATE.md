# STATE.md — DIR-01 准备完成，待正式测量

更新时间：2026-10-26T22:12:12+08:00，Asia/Hong_Kong。项目：`D:/NewWorkspace/projects/P001-目录感知`。

## 当前结果与计划位置

**PROTO-01 已完成；DIR-01 进行中，准备阶段已完成，正式性能矩阵尚未运行。** 当前没有运行中的编译、正确性测试或性能实验进程，也没有已登记的 DIR-01 性能实验编号。

三方案 C++17 目录层、独立判定器及小规模正确性门保持有效。DIR-01 准备新增默认/插桩双核心基准驱动、只读统计、冻结输入、正式矩阵运行器与汇总器；快照为 **SNAP-0b110bb7dee8280f**。在包含新增基准自检的验证中，**Release 与 RelWithDebInfo+ASan 各 7/7 CTest 通过，默认和插桩基准自检均通过**；ASan 未报告地址内存错误。准备审查、命令、退出码和日志见 `notes/dir01-preparation-20261026-01/`。

这些结果只证明当前单父目录、串行核心及基准门在冻结小规模输入上的正确性；**没有性能测量值、检索质量结果或全库规模结论**。CTest/自检耗时不是论文性能结果，准备完成也不等于 DIR-01 完成。

- 已完成：既有材料/精读/范围审核、SPEC-TREE-01、DATA-ARXIV-SCOPE-01、DATA-CATEGORY-MEANING-01、DATA-TIME-PILOT-01、ENV-01、ORACLE-01、CORE-01/02/03、CHECK-01、SPEC-TIME-PILOT-01、PROTO-01；DIR-01 的驱动/统计/输入/准入门准备已完成。
- 进行中：DIR-01 正式测量；DATA-01、SPEC-01 的剩余真实数据与协议核验。
- 材料阻塞：SPEC-ARXIV-CATEGORY-01（真实类别非递归/多归属 DSM）。
- 未开始：SEARCH、SCALE、REPORT；未运行训练、正式性能基准或完整实验，未购买资源。

## 恢复工作应先看

| 内容 | 唯一详细记录 |
|---|---|
| 目标、授权及验收 | `TASK.md` |
| 顺序、依赖与状态 | `REPRODUCTION_PLAN.md` |
| 已冻结的小规模性能协议 | `notes/benchmark-protocol.md`，SHA-256 `81ec16d0f07ea1c74715de2a4b6c049c9292766ddc0e36240a1668f3a21eed24` |
| DIR-01 准备审查与验证 | `notes/dir01-preparation-20261026-01/review.md`、`validation-record.json`、Release/ASan 日志；快照 SNAP-0b110bb7dee8280f |
| 冻结基准输入 | `notes/benchmark-fixtures-20261026-01/manifest.json`，SHA-256 `6a300c9d995084a5ae3782ae2d5b763e08056f900c0e23967749c5d3272fe1d8` |
| 核心方法映射与原始正确性证据 | `notes/core-review.md`、`notes/core-implementation-20261026-01/validation-record.json`，基线快照 SNAP-dd12b2f5ac546566 |
| 实现入口/可执行命令 | `code/README.md`、`code/scripts/build-test.cmd` |
| 语义约定/时间样本序列 | `notes/operation-spec.md` §1–7 |
| 环境/依赖 | `notes/environment.md`、`code/third_party/croaring/LOCK.json` |
| 原文理解/材料缺口 | `notes/paper-card.md`、`notes/materials-and-gaps.md` |
| 只读数据核查 | `notes/data-audit.md`、`notes/category-semantics.md` |

## DIR-01 准备边界

- 冻结图 2 输入含 9 条绑定、11 个目录、22 条查询；时间视图含 10,000 条绑定、34 个目录、68 条查询。预期由独立 Python 枚举生成，C++ 仍逐 ID 对照独立判定器。
- 默认与插桩矩阵各 105 个独立进程，合计 210；`--plan-only` 仅核对矩阵，实测进程数为 0。预期完整原始行数已核对，但不是已产生的实验输出。
- 默认核心没有查询计数路径；插桩计数与默认计时不混池。空间分别记录目录/catalog/bitmap/Roaring portable 大小及 Windows 进程指标，不冒充完整堆容量。
- catalog 包含在公开维护总时延中；未单列的 catalog/阶段耗时明确标为未采集，不能用计数或减法伪造。

## 尚未解决与影响

1. ARXIV 类别列表祖先/后代同时出现，递归观测不能唯一确定直接归属。时间视图通过不能解除真实类别非递归/维护缺口，不取首类别或静默去祖先。
2. WIKI 原查询目录、作者 DSM 序列缺失；距离/归一化、质量真值与 Viking 配置未完整恢复。不得将项目诊断说成作者工作负载或声明原版数值对齐。
3. 公共 catalog 冲突合并刷新采用扫描，计数单列；PE 用稳定目录对象关联 catalog。后续性能须说明这些工程选择和成本边界。当前没有微秒延迟、内存对比或加速倍数结论。
4. 不覆盖并发、持久化、内存分配失败回滚、真实多归属；未验证任意深度/全量规模。

## 下一步与资源保护

下一项为 **DIR-01 正式小规模测量**：启动前在 `EXPERIMENTS.md` 登记唯一真实实验编号及协议/快照/输入，由用户明确指示后运行冻结矩阵；保存全部成功、失败或中断记录，再汇总和判断是否满足 DIR-01 完成条件。不得用准备自检或 `--plan-only` 代替正式实验，不得减少重复数或改小输入冒充原协议。

当前 Windows 11、约 15.81 GiB 内存，MSVC/CMake/Ninja 与 CRoaring v5.3.2 可构建；未安装/启动 Linux/WSL，ANN 未接入。大规模运行仍须用户另行决定。真实类别/WIKI 等各自材料前置不变。

原始 `dataset/raw/` 只读；复用冻结 metadata，未读取全量向量。工作区和项目均不是 Git 仓库；没有 commit，未初始化、提交或推送。源码快照/hash 代替 Git 版本。构建目录含真实二进制，可再生成；不能以文件存在代替日志。

## 本次增量：DIR-01 准备完成

- 修复准备增量中已确认的源码文本损坏，从 SNAP-dd12b2f5ac546566 恢复受损内容后加入基准准备功能；三方案查询集合及 MOVE/MERGE 核心算法未改。详细边界见准备审查记录。
- 新增基准驱动、自检、只读统计、冻结输入生成、运行与汇总脚本；保存 SNAP-0b110bb7dee8280f、源码 zip/hash/diff、固定输入及协议哈希。
- Release 与 ASan 各 7/7 CTest、默认/插桩自检通过；三个 Python 脚本通过 `py_compile`，`--plan-only` 成功且未测量。
- 未登记正式实验、未创建 `experiments/<实验编号>`、未运行性能矩阵，未产生任何性能结论。TASK 的目标与范围未改变。
- 交接只读复核：当前 32 个清单文件及 ZIP 成员与 SNAP-0b110bb7dee8280f 一致，ZIP 校验值与记录一致；Release/ASan 日志锚点仍有效，`experiments/` 为空，相关运行进程为 0。PLAN、TASK、EXPERIMENTS 状态无需因本次交接改变。
