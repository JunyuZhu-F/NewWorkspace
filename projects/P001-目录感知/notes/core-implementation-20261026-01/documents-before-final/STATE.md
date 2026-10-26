# STATE.md — 已通过范围审核，正在核对数据

## 1. 状态与停止点

- 更新时间：2026-10-26，Asia/Hong_Kong。
- 总体状态：用户已接受三项范围/资源决定，先用现有电脑做小规模检查。**现已获得单父目录核心实现、审查与小规模正确性测试授权；尚未运行性能实验。**
- 计划位置：此前材料/阅读/范围审核、SPEC-TREE-01、DATA-ARXIV-SCOPE-01，加上 DATA-CATEGORY-MEANING-01、DATA-TIME-PILOT-01 已完成；DATA-01、SPEC-01、ENV-01 进行中。SPEC-ARXIV-CATEGORY-01 材料阻塞；SPEC-TIME-PILOT-01 未开始，索引/性能任务未开始。
- 当前现场：类别解释调查已收尾，证明现有递归观测不能唯一恢复 Local；没有据此选定作者协议。已固定时间命名空间前 10,000 条 metadata 输入和 34 目录计数，下一步将其操作案例写入 SPEC-01。
- 材料障碍：WIKI 原查询目录约束和 DSM 操作清单未获得；ARXIV 两套查询/多归属语义、质量真值与 Viking 参数仍需核查。详细影响见 GAP-01–10，不把这些障碍说成整篇论文不可理解。

## 2. 已验证的工作

| 工作 | 真实结果与验证边界 | 证据 |
|---|---|---|
| 材料与版本 | 本地 PDF 15 页，首页 v1；SHA-256 已计算；无独立补充材料在场；本地 code 为空 | `notes/materials-and-gaps.md` §1–2 |
| 论文理解 | 全文方法、唯一式 (1)、12 幅图/7 张表人工清单；结果是作者报告而非本项目实测 | `notes/paper-card.md` |
| 精读结构审计 | 原装 auditor：14 pass、0 warning、0 error，退出码 0。自动清单漏图 6/全部罗马表，已人工补齐，不据审计断言科研正确 | `notes/reading-20261026/audit-report.json` |
| 交付检查 | 论文 hash 不变，新旧逐页文本一致；数据文件名/长度无变化，文档链接和人工图表清单检查通过；不等于数据全量内容校验 | `notes/reading-20261026/document-check.json` |
| 数据轻量核验 | 文件名/大小、fvecs 首维度和长度推算；全读 WIKI 456 查询及两套 ARXIV 小型约束。WIKI metadata 全空 | `notes/reading-20261026/local-data-inventory.json`、`query-schema-check.json` |
| 范围审核 | 用户已接受：先三方案目录层，暂不做应用实验，现有电脑小规模，大规模单独决定；REVIEW-01 已完成 | `TASK.md` §6，本聊天明确回复 |
| 数据初查 | 各前 10,000 条元数据、各 264 条 corpus 向量；全部 2,456 查询向量及小型真值/qrels。格式抽查无维度/非有限值异常；发现 ARXIV 多类别和非统一范数 | `notes/data-audit.md`、`notes/data-audit-20261026-01/audit-with-norm-rows.json` |
| 关键发现复核 | PowerShell 独立复算 3 个向量范数并核对 metadata id=145，多类别及大范数发现得到直接复核 | `notes/data-audit-20261026-01/independent-spot-check.json` |
| 关联代码核对 | 固定版本路径 helper：id=145 的 URI 只取第一类别，当前两套各 1,000 约束均提取为根路径；未执行后端 benchmark | `notes/reference-loader-review.md`、`notes/data-audit-20261026-01/reference-helper-check.json` |
| 真值顺序诊断 | 两套各 10 个固定 query 的真值相邻顺序均与 L2 相容；不是完整 top-k 验证，L2 仍为推测 | `notes/data-audit.md` §8、`notes/data-audit-20261026-01/gt-distance-order.json` |
| ARXIV 成员核查 | 新分层 20 查询的全部 2,000 GT 引用均递归匹配；800 个只有后代路径；仅取首类别会丢失 792 个匹配。独立成员判定/计数复核通过 | `notes/data-audit.md` §9、`notes/arxiv-scope-audit-20261026-01/summary.json`、`verification.json`（同目录） |
| 元数据定位范围 | 流式解析前 2,757,791 条，仅保留 1,998 个目标记录；目标全部找到，扫描前缀 ID/行序零差异。不是全文件/全向量完整性验证 | `notes/arxiv-scope-audit-20261026-01/selection.json`、`summary.json`、`references.jsonl`（同目录） |
| 单父目录约定 | 写清图 2 全目录集合、独立 MOVE/MERGE 人工预期与接口边界；未运行三方案 | `notes/operation-spec.md` |
| C++ 环境 | 现有 MSVC 成功编译/运行 64 位 C++17 极小探针；CMake/Ninja 版本已查，Roaring 尚未核验 | `notes/environment.md`、`notes/env-probe-20261026/` |
| 类别调查收尾 | 1,998 条记录的祖先冗余可不改变递归观测；1,014 条仍多分支。公开来源未给作者直接绑定映射，真实类别协议单列阻塞 | `notes/category-semantics.md`、`notes/category-semantics-20261026-01/analysis.json` |
| 时间小输入 | 不依赖 GT 的前 10,000 ID/time 映射固定，原始类别保留；34 目录计数和哈希独立复核通过，无向量读取 | `notes/data-audit.md` §11、`notes/time-pilot-20261026-01/manifest.json`、`notes/category-semantics-20261026-01/verification.json` |
| 实验状态 | 未运行检索、维护、训练或全量基准；未创建实验记录/结果；EXPERIMENTS 模板不变 | `code/`、`experiments/` 为空；材料核验不登记成算法实验 |

## 3. 现场与保护事项

- 根目录：`D:/NewWorkspace/projects/P001-目录感知`。该路径及上级不构成可用 Git 仓库（git status 返回 not a git repository）；无分支/commit，不曾初始化、提交或推送。
- 原论文在 `paper/`，原数据在 `dataset/raw/{WIKI-Dir,ARXIV-Dir}/`。只读，未移动、覆盖或下载替换。
- 原 `notes/source_bundle.json` 和 `notes/rendered-pages/` 保留；本轮独立核验输出在 `notes/reading-20261026/`。未修改其他项目或根规则。
- `notes/` 下新增只读审计脚本、参考源码快照和极小环境探针；正式 `code/` 与 `experiments/` 仍为空，没有三方案算法入口。这些是材料/环境检查，不是论文算法实现。
- 本机 Windows 11、i7-13650HX、约 15.81 GiB 可见 RAM；用户确定先用现有电脑，现有 MSVC/CMake/Ninja 已核查，Roaring/ANN 后端未锁定。无 Linux/云资源采购或大规模预算授权，不能使用原文 125GB 的规模假定。
- 本轮未启动项目实验；指定名称 python/pythonw/wsl 的进程采样为空，不代表检查了全机所有后台任务。无已知项目检查点或实验日志需接续。

## 4. 已确认决策与尚未解决的技术问题

| 事项 | 当前判断/影响 | 依据 |
|---|---|---|
| 是否从目录层做起 | 用户已接受，原版绝对耗时对齐暂不能保证 | TASK §3/4/6；GAP-06/09 |
| 是否纳入 OpenViking 应用 QA | 用户接受暂不纳入 | TASK §3/6 |
| ARXIV 多归属 | 省去冗余祖先的假设视图与原列表有相同递归观测，但仍有 1,014 条多分支；作者 Local/catalog/DSM 无法由现有递归真值唯一恢复，相关真实类别协议材料阻塞 | notes/category-semantics.md；GAP-04 |
| ARXIV 距离协议 | 查询向量多数范数不为 1；20 查询真值列表顺序与 L2 相容、与内积/余弦不相容；未搜索全库验证 top-k | data-audit §4/8；GAP-05 |
| 开源边界 | 有关联 OpenViking 系统及当前 backend benchmark 文档，不等于已经核实论文三方案/Viking 实验包；不声称全网无代码 | materials-and-gaps §2，固定 commit 快照 |
| 缺失 WIKI 约束 | OpenViking 当前文档也承认缺口；其真值派生诊断协议不是原文查询，未采用为忠实基线 | GAP-01；对应 README 快照 |
| 后续计算平台/预算 | 用户已确定先现有电脑小规模，扩大规模以后单独决定 | TASK §5/6，PLAN SCALE-01 |

## 5. 下一步

1. 主线下一项 SPEC-TIME-PILOT-01：在已冻结的时间目录小输入上写清查询锚点、合法 MOVE/MERGE 案例及预期；仍不开始索引实现或性能实验。
2. WIKI 目录约束和原始 DSM 清单仍缺失；继续材料核对，未获授权不联系作者，不用 qrels 派生范围冒充原文。
3. 辅助 ENV-01 可独立推进 Roaring 依赖核验；人工树 ORACLE/CORE 分支仅限 SPEC-TREE-01，不能替代完整 DATA/SPEC，也不允许直接运行尚未定义的真实数据实验。
4. 不重复询问三项已批准决定；任何大规模运行仍另行确认。计划中的任务按依赖而非表格行号推进，主线优先级见 PLAN §2“当前主线与辅助工作”。

## 6. 继续会话的入口

先读适用 AGENTS、TASK 和本文件；规划时读 PLAN。方法疑点按 paper-card 章节或 GAP 定向查证，不重新扫整个项目。

现有 `D:/anaconda3/python.exe` 可运行本轮材料审计脚本，命令与覆盖范围在 `notes/data-audit.md`；输出已存在时须用新输出名，不能覆盖旧证据。JSON/JSONL 只读前缀，corpus 向量仅抽样，不得把它们写成全库通过。数据核查没有登记为算法实验，EXPERIMENTS 模板不变。

本次在 `notes/arxiv-scope-audit-20261026-01/` 保存了新的完整目标元数据与 2,000 个引用，可以直接复用，不必再次流式扫描 482MB metadata。本次未读取任何向量，且与前次 L2 诊断采用不同选样；不要混用两次覆盖范围。

本次交付核验见 `notes/arxiv-scope-audit-20261026-01/handoff-check-final.json`：脚本/解析辅助与运行记录哈希匹配、输入小文件哈希未变、独立复核通过；实际运行版源码已在同目录冻结。初次版本核验发现的不匹配及恢复过程保留在 data-audit.md §9.6，未更改原运行结果。

本轮不再为识别 Local 而重复扫描相同递归 GT。类别结论是有界来源核对后的不可唯一判定，不是原文方法已被改写或所有复现工作均受阻。时间小样本能继续落实单父协议，父任务 DATA/SPEC 不关闭。

最新执行指令：2026-10-26 用户明确同意正式实现并审查、更新文档。当前主线改为 ENV → ORACLE → CORE → CHECK（单父目录范围），历史数据核查结论保留。
