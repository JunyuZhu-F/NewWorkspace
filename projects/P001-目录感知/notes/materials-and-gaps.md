# 材料核验、来源边界与待确认事项

2026-10-27最新：SEARCH-02当前时间/独立IVF小规模分支完成，EXP-20261027-006五进程1202400行计时及全部排名独立核验通过，质量/总延迟曲线和限制见006/record.md、results.md。采用明确项目L2/子集GT及模式展开，仍未恢复作者距离/PG/Viking/WIKI协议，不关闭相应GAP；以下“尚无检索”等初始现场是历史描述。

2026-10-27 SEARCH-01增量：当前时间/独立IVF小数据分支准入已验证，协议search01-protocol-20261027.md、记录search01-validation-20261027-01/record.md。明确采用项目L2/子集GT，不表示GAP-03/05/06的作者设置已恢复；PG/WIKI/原版Viking仍缺。以下初始“无检索实验”等表述为历史现场，不覆盖最新STATE。

核验日期：2026-10-26（Asia/Hong_Kong）。本文件保存“读了什么、现场有什么、还缺什么”，论文方法和结果分析只在 `paper-card.md`。初次核验时无正式实现；后续已获授权完成单父目录独立实现/正确性测试，见 core-review.md。仍无检索/维护性能实验或大型数据下载。

审核后已开始有上限的数据核查，新增证据见 [data-audit.md](data-audit.md)。下方材料清单保留初次阅读时的历史现场，不代表当前 code 仍为空；当前状态以 STATE.md/core-review.md 为准。GAP 状态按后续证据更新。

## 1. 本地论文与已有材料

| 材料 | 本次核验结果 | 状态与边界 |
|---|---|---|
| 根/项目规则 | 已读 `D:/NewWorkspace/AGENTS.md`、项目 `AGENTS.md` | 已验证；均未修改 |
| 原有管理文档 | TASK、STATE、PLAN 均为空骨架；README/EXPERIMENTS 也是模板 | 已验证；本轮更新前已读相关内容 |
| 论文 | `paper/Wang 等 - 2026 - Directory-Aware Query and Maintenance in Vector Databases.pdf` | 3,082,250 bytes，15 页；正文 PDF pp. 1–12，参考文献 pp. 13–15，无附录 |
| 论文 SHA-256 | `00c59850614b7c286d82669b5e1447bacb5fb7115cbd442d8b29c801bd65e968` | 已验证，采用本地文件为阅读依据 |
| 采用版本 | 首页 arXiv:2606.16903v1，15 Jun 2026 | 与 arXiv 元数据一致；未下载远程 PDF 作逐字节比对，不能说本地文件与远端哈希一致 |
| 独立补充材料 | `paper/` 只有上述 PDF；正文无附录，已检查 arXiv 入口 | 未发现独立附件；不等于证明作者未在任何其他地方发布补充材料 |
| 已有笔记 | `notes/source_bundle.json` 与 `notes/rendered-pages/page-001.png` … `page-015.png` | 只有提取/渲染材料，没有已有人工精读/历史决策笔记；原文件保留 |
| 源码/实验 | `code/`、`experiments/` 顶层为空 | 没有在场实现、配置或真实实验记录 |
| Git | `git -C <项目> status --short --branch` 返回 not a git repository | 没有可报告的分支/commit；未初始化 Git、未提交或推送 |

### 提取与视觉核对

按精读技能运行原装脚本，未编写替代 PDF 提取器：

```powershell
python 'C:\Users\PC\.codex\skills\nature-paper-card\scripts\prepare_paper.py' `
  'D:\NewWorkspace\projects\P001-目录感知\paper\Wang 等 - 2026 - Directory-Aware Query and Maintenance in Vector Databases.pdf' `
  --output 'D:\NewWorkspace\projects\P001-目录感知\notes\reading-20261026\source_bundle.json'
```

- 第一次用 Codex bundled Python 调用，报缺 PyMuPDF；未安装/修改环境。
- 随后用现有 `D:/anaconda3/python.exe`（即 `python`）运行，实际退出码 0，15 页，validation=valid，page-grounded。源 SHA-256 与手工计算相同。
- 与旧 bundle 对照并复用原页面图，视觉核对方法、公式和主要实验表图所在页。自动清单只识别 11 图、0 表，漏了 Figure 6 和罗马数字表 I–VII；人工完整清单在 `paper-card.md` §10，不修改提取脚本以“修正”自动结果。
- `reading-20261026/audit-report.json` 是精读技能审计结果；审计检查结构和定位，并不能证明研究结论正确，人工图表清单与数值复核仍必需。

实际使用的审计命令（退出码 0，14 pass、0 warning、0 error）：

```powershell
python 'C:\Users\PC\.codex\skills\nature-paper-card\scripts\audit_paper_card.py' `
  --card 'D:\NewWorkspace\projects\P001-目录感知\notes\paper-card.md' `
  --bundle 'D:\NewWorkspace\projects\P001-目录感知\notes\reading-20261026\source_bundle.json' `
  --locator-mode page-grounded `
  --report 'D:\NewWorkspace\projects\P001-目录感知\notes\reading-20261026\audit-report.json'
```

交付检查保存在 `reading-20261026/document-check.json`：论文 hash 与初始一致；新旧 bundle 逐页文本相同；原数据文件名/长度无变化（不是全量数据内容哈希验证）；代码和实验目录仍空；人工图表行无遗漏，Markdown 文件链接可解析。

## 2. 外部来源及官方实现边界

| 来源 | 核查方式/版本 | 实际支持的事实 |
|---|---|---|
| [arXiv v1](https://arxiv.org/abs/2606.16903v1) | 浏览官方记录；DOI 10.48550/arXiv.2606.16903 | 标题/作者/提交日/采用版本；不是已核实的正式发表信息 |
| [作者数据仓库固定版本](https://github.com/KurtPatrickHere/dir-vector-dataset/tree/de79569b07ed32b37e3725225dbcf86e1300b2f0) | GitHub API 核验 main 当时 SHA；commit 日期 2026-06-10；根清单只有 README.md | 数据说明、Google Drive 下载入口、指向 OpenViking 的关联链接；不是三方案算法仓库 |
| [OpenViking 固定版本](https://github.com/volcengine/OpenViking/tree/22a28101089515ddef85b96617449924baef9f35) | GitHub API 核验 main 当时 SHA；commit 日期 2026-10-26；列出根与 benchmark 清单 | 相关开源系统和 benchmark 目录确实存在；未审计内部源码，未核实与论文实验的等价性 |

原始核验摘要：`reading-20261026/external-source-check.json`；数据仓库 README 快照：`reading-20261026/dataset-repository-README.md`；OpenViking benchmark 文件清单：`reading-20261026/openviking-benchmark-list.json`。浏览工具曾无法打开 benchmark 子目录，之后用 GitHub API 获取列表；未 clone 仓库、运行 benchmark 或下载 Google Drive 数据。

补充定向查看同一固定 commit 下的 [benchmark/vectordb_perf/README.md](https://github.com/volcengine/OpenViking/blob/22a28101089515ddef85b96617449924baef9f35/benchmark/vectordb_perf/README.md)，快照和目录清单另存 `reading-20261026/openviking-vectordb-perf-README.md`、`openviking-vectordb-perf-list.json`。该文档描述的是 OpenViking storage backend 基准，支持 dir-vector 数据；明确指出公开 WIKI 查询缺少目录 constraint，其 `derived_gt_lca_v1` 是使用真值推导范围的诊断协议，不能代表官方目录查询分布。这支持 GAP-01，但不恢复作者原始约束；该诊断协议没有纳入本项目忠实基线。文档列有不同距离和抽样选项，它们不构成论文原始参数证据。初读时只看文档/清单；用户要求继续后，已定向核对 runner 的加载实现和纯路径 helper，见 [reference-loader-review.md](reference-loader-review.md)。未执行该 runner 的后端 benchmark。

**已验证与待确认的区别**：论文确实链接 OpenViking，用户也明确本轮按无源代码条件准备；目前缺少的是与原文 C++/Viking、PG/IVF、三方案和实验工作负载对应的完整可重跑代码包。不能反过来断言互联网上绝无相关代码。未来如审查 OpenViking，必须固定版本、逐模块比对论文，不把当前 main 等同于作者实验版本。

## 3. 数据现场（仅轻量核查）

数据实际位于本项目 `dataset/raw/`，不是工作区根目录 `dataset/`。文件清单、字节数和首次记录维度见 `reading-20261026/local-data-inventory.json`。本轮未对约 19GB 语料向量逐字节哈希，未扫描全部向量和大型元数据，也未确认全部 ID/行对齐。

| 数据/文件 | 已核查事实 | 验证边界 |
|---|---|---|
| WIKI corpus vectors | `dbpedia_dir_2m_corpus_vectors-001.fvecs`，7,960,883,900 bytes；首记录 1024D | 按固定 4100 bytes/行推得 1,941,679 行，余数 0；尚非逐记录完整性证明。文件名与发布说明略异，不能仅凭 `-001` 判断缺 shard |
| WIKI query vectors | 1,869,600 bytes；首记录 1024D | 同样推得 456 行 |
| WIKI 查询 | 读取全部 456 条小型 JSONL：字段只有 `_id/text/metadata`，所有 metadata 为空 | **没有目录约束**。不是只看前几行的猜测；统计见 query-schema-check.json |
| WIKI paths/corpus/qrels | 文件在场，头部有路径 id、语料 _id、query-id/corpus-id/score | 只读头部，未验证全体 ID 和相关性等级覆盖；qrels 样本有 score 1/2，不能当精确 top-k 真值 |
| ARXIV corpus vectors | 11,330,526,300 bytes；首记录 1024D | 固定格式推得 2,763,543 行，余数 0，未全量校验 |
| ARXIV 两套 query vectors | 各 4,100,000 bytes；首记录 1024D | 各推得 1,000 行，不能只按文件名确定论文用了哪套 |
| ARXIV 混合约束 | `arxiv_query_constraint.json` 全部 1,000 条，499 category、501 time | 顶层 query_id/constraints；没有递归模式标志 |
| ARXIV 类别约束 | `arxiv_category_query_constraint.json` 全部 1,000 条，均 category | 同上；不能默认这是非递归任务 |
| ARXIV metadata | 头部有 id、categories 列表、time；类别路径无前导 /，月份如 1991/7/ | 不假设全文件含标题/摘要；不自动将月份补零，因为这会改目录键 |
| ARXIV 真值 | 两个 txt 文件在场，混合真值头部每行是 ID 列表 | 行与 query_id 对齐、距离函数、候选不足 100 的行为需后续核对 |
| DSM 序列 | 两个数据目录顶层未见单独操作文件 | 大型 paths/metadata 只读了头部，尚不能排除文件内部带额外信息；当前没有可执行的原始操作清单 |

本轮只做材料/文件格式核验，没有生成检索结果或性能数字；上述行数为“首维度与文件长度一致时的推算”，不得在未来报告中写成已全量验证。

## 4. 疑点清单与解除方法

用户后续决定：GAP-TIME-COVERAGE-01不再追查或补齐，不作为当前复现阻塞；按现有2,763,543条记录推进。缺1995年的事实及原因未恢复的边界仍保留，不改数据、不宣称已恢复发布规则。

2026-10-27新增 **GAP-TIME-COVERAGE-01**：全量本地ARXIV时间metadata从1991/7到2025/7之间缺1995年全部12个月；ID/语法/行数结构核查通过，缺口原因与发布过滤规则未确认，不能自动判损坏或填补。证据见 [全量时间审计](arxiv-time-full-audit-20261027-01/report.md)。该调查只影响相应覆盖声明，不解除真实类别/WIKI/作者协议缺口。

| ID | 待确认事项 | 影响/优先级 | 解除方法与当前默认边界 |
|---|---|---|---|
| GAP-01 | WIKI 逐查询目录锚点、深度选择、递归/非递归工作负载未在查询中提供 | 阻塞原文 WIKI DSQ/深度对照 | 复核原包及说明；若需问作者先经用户授权。缺失时只能单列自建协议，不从 qrels 反推有利约束。 |
| GAP-02 | 1000 MOVE/1000 MERGE 序列与生成规则、冲突比例、操作顺序、是否每次恢复树未知 | 阻塞原文 DSM 数值对照 | 获取清单；否则冻结独立生成协议，记录子树目录数、ID 数、深度、冲突及重置策略。 |
| GAP-03 | ARXIV 两套查询与图表对应，如何生成非递归约束 | 阻塞该部分质量对照 | 新分层 20 查询的 2,000 个引用均满足递归条件，其中 800 个只有后代路径；不能将 category-only 当 non-recursive。见 data-audit §9；全量及图表对应仍待核验。 |
| GAP-04 | 类别直接绑定、catalog 和多归属维护仍缺作者来源 | 调查完成：递归观测无法唯一识别 Local；相关真实类别协议材料阻塞 | 见 category-semantics.md；祖先冗余假设视图不改变递归观测，仍有 1,014 条多分支。不再靠重复同类抽样猜测，不暗改算法。 |
| GAP-05 | 距离、向量归一化、nDCG 增益/IDCG、Recall 真值及分母、空集/少于 k/并列分数规则 | ARXIV 范数不统一；20 条固定查询真值顺序与 L2 相容、与内积/余弦不相容 | data-audit §4/8；L2 仍是推测，未证明全库精确真值。WIKI 非递归 Recall 真值也不能用 relevance qrels 自动代替。 |
| GAP-06 | Viking 实现/PG 类型/IVF 参数、过滤搜索策略、构建和搜索调参点、线程 | 阻塞精确引擎复现 | 有源包则锁版本；没有则由用户审核后选公共替代后端，原文绝对时间只作参考。 |
| GAP-07 | 非法 MOVE、同名目标、根目录操作、源目标包含关系、catalog 刷新、读写原子性及失败处理 | 影响核心正确性 | 先写合法操作域和逐步不变量，禁止形成环；MERGE 初版按原文互不包含情形；未定义情况显式拒绝，不自行扩充论文行为。 |
| GAP-08 | bitmap 返回/复制方式，catalog 排除边界，预热/缓存/分位计算/运行重复数 | 影响微秒测量、维护收益与公平性 | 预先统一计时协议；并列报告模块净成本与完整系统成本，不把读取引用当候选物化。 |
| GAP-09 | 后端/bitmap 版本及后续资源上限 | 现有 MSVC/CMake/Ninja 与 C++17 极小探针已核验；Roaring 未锁定 | 见 environment.md；用户确定先现有电脑小规模，未安装/购买 Linux 资源，大规模另批。 |
| GAP-10 | 原始版本/hash、全部 ID/路径/向量/真值是否对齐；路径与深度口径 | 元数据扫描前缀 ID/行序已进一步核实，完整审计未完成 | 本次前 2,757,791 metadata ID/行序一致，20 查询目标都找到；不是全向量或尾部验证。见 data-audit §9；保留原路径，不默默重建层级。 |

## 5. 资源与活动任务核验

- 快照：`reading-20261026/resource-snapshot.json`。系统 Windows 11 家庭版；i7-13650HX，14 核/20 线程；可见内存 16,580,472 KiB（约 15.81 GiB），快照采样时空闲约 3.63 GiB，空闲值会变化。没有在本轮确认 GPU、WSL、编译器或可用 Linux 服务器。
- 原文为 Linux、48 核 Xeon Silver 4310、125GB RAM（PDF p. 9）。仅 ARXIV 原始语料向量就约 10.55 GiB，加目录解析、索引和重复副本可能超过可用内存，不能直接装入全部数据比较三方案。
- 采样时未发现 python.exe/pythonw.exe/wsl.exe 进程；这只是指定名称的进程检查，不等于证明全机没有其他任务。`experiments/` 为空，本轮未启动项目实验。

## 6. 本轮核验结论

已完成：确定所读材料、读全文、核实核心图表和方法、核查小型查询文件与向量头、梳理可执行前置条件。尚未完成：数据完整性审计、作者实验协议恢复、源码核对、任何算法实现或实验复现。

后续执行顺序只在 `../REPRODUCTION_PLAN.md` 维护；当前停止点见 `../STATE.md`。
