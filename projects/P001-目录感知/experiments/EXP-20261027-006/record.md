# EXP-20261027-006 — SEARCH-02 时间/独立IVF质量—总延迟

状态：**完成，5/5正式进程、1202400行计时独立核验通过**。status.json、verification.json和final-check.json为最终状态入口。质量—总延迟图及逐点均值见results.md、analysis-02/figures/；不是原版Viking数值复现。

用户于2026-10-27要求阅读必要文档并按下一步计划执行。本轮执行当前时间/独立IVF小规模分支，不包括PG/WIKI、全量索引或原版Viking数值对齐。

科学协议启动前另存notes/search02-protocol-20261027.md，正式快照protocol.md；配置config.json、输入input-manifest.json；Git基线6a66c9e+已有未提交SEARCH-01成果+新增SEARCH-02，实际源码source/及source-hashes.json，差异git-diff.patch，环境environment.json，编译配置CMakeCache.txt/compile-flags.json。

数据仍10000条，但按floor(i*(2763543-1)/9999)跨全量ID等间隔选择；对应原始1024D向量只读抽取41MB。新样本34年/388月/含根423目录，与旧前缀样本另版本，不互换成绩。全部501个真实time查询的两模式共1002case，子集独立精确GT，不用发布GT筛选。

原样复用已验证SEARCH-01的独立后端：平方L2、不归一化、k100、ID并列升序，16中心/种子42/8次Lloyd，exact及nprobe1/4/16；三目录策略共用每进程同一个后端对象。原型通过遍历允许ID并检查分区过滤，不是优化倒排遍历或Viking。

前置准入notes/search02-preparation-20261027-02/status.json/verification.json已通过：Release/ASan各契约1/1、12024条结果，独立候选/排名/分区/global-dense映射及跨构建一致。501递归非空；235月份非递归非空；266年份非递归为空，空真值null，不记召回1。

正式命令（项目根工作目录）：

```powershell
python code/search02/pipeline.py --stage run --preparation notes/search02-preparation-20261027-02 --experiment EXP-20261027-006
```

5个独立Release进程串行，run0..4策略顺序循环移位，同一run共享固定打乱的case/probe顺序。每进程3预热/20测量，每次计时外完整检查scope和结果不变；预计1202400条计时。原始run-*/timings.csv，完整结果answers.jsonl、候选scopes.tsv、模型model.json、顺序order.tsv、时钟clock.csv、setup.csv；实际命令/退出/时间commands.jsonl，过程日志和每秒资源样本run-*-monitor.json。

总延迟=目录query+bitmap/ID转换+后端排名/返回ID映射，三阶段直接读取差值之和。排除加载/训练/建树、序列化/transport/计时末仍存活临时集合的最终释放；不得说成完整服务请求时延。查询计时含阶段clock探针，校验在计时外影响缓存；全部方案一致，原始值保留且不扣时钟开销。

单worker600秒、矩阵1800秒、private2GiB、available至少2GiB、输出1GiB，超限终止并留失败。不得据结果改参数或删反例。

## 真实完成事实

2026-10-27 11:08:01–11:11:01+08，5/5正式worker及独立核验退出0，总阶段约180.08秒（包含加载/训练和事后核验，**不是查询延迟**）。每worker240480行，共1202400行，每行总时间等于三个阶段直接区间之和；20个重复格位无缺漏/重复。共60120条基线检索结果、15030条候选记录全部独立核对；所有重复在计时外还检查完整scope/ID/距离不变。模型跨5进程字节hash一致，三策略结果一致；旧core30文件、SEARCH-01最终冻结8文件及本轮46个运行源码文件核对不变。

正式worker按每秒样本观测的private峰值82186240字节、系统available最小5492764672字节；未触发停止条件，不称这些稀疏样本是精确内存峰值或索引独占空间。结果及图约140.6MB（收尾前统计），低于1GiB；未控制背景负载，不宣称空闲机器。

| 模式 | nprobe | 非空case | Recall@100 | ONLINE总均值μs | OFFLINE总均值μs | TrieHI总均值μs |
|---|---:|---:|---:|---:|---:|---:|
| 递归 | 1 | 501 | 0.229179 | 69.9676 | 56.9964 | 57.4080 |
| 递归 | 4 | 501 | 0.555440 | 121.2350 | 107.1855 | 107.7700 |
| 递归 | 16 | 501 | 1.000000 | 265.9456 | 246.3632 | 247.7015 |
| 非递归 | 1 | 235 | 0.120141 | 20.8532 | 20.3903 | 20.1815 |
| 非递归 | 4 | 235 | 0.363283 | 29.1679 | 28.1565 | 28.1088 |
| 非递归 | 16 | 235 | 1.000000 | 50.7824 | 49.3293 | 49.6542 |

另有exact对照，其与独立GT一致、非空Recall=1。完整8配置/模式点、全请求与空范围均值在results.md；每阶段和nearest-rank P90/P95/P99/P99.9、每run均值在verification.json。低召回和高延迟不剔除；266个年份非递归空请求单列，质量记null，不当1。

## 解释边界

三方案相同质量下，本次递归总均值OFFLINE/TrieHI低于ONLINE；nprobe4约低11.59%/11.11%，只描述此数据/固定后端，不宣称普遍加速或原文倍数。目录阶段递归均值为ONLINE5.1930、OFFLINE1.1825、TrieHI1.0664μs；但其余阶段也有缓存/执行波动，不把全部总差异都归因目录算法。

非递归目录阶段反例仍在：ONLINE1.1185μs低于OFFLINE1.5078/TrieHI1.2198μs，而总量却略高。各阶段、每run和配对进程均值差均保留，不能用总量抹平非递归集合差开销，亦不能将相同后端等同“每次CPU耗时相同”。未做显著性检验，重复调用不是独立查询样本，尾部不作稳定性保证。

## 图表、失败与环境

两张最终单轴图分别为递归/非递归，保留全部501/235个非空请求；266空请求仅从Recall和主曲线排除，耗时仍单独报告。横误差条为5个独立进程均值的样本SD（不是置信区间），点/线不平滑；OFFLINE/TrieHI近重合来自真实近值，不抖动坐标。curves.csv保留所有数值，paired-differences.csv保留逐进程配对差。

绘图首次在原Anaconda因NumPy2.0.2/Matplotlib3.5.2 ABI不兼容失败；第二次直接调用已有Python3.10环境又因继承base DLL搜索路径导致本机加载失败。没有安装/降级依赖，没有影响已完成测量。隔离该已有环境的子进程PATH后成功，版本NumPy1.26.4/Matplotlib3.10.9；plot-runtime.json和figure-render*.log保留全部尝试。原partial figures/只有CSV/contract，**最终图在analysis-02/figures/**，原始verification.json字节拷贝到该分析目录并核对。

采用nature-figure的Python工作流。静态图源20PASS/1WARN/0FAIL；WARN为127mm自定义报告尺寸，无投稿期刊指定。最终两PDF各最小字号7pt、0个低于5pt；碰撞检查均0FAIL/0WARN，视觉检查完整/可读。各为单轴，alignment记录NOT APPLICABLE，不假称多面板对齐通过。自动检查和人工检查记录见figure-qa.json及图旁审计文件，图源和来源CSV保留。

本轮SEARCH-02当前时间/独立IVF分支完成；下一项SCALE-01仅资源/规模协议评估。PG/Viking原参数、作者距离确认、真实类别/WIKI约束/nDCG仍缺，整体OBJ-04和全文验收未完成；未启动全量向量加载或扩规模。不追查1995年，不处理组会。
