# EXP-20261027-007 — WIKI独立目录性能

状态：完成当前独立小规模分支，10/10正式进程退出0，43470条原始计时核验通过，其中正式测量37800条、保留的预热记录5670条。最终入口status.json、verification-*.json、final-check.json；结果表及可重绘CSV在results.md、analysis-01/。非作者原始工作负载，不关闭原论文数值对齐或全量目标。

## 授权、协议和版本

用户明确要求按独立协议执行、审查并更新文档；不等待作者联系。启动前协议notes/wiki-independent-protocol-20261027.md已冻结（正式副本protocol.md），实验已登记EXPERIMENTS。Git基线be59bbccb9e3f8e283328f453643b7d50211736d加保留的未提交成果；实际source/和source-hashes.json为源码依据，environment.json包含现场与Git状态，不能只用HEAD代表运行源码。原006的46源码未改，未重跑ARXIV。

本轮复用WIKI-DATA/CHECK的10000等间隔global ID样本，不按qrels或测量结果选样；源向量只读抽取这些记录及456条query。query metadata为空的描述/文件不一致保留，用户确认网盘文件也为空；本项目没有补造作者约束。

## 入口与真实运行

项目根使用D:/anaconda3/python.exe -B code/wiki_experiment/pipeline.py --stage directory --preparation notes/wiki-independent-preparation-20261027-01 --experiment EXP-20261027-007。该命令已执行，不可覆盖既有实验目录；后续重跑必须另选EXP并登记。

科学准入证据见notes/wiki-independent-preparation-20261027-01/：新目录默认/phase及检索包装器Release/ASan均通过独立核验。原后端前缀逐字节相同，检索包装器仅调整456/912形状和合同标签，生成差异由pipeline.generated断言核查。三方案算法无修改，固定样本旧WIKI准入未重跑。

正式阶段从2026-10-27T04:29:23.827582+00:00到2026-10-27T04:41:03.712195+00:00（UTC；香港时间+8小时），不是查询延迟。commands.jsonl逐条保存真实命令、退出码、时间、观测资源，run-*.log及每秒monitor保存原过程。build flags及CMakeCache已快照，Release正式计时关闭ASan。默认/phase分池；原始重复值、候选和质量数据不筛选。

资源门禁：单进程600秒、矩阵1800秒、private≤2GiB、available≥2GiB、输出≤1GiB。本次正式worker按每秒采样观测private最大157949952字节、available最小4963151872字节，未触发门禁。采样值不是精确峰值/索引独占；核验器也有独立内存开销，不能把worker样本当整轮最大内存。结果规模见final-check，不安装/修改依赖。

## 核验和结论边界

统计导出首次遇Python源编码识别错误，原日志notes/wiki-independent-preparation-20261027-01/export-console.log保留；添加显式UTF-8声明后另存export-recovery-01-console.log成功，没有重跑测量。最终finalize-console.log及final-check通过。

独立Python核验源区域、目录选择/哈希配对/操作规则、候选状态、模型/排名（检索）、全部重复格位、统计与计时边界；全部worker输出、当前源码及归档快照、fixture哈希在收尾再次核对。C++测量过程每次比较完整候选/结果；目录维护后全树/catalog/bitmap校验。程序运行时间不作为论文成绩。

本轮不报告nDCG：均匀样本仅46条查询有标注，未标注不等于不相关。查询目录、维护序列与距离/后端都是已声明项目约定，不能称为作者原始设置；原型IVF不是Viking或优化倒排实现。全部实测数值、反例、分位数和逐run差异见results.md及CSV，不作全面加速/显著性/尾部稳定性声明。核心目录正确不等于整篇论文复现成功。

目录专属：58个两模式case、连续4项MOVE/MERGE，默认/phase各5进程，每pass从相同初始树重建；3预热20测量。catalog纳入默认API总量，直接catalog时间只来自phase，不做跨构建相减。portable字节仅位图序列化大小，不是完整树/catalog空间或物理堆；本轮没有额外allocation追踪。
