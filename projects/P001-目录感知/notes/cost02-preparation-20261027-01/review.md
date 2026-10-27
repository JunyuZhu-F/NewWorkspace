# DIR-01-COST-02 实施与准入审查

2026-10-27，Asia/Hong_Kong。用户明确指定实施独立阶段计时/内存追踪并完成准入；**未指定正式135进程补测**。本任务只交付工具、证据和冻结配置，没有新真实实验编号、没有正式补测结果。

## 1. 实际改动及算法边界

- 新 diagnostics.hpp / diagnostics.cpp：阶段构建只做互斥直接区间计时；allocation构建只追踪请求分配，宏互斥使用。默认核心不链接 diagnostics.cpp，宏清空，不增加默认数据成员。
- index.cpp / path.cpp / bitmap.hpp：只增加条件注解/guard及 catalog 的诊断构造与控制块归属；目录结构、容器、posting/Inc操作、catalog扫描、更新顺序、拒绝语义不改。transparency.json 核对已知注解剥离后的语句token与004一致；公开index.hpp及原build-Release两个二进制hash不变。
- cost_diagnostics.cpp / cost_core_tests.cpp：复用原冻结fixture加载器、判定器与core tests；独立模式重新执行固定/随机/真实时间样本，新增phase/分配合同和每子负载一次admit，不运行正式3+20矩阵。
- CMake默认新选项OFF；独立Cost构建目录/库/可执行文件，不覆盖原默认构建。build-test.cmd增加cost、build-only、admission-only路径。cost输入验证只读，避免旧生成器的共享别名竞争。
- run-cost02 / summarize-cost02：计划、冻结源码/输入/Release二进制核对、早期失败记录、资源停止及严格完整性统计。新工具未与原004默认数据混池。
- 旧代码/文档未提交修改保留，没有Git提交、推送、重置。raw数据、第三方源码、旧正式协议和004实测文件不改。

## 2. 真实验证结果

| 验证 | 实际命令/日志 | 结果 |
|---|---|---|
| 初轮Release全套 | ctest Release-Cost；release-ctest.log | 23/23，退出0 |
| Release最终核心/驱动门 | build-test.cmd Release normal cost；release-final.log | 23/23，原默认/计数自检各通过，退出0 |
| ASan最终核心/驱动门 | build-test.cmd RelWithDebInfo asan cost；asan-final-attempt2.log | 23/23，原默认/计数自检各通过，退出0；ASan未报告地址错误 |
| 最终schema Release | build-only后ctest -R admission；release-schema-build.log、release-schema-admission.log | 2/2，退出0 |
| 最终schema ASan | build-test.cmd RelWithDebInfo asan cost admission-only；asan-schema-admission.log | 2/2，退出0 |
| 独立准入输出核验 | verify-admission.py；admission-verification.json | Release/ASan各291条阶段+33条allocation；全组通过，旧11文件hash一致 |
| 默认算法边界 | verify-transparency.py；transparency.json | 三源码注解剥离token一致，公开header/原Release二进制不变 |
| 输入 | verify-cost-fixtures.py | 10个冻结输入文件及PROTO-01 hash通过，0写入 |
| 运行器 | run-cost02.py --plan-only；plan-only-final.json | 135计划进程；实测0；预期phases33465/allocation3795/overhead135/process135 |
| 早期失败包络 | run-cost02.py --self-test .../runner-selftest-final | 隔离的synthetic缺快照失败正确落盘，测量进程0；不是实际EXP |
| 汇总器与Python | verify-admission.py | 已知nearest-rank检查/语法通过；不完整synthetic输入被拒绝、没有生成正常summary |

最后一次C++输出字段修订只增加独立协议编号和进程内存指标，不改变已通过23项的核心库或core-tests；因此只重编译两个诊断驱动并重跑两项admission，保留此前全套日志，未无故重跑长随机门。ASan完整LastTest原始输出保存在 asan-full-LastTest.log，最终四组admission原始值复制到 admission/，不只依赖忽略的构建目录。

这些数字是准入结果，不是论文性能样本。正式矩阵和完整矩阵的成功汇总尚未执行；summarize-cost02正向全135矩阵分支将由后续真实运行进一步检验，不把synthetic负向测试当正式通过。

## 3. 准入覆盖

阶段：每操作reset，固定容量scope栈，嵌套暂停/恢复直接计时；异常离开函数时闭合。admit检查build contains/bind调用覆盖、MERGE catalog调用、MOVE无catalog调用及陈旧计数清零；query在计时外逐ID+摘要，DSM每步oracle及全状态。阶段之和与外层total不要求相等，也不构造残差。

分配：C++ new/delete的普通、数组、sized、aligned和nothrow路径；零大小/空释放；calloc溢出；失败注入的new/realloc；不同当前归属下释放原指针。map节点/桶/字符串请求由C++账本记录，Roaring由官方hooks记录；嵌入catalog控制块不重复算根块。稳定采样先于oracle，验证前后live bytes相同；拒绝前后live不变，销毁后directory/catalog/bitmap字节和块数全0。

独立核验还检查三方案catalog稳定态字节在同一输入的各维护状态一致，所有准入行有正确新协议编号，阶段值不是total-catalog构造，内存包含/排除口径明确。ledger_complete针对当前已审查的串行C++/Roaring路径，不是任意系统堆覆盖证明。

## 4. 失败、修复与证据保护

1. release-build-attempt1.log：编译退出4，CRoaring memory hook接口在全局命名空间，初稿误放 roaring::api；改为全局接口后release-build-attempt2成功。第三方文件未改。
2. asan-final.log：准备退出2，原因是同时启动两套旧fixture准备导致共享别名生成/移除竞争，未进入CTest。改为cost构建只读核对冻结输入后，顺序重试成功；不改原生成算法或原始数据。
3. 冻结首轮断言 len(fixtures)==10 失败：上述竞争遗留了一个 time-dsm-queries.tsv。核对其字节hash与time-queries.tsv相同，确认为本轮生成的冗余别名，移入 shared-fixture-race-leftovers/ 保留；原10个输入未改。随后冻结成功。该首次freeze失败发生于zip/清单写入前，没有覆盖已有快照。
4. 旧001/002/003失败记录全部保留。本次synthetic运行器检查在notes下独立目录，不伪装新EXP或真实性能结果。
5. 最终证据复核脚本再次读取含中文路径的origin.txt时，系统默认GBK解码UTF-8失败；明确指定UTF-8后重核验通过。只修改notes下验证脚本，不改冻结code快照、二进制或任何准入原始值。

## 5. 冻结交付与限制

快照 COST02-440a2e0f81208f81，完整源文件hash `440a2e0f81208f814bddf4b3f709b8739ec122471e8d32cae57f86418a1fb997`（code树30文件）。协议hash `589d3b6f7abe9123c3f094a04e54084e885a7d77114fc3ae74770f92dc56e066`。完整source-snapshot.zip及容器hash、输入10文件、Release/ASan诊断二进制hash在 source-hashes.json；build-info.json记录真实优化/ASan选项。

当前工具边界：拒绝操作的scope外异常传播未完整分阶段，明确标incomplete；directory_core_observed_ns是直接区间合计，不冒充默认净时间；小时段与探针开销同量级时不能可靠排序。内存是requested载荷字节，不含CRT元数据、碎片、observer账本，不是物理堆或序列化大小；分类峰值不能相加当同时总峰值。自定义new_handler、并发和OOM回滚不在当前域。未来实测仍须保留这些限制。

**结论：DIR-01-COST-02 工具实施、审查与准入完成，具备接收正式补测指令的准备条件。DIR-01/OBJ-03不关闭。** 下一步只能在用户明确指定运行后登记唯一实际EXP、执行冻结135进程矩阵、保存真实成功/失败/中断并核验结果。不自动运行、接ANN或扩规模。
