# EXP-20261027-004 — DIR-01

- 状态：complete。
- 协议：PROTO-01-20261026，项目诊断工作负载，不是作者原始工作负载。
- 源码快照：`source/hashes.json`；环境与命令：`environment.json`、`config.json`、`run-order.jsonl`。
- 原始记录：`raw/`；进程日志：`logs/`。
- 完成时统计：`summary.json`、`correctness.json`；失败时不得据此声明正常性能结论。
- 失败/中断：无。

## 版本、准入与执行

- 日期/时间：2026-10-27 00:24:48–00:27:15（Asia/Hong_Kong）；矩阵 wall-clock 146.719 秒，运行器退出码 0。
- Git 基线：main，37981aa4b187d69aa8ca8c56bbb068fe068de00d；存在工程修复未提交差异，见 engineering-repair.patch。无算法、冻结输入、协议更改。
- 实际源码/输入快照哈希：`9449921fb89f2723586c9f9dd041b72d8eb2932e3d8b9e6e56f1b8cbad9d404f`。该标识的清单范围/命名规则由运行器生成，不与准备期 SNAP 标识算法混同。
- 启动命令：`python code/scripts/run-dir01.py --project . --experiment-id EXP-20261027-004`。
- 修复后准入：Release/ASan 各 7/7 CTest，默认/插桩自检各通过；真实命令、退出码、日志在 `../EXP-20261027-003/repair-validation.json`。
- Windows 11、i7-13650HX、14 核/20 逻辑处理器、约 15.81 GiB RAM，MSVC 19.51.36260.0、CRoaring v5.3.2，Release、ASan OFF。补充环境见 environment-supplement.json；未改电源模式、亲和性或优先级，背景负载未受控。
- 原矩阵完整执行：5 个 run × 7 子负载 × 3 方案 × 默认/插桩，210 个独立进程，每个 3 次预热、20 次测量。没有减少重复或更改输入。

## 结果与独立核验

- 210/210 成功；build 1,380、DSQ 62,100、DSM 3,450、space 1,380、process/timing 各 210 条，均含预热原始值。
- `verify-results.py` 独立核对确切矩阵、每组 23 次迭代、DSQ 唯一键、接受/拒绝标志、快照/协议/输入哈希，重算汇总均值及 nearest-rank 分位数；最终退出码 0，证据见 independent-verification.json。
- 核验脚本一次在已完成核验后打印含 µ 的中文报告时遇到终端 GBK 编码异常；UTF-8 结果文件已写出。移除冗余终端报告打印后，完整重核验退出码 0。未重跑或改变任何测量数据。
- 完整描述与空间口径见 results.md；逐路径、每进程均值和尾部分位数见 summary.json。默认与插桩分池，拒绝操作不混入成功操作，ASan 结果不用于性能。
- time 默认均值（微秒）：递归 DSQ ONLINE/OFFLINE/TrieHI = 6.5276/2.6992/2.7203；非递归 = 2.4195/5.4386/5.4071；MOVE = 6.4590/13.8530/6.9070；MERGE = 207.2880/191.2200/162.5300。保留 TrieHI 非递归较慢、MOVE 未优于 ONLINE 等反例；不声称全面加速。
- 空间采样最大 private bytes 4,956,160；最大 peak working set 9,166,848；空间采样时系统可用内存最小 5,862,715,392 字节，均未触及停止阈值。它们不是目录完整堆容量。

## 验收边界与后续

- 冻结矩阵执行成功；集合检查与原始产物完整性通过。这不是论文复现整体成功，也不是原版 Viking 数值对齐。
- 独立 catalog/分阶段/目录净耗时、完整逻辑 live bytes 未采集。目录/catalog 数量、Roaring portable 大小及 Windows 进程指标分别记录，不能冒充完整存储拆分。DIR-01 的全部完成条件和 OBJ-03 仍保留这项缺口。
- 前三次失败完整保留在 001/002/003，未混入成功矩阵；未下载数据、加载向量、运行 ANN 或扩规模。
- 下一步只做结果/成本口径审查，确定补测设计或明确有限验收范围；任何新协议应另存版本，不能回改本次冻结协议与实测记录。
