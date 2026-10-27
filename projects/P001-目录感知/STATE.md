# STATE.md — WIKI独立小规模目录/检索已完成并审查

更新时间：2026-10-27，Asia/Hong_Kong；WIKI优先级调整与实际准入完成。项目：D:/NewWorkspace/projects/P001-目录感知。

当前阶段：用户授权的WIKI独立小规模目录/检索已完成并审查，不等待作者联系。007目录默认/phase10/10进程、008检索5/5进程均独立核验、导出与最终hash通过，原算法未改，旧ARXIV未重跑。下一项REPORT-01仅对两数据集已完成小规模范围汇总；整体复现、原作者协议、nDCG、PG/Viking与全量未完成。SCALE后移，不自动启动扩规模；交接核查未见本项目实验/构建活动。

## 当前事实

- 最新唯一入口：007/008的record.md、results.md、final-check.json；新增驱动准入/自审见notes/wiki-independent-preparation-20261027-01/record.md、review.md、final-check.json。007原始43470行（正式37800/预热5670）；008正式1094400行、54720基线排名、13680候选记录，所有格位完整、阶段会计正确、模型/排名跨策略/进程一致。新75个worker文件、当前/归档源码与输入hash匹配，旧006的35个worker文件及46原源码未变。
- 008 nprobe4：递归456非空Recall@10=0.299882，ONLINE/OFFLINE/TrieHI非空总均值2753.2620/432.4738/416.7875μs；非递归127非空/329空，非空Recall=0.110236，总均值16.2986/18.5745/16.8638μs。exact/全探测非空Recall=1；质量相同不代表CPU时间相同，不把全部差异归因目录。空范围质量null且延迟另报，低召回保留，nDCG不报告。目录是query ID/固定哈希配对，不代表自然查询相关性分布。
- 结果CSV位于各analysis-01/，007含逐深度/逐case/维护几何/portable，008含阶段/分位数、5进程均值SD和配对差。默认/phase不混池，catalog不从默认相减，portable不是物理堆；无全量向量加载/重编码/依赖安装。
- 首次统计导出遇Python源编码识别错误，export-console.log保留；添加显式UTF-8声明后export-recovery-01-console.log成功，测量未重跑。finalize-console.log及总final-check通过。原始失败、快照、被忽略的fixture/*.fvecs和构建二进制全部保留。
- 当前Git main/HEAD be59bbccb9e3f8e283328f453643b7d50211736d。除此前STATE/旧WIKI未提交成果，新增code/wiki_experiment、build-wiki-experiment.cmd、007/008及本轮证据，更新TASK/PLAN/STATE/EXPERIMENTS/README/项目AGENTS/材料GAP；未提交、推送、重置、清理。源码快照007共53项、008共54项，差异只多README说明，无算法/配置变化。原始数据只读。

- 007默认已核验均值μs（ONLINE/OFFLINE/TrieHI）：递归1426.51/2.02/1.83；非递归3.38/25.67/18.43。large MOVE约34273.83/34593.87/15.87，large MERGE约31356.37/31694.69/406.57；deep MERGE约355.46/248.30/371.29，保留TrieHI并非最快反例。原始精度和完整分位数见007/verification-directory-default.json；诊断catalog另在phase报告，不混池或从默认相减。

- 本轮独立协议与驱动准入：notes/wiki-independent-protocol-20261027.md；notes/wiki-independent-preparation-20261027-01/record.md、review.md、status.json及三份verification。58目录case、4连续维护；large源8785目录/4734条目，deep源深31且1目录/1条目。检索912case中递归456非空、非递归127非空/329空；qrels不参与，本轮不报告nDCG。原三方案/后端46源码hash不变，生成包装仅三处已声明变更；不再将作者联系/约束恢复作为独立分支前置。

- WIKI最新证据唯一入口 notes/wiki-preparation-20261027-01/record.md；run-01/report.json与verification.json为数据主审计/独立复核，check-02/status.json与independent-verification.json为目录准入最终状态。
- WIKI全量1941679条path/corpus ID连续等于行号；固定10000等间隔原始ID与向量及全部456查询向量核验通过。原始文件size/mtime不变，全量向量未逐条验证。独立解析复核全量目录统计和样本绑定通过。
- 不同末端路径363467、平均深度11.9512445与论文数值吻合；补齐祖先含根468031目录，非根均深11.8313719。作者按末端路径统计仅为合理推测，定义未确认，不能删祖先迎合数字。
- WIKI 456条query metadata仍全部为空；10851对qrels、10410个文档，标注合法并覆盖全部查询。样本只含56相关文档/61标注，46查询有样本标注、410没有，不能以其代表完整WIKI nDCG或填0/1；原作者查询目录、指标与DSM序列缺口不关闭。
- WIKI真实路径10000样本：新增独立code/wiki/入口和build-wiki.cmd，原核心不变；Release/ASan各5292次范围集合核验通过（初始/MOVE/MERGE/拒绝，各阶段全量不变量）；答案字节相同，另有Python路径状态判定器复核全部输出与覆盖。006的46个原源码文件hash仍匹配。该运行是正确性准入，不是性能/ANN成绩。
- check-01首次cmd路径写法导致未生成二进制，整体failed保留；修正命令及产物断言后另存check-02通过。独立核验首次在ASan结束前被状态门禁拒绝，日志保留，完成后核验成功；没有覆盖/隐瞒失败。主数据审计31.031秒、独立数据复核18.844秒，Release/ASan测试4.813/98.985秒，不作为查询延迟；ASan采样private最大1156001792字节，未触发资源门禁。
- 本次小型公开源快照见public-sources-01/：作者数据仓库根仅README，关联OpenViking说明仍承认缺WIKI query约束。web工具不能访问Google Drive目录，未取得远端清单，不断言网盘没有补充资料；未联系作者、未下载大型数据。
- Git基线仍main/be59bbccb9e3f8e283328f453643b7d50211736d。本次保留原STATE未提交增量，并新增WIKI入口/脚本/准入证据与更新TASK/PLAN/EXPERIMENTS/STATE；不提交/推送/重置/清理。当前代码与未跟踪文件以实时git status为准，不再使用下方旧交接的“只STATE变化”作为当前现场。

- SEARCH-02当前时间/独立IVF分支已完成：EXP-20261027-006，5/5独立进程、1202400条原始计时、60120条基线结果及15030条候选记录通过独立核验，所有重复格位完整、各阶段和等于总量、模型/排名跨策略与进程相同。2026-10-27 11:08:01–11:11:01+08为正式阶段及核验时间，不是查询延迟。
- 新输入仍10000条，按全量ID等间隔跨时间选择，34年/388月/含根423目录；501真实time查询两模式，501递归非空、235月份非递归非空、266年份非递归为空（质量null）。Release/ASan各契约1/1及12024条准入结果已通过，证据notes/search02-preparation-20261027-02/；首次换行防护失败及有效输入留在preparation-01。
- 实测示例nprobe4：递归Recall0.555440相同，总均值ONLINE/OFFLINE/TrieHI为121.2350/107.1855/107.7700μs；非递归非空Recall0.363283，总均值29.1679/28.1565/28.1088μs。exact/全探测非空Recall均1。目录阶段非递归仍ONLINE更低（1.1185/1.5078/1.2198μs），不把总量差全部归因目录。原型后端/缓存/计时边界和波动限制见record.md。
- 完整入口experiments/EXP-20261027-006/record.md、results.md、verification.json、final-check.json；最终两张曲线在analysis-02/figures/，CSV/逐进程差/误差条SD及PDF字号/碰撞QA齐全。绘图使用已有兼容Python环境及子进程DLL路径；前两次失败日志保留，无依赖安装或测量重跑。

- SEARCH-01当前时间/独立IVF分支已完成：10000条1024D、104case，Release/ASan各契约1/1、各1248条结果均通过独立核验；候选/排名/距离/分区一致，无越界。64非空/40空；exact和nprobe16非空Recall=1。诊断nprobe1/4为0.126397/0.455629，不是论文质量成绩。32原始约束case在头部样本全空，非空证据来自诊断且共用query_id0，不宣称代表性。
- 最终证据notes/search01-validation-20261027-01/record.md、verification.json、final-status.json；ASan首次缺DLL启动失败保留在根run-status.json，修复子进程PATH后recovery-01/status.json通过，原Release未重跑/覆盖。新增code/search及独立构建，旧COST30文件保持。该准入不等于SEARCH-02性能曲线，PG/WIKI/作者Viking缺口不关闭。

- EXP-20261027-005已完成并收尾：135/135成功，194.859秒，2026-10-27 01:34:55–01:38:10。重核验通过，没有重跑实验。phases 33,465、allocation 3,795、overhead/process/run-order各135行。
- 与004的210进程结果共同完成DIR-01当前人工树/10,000条单父目录小规模分支；冻结条件验收见 notes/dir01-small-scope-acceptance-20261027.md。不等于全数据、全规模或整篇论文复现通过，整体OBJ-03仍未最终验收。
- DATA-TIME-FULL-01已完成：全量2,763,543条metadata，ID连续0–2,763,542且逐条等于行号，time合法；34年/397月/含根432目录，深度2。主扫描19.734秒，独立逐条复核29.437秒，均退出0，无异常。两遍完整metadata hash一致，输入size/mtime未变。
- 完整绑定 notes/arxiv-time-full-audit-20261027-01/run-01/bindings.tsv 共46,577,712字节；SHA-256 127a7d07902cb997489da526be1da973bc9bac09f0da133787f0c28323ea72a2。前10,000原始对象和绑定字节与旧冻结样本一致；全量清单是后续数据依据，还没有用于全量索引或性能运行。
- DATA-TIME-FULL-01当时只读向量4字节首维头（1024），载荷0；文件长度与全量行数结构相容，不是向量全量校验。本轮SEARCH另行读取并检查10000个抽样完整记录，仍不是全量向量校验。501个time约束目录全存在（266年/235月），未恢复作者递归/非递归生成协议。
- 用户已取消组会工作，后续只按论文复现目标推进；已有组会草稿保留，不再维护。

## 最近结果及解释边界

004默认time均值（微秒，ONLINE/OFFLINE/TrieHI）：递归DSQ 6.5276/2.6992/2.7203；非递归2.4195/5.4386/5.4071；MOVE 6.4590/13.8530/6.9070；MERGE 207.2880/191.2200/162.5300。反例保留，无全面加速声明。

005诊断time MERGE中catalog占同构建已观测核心区间约94.7%/90.3%/94.0%；不能推为004默认占比。初始目录+catalog+bitmap请求字节518288/542136/544840，catalog均480064。不是物理堆、序列化大小或全库结论。ONLINE诊断MOVE最大3.9435ms保留，中位数7.2微秒，均值46.646微秒；高值原因待验证，不修改默认成绩。拒绝异常传播阶段覆盖不完整，小时段受探针影响。

## 恢复入口

- TASK.md：目标和授权；REPRODUCTION_PLAN.md：任务依赖和完成标准。
- 005：experiments/EXP-20261027-005/record.md、results.md、independent-verification.json、run-status.json；原始值raw/，全部命令run-order.jsonl。
- 004：experiments/EXP-20261027-004/record.md、results.md、summary.json；旧11个关键文件hash重核验未变。
- 准入/冻结：notes/cost02-preparation-20261027-01/；Release/ASan各23/23及最终schema各2/2；PROTO-COST-02-20261027、COST02-440a2e0f81208f81，code30文件hash 440a2e0f81208f814bddf4b3f709b8739ec122471e8d32cae57f86418a1fb997。已有源码/二进制/输入快照和失败记录保留。
- 数据入口：notes/data-audit.md、notes/time-pilot-20261026-01/manifest.json、notes/prepare_time_pilot.py；按本任务需要定位，不递归读取全部notes。
- 最新全量数据证据：notes/arxiv-time-full-audit-20261027-01/report.md，run-01/manifest.json、verification.json、coverage-summary.json、完整bindings.tsv和directory-counts.json；脚本快照及真实日志均保留。metadata本地完整SHA-256 93a4e0db140c82a2e154274d7b80bf4e95ade0152d79a63424e02ff3b3874a0f，未与发布方checksum对齐。

## 现场与剩余限制

交接时实测Git根D:/NewWorkspace，分支main，HEAD为be59bbccb9e3f8e283328f453643b7d50211736d（SEARCH-02完成记录）；核查开始时工作树干净。本次只留下STATE.md未提交更新，没有未提交代码。旧STATE的“HEAD仍6a66c9e/存在开发未提交”已过时；006记录中的6a66c9e是实验当时基线，必须保留，不能改成当前HEAD。开发增量code/search/、code/search02/及两个build-search*.cmd已纳入当前HEAD；原目录核心/第三方文件不变。本次不提交、推送、重置或清理。

交接证据复核通过：006清单46个当前源码及46个归档副本匹配；5个worker各timings/answers/scopes/model共20个关键文件、6个fixture文件及8个最终图导出hash匹配；协议、Release/ASan二进制匹配，源向量size/mtime与运行记录一致。没有重算全部历史实验或重新执行测试。按进程名/命令行检查未发现directory实验、Python任务或CMake/CTest/Ninja/MSVC构建仍在运行。

已验证运行设置：Windows，现有MSVC/CMake/Ninja和CRoaring；测量/独立判定采用D:/anaconda3/python.exe（记录Python3.9.13/NumPy2.0.2/psutil5.9.0），Release开启优化、关闭ASan及成本诊断，实际flags见006/CMakeCache.txt、compile-flags.json。绘图采用已有D:/anaconda3/envs/zhu_3_10/python.exe（NumPy1.26.4/Matplotlib3.10.9），必须隔离子进程DLL搜索路径，成功命令见006/plot-runtime.json及notes/search02-preparation-20261027-02/render_figures.py。不要为恢复安装/降级依赖，base Matplotlib失配和此前失败日志保留。

必须保留：dataset/raw/只读原数据、忽略Git的本地fvecs派生输入和build二进制、所有冻结快照与原始结果。尤其notes/search02-preparation-20261027-01/status.json虽failed，其fixture仍被成功preparation-02和006引用，不能当失败垃圾清理；006最终图在analysis-02/figures/，根figures/是失败绘图的部分输出。SEARCH-01根run-status.json同样是历史失败，最终入口为final-status.json和recovery-01/status.json。工作树干净不代表这些被忽略的本地文件已进入Git。

DATA-01/SPEC-01仍未整体完成。真实类别直接归属/多归属DSM、WIKI查询目录、作者维护序列、作者距离/真值/Viking配置仍缺。独立时间/L2/IVF小规模SEARCH-01/02分支已完成；PG/WIKI、整体OBJ-04、SCALE/全文REPORT未完成，扩大性能规模仍需单独决定。

可信状态：上述小规模实现/准入/测量为已验证；作者ARXIV原GT可能使用L2仅为顺序相容证据支持的合理推测，作者实际距离和生成协议待确认。全量向量逐条完整性、WIKI/类别协议和大规模可行性仍待验证；相应材料缺口不是本轮小分支失败，也不能因小分支完成而关闭。

新增GAP-TIME-COVERAGE-01：观测时间1991/7–2025/7之间缺1995年全部12个月；不是抽样遗漏，原因/发布过滤规则待确认。不得据此认定数据损坏或填造/改写原始数据。

用户已明确“不用管1995年的数据”：该项保留为已知数据边界，不再追查、补齐或作为后续阻塞；按现有2,763,543条记录推进。这不是证明缺口原因已经恢复。

## 下一步

建议下一项REPORT-01：汇总ARXIV 004–006与WIKI 007/008已完成的小规模证据，逐OBJ标注独立语义/趋势/原版不可比/未执行；不启动新测量，不把本分支完成改成全文通过。若后续扩规模，先SCALE-01具体预算，再由用户决定SCALE-02。当前不联系作者，不加载全量，不接PG，不追查1995年，不处理组会。

最小恢复入口：根/项目AGENTS、本STATE、TASK、PLAN相关WIKI/REPORT任务行；007/008各record.md、results.md、final-check.json，必要时定向读取对应verification和CSV。审查/准入在notes/wiki-independent-preparation-20261027-01/。不要重跑已通过矩阵或覆盖旧输出；更早WIKI-DATA/CHECK证据在wiki-preparation-20261027-01/，只在核查数据时按需读取。

以下是本次WIKI优先级调整之前的SCALE安排，已后移：

下一项SCALE-01：依据006实测及现有硬件评估目录层/含向量检索两种范围的内存、磁盘、oracle与耗时预算，提出具体可行规模/矩阵后再决定运行。不能将小样本线性外推当全量可运行证明；目前2GiB停止预算与全量约11.33GB向量不相容。SCALE-02尚未授权/启动，不自动加载全量或接PG，不追查1995年，不处理组会。原始工作负载缺口仍保留，不以本项目曲线冒充作者数值。

新窗口最小读取顺序：根AGENTS.md、项目AGENTS.md、本STATE、TASK；REPRODUCTION_PLAN中SEARCH-01/02完成条件与SCALE-01依赖/资源约束；EXPERIMENTS仅006索引行；006/record.md、config.json、final-check.json。需要做SCALE-01的成本估计时，再定向读取006的verification.json、run-*/setup.csv及相应oracle源码，不递归读取全部notes/日志。恢复时先核对Git与活动进程，再核对这些入口；无需重跑已经验证的矩阵。
