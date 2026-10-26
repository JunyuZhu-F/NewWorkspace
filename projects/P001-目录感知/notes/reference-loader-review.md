# 固定版本 OpenViking 数据加载路径核对

日期：2026-10-26。这里分析的是关联开源系统当前版本的诊断 benchmark，**不是已核实的论文三方案/Viking 官方实验包**。不修改上游代码，不运行后端基准。

## 来源与证据

- 固定 commit：`22a28101089515ddef85b96617449924baef9f35`。
- [原始 run.py](https://github.com/volcengine/OpenViking/blob/22a28101089515ddef85b96617449924baef9f35/benchmark/vectordb_perf/run.py)。本地完整参考快照为 `data-audit-20261026-01/openviking-run.reference.py`，73,386 bytes，SHA-256 `e3a32a90529a7b228b8f4a524cbaf3767325a4ec69df60aff2f566b9e5237dab`。
- 只选取已检查的六个纯路径辅助函数和一个常量，以 AST 载入后对本地记录求值；没有 import 整个参考模块、连接向量库、建表、写入或运行 benchmark。检查脚本：`check_reference_loader.py`；实际结果：`data-audit-20261026-01/reference-helper-check.json`，退出码 0。
- 函数级求值能够验证这些 helper 的结果，不等同于运行并证明整套 OpenViking 系统的最终行为。

## 1. ARXIV 多类别和时间路径

源码路径：

1. `extract_legacy_path` 在没有通用路径字段时，枚举记录值并取含 `/` 的字符串/字符串列表（行 531–543）。
2. `normalize_path` 将路径列表拼成用分号分隔的字符串（行 479–493）。
3. `resource_uri` 只使用分号前第一段生成 URI（行 660–668）。
4. ARXIV records 分支调用上述提取，再生成资源 URI（行 901–932）。

对真实 metadata id=145（含三个类别和一个 time）的 helper 求值结果：

```text
legacy_path = /Mathematics/math.DG;/Mathematics/math.QA;/Physics/hep-th
resource_uri = viking://resources/bench/arxiv/Mathematics/math.DG/145
```

**已验证的 helper 行为：**这个映射保留第一类别 URI，没有在该条记录 URI 中同时保留其他两个类别或时间目录。它不能作为“原文就是这样处理双命名空间、多类别”的证据。

## 2. ARXIV 查询约束

`GENERIC_PATH_FIELDS`（行 496–506）没有 `category` 或 `time`；`extract_declared_path` 只在 constraints/metadata 等容器中找这些通用字段（行 509–524）。`extract_legacy_path` 的后备逻辑也不递归解析嵌套 dict。

对当前在场的全部两套 ARXIV constraint JSON 求值，均为：

| 文件 | 条数 | helper 返回根路径 `/` 的条数 |
|---|---:|---:|
| arxiv_query_constraint.json | 1,000 | 1,000 |
| arxiv_category_query_constraint.json | 1,000 | 1,000 |

源码 query 分支在行 948–953 调用这一 helper，行 982 将得到的目录生成 URI。因此**这条加载代码路径**不会忠实保留当前 ARXIV 嵌套 category/time 约束。这里只核查固定版本与本地文件组合；不泛化为所有 OpenViking 版本、接口或作者原始实现均如此。

## 3. 真值行号与指标

- `load_scored_ground_truth` 行 787–788 明确按纯文本文件行号作为 query ID。这支持本项目此前“第 i 行对应 query_id=i”的解释，但仍不是作者原始生成脚本的证明，也未证明其中 ID 是哪种距离的精确 top-k。
- query 组装在行 945–946 对抽样子集过滤全量真值；这只能支持该诊断工具的抽样检查，不应当作本项目严格的子集精确 top-k 真值。
- 检索质量段落在行 1187–1195 记录的是 `hit_rate_at_k`：至少命中一个真值的查询比例；不是论文 Recall@100 的逐查询召回率定义。不能只改显示名称就拿来对齐论文曲线。

## 4. 本项目处理

1. 不直接使用这份 runner 作为三方案忠实复现入口，不修改或“修好”上游快照。
2. 数据适配须显式解析 `constraints.category`/`constraints.time`，保留原始类别列表和 namespace；不能依赖泛化字段猜测。当前仅写要求，没有实现适配器。
3. 目录层单父目录核心按 `operation-spec.md` 继续；多归属 DSM 和质量协议仍待核对，不用当前 runner 的行为填补论文空白。
4. 相关源码路径与版本可以复用作后续检查依据，但不能称为已经运行了官方实验或恢复了作者参数。
