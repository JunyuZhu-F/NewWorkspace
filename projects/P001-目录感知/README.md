# Directory-Aware Query and Maintenance in Vector Databases

> P001-目录感知，采用 arXiv:2606.16903v1。复现范围已确认，单父目录三方案已实现并完成审查，Release/ASan 各 7/7 正确性测试通过；尚无性能或 ANN 复现结果。

初次阅读建议先看 [精读笔记](notes/paper-card.md) 和 [材料/疑点清单](notes/materials-and-gaps.md)，再审核下面的目标与计划。

最新交付：[核心实现与审查](notes/core-review.md)、[构建和使用入口](code/README.md)。数据边界见 [DATA-01 小规模核查](notes/data-audit.md)。用户确认先用现有电脑，暂不做应用实验，大规模运行另行决定。

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

现有 Windows x64、MSVC/CMake/Ninja，CRoaring v5.3.2 已固定。代码和命令见 [code/README.md](code/README.md)，真实验证、源码快照与原始日志见 [core-review.md](notes/core-review.md)。本轮仅处理目录和 ID，未接入向量搜索。

原始数据在 dataset/raw/，保持只读；前 10,000 条时间视图用于正确性。DATA-01/SPEC-01 的真实类别、WIKI/作者工作负载缺口仍保留，关联 OpenViking 不能直接视为完整原文实验包。

下一任务是 PROTO-01：先写小规模目录性能协议，暂不执行基准。大规模运行由用户以后单独决定。
