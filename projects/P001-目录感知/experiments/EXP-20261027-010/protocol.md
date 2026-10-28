# SCALE-02：25k纯目录正式测量冻结协议

2026-10-27，用户在说明具体矩阵/预算后要求按计划执行、审查、更新文档，授权本矩阵及必要正式入口检查。先WIKI（EXP-20261027-009），再ARXIV-time（EXP-20261027-010）；两者各25000条、各5个串行启动的独立进程，run=0..4，每进程每策略3预热+20正式测量。不是同时运行5进程。

## 冻结输入与边界

原样复用notes/scale-prep-20261027-02/fixtures/{wiki,arxiv}-25000；归档副本逐文件hash匹配。原预处理/选样协议notes/scale-prep-protocol-20261027.md继续适用，不根据时延改目录/查询/维护。ARXIV428目录、20case；WIKI43589目录、62case（目录数未含人为维护父目录）。WIKI使用真实语料层级，查询/维护仍为独立协议，不冒充作者缺失的查询约束。

每pass先新建索引/插入，再查询初始状态，按冻结顺序MOVE large/MERGE large/MOVE deep/MERGE deep；每步完整树/catalog/invariants以及全部查询集合独立核对。API计时仅build、初始查询与4次维护；后续状态查询用于正确性，不混入初始查询延迟。setup、pass全量校验/析构、总wall另存。时钟10000次不变，默认关闭phase/allocation/ASan。三策略顺序按run%3轮换（run0/3 ONLINE先，1/4 OFFLINE先，2 TrieHI先），各策略内部23pass。不是完全平衡拉丁方，保留顺序/主机波动限制。

代码另建code/scale_formal与独立build tag，复用冻结准入生成器后仅替换admission guard及按label/N限制正式和入口检查。不改core/第三方/旧驱动。正式仅接受run0..4、N25000、3/20、label=formal；entry-check仅N5000、0/2，用于run编号/轮换/重复格位检查。先ARXIV5k Release run0..4及WIKI5k Release/ASan run1双pass；独立核验与跨构建比较通过后才开正式测量。旧准入结果继续有效，不重复原核心测试。

## 资源、停止与失败

使用已审查预算notes/scale-prep-20261027-02/budget-reviewed.json；WIKI1.5倍场景1412.66s、ARXIV227.38s，WIKI接近1440s筛查线，估计不是保证。不放宽原停止预算：每命令600s、每数据集从第一个启动门禁至核验/分析结束1800s，两数据集各独立预算；准备/构建不计入正式单元。预算内包含5worker和1核验器共6×20秒启动窗口，不另藏时间。

重型命令前available≥4GiB连续20秒、D自由≥10GiB；运行private进程树≤2GiB、available≥2GiB、每单元输出≤1GiB，100ms整循环目标并记录实际间隔，要求≤250ms。每次检查剩余单元时限，运行时deadline同时约束worker/核验器/监控。门禁/资源/时限/采样间隔/正确性失败立即停止该流程，标failed/resource_blocked，未运行run明确保留；不减重复、不换样、不清日志、不自动重跑失败正式单元。

## 输出与验收

每数据集独立5进程，不把内部重复当独立进程；保存全部预热/正式原始timings、每pass每阶段space、完整首pass答案摘要、10000clock、每pass全wall、资源遥测、顺序、协议/配置/输入/源码/二进制/flags与Git差异快照。C++每pass/阶段执行完整集合比较；Python独立路径元组判定器复核首pass摘要并检查全部重复格位/空间状态和跨进程一致性。

预期原始timing：WIKI23115（正式20100/预热3015），ARXIV8625（正式7500/预热1125）；space各1725；answers WIKI4650/ARXIV1500。预期是验收合同，不是已测结果。每worker full-scope比较=3×23×5×Q。只有5/5完整、正确性/资源/预算/冻结hash均通过，才可记完成；失败/中断不能当正式成绩。

分析仅使用pass3..22。导出逐case、逐run、递归/非递归、四维护、build均值/分位数与5进程均值SD；空请求纳入原冻结权重并在逐case表标候选数，不筛掉反例。默认结果不混诊断，portable不是物理堆，wall不是API延迟。不将不同N选样/查询集合的均值当严格规模增长率；不做ANN/nDCG、PG/Viking、50k/100k或全量扩展。最终审查核对真实输出/hash/资源/活动进程并更新STATE/PLAN/TASK/README/EXPERIMENTS。
