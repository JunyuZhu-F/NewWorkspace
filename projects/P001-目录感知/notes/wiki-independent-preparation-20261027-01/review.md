# WIKI独立协议与新增驱动审查

## 最终审查结论（已验证）

准入三份独立verification、007默认/phase各5进程、008检索5进程及所有final-check均通过。新75个worker文件、源快照及当前源、原始向量样本匹配；旧006的35个worker文件和46原源码匹配。007/008源码清单为53/54项，多出项仅README，无算法或参数差异。finalize补充逐行核对run标签、全部raw run ID、Release/ASan关闭标志及CSV导出来源hash；未发现需改核心算法的问题。

007正式37800条加5670预热，008正式1094400条；C++完整集合比较、独立Python状态/排名/模型/格位/会计核查均通过。报告保留非递归、deep MERGE反例与nprobe4低召回、329空非递归case，不用高召回点掩盖低值。两份results与analysis-01/已导出，方法限制与nDCG未报告状态一致。

收尾导出首次失败为Python源编码识别报错（export-console.log），源文件经UTF-8解码/AST核对后显式加入编码声明，export-recovery-01-console.log成功。没有改参数或重跑测量；finalize-console.log通过，所有失败日志保留。该问题只影响报表导出，不影响已通过的原始实验与独立真值核验。

最终状态与入口已同步TASK、PLAN、STATE、EXPERIMENTS、README、项目AGENTS及materials-and-gaps。用户不联系作者的决定保留，原作者GAP和全文/全量/PG/Viking目标不关闭；未提交Git、未安装依赖、无本项目活动实验/构建。

本次为当前执行者的源码/协议自审及独立判定核验，不冒称其他审查者或代理已审查。测试/正式运行事实以本目录status和实验记录为准，本文不提前宣布未完成的运行成功。

## 科研边界与授权

- 用户明确授权采用独立协议、执行并审查文档，且不等待作者联系；TASK先更新再更新PLAN。原作者GAP-01/02/05/06仍开放，独立分支不受作者联系阻塞。
- README确实把约束指向dbpedia_dir_2m_query.jsonl，但该文件456条metadata为空；这是描述与发布文件不一致，不能写成作者未指定文件名。materials-and-gaps的GAP-01已修正，用户网盘核对作为用户提供的证据记录，不伪称本程序重新下载网盘。
- 本轮10000样本固定、目录/查询配对及维护序列均不依据qrels/测量结果；nDCG明确不报告。Recall@10只针对本项目目录内子集精确GT，不是相关性Recall，不将曲线冒充原文工作负载。
- 8次Lloyd为既有独立IVF的索引构建设置，不涉及神经模型训练、重新编码全库或超参数搜索。

## 源码与测量边界

- 目录核心、CRoaring和独立后端不修改。原46源码hash在snapshot/准入/正式结束时逐条核对。新增代码全部隔离在code/wiki_experiment及build-wiki-experiment.cmd，旧WIKI检查/SEARCH/004–006输出不覆盖。
- search01_backend.inc须字节等于search.cpp的main前缀；wiki_search.cpp须严格等于SEARCH-02包装器仅替换query数量501→456、case数量1002→912、合同标签。pipeline.generated执行两项字节断言；不是拷贝后暗改算法。
- 新目录驱动在计时外预建独立C++ oracle的5个状态；每次返回完整ID集合逐项比对、每维护后全树/catalog/bitmap不变量及固定查询核验。Python另从原始样本路径重建状态、核对全部candidate数/ID摘要/查询覆盖与计时格位；摘要检查不取代C++完整集合比较。
- build/DSQ/DSM API均用steady_clock直接区间。输入加载、独立判定、输出排除；DSQ返回bitmap及调用者后续释放的边界已明示。构建每pass重新创建索引，随后同一索引执行查询和固定连续维护；不解释为冷缓存/独立操作样本。
- 默认和phase独立5进程，不能混池。phase直接观测catalog和其他scope，阶段总和≤API总量；剩余区间不靠差值填造。未做额外allocation追踪，portable bitmap字节与catalog条目数/进程内存分列，不当物理堆或全系统序列化大小。
- 查询按输入UTF-8排序，无根据延迟筛选；三方案顺序随run循环移位；检索case/probe由固定每run种子打乱，三方案共享同一后端对象，跨进程模型hash和结果必须相同。
- 精确GT采用float64平方L2，ID并列升序；root单独解析成空路径元组，避免把根误判成['']。空候选Recall=null，所有空范围延迟保留；非空Recall分母min(10,候选数)。approximate召回低不剔除。

## 独立核验与限制

核验器检查源向量选取区域与派生文件逐记录相等、输入size/mtime、固定样本、目录分层/哈希配对和维护选择规则；默认/诊断矩阵全部重复格位必须唯一完整；各次空间状态一致；检索独立重算分区、完整候选、exact/IVF排名与距离、跨构建/策略/进程一致和阶段和等于total。完整通过记录将在准入/实验verification文件生成后引用。

限制：只覆盖独立小样本、单父目录、串行、既有原型IVF；该原型遍历允许ID并过滤分区，不是优化倒排遍历/Viking。查询ID哈希配目录是结构压力输入，可能与文本意图不相关，不能据此解释自然用户任务质量。目录深度/候选规模分布、极小/空集合比例须随结果报告；未做显著性检验，尾部分位数不宣称稳定。probe开销、校验引起的缓存效应与未控制的背景负载保留；不把总延迟全部归因于目录算法。

当前准入过程无须重新执行旧核心测试矩阵或ARXIV实验；新驱动与数量适配的Release/ASan准入是本轮必要验证。若失败，保留目录并另开恢复编号，不修改参数迎合成绩。
