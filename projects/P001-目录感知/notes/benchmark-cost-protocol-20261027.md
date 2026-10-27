# PROTO-COST-02-20261027 — 独立成本诊断补充协议

版本：2026-10-27。状态：**实施和准入通过，协议冻结；正式矩阵尚未运行**。冻结哈希/源码清单见 `cost02-preparation-20261027-01/source-hashes.json`，准入日志和验证见同目录。继承设计 `dir01-cost-supplement-protocol-draft-20261027.md`，实际实现边界以下文为准。它是项目诊断工作负载，非作者原始设置。无训练、向量读取、ANN 或扩规模。

## 1. 与旧实验的关系

保留 EXP-20261027-004 的默认总时延为主结果，不重复或替换该矩阵；旧原始数据和 PROTO-01 不变。新阶段数据不与旧默认时延混池、不跨构建相减，不以阶段计时解释出未经测量的默认耗时比例。

冻结输入 manifest SHA-256 `6a300c9d995084a5ae3782ae2d5b763e08056f900c0e23967749c5d3272fe1d8`。图 2 为 9 条绑定/11 目录/22 查询；time 为 10,000 条绑定/34 目录/68 查询，时间原始样本哈希和操作顺序沿用 PROTO-01。所有方案、阶段和内存构建都复用原输入，不生成新的有利目录或操作。

## 2. 构建、执行和精确矩阵

独立构建目录 `code/build-Release-Cost` 与 `code/build-RelWithDebInfo-ASan-Cost`，不覆盖原 build-Release/ASan。启用 DIRECTORY_BUILD_COST_DIAGNOSTICS。默认 directory_core 和计数构建仍无新诊断宏；新 directory_core_phase 和 directory_core_allocation 分别启用 DIRECTORY_PHASE_DIAGNOSTICS / DIRECTORY_ALLOCATION_DIAGNOSTICS，不同时启用。CRoaring v5.3.2 原文件不修改。

准入命令：`code/scripts/build-test.cmd Release normal cost`、`code/scripts/build-test.cmd RelWithDebInfo asan cost`。cost 模式仅校验冻结 fixtures，不重新生成共享别名；time-pilot TSV 在各自构建目录生成，原始样本只读。ASan 仅用于正确性。

正式工具：`python code/scripts/run-cost02.py --project . --experiment-id <真实编号>`。当前没有登记新 EXP，也未授权运行该命令。纯计划命令为 `python code/scripts/run-cost02.py --plan-only`，不创建实验或启动测量。

| 类型 | 每个 run | 总进程 | 每进程 |
|---|---|---:|---|
| phase | 原 7 子负载×3 策略 | 105 | 3 预热+20 测量 |
| allocation | figure2/time×3 策略 | 30 | 3 预热+20 测量迭代；figure2 迭代含两次独立重建 |
| 合计 | run 0…4 | 135 | 串行运行，不重跑旧默认进程 |

phase 的 DSQ 在同一个初始索引上预热/测量；build 每次新建；figure2 MOVE/MERGE 各自独立初始树，time DSM 连续 MOVE→MERGE→拒绝 MOVE，每序列重建。allocation 的 figure2-move、figure2-merge 是两个独立 series，每迭代各记录 initial/after_operation/after_destroy 共6行；time-dsm 的 initial/after_move/after_merge/after_move_rejected/after_destroy 共5行。

含预热预期：phases.jsonl 33,465 行（build 690、DSQ 31,050、DSM 1,725）；allocation.jsonl 3,795 行（figure2 2,070、time 1,725）；overhead.jsonl 和 cost-process.jsonl 各135行，run-order 135行。保存全部失败/中断，不挑选或减少重复。策略在每个 run 循环移位，负载按运行器 matrix() 顺序固定，phase 后接 allocation。

## 3. 实际阶段口径

每次公开调用的外层总时间由驱动真实计时；core scope 先进入 directory 阶段，局部 scope 进入时暂停前一阶段、退出时重新开启前一阶段的新直接区间。每段由自身两次时间戳得到，累计互斥区间，不采用“总量减 catalog”构造净时间，不分配事件日志容器、不在计时内 I/O。

字段 phase_ns / phase_calls 的顺序与含义：

| 字段 | 范围 |
|---|---|
| directory_misc | 未单列的目录逻辑、循环、结构/路径更新及函数内局部清理 |
| path_location | parse_path，Trie locate，Flat required/find 的已标注范围；其它路径辅助处理留在 directory_misc，不冒充更细的纯解析时间 |
| bitmap_create_copy | Roaring bitmap 创建/复制 |
| bitmap_sets | posting/Inc add、or_inplace、andnot_inplace |
| ancestor_update | update_ancestors 中除上述内层 scope 的区间；祖先集合的前置构造可留在 directory_misc |
| catalog | map 构造、contains、bind、全表扫描 rebind 的直接区间 |
| bitmap_cleanup | Bitmap 析构中的释放；其他局部析构仍在其外层目录 scope 中 |

directory_core_observed_ns 是上表除 catalog 外直接观测区间之和。它是当前插桩构建下观测到的目录核心区间，不代表原默认构建的“净耗时”。公开 total 还包含探针、调用与循环边界等开销；不要求各阶段恰好等于 total，不用差值填补未分类时间。

拒绝操作记录 accepted=false，core 内参数检查和异常展开仍被 scope 关闭；**core scope 退出到调用者 catch 之间的异常传播不完整覆盖**，字段 rejection_exception_propagation_coverage=incomplete_outside_core_unwind。拒绝操作的诊断总值可保存，但不能称完整排除 catalog 后的拒绝净成本；不得把未调用 catalog 的0当作测量失败或继承上一步计数。完整拒绝 API 的旧总时延仍在004。此处是草案落实后的显式限制，不声称该细分字段全部覆盖。

每进程做10,000次空区间和10,000次空 PhaseScope 框架开销诊断，记录均值/P90/P99、标称 Clock 周期、观测最小非零 delta、零 delta 次数。不扣开销；阶段值与框架开销同量级时标为不可可靠分辨，不据此推断精细占比或稳定排序。驱动保持所有查询逐 ID oracle/冻结摘要及维护后全状态验证，检查与输出均在计时区外。

## 4. 分配追踪与内存口径

仅 allocation 可执行文件替换 C++ new/delete 家族，并在创建第一个 bitmap 前安装 CRoaring 官方 malloc/realloc/calloc/free/aligned_malloc/aligned_free hooks。仍使用现有 CRT malloc/free/_aligned_malloc/_aligned_free，不改容器或位图算法。固定容量2^18指针账本采用开放寻址、删除墓碑，不动态分配账本；溢出/重复指针/无效嵌入归属使进程失败。串行环境、默认 new_handler；自定义 new_handler、并发追踪和生产 OOM 回滚不在准入范围。

按指针记录实际请求字节及归属，释放时使用指针原归属，不依赖释放时的当前 scope；成功 realloc 改记新块，失败保留旧块。所有权为 observer（不纳入账本）、directory、catalog、bitmap。目录公开操作和工厂建立 directory 归属，Catalog 方法/默认 map 构造建立 catalog 归属，CRoaring hook 建立 bitmap 归属。使用同一类归属的临时对象在返回前释放；操作峰值包含这些临时字节，不把稳定态之外的峰值当持久占用。

根对象嵌入的 Catalog 控制块按真实子对象范围从根分配归属转入 catalog，根块计数不重复增加。SSO 在对象块中，长字符串实际缓冲、容器节点和哈希桶由 C++ 分配账本捕获；bitmap 外部容量由 hooks 捕获，不叠加 portable 大小。bitmap 对象中的指针仍属于节点本体，不重复计数。

requested_live_bytes 是请求载荷字节（包括容器内部实际请求容量），不含 CRT 元数据、碎片、OS 提交量或 observer 账本。category_peak_bytes 是各归属随实际分配/归属转移发生的观测峰值，不能相加冒充同一时刻峰值；total_peak_requested_bytes 单独记录同时存活峰值。根构造早期暂属 directory 的块在 Catalog 构造时分归属，分类峰值应按该时间线解释。observer_excluded 对应0只是“排除在账本外”，不是观测器真实占用为0。

在 initial 和每次维护后先采样，再在局部作用域创建 oracle 并检查；oracle 及 check_state 临时对象必须离开作用域，检查前后所属 live 字节一致。拒绝前后 live 字节不变；销毁后 directory/catalog/bitmap 字节和块数均归零。若不满足就失败，不输出正常汇总。ledger_complete 仅指已审查的当前 C++/CRoaring 分配路径与当前串行合法域，不是对任意程序堆的完整性证明。

每个 allocation 状态另存进程 working set/private bytes/peak working set/系统可用内存；进程值包含输入、固定账本、日志与分配器缓存等，不当索引净值。独立 bitmap portable 大小可从旧004同状态初始记录引用，不从进程总值倒算。稳定态请求字节可支持逻辑空间对照，仍不能直接对齐论文完整索引序列化大小。

## 5. 准入与失败记录

默认、phase、allocation 各自位图/固定语义/四种子各1,000混合步骤/10,000时间样本共21项 CTest；加两项诊断 admission 合计23项。admission 只做每子负载一次检查，不运行正式3+20矩阵。检查嵌套/异常事件闭合、状态清零、contains/bind覆盖、MERGE catalog调用与MOVE无调用、所有目录逐ID oracle、拒绝不变性和销毁归零。

分配合同测试包括普通/数组/对齐/sized/nothrow分配释放，零大小/空指针，calloc 溢出，失败注入的 throwing/nothrow与realloc，原指针异归属释放；通过结果只证明测试覆盖范围。默认算法透明性另见 preparation/transparency.json：仅去除已知诊断注解后的语句 token 与004匹配、公开索引头不变、原Release二进制不变；不是所有诊断行为的形式化证明。

运行器在创建唯一目录后立即写 running 状态，后续包括快照、配置、环境、编译配置/二进制/hash检查都在失败记录 envelope 内；失败或KeyboardInterrupt保存状态。电源输出按原字节及解码值记录。启动前检查登记、Release/ASan OFF、准入二进制hash、源文件完整清单、协议及输入哈希，每进程前复核输入和二进制。不能复用已有实验目录。

单进程120秒、整体30分钟（从创建实验前开始）、private bytes2GiB、系统可用至少2GiB、输出上限1GiB；系统/输出/整体上限在新进程前检查，private/system另在驱动迭代前检查。停止并保存实际失败/中断，不删除旧数据或减小矩阵。不改变电源、优先级、亲和性，背景负载如实记录。

## 6. 冻结、运行与验收

最终准入后将正式协议 SHA-256、源码文件清单/hash、Release诊断二进制hash和 fixtures 清单记录到 `notes/cost02-preparation-20261027-01/source-hashes.json`；完整源码快照与准入日志同行保存。后续任意源码/协议变动须重新核验并新快照，不能继续冒用冻结配置。

正式运行必须由用户另行指定，登记新 EXP 后执行。原始 phases/allocation/overhead/cost-process、config/environment/run-order、日志和source/protocol快照齐全后，summarize-cost02.py 才生成正常汇总。只统计 warmup=false，逐阶段/路径/操作/状态分组，5 run 各均值与 pooled nearest-rank 分位数均保留；小样本尾部不稳定。阶段、allocation 与004默认结果三种口径分开报告。

DIR-01-COST-02 的“工具实施与准入”可在上述门通过、快照冻结时完成；**不代表正式补测完成，也不关闭 DIR-01/OBJ-03**。未来正式测量的阶段不可分辨、拒绝异常传播未覆盖、请求字节与物理/序列化空间不可比等限制必须保留。任何有限验收范围调整仍须先由用户明确决定并更新TASK。
