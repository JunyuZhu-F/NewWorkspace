# WIKI-DATA-01 / WIKI-CHECK-01 — 完成当前小规模前置与目录准入

日期：2026-10-27，Asia/Hong_Kong。用户要求优先推进 WIKI；SCALE-01 后移。本文为实际事实入口，不是原版论文 WIKI 性能或质量验收。

## 输入与执行

原始输入只读：`dataset/raw/WIKI-Dir/` 六个在场文件。原始路径文件604,190,439字节，corpus JSONL 880,191,293字节，corpus向量7,960,883,900字节。全量向量未载入/逐条扫描，不安装依赖、不下载大型数据、不改核心算法。

项目根执行，解释器 `D:/anaconda3/python.exe`，均为真实命令：

```powershell
& 'D:/anaconda3/python.exe' -B notes/wiki-preparation-20261027-01/audit.py
& 'D:/anaconda3/python.exe' -B notes/wiki-preparation-20261027-01/verify.py
& 'D:/anaconda3/python.exe' -B notes/wiki-preparation-20261027-01/check_sources.py
& 'D:/anaconda3/python.exe' -B notes/wiki-preparation-20261027-01/run_check.py
& 'D:/anaconda3/python.exe' -B notes/wiki-preparation-20261027-01/run_check.py check-02
& 'D:/anaconda3/python.exe' -B notes/wiki-preparation-20261027-01/verify_check.py
```

首次 `run_check.py` 留在 check-01（失败）；最终入口为 check-02。所有脚本拒绝覆盖已有运行目录/核验输出；以上为历史命令，不可直接重复运行到相同目录。主控台日志分别在本目录对应 `*-console.log`，构建/测试完整命令、时间、退出码和资源样本摘要见 `check-02/commands.jsonl`。Git基线be59bbccb9e3f8e283328f453643b7d50211736d加既存STATE及本轮未提交增量；源快照及hash见check-02/source/、source-hashes.json。

## 数据事实：已验证

- `run-01/report.json`：1,941,679 条 path ID 均等于行号；全量 corpus JSONL ID 也连续等于行号。向量固定记录长度推算的行数相同，但这不是全量向量内容完整性证明。路径满足当前单父目录解析合法域。
- 全量严格流式JSON解析检查数组闭合、EOF、分隔符、重复键；另一种按格式逐对象解析独立复核全部路径、ID、目录统计和10000条选样绑定，见 `run-01/verification.json`。corpus只做ID/JSON核查，不声称逐条验证标题与目录语义。
- 全量不同末端路径 **363,467**，其不加权平均深度 **11.9512445421**。补齐祖先并含根则 **468,031** 目录；非根目录平均深度 **11.8313719206**；按条目加权深度 **12.5764732482**，范围1–31。
- **合理推测**：末端路径数和均深恰与论文§V-A的363,467/11.95吻合，支持作者按不同末端路径统计；没有作者统计脚本，不能将该定义标为已确认。完整树必须保留祖先，不能为迎合数字丢弃目录。
- 456条query ID与查询向量行号连续对齐，metadata全部为空；查询仍无目录约束。10,851对qrels覆盖456查询、10,410个不同文档，grade=1/2计数6357/4494，无重复query/doc对或越界ID。qrels为相关性标注，不能直接当精确近邻Recall真值。
- 10000个全库等间隔ID：`floor(i*(1941679-1)/9999)`，不依赖query/qrels，真实路径补齐祖先后23025目录。逐条检查10000个原始corpus向量及全部456个query向量的1024D头、记录完整性、有限性、非零；独立复读10000条样本记录hash一致。没有重新归一化。
- 该样本仅含56个qrels文档、61条query/doc标注，只有46个查询有样本内标注，另外410个没有。不得将样本无标注视作确定不相关，或以该子集分数代表完整WIKI nDCG。
- 原始文件前后size/mtime一致。全量paths本地SHA-256：`d9642870803d14fa6d9193f743ed1d2a758ab643fcffe248d2d9009cf73a616a`；corpus完整hash见report。没有发布方checksum对齐声明。
- 主审计31.031秒、独立复核18.844秒，仅是审核运行时间，非查询延迟。主审计进程观测peak working set为393,027,584字节。

## 目录正确性：已验证

冻结协议 `protocol.md`。新增 `code/wiki/validate.cpp`、隔离CMake与`code/scripts/build-wiki.cmd`，原算法及原独立C++ oracle不变。

- 相同10000个真实global ID/路径，另建两个显式测试空目录；初始23027目录。每层最多8个固定查询目录，另查根、空/不存在、操作相关路径；当前四个状态分别220/220/221/221路径，两模式、三方案合计每构建 **5292次集合核查**。
- 初始、合法MOVE、互不包含MERGE、非法自包含MOVE拒绝后，三方案与独立C++ oracle完整ID集合零差异；各阶段全量目录/catalog/inclusive bitmap不变量通过，拒绝前后不变。
- Release退出0；ASan退出0，无报告的地址错误；两个构建完整答案文件字节相同。`check-02/status.json` 为通过状态，`check-02/independent-verification.json` 记录第三份Python路径状态判定器对全部输出的候选数/ID摘要、状态存在性和查询覆盖复核通过。Python摘要检查不能代替C++完整集合比较，两者职责不同。
- 与006冻结的46个源码文件逐一hash匹配，既有ARXIV成果未修改。新入口/协议/输入快照均留证。
- Release运行4.813秒，ASan运行98.985秒，仅为正确性执行时间。ASan private字节按0.2秒采样观测最大1,156,001,792，系统available观测最小4,694,437,888；未触发180秒/2GiB/available2GiB门禁。不将采样值当精确峰值、索引独占空间或性能成绩。

## 失败与公开材料边界

- check-01：构建命令误用正斜杠，cmd返回0但没有生成目标二进制；随后启动FileNotFoundError，整体状态为failed。未执行有效WIKI测试。保留全部快照和日志；修正为反斜杠并增加目标产物断言后，另开check-02通过，没有覆盖失败。
- 独立verify_check首次在ASan尚未结束时提前调用，被status门禁拒绝；原失败日志 `verify-check-console.log` 留存。实际两构建结束后再次调用成功，日志为 `verify-check-final-console.log`，没有重跑测试。
- `public-sources-01/sources.json` 保存本次实际HTTP读取的URL、时间、ETag、hash及正文。作者数据仓库根目录API本次仅列README；公开README仍未给逐query目录。OpenViking benchmark README仍明确WIKI公开query没有constraint，其 `derived_gt_lca_v1` 从GT反推范围，不能代表作者分布；本项目未采用。查询Google Drive目录的web工具访问失败，未取得远端文件清单，不能断言发布网盘没有补充文件。
- 来源：[作者数据仓库](https://github.com/KurtPatrickHere/dir-vector-dataset)、[OpenViking关联基准说明](https://github.com/volcengine/OpenViking/blob/main/benchmark/vectordb_perf/README.md)。本地快照是本次读取证据，mutable main不作为作者原始实验版本。

## 下一项与未完成

先执行WIKI-DIR-01：依托本次准入输入冻结小规模DSQ/DSM性能协议及具体矩阵，保留深度、候选量、目录/公共catalog成本边界，至少5独立进程；自建操作必须标注，不能称作者2000条DSM序列。冻结后方可测量，不重跑ARXIV。

WIKI-PROTO-01同时以本次事实推进：优先继续定位作者原始query目录；若不可恢复，另存不依赖qrels的独立目录协议，明确平方L2/余弦等选型与作者未知设置的区别；nDCG须规定增益与目录内IDCG、未标注/空标注/缺失标注处理，Recall须用独立的对应候选范围真值。现有均匀样本不支持完整456查询的代表性相关性成绩，应先解决该评价覆盖问题，不能填0/填1混入曲线。

本轮没有WIKI性能曲线、ANN质量成绩、全量索引、原版Viking/PG结果；SCALE-01后移，1995年不追查，组会不处理。
