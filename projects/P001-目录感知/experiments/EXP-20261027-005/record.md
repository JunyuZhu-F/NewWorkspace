# EXP-20261027-005 — cost diagnostics

- Actual status: complete
- See run-status.json, config.json, run-order.jsonl, raw/, logs/.
- Project diagnostic workload, not author workload; no vectors or ANN.

## 实际执行与版本

- 状态：完成，135/135进程成功，运行器退出码0；重核验脚本退出码0。没有重跑旧004或重新编译。
- 本地时间：2026-10-27 01:34:55–01:38:10（Asia/Hong_Kong），wall-clock 194.859秒；UTC原值见run-status.json。
- 命令：`python code/scripts/run-cost02.py --project . --experiment-id EXP-20261027-005`。逐进程真实命令、起止时间、退出码在run-order.jsonl，标准输出在logs/。
- 协议：PROTO-COST-02-20261027；SHA-256 `589d3b6f7abe9123c3f094a04e54084e885a7d77114fc3ae74770f92dc56e066`。代码：COST02-440a2e0f81208f81，30文件hash `440a2e0f81208f814bddf4b3f709b8739ec122471e8d32cae57f86418a1fb997`，已保存实际source/和二进制hash。Git基线37981aa，含保留的未提交诊断增量，未提交/推送。
- 5个run，3预热+20测量，105阶段进程+30分配进程。冻结人工树和10,000条时间视图，单线程串行，未更改电源/优先级/亲和性，背景负载未受控。环境见environment.json、environment-supplement.json、build-info.json。
- 配置文件中status/measurements_run是启动时计划字段，最终实际状态以run-status.json、run-order.jsonl和raw/cost-process.jsonl为准，不能据配置中的0推断没有运行。

## 完整性与结果

- 原始phase 33,465行、allocation 3,795行、overhead/process/run-order各135行，包含全部预热。正常统计排除预热，未删异常值。
- 运行器严格汇总通过；verify-and-report.py重新核对矩阵/源码/输入/协议，重算阶段均值、nearest-rank分位数和各run均值，以及请求内存统计。所有索引销毁后归属字节/块归零，拒绝前后存活字节相同。独立证据见independent-verification.json，结果表见results.md。
- 时间MERGE中catalog占同一诊断构建已观测核心区间均值的比例：ONLINE 94.7%、OFFLINE 90.3%、TrieHI 94.0%。是直接区间观测，不是默认总时间减法，也不推断004默认占比。
- 时间初始目录+catalog+bitmap请求字节：ONLINE 518,288、OFFLINE 542,136、TrieHI 544,840；其中catalog均480,064字节。在此浅树实现中TrieHI没有总逻辑请求内存优势；不能推广为所有规模或原版表V结论。
- ONLINE诊断MOVE均值46.646微秒，中位数7.2微秒、最大3,943.5微秒，高值已完整保留；没有证据确认其原因，不能用诊断均值替换004默认成绩。
- 旧004的11个关键文件hash保持一致，原默认二进制/源数据/旧协议未改。本轮中断发生在记录收尾，矩阵和核验已实际完成；此次只补记录并重核验，没有重新测量。

## 验收与限制

当前人工树/10,000条单父目录诊断分支的运行及证据条件已满足；与004共同支持DIR-01小规模任务的有边界验收，见notes/dir01-small-scope-acceptance-20261027.md。这不关闭DATA/SPEC、真实类别/WIKI、ANN、全量规模或整篇论文复现。

阶段探针有开销，小时段不可精确归因；拒绝异常传播未完整分阶段。内存是实际请求载荷，不含allocator元数据、碎片和observer，非物理堆或序列化大小。质量/全库/原版数值对照均未执行。下一步依用户授权只读核查全量ARXIV时间metadata，不启动扩规模性能矩阵。
