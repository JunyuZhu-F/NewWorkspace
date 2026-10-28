# Directory-Aware Query and Maintenance in Vector Databases

当前正式结果：SCALE-02两数据集各25k纯目录、各5独立进程/3预热20测量已完成并审查通过：[WIKI009](experiments/EXP-20261027-009/record.md)、[ARXIV010](experiments/EXP-20261027-010/record.md)，合计27600正式计时/141450次集合核对。全部格位、资源/预算与源/输入/二进制hash通过；[准备与恢复审查](notes/scale02-preparation-20261027-03/record.md)保留01/02错误，未重跑已验证原生入口或正式实验，原核心/旧记录不改。各record提供完整CSV/5进程SD与反例；不同N选样/目录case不同，不作严格增长率或全文验收。下段是此前SCALE-PREP交付时点，当前状态以上述为准。

当前进度：[SCALE-PREP-01最终准入](notes/scale-prep-20261027-02/record.md)及[审查](notes/scale-prep-20261027-02/review.md)通过：两数据集5k Release/ASan、25k Release共6worker/3390次完整集合及独立核验通过，原核心与旧实验不变、向量载荷0。首次监控间隔偏差已保留并修正，最终实际采样达标。[审查预算](notes/scale-prep-20261027-02/budget-reviewed.json)补入启动窗口后过筛查，WIKI余量很小。SCALE-01仍待正式矩阵/预算决定，SCALE-02未授权；[新入口](code/scale_directory/README.md)目前仅admission单pass，尚不能当正式性能结果。

当前报告：[两数据集小规模结论、证据、限制与补测决策](REPORT_SMALL_SCALE.md)已完成并复核（REPORT-01-SMALL-01）。仅当前独立小范围通过，全文REPORT-01仍进行中。WIKI有真实语料目录，缺的是逐查询范围，已授权项目工作负载不冒充作者约束；扩规模状态见上方评估。

> P001-目录感知，采用 arXiv:2606.16903v1。当前小规模DIR-01、全量时间metadata审计及SEARCH-01/02时间/独立IVF分支完成；006五进程质量—总延迟对照通过独立核验。全量索引/性能、完整真实协议及PG/原版Viking未完成。

WIKI独立小规模分支已完成：[007目录性能](experiments/EXP-20261027-007/results.md)默认/phase共10进程，[008检索结果](experiments/EXP-20261027-008/results.md)五进程/1094400正式计时均通过独立核验与最终hash。依据用户授权的[独立协议](notes/wiki-independent-protocol-20261027.md)，[准入与审查](notes/wiki-independent-preparation-20261027-01/review.md)齐全；qrels不参与选目录，nDCG因覆盖不足不报告。原作者约束/DSM/PG/Viking和全量缺口保留，不再等待作者联系，不将本分支当全文验收。

初次阅读建议先看 [精读笔记](notes/paper-card.md) 和 [材料/疑点清单](notes/materials-and-gaps.md)，再审核下面的目标与计划。

最新交付：[核心实现与审查](notes/core-review.md)、[构建和使用入口](code/README.md)。数据边界见 [DATA-01 小规模核查](notes/data-audit.md)。用户确认先用现有电脑，暂不做应用实验，大规模运行另行决定。

已有ARXIV检索：[SEARCH-02正式记录](experiments/EXP-20261027-006/record.md)、[质量—总延迟结果](experiments/EXP-20261027-006/results.md)、[构建/重跑入口](code/search02/README.md)。10000跨时间样本、501个真实time查询两模式，5进程1202400行计时通过独立核验；[递归曲线](experiments/EXP-20261027-006/analysis-02/figures/recursive.pdf)/[非递归曲线](experiments/EXP-20261027-006/analysis-02/figures/nonrecursive.pdf)。[SEARCH-01旧诊断](notes/search01-validation-20261027-01/record.md)保留，不混合成绩。

继续推进的依据：[单父目录操作约定](notes/operation-spec.md)、[关联加载器核对](notes/reference-loader-review.md)、[本机 C++ 环境](notes/environment.md)。

## 快速导航
- 目标、复现范围与验收：[`TASK.md`](TASK.md)
- 本论文专属复现计划：[`REPRODUCTION_PLAN.md`](REPRODUCTION_PLAN.md)
- 当前状态与下一步：[`STATE.md`](STATE.md)
- 实验索引与记录约定：[`EXPERIMENTS.md`](EXPERIMENTS.md)
- 项目特有操作约定：[`AGENTS.md`](AGENTS.md)
- 阅读笔记、方法对应关系与决策：`notes/`
- 实验记录、配置快照、日志和结果：`experiments/`

## 目录约定
```text
P001-目录感知/
├── AGENTS.md
├── README.md
├── TASK.md
├── REPRODUCTION_PLAN.md
├── STATE.md
├── EXPERIMENTS.md
├── paper/        论文与补充材料
├── code/         实现、脚本、配置、测试和依赖
├── dataset/      数据说明、版本/划分清单或外部数据引用
├── experiments/  按实验编号保存记录、配置、日志与输出
└── notes/        阅读笔记、决策与必要历史
```

按实际需要创建子目录，不要为符合示意结构而搬动现有数据。大型数据可放在外部，但需记录真实位置、版本和校验信息。

## 环境与运行

现有 Windows x64、MSVC/CMake/Ninja，CRoaring v5.3.2 已固定。目录代码和命令见 [code/README.md](code/README.md)，核心初次验证见 [core-review.md](notes/core-review.md)。独立exact/IVF小规模检索已接入，ARXIV结果见006，WIKI推进见当前STATE；不是作者Viking后端。

原始数据在 dataset/raw/，保持只读；前 10,000 条时间视图用于正确性。DATA-01/SPEC-01 的真实类别、WIKI/作者工作负载缺口仍保留，关联 OpenViking 不能直接视为完整原文实验包。

全量时间metadata和432目录的证据见[数据核查报告](notes/arxiv-time-full-audit-20261027-01/report.md)；005见[实验记录](experiments/EXP-20261027-005/record.md)，小规模分支见[验收](notes/dir01-small-scope-acceptance-20261027.md)。按用户指示不追查1995年，直接评估现有真实时间目录实验的规模/协议，未自动启动大规模运行。
