# WIKI独立协议新增驱动准入 — 完成

2026-10-27。用户明确授权按独立协议执行并审查/更新文档；不等待作者联系。此前WIKI-DATA/CHECK原证据不覆盖；此处仅为新性能驱动与检索形状适配的准入，不作正式成绩。

## 实际执行与证据

项目根命令：`D:/anaconda3/python.exe -B code/wiki_experiment/pipeline.py --stage prepare --preparation notes/wiki-independent-preparation-20261027-01`。此目录已经存在，不能原地重跑。状态status.json为passed，2026-10-27T04:19:46.442859Z–04:29:13.461413Z（香港时间+8h）；commands.jsonl保存真实命令/退出/采样资源，日志完整保留。

新目录默认/phase及检索的Release、ASan构建/运行全部退出0。两构建均运行检索合同。三份独立核验：verification-directory-wiki_directory.json、verification-directory-wiki_directory_phase.json、verification-search.json均passed。目录每构建189条准入计时/870次完整集合核验（5状态×58case×3策略），独立Python对全部候选摘要、状态和格位核查；检索每构建10944条准入计时和排名、2736条候选记录核查，跨构建排名/距离/模型一致。这里的计时是准入输出，不是007/008正式测量。

ASan默认目录67.282秒、phase67.500秒、检索299.000秒；独立核验18.015/17.984/24.375秒；均未触发单命令600秒/资源门禁。elapsed只是执行时长，不是查询延迟。新准入没有失败或覆盖旧输出；原先旧WIKI检查check-01启动失败仍在自己的历史目录，不能混为当前失败。

## 输入和审查事实

- 科学协议是protocol.md快照（原notes/wiki-independent-protocol-20261027.md），源hash/source/、environment.json保存实际未提交源码与环境，当前HEAD不能代替源码清单。
- fixture为旧WIKI已核验10000等间隔global ID；23025真实目录加1个空维护父目录=23026。58个目录两模式case；维护large源含8785目录/4734条目，deep源深度31且1目录/1条目；两次MERGE冲突目录各1，均为源根对应目标根的重合，不声称覆盖大量内部冲突压力。
- 912检索case使用456条原query向量，按query ID/哈希选择目录；递归456非空，非递归127非空/329为空。空质量null，延迟仍记录，不改选择规则去掉空范围。qrels不被生成/检索/核验代码读取，不报告nDCG。
- 原始query文件说明声称带约束，但实际metadata均空；用户也另从作者网盘确认。GAP-01未恢复，采用独立协议是已授权范围选择，不是修补原始数据。
- generated文件已验证严格只改变query形状501→456、case形状1002→912和合同标签；原后端前缀逐字节复用。原006的46源码hash通过，不改核心三方案或后端算法。
- 独立Python从原始选样绑定重建目录、生成规则和操作，逐记录对照源向量区域，验证exact和全探测非空Recall=1以及IVF分区/排名/距离。计时重复格位完整、阶段和与总量会计正确。

方法与边界的具体源码自审见review.md；本轮无外部审查者/代理，不把自审冒称多人审查。所有阶段正式完成后再由007/008的record/results/final-check关闭本小分支；原作者协议/全量/PG/Viking目标仍未完成。

## 正式矩阵

007目录默认/phase各5独立进程；008检索5独立进程。均为3预热20测量，实验启动前EXPERIMENTS已登记，正式状态只看相应实验目录。不从本准入的耗时、召回或进程内存推断正式成绩。分析导出由本目录summarize.py完成，最终哈希/记录由finalize.py核查，均不重跑测量。
