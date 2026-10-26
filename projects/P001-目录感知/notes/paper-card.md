# Directory-Aware Query and Maintenance in Vector Databases：精读笔记

> Source coverage: Full paper（本地 PDF 全文 15 页；无独立补充材料）
> Extraction confidence: High for text; tables/figures manually checked（自动图表清单不完整）
> Locator mode: page-grounded（本文页码均指 PDF 从 1 起的页序）
> Primary analytical lens: methods（算法与数据库系统）
> Secondary analytical lens: None（数据集作为验证材料一并审查）
> Context verification: Targeted external check（只核实论文元数据和作者链接材料，未作新颖性检索）
> Card completeness: Complete relative to supplied source（实现细节缺失显式保留）

阅读日期：2026-10-26。证据标签：`[Paper]` 为作者陈述；`[External]` 为外部材料；`[Analysis]` 为本项目分析；`[Hypothesis]` 为待检验假设；`[User]` 为用户信息。这里的“已验证”主要指核对了原文或文件，并不表示本项目重跑了实验。材料版本、文件核查、GAP 清单见 [materials-and-gaps.md](materials-and-gaps.md)。目标与计划只引用本笔记，不重复详细方法。

术语统一如下（保留原文命名，不把目录索引称为新向量模型）：

| 术语 | 首次定义/中文解释 | 原文形式与本笔记用法 |
|---|---|---|
| DSQ | Directory-Semantic Query，目录语义查询 | 先确定合法条目 ID，再做向量排名 |
| DSM | Directory-Semantic Maintenance，目录语义维护 | 本文主要是 MOVE 和 MERGE |
| PE-ONLINE | Online Path Expansion，查询时展开路径 | 原文也排作 PE-Online；统一大写 |
| PE-OFFLINE | Offline Path Expansion，写入时物化祖先归属 | 同上；不把 OFFLINE 理解成离线训练 |
| TrieHI | Trie-based Hierarchical Index，基于前缀树的层次索引 | 正文也排作 TRIEHI；本笔记统一 TrieHI |
| Inc(v) / Local(v) | 节点全子树 ID 集合 / 直接归属 ID 集合 | Local 是语义定义，不代表论文额外存储了 Local bitmap |
| PG / IVF | proximity graph / inverted file，图式/分区式 ANN 执行器 | PG 不等于已经确定为 HNSW；原文未给具体构建算法 |
| catalog | 条目到当前目录表示的映射 | 三方案共用，部分论文计时不含它 |

## 01 基本信息

- [Paper] 标题如上；作者依次为 Mengzhao Wang、Zheng Gong、Jingpei Hu、Jiajie Fu、Maojia Sheng、Junwen Chen、Yifan Zhu；单位为杭州电子科技大学、浙江大学、字节跳动。首页标记 arXiv:2606.16903v1 [cs.DB]，2026-06-15。[Paper: PDF p. 1, title and arXiv identifier]
- [External] [arXiv 记录](https://arxiv.org/abs/2606.16903v1)核实标题、作者和 v1；DOI 是 [10.48550/arXiv.2606.16903](https://doi.org/10.48550/arXiv.2606.16903)，不是已核实的会议出版 DOI。
- [Paper] 原文研究使用 C++/Viking，发布 WIKI-Dir/ARXIV-Dir，声称 TrieHI 已集成 OpenViking。[Paper: PDF pp. 1–2, Abstract and contributions; PDF p. 9, Implementation Details]
- [User] 已有数据，论文未提供源码。[Analysis] 本地确有两数据目录且 `code/` 为空；不能由“关联 OpenViking 开源”推断本文三方案实验完整开源。
- 论文类型：数据库系统/索引方法；关键词：目录语义、过滤向量检索、路径展开、Trie、Roaring bitmap。用户目标：忠实理解并规划独立复现，尚未进入实现。

## 02 一句话总结

[Paper + Analysis] 把目录范围表示为可复用的树节点及其后代 ID 集合，TrieHI 在不改向量排名算法的前提下避免查询时逐路径展开，并在目录变更时尽量重连子树、更新受影响祖先；代价是额外集合存储和非递归集合差运算。[Paper: PDF pp. 6–8, §IV; PDF pp. 10–11, Tables IV/V]

## 03 研究问题

[Paper] 检索“相似内容”还不够：当前项目、当前版本、某个用户的目录决定哪些内容允许参与排名。把路径当普通字符串会丢掉祖先/后代关系。应用先从外部系统展开所有后代路径再拼过滤条件，既增加查询工作，也使目录变更需要协调多处状态。[Paper: PDF pp. 1–3, §I/II]

输入是向量条目、目录路径，以及查询向量/目录约束或目录变更命令；输出分别是合法范围内的 top-k，或变更后供后续查询使用的一致目录状态。

[Analysis] 精确研究问题：能否让三个方案返回完全相同的目录范围，同时让递归查询不再按后代路径数逐一展开，让子树移动不再重写每个后代目录的字符串键？这比“让 QA 更准”更直接对应论文方法层。

适用范围：[Paper] 层次目录、递归/非递归查询、子树 MOVE/MERGE；不替代 ANN、不改变相似度函数。分支排除可由集合差组合表达；兄弟和祖先查询可组合遍历得到，原文评估聚焦两个基础 DSQ。[Paper: PDF pp. 2–3, §II-A/C/D]

## 04 研究背景与发展路线

以下是 `[Paper-framed; external verification not performed]`，仅复述原文的定位，未独立证明首创性：

1. ANN 工作优化怎样从向量中快速找近邻。
2. 标量过滤限定候选，但路径平铺后需要额外展开层级。
3. PE-ONLINE 把展开放到查询时；PE-OFFLINE 把祖先归属提前存好。
4. TrieHI 用原生目录树保留结构，以相同范围集合接口接入 ANN。

[Paper: PDF pp. 2–6, §II/III/IV; PDF p. 12, §VI]

[Analysis] 作者提供的是一种索引表示和成本取舍，不是证明“前缀树”或“层级过滤”这一通用概念首次出现。

## 05 论文指出的痛点

| 痛点 | 表现 | 作者给出的原因 | 原文依据 |
|---|---|---|---|
| 语义相似但目录范围不对 | 新旧版本、用户空间或日志混进搜索 | 平面属性未表达拓扑 | [Paper: PDF pp. 1–2, §I; Figure 1] |
| 递归范围展开太慢 | 浅层目录需查很多子路径并合并 posting | PE-ONLINE 查询时重建范围 | [Paper: PDF pp. 4–5, §III-A; Table I] |
| 把成本提前也有代价 | 写入复制到祖先、非递归做集合差 | PE-OFFLINE 的祖先物化 | [Paper: PDF pp. 5–6, §III-B/C] |
| 目录变更放大写操作 | 一个逻辑 MOVE 触发多个路径键重命名 | 字符串路径不具有稳定子树身份 | [Paper: PDF pp. 4–7, §III/IV] |

## 06 核心想法

表面做法：[Paper] 用路径段为边、目录为节点的前缀树；每个节点存 `inclusive_ids`，供递归查询直接读取。[Paper: PDF p. 6, §IV-A, Figure 5]

核心：[Analysis] 子树内部目录不变时，MOVE 改的是“这棵子树挂在哪”，不应要求每个后代重新生成完整路径。稳定节点身份提供这个操作单位；受影响祖先的集合仍须更新，不能省略。

可迁移认识：[Analysis] 物化范围与保存拓扑是两回事。TrieHI 和 PE-OFFLINE 都物化祖先集合；前者额外保留节点连接关系，主要在维护路径上获得不同成本。论文也显示 TrieHI 存储最大，而非所有指标都最优。[Paper: PDF pp. 6–7, Tables I/II; PDF p. 11, Table V]

## 07 方法总览

```text
写入：条目 ID + 目录 + 已有向量
    -> 三选一的目录元数据表示 + 公共 catalog
查询：目录约束 -> 解析候选 ID 集合 -> 同一个 ANN 执行器 -> 合法范围内 top-k
维护：MOVE/MERGE -> 更新目录表示、catalog 与范围集合 -> 后续 DSQ 看到新结构
```

[Paper] 三种方案都在 ANN 上面工作，集合用 Roaring bitmap。原文不是先全库 top-k 再删掉越界结果；其语义是先限定允许范围，再在其中排名，但底层 PG/IVF 如何消费过滤集合的细节没有完整给出。[Paper: PDF p. 2, §II-A; PDF pp. 4–7, §III/IV; PDF p. 9, Implementation Details]

训练需求：[Paper] 数据向量用既有 embedding 模型编码；本方法本身没有新模型训练目标。IVF 后端可能需要分区训练，但原文没写参数，不能因此虚构新的论文训练阶段。[Paper: PDF pp. 8–9, §V-A]

关键假设：[Analysis] 路径按完整段匹配；目录结构无环；entry ID 与向量行正确对应；操作后 catalog、拓扑和集合表示一致。原文以一个逻辑父目录解释条目归属，但 ARXIV 又有独立类别/时间命名空间；跨命名空间和多类别的具体处理待核查（GAP-04）。

## 08 核心模块拆解

| 模块 | 功能与必要性 | 输入→输出 | 原文/支持证据 | 去除后的影响 |
|---|---|---|---|---|
| PE-ONLINE | 只存直接归属 posting；辅助目录索引枚举后代 | 路径→直接 ID 或后代 posting 并集 | [Paper: PDF p. 4, §III-A; Figures 3/4] | [Analysis] 无辅助索引则无法按原文解析递归范围 |
| PE-OFFLINE | 每条数据写入所有祖先 posting | 路径→物化全子树集合 | [Paper: PDF pp. 5–6, §III-B; Table I] | [Analysis] 取消祖先物化即改变方案；非递归仍需扣除子树 |
| TrieHI 节点 | segment、children 哈希表、parent、inclusive_ids | 路径→节点及其范围 | [Paper: PDF pp. 6–7, §IV-A; Figure 5; Table II] | [Analysis] 去掉 Inc 会失去直接读取递归范围；未见单独去除实验 |
| 公共 catalog | 将条目映射到当前目录表示 | ID→path key 或 node | [Paper: PDF pp. 6–7, §IV-A; PDF p. 9, Implementation Details] | [Analysis] 查询/维护记账需要它，原文成本比较部分排除它 |
| 向量执行器 | 在允许 ID 范围中检索 | 查询向量+bitmap→top-k | [Paper: PDF pp. 2/9, §II-A/V-A; Figures 7/8] | [Analysis] 去掉后只能验证目录集合，不能宣称 ANN 端到端复现 |
| OpenViking 集成 | URI 目录、L0 摘要/L1 概览/L2 全文与检索 | 上下文范围→相关证据 | [Paper: PDF pp. 8–9, §IV-C; Figure 6; Table III] | [Analysis] 表 VI/VII 没有隔离“只去掉 TrieHI”，不可量化其独立 QA 贡献 |

### 写入与查询：逐步对照

- PE-ONLINE：记下条目父目录，只在该目录 posting 加 ID；递归查询枚举包含自身在内的全部后代目录并求并集；非递归直接查父目录 posting。[Paper: PDF p. 4, §III-A]
- PE-OFFLINE：写入时沿路径向每个祖先加 ID；递归直接读锚点 posting；非递归读取锚点全量、所有直接子目录的全量，先合并子集合再做差。不是重新枚举所有孙目录。[Paper: PDF p. 5, §III-B]
- TrieHI：沿路径创建/访问节点，写入终点及祖先 Inc；递归沿路径找到节点后读 Inc；非递归与 PE-OFFLINE 一样做直接子树集合差。[Paper: PDF pp. 6–7, §IV-A]

### MOVE：保持子树内容不变，换一个父目录

运行例把 `/Dept_A/` 挂到 `/Dept_B/` 下，最终路径理解为 `/Dept_B/Dept_A/`；MERGE 则把源根内容合入 `/Dept_B/` 本身，不能混淆。[Paper: PDF pp. 3–5, §II-C/III]

- PE-ONLINE：枚举源子树目录键，替换前缀，重映射 posting 和辅助键。
- PE-OFFLINE：做上述重映射，还要用源子树 ID 集合更新变化的祖先 posting。共同祖先保持不变；源根 posting 随路径重映射，不再在祖先步骤重复改。
- TrieHI：定位源节点和新父节点，收集 `S=Inc(s)`，计算失去/新增子树的祖先，更新这些祖先 bitmap；从旧父 children 摘下源节点，挂到新父 children 并改 parent。子孙保持节点身份。

[Paper: PDF pp. 4–5, §III-A/B; PDF p. 7, §IV-A, Directory Move]

### MERGE：同名目录递归合并，不冲突子树整体转挂

- PE 两方案遍历源目录键，映射到目标路径；有同名目标则并集合，无目标则移键；PE-OFFLINE 还维护祖先聚合。
- TrieHI 以互不包含的源、目标子树为讨论情形：源集合从源侧独有祖先移除，加入目标根和目标侧独有祖先，共同祖先不改；不冲突孩子整体挂接，冲突孩子递归合并；直接挂在源根的条目也须归入目标根并刷新 catalog。

[Paper: PDF pp. 4–5, §III; PDF p. 7, §IV-A, Directory Merge/Consistency During Updates]

[Analysis] 最后一句的根部条目处理是由 DSM 语义及 catalog 一致性推导出的实现义务；原文没有给完整伪代码。递归冲突节点上的 Inc 必须逐层正确合并。尤其要防止仅合并 children 却漏掉源根 Local 条目。

一致性：[Paper] 重叠路径变更串行化；一致性段落给出“先收集受影响集合→改父子连接→刷新 catalog 与祖先集合→清理旧绑定”。MOVE 介绍段却先讲集合更新再讲重连。[Analysis] 这可能是叙述层次不同，不应擅自认定线上读者总能看到原子状态；锁范围、读同步和失败回滚均待确认（GAP-07）。[Paper: PDF p. 7, §IV-A]

## 09 必要公式、符号与成本

唯一编号公式是：

\[
Inc(v)=Local(v)\cup\bigcup_{w\in Child(v)}Inc(w).\tag{1}
\]

[Paper: PDF p. 6, Equation 1 / 公式1]

含义：一个目录的全部条目 = 直接放在这里的条目 + 每个直接子目录的全部条目。它是必须在写入、MOVE、MERGE 后保持的**不变量**，也就是“任何时刻都应该成立的规则”。

以下是对文字定义的 `[Analysis]` 数学整理，不是论文额外编号公式：设直接归属集合为 `L(p)`，目录子树（含 p）为 `D(p)`，则：

\[
Scope_{rec}(p)=\bigcup_{d\in D(p)}L(d),\qquad
Scope_{nonrec}(p)=L(p)=Inc(p)\setminus\bigcup_{w\in Child(p)}Inc(w).
\]

[Paper: PDF pp. 3–7, §II-C/III/IV]

令 `A_old`、`A_new` 为 MOVE 前后源根的严格祖先集合，`S=Inc(s)`；原文祖先处理可写成：旧侧独有祖先减 S，新侧独有祖先并 S，共同祖先不变。MERGE 还必须把 S 并入目标根，并递归处理冲突节点。[Paper: PDF pp. 5/7, §III-B/IV-A]

| 操作 | PE-ONLINE | PE-OFFLINE | TrieHI |
|---|---|---|---|
| 写入 | 一份父目录 posting | t 级祖先 posting | t 级节点聚合更新 |
| 递归 DSQ | m_q 个目录枚举/查找并集合 | 一次物化集合查找 | t 级遍历+一次集合读取 |
| 非递归 DSQ | 一次直接 posting 查找 | c 个孩子集合并后做差 | t 级遍历+c 个孩子集合并后做差 |
| MOVE | O(m_u) 路径键重映射 | O(m_u+t) 元数据更新 | O(t) 节点访问与祖先更新 |
| MERGE | O(m_u)+冲突集合并 | O(m_u+t)+冲突集合并 | O(t+r)+冲突集合并 |

[Paper: PDF p. 5, Table I; PDF p. 7, Table II]

`t` 是相关路径深度/祖先数量界，`m_q/m_u` 是查询/修改子树的目录键数，`c` 是直接孩子数，`r` 是递归协调的源节点数。MERGE 最坏 r 可以接近全部源节点。[Paper: PDF pp. 4–7, §III/IV]

[Analysis] 表中 O(t) 计的是节点/集合操作次数，**没有把任意大小的 bitmap 并差当成常数的现实保证**。复制/输出候选集合的方式也影响成本。TrieHI 不保证 O(1) MOVE、O(1) 递归端到端延迟，也不保证总存储比 PE-OFFLINE 小。

多归属警告：[Analysis] 如果同一 ID 还通过另一分支保留在某祖先下，直接对祖先减 S 可能误删它；非递归集合差在“同一目录直接归属且同时属于其后代”的情况下也需重新检查。原文单父目录模型避免了此问题；ARXIV 的 category 列表是否满足它尚未验证，不能先假设成立。

## 10 实验设计与证据链

### 数据、预处理与运行条件

| 项目 | WIKI-Dir | ARXIV-Dir |
|---|---|---|
| 来源/规模 | Wikipedia+DBpedia 查询与相关性；约 1.94M 条目、456 查询 | 约 2.76M 摘要，1,000 查询 |
| 层级处理 | Wikipedia category DAG 为每条目选一个路径，去无效链接，转为规范树 | 类别、发表时间两个独立层级 |
| 目录统计 | 363,467 目录；平均深度 11.95 | 类别 168、平均 2.19；时间 432、平均 1.92 |
| 向量 | bge-m3，1024D | 原文拼写 mxb-ai-embed-large-v1，1024D |
| 查询/真值 | 声称不同深度的目录约束；DBpedia relevance labels | 从摘要采样，构造目录约束；在约束范围暴力搜索得真值 |
| 维护工作负载 | 声称生成 1,000 MOVE + 1,000 MERGE | 未给出同样明确的 DSM 生成细节 |

[Paper: PDF pp. 8–9, §V-A]

比较方法是三种目录策略，各接同一 Viking PG/IVF 执行器；表 V 额外有无目录模块的纯向量基线。CPU、内存、语言、bitmap 与 catalog 排除范围见 `TASK.md`。没有神经网络训练协议，也未交代 ANN 构建/搜索参数、距离、种子、重复次数和完整计时规程。[Paper: PDF p. 9, §V-A]

指标：[Paper] DSQ 记录质量和总查询延迟，目录单独延迟指“目录条件→候选 ID 集合”时间；DSM 是 MOVE/MERGE wall-clock；索引时间和大小包含向量及目录部分。图 7 WIKI 用 nDCG@10，图 8 WIKI 改用 Recall@10；ARXIV 两图均为 Recall@100。原文没有解释 WIKI 两种真值指标切换。[Paper: PDF pp. 9–11, Figures 7/8 and Tables IV/V]

[Analysis] 评估需区分三种“正确”：范围集合正确、近邻近似误差、人工 relevance 相关性。前者可要求零差异，后两者不能混成一项。nDCG 增益（线性还是指数）、IDCG 是否在目录内计算、Recall 分母及候选不足 k 的规则均未给出。

### 主图、主表与公式证据清单

自动 bundle 漏识别 Figure 6 和全部罗马数字表格，以下人工清单补齐；不修改技能脚本，也不把脚本覆盖检查当作完整性证明。

| 原文对象 | PDF 页 | 论证用途 |
|---|---|---|
| Figure 1 | 1 | 代码库、企业 wiki、文件系统的目录动机 |
| Figure 2 | 3 | 全文例子，doc_1…doc_9；可作为第一组语义检查 |
| Figure 3 | 3 | PE 两方案写入时一份 posting 与祖先复制的区别 |
| Figure 4 | 4 | 递归查询时多路径展开与一次物化读取的区别 |
| Figure 5 | 6 | TrieHI 节点及 Inc 聚合结构 |
| Figure 6 | 8 | OpenViking URI 与 L0/L1/L2，不是独立消融 |
| Figure 7 | 9 | 递归质量-平均延迟曲线，PG/IVF×两数据集 |
| Figure 8 | 9 | 非递归对应曲线；WIKI 指标不同于 Figure 7 |
| Figure 9 | 10 | MOVE/MERGE 逐操作延迟曲线；没有原始逐项数值和明确生成种子 |
| Figure 10 | 10 | 深度 1/2/4/9 的目录规模和直接孩子统计 |
| Figure 11 | 10 | WIKI 深度影响：PG/IVF 有不同响应 |
| Figure 12 | 11 | 路径获得、bitmap 获取、bitmap 计算的时间分解，标注为 µs |
| Table I | 5 | PE 两方案操作成本对照 |
| Table II | 7 | TrieHI 操作成本及 MERGE 冲突依赖 |
| Table III | 9 | OpenViking 能力与 DSQ/DSM 对应 |
| Table IV | 10 | 目录延迟均值、P90/P95/P99/P99.9 |
| Table V | 11 | 总索引构建时间和总大小 |
| Table VI | 12 | LOCOMO 整体应用结果 |
| Table VII | 12 | HotpotQA 整体应用结果 |
| Equation 1 | 6 | TrieHI 必须维护的集合不变量 |

### 关键结果：均为论文报告，非本项目实测

| 实验/主张 | 条件与报告结果 | 能支持什么 | 不能据此认定什么 | 定位 |
|---|---|---|---|---|
| 递归目录解析避免展开 | WIKI 均值（µs）：PE-ONLINE 365,000.80；PE-OFFLINE 235.23；TrieHI 273.10。ARXIV 对应 1,089.20 / 0.12 / 0.43 | 在给定工作负载中，后两者目录层大幅省去展开成本 | TrieHI 在递归目录解析上一定快于 PE-OFFLINE；总检索必有同倍加速 | [Paper: PDF p. 10, Table IV; PDF p. 9, Figure 7] |
| 非递归反向取舍 | WIKI 均值（µs）：29.07 / 1,037.07 / 945.17；ARXIV：4.35 / 163.91 / 112.49 | PE-ONLINE 直接父目录查找更便宜 | TrieHI 所有读操作最优 | [Paper: PDF p. 10, Table IV; PDF p. 9, Figure 8] |
| 维护减少路径重写 | 图 9 中 TrieHI 曲线通常更低，PE 曲线变异更大 | 支持该工作负载中节点重连的维护优势 | 固定平均加速倍数；所有冲突比例/所有子树均如此。原文未给可抄录的平均值，不编造 | [Paper: PDF p. 10, Figure 9, §V-C] |
| 资源有代价 | WIKI-PG 纯向量 1491.27s、7925MB；TrieHI 1502.21s、8326MB。PE-ONLINE 1502.49s、8143MB；PE-OFFLINE 1515.25s、8213MB | 此配置下 TrieHI 构建增量不大、存储更高 | 一般性地“树表示压缩了所有 metadata” | [Paper: PDF p. 11, Table V] |
| 深度影响不只来自目录层 | 浅层展开键更多；PG 在更深过滤下后两方案总延迟可升，作者归因于有效节点密度和连接性；IVF 更平稳 | 目录选择性与 ANN 执行行为需要分开分析 | 深度越大总查询一定越快，或文字解释已经单独因果验证 | [Paper: PDF pp. 10–11, Figures 10/11/12, §V-E] |
| OpenViking 用户记忆 | LOCOMO：OpenClaw 24.20%→82.08%，平均访问 95.14s→38.8s；另有 Hermes、Claude Code 对照 | 整套 OpenViking 集成在该设置下的收益 | 上述差值均由 TrieHI 单独带来 | [Paper: PDF p. 12, Table VI; PDF p. 11, §V-F] |
| OpenViking 多跳 QA | HotpotQA top-5：72.75%、3154 tokens/QA、0.22s；top-20：91.00%、12533 tokens/QA、0.23s。LightRAG：89.00%、28443 tokens、75s | 更多检索预算的系统级质量/成本取舍 | 同预算单组件消融、所有 RAG 场景普遍优胜 | [Paper: PDF p. 12, Table VII] |

补充解读：[Analysis] 表 IV 的极低 ARXIV 时间需要核对 bitmap 是借用、复制还是实际物化；该表给分位数但没有重复次数或置信区间。表 V 的“总索引大小差值”也不能自动等于进程峰值内存。质量曲线未提供原始点，本文不从小图编造精确数值。[Paper: PDF pp. 9–11, §V-A and Tables IV/V]

## 11 怎样正确理解结论

- [Paper] 支撑最直接的是 RQ1–RQ3：三种目录表示在递归/非递归、维护和资源上的取舍。TrieHI 的目标是兼顾递归和维护，不是每一项最小。[Paper: PDF pp. 8–11, §V]
- [Analysis] 三方案语义上应输出相同合法集合；如果质量明显不同，先排查范围、过滤执行和参数，而非说“树本身提高了向量语义质量”。
- [Analysis] 图 11 深度更具体时相关性变高，与目录提供有效先验一致，但范围改变也改变了任务。不能把这等同于编码模型改进。[Paper: PDF pp. 10–11, Figures 10/11]
- [Analysis] 系统级 QA 证据将目录检索、分层内容、记忆组织等一起改变，缺少单独切换目录策略的应用消融。表 VI/VII 可作应用动机，不用于认定 TrieHI 独立增益。[Paper: PDF pp. 11–12, §V-F]
- [Analysis] 正文成本模型不包含完整生产事务/持久化证明，性能计时还排除了公共 catalog 部分；复现必须写清比较口径。[Paper: PDF pp. 7/9, Consistency During Updates / Implementation Details]

有边界的结论：原文在 Viking 和指定工作负载中支持“保留目录树、物化范围、对子树作节点操作”的读写取舍；当前材料不足以保证在其他引擎/硬件上重现相同绝对数值。

## 12 作者明确提出的局限与后续方向

没有独立 Limitations 章节。可明确定位的未来方向如下，不把本项目批评冒充作者承认：

| 作者明确边界 | 表现 | 作者提出方向 | 来源 |
|---|---|---|---|
| 派生路径模式没有正式化和评估 | 通配路径段只作讨论 | 扩展 DSQ 路径谓词 | [Paper: PDF p. 7, Derived Path Patterns] |
| 更丰富路径谓词及混合约束规划仍属后续工作 | 未提供现成评估 | cost-aware planning | [Paper: PDF p. 12, §VII] |

另有作者说明的成本约束（不是正式局限声明）：TrieHI 非递归需要集合差、存储包括每节点聚合、MERGE 依冲突而定。[Paper: PDF pp. 7/10, §IV-B/V-D]

## 13 复现时必须追问的细节

| [Analysis] 观察 | 潜在问题及影响 | 如何验证 | 依据/追踪 |
|---|---|---|---|
| 本地 WIKI 查询只有 ID/text/空 metadata | 缺真实目录锚点，不能照跑深度和 DSQ 曲线 | 查原始发布包/说明；询问作者需用户授权；不能用 relevance labels 挑有利范围 | `reading-20261026/query-schema-check.json`；GAP-01 |
| 没有单独 DSM 操作文件 | 分布、合法性、顺序及状态重置不明 | 请求原始序列或先冻结自建协议并单列 | 原文 p. 8；本地清单；GAP-02 |
| ARXIV 有混合与类别两套查询，无递归标志 | 图表对应不明，原真值不能直接视为非递归真值 | 对照约束、原包和小规模精确真值 | 原文 pp. 8–9；GAP-03/05 |
| category 是列表、还存在 time 命名空间 | 单父目录/集合减法假设可能不适用 | 流式统计多归属，再核查语义；不得直接改进算法掩盖差异 | 式 (1)、原文 p. 9；GAP-04 |
| Viking PG/IVF 配置未给 | 质量/总延迟不能与原文精确对齐 | 找到作者配置，或审批准许替代后端并标注限制 | 原文 p. 9；GAP-06 |
| 更新顺序和读一致性不完整 | 中间状态或失败可能破坏 Inc/catalog | 先书面定义串行合法域；以后另做并发测试 | 原文 p. 7；GAP-07 |
| nDCG/Recall 规则及计时边界不全 | 即使同数据也可能算出不同结果 | 冻结指标公式/空集合/拷贝/预热/重复/线程规程 | 原文 pp. 9–11；GAP-05/08 |
| 当前机器内存小于论文服务器 | 全量索引可能换页或失败，延迟无法比较 | 先按预计 footprint 设规模上限；核对 Linux 资源 | `reading-20261026/resource-snapshot.json`；GAP-09 |

[External] 固定版本的 OpenViking [backend benchmark 文档](https://github.com/volcengine/OpenViking/blob/22a28101089515ddef85b96617449924baef9f35/benchmark/vectordb_perf/README.md)也说明公开 WIKI 查询缺目录约束，并将从真值派生目录标为诊断口径。它印证材料缺口，不是论文原始查询协议；本轮未运行该 benchmark。来源快照见 materials-and-gaps.md §2。

## 14 从中学到的知识

以下是 Agent-derived knowledge candidates（非用户自行提出）：

1. [Analysis] 过滤正确性先于检索质量：先验证“允许哪些 ID”，再讨论 ANN 快不快、准不准。
2. [Analysis] 读快往往来自提前计算。PE-OFFLINE 与 TrieHI 的聚合集合以写入和空间换递归读取速度。[Paper: PDF pp. 5–7, Tables I/II]
3. [Analysis] 数据结构的“操作对象”决定更新成本：路径键 vs 稳定子树节点；但集合并差成本仍需单独计量。[Paper: PDF pp. 6–7, §IV]
4. [Analysis] 总延迟应拆目录和向量两部分，不能用一层的微秒节省替代端到端证据。[Paper: PDF pp. 9–11, Table IV/Figure 12]

## 15 与已有知识的联系

用户未提供相关知识笔记；以下为 Agent-derived candidate，未作独立文献核验：

- [Analysis] 可以把 Inc 理解为树上的物化汇总：查汇总快，改归属时必须维护汇总。与数据库物化视图的直觉相通，但此处不作历史归属或理论等价结论。
- [Analysis] MOVE 类似目录树重挂接；MERGE 类似按名称递归协调两棵树，稳定节点不意味着冲突协调免费。[Paper: PDF p. 7, §IV-A]
- [Analysis] 目录范围确定“可检索集合”，embedding 决定集合内“相似程度”，二者职责互补；这也是把目录层与 ANN 解耦的原因。[Paper: PDF p. 2, §II-A]

## 16 研究想法

本轮仅复现规划，不安排算法改进。保留一个与忠实性审查直接有关的 Agent-derived research candidate，供未来选择，未纳入实现目标：

- 名称：多归属下的 DSM 正确性压力检查。
- 来源：[Analysis] 单父目录表述与 ARXIV category 列表/双命名空间之间的待确认关系。[Paper: PDF pp. 6–7, Equation 1 and DSM; PDF p. 9, ARXIV-Dir]
- 核心假设：[Hypothesis] 若同一个逻辑 ID 同时存在于多个分支，直接对旧祖先减去整个 S 可能删去其仍有效的其他归属。
- 相对论文的改变：只改变测试的数据归属条件，不先改算法；多归属若不在原文合法域，应标注边界压力检查，不能作为论文失败证据。
- 初始方法：在人工小树给同一 ID 两个归属，执行一次 MOVE/一次冲突 MERGE，以朴素枚举判定器对比每个范围。
- 如何验证：固定同一树、ID、操作和 bitmap，实现后在极小预算下比较每步范围与不变量；只有在多归属合法性得到来源确认后才作为核心验收。若所有合法多归属案例均正确，或者原文明确禁止多归属，则该失效假设不成立/不适用。
- 可能失败：①误把两个独立命名空间当成一棵树，测试建模本身有误；②实际 catalog 采用归属实例 ID 而非 payload ID，集合减法仍正确；③相关目录数据本来单归属。
- 创新状态：unverified。没有新颖性检索，不声称新算法或新问题；当前不执行。
