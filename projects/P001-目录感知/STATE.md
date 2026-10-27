# STATE.md — SEARCH-02当前时间/IVF小规模分支完成

更新时间：2026-10-27，Asia/Hong_Kong。项目：D:/NewWorkspace/projects/P001-目录感知。

## 当前事实

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

本轮Git根D:/NewWorkspace，main，HEAD仍6a66c9e。本轮开始时已有未提交SEARCH-01成果，全部保留；新增SEARCH-02和相关文档/实验，未提交、推送、重置或清理。旧core30文件、SEARCH-01冻结8文件及004/005结果不变。当前没有运行中的性能实验。

DATA-01/SPEC-01仍未整体完成。真实类别直接归属/多归属DSM、WIKI查询目录、作者维护序列、作者距离/真值/Viking配置仍缺。独立时间/L2/IVF小规模SEARCH-01/02分支已完成；PG/WIKI、整体OBJ-04、SCALE/全文REPORT未完成，扩大性能规模仍需单独决定。

新增GAP-TIME-COVERAGE-01：观测时间1991/7–2025/7之间缺1995年全部12个月；不是抽样遗漏，原因/发布过滤规则待确认。不得据此认定数据损坏或填造/改写原始数据。

用户已明确“不用管1995年的数据”：该项保留为已知数据边界，不再追查、补齐或作为后续阻塞；按现有2,763,543条记录推进。这不是证明缺口原因已经恢复。

## 下一步

下一项SCALE-01：依据006实测及现有硬件评估目录层/含向量检索两种范围的内存、磁盘、oracle与耗时预算，提出具体可行规模/矩阵后再决定运行。不能将小样本线性外推当全量可运行证明；目前2GiB停止预算与全量约11.33GB向量不相容。SCALE-02尚未授权/启动，不自动加载全量或接PG，不追查1995年，不处理组会。原始工作负载缺口仍保留，不以本项目曲线冒充作者数值。
