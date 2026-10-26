# 单父目录三方案：实现审查与正确性记录

日期：2026-10-26。**已验证当前单父目录、串行合法域；未执行性能或 ANN 实验。** 本项目依据论文独立编写，不是作者源码。范围与最终验收见 `../TASK.md`；原文精读见 `paper-card.md`。

## 1. 做到了什么

把“目录里应该有哪些 ID”落成三种可运行索引。查询返回候选 ID 位图；移动改变子树位置，合并把源目录内容合入目标。用另一份逐条目枚举程序判定答案，不靠三方案互相赞同来证明正确。

源码在 `../code/`，本次验证版本 **SNAP-dd12b2f5ac546566**。`core-implementation-20261026-01/validation-record.json` 保存 18 个工程/依赖文件的字节数与 SHA-256、测试配置、二进制和输入哈希；同目录 `source-snapshot.zip` 保存同版源码。无 Git，不虚构 commit。

## 2. 方法到源码及工程选择

| 内容 | 原文定位/性质 | 当前实现 |
|---|---|---|
| PE-ONLINE | PDF pp. 4–5，§III-A，表 I | `../code/src/index.cpp` 的 FlatIndex(false)：只存直接 posting；递归枚举子树目录并集合，非递归直接读 posting；维护重映射全部源子树路径键 |
| PE-OFFLINE | PDF pp. 5–6，§III-B，表 I | 同文件 FlatIndex(true)：插入写终点及祖先 posting；递归读取物化集合，非递归减直接孩子子树并集；维护另更新变化的祖先 |
| TrieHI | PDF pp. 6–7，§IV-A，图 5、表 II | 同文件 TrieNode/TrieIndex：segment、parent、children、inclusive；不存完整路径或 Local 位图。MOVE 只摘挂源根，MERGE 冲突递归协调，不冲突子树整体转挂 |
| 范围不变量 | PDF p. 6，公式 (1) | Inc=直接归属条目∪直接孩子 Inc。validate() 从 catalog 重算期望，仅作调试；外部判定器还逐目录比较两种查询 |
| 祖先维护 | PDF pp. 5/7，§III-B/IV-A；符号整理见 paper-card.md §09 | 源侧独有严格祖先减源集合，目标侧独有严格祖先并源集合，共同祖先保持；MERGE 目标根在冲突协调时并入 |
| 源根直接条目 | MERGE 语义/catalog 一致性推导，原文无完整伪代码 | 冲突节点合并 posting/Inc，并将源节点的直接 catalog 绑定转向目标，避免只处理孩子而漏源根条目 |
| API/边界 | 项目约定，非作者完整规范 | `../code/include/directory/index.hpp`、`../code/src/path.cpp`；规则见 operation-spec.md。缺失与空目录区分；重复 ID、非法路径、成环或同名 MOVE、包含 MERGE 拒绝；同父 MOVE 成功 no-op |
| 公共位图 | 原文用 Roaring，版本未给 | 官方 CRoaring v5.3.2 C/h；`../code/include/directory/bitmap.hpp` 为小型 RAII 所有权适配，不实现新位图算法 |

两个 PE 共享路径辅助结构，posting 与算法分支不同。辅助目录索引用 std::map 和直接孩子路径集合，是论文抽象结构的一种工程落实，不能据此声称精确复现作者容器和复杂度常数。所有查询返回独立拥有的位图副本；复制成本未来必须计入或单列。

**公共 catalog 的边界：**三方案都用 ID→稳定目录对象指针记录归属；PE 对象路径随路径键重映射更新。这是项目工程选择，并非声称作者 PE catalog 使用相同的稳定句柄。冲突合并扫描公共 catalog，将源节点的直接绑定转向目标；扫描数计入 catalog_entries_scanned。范围查询不扫描 catalog，不借它绕过非递归集合差。后续须分列目录部分与完整系统成本，不能直接把整段维护时间对齐原文排除 catalog 的比较。

## 3. 审查内容

本轮为自审，没有冒称第三方独立代码审查；独立的是判定器实现及其数据结构。

- 查看路径解析、接口、三方案写入/查询/维护、辅助目录、catalog 与测试调用；检查输入预条件先于结构变更。
- 核对 MOVE 的旧/新祖先、共同祖先、后代身份；核对 MERGE 源根条目、连续同名冲突、不冲突子树转挂，旧路径消失但全局 ID 不增减。
- 审查 unique_ptr 摘挂、map 键生命周期、位图深复制与移动。落实 moved-from 位图重用、显式指针返回类型、摘挂前复制键等防御性修整；不把它们称为测试已发现的崩溃。
- 检查使用显式 require，Release 下不会因 NDEBUG 消失；查询快照不受后续维护影响。
- 未给 PE-OFFLINE/TrieHI 增加 Local 位图；验证入口 bindings/directories/validate 不参与正式范围查询。
- 两份最终日志保留上游 roaring.h:6110 的 C4702（unreachable 后返回分支）；已定位为上游不可达兜底，不修改上游源码，不宣称零警告。

## 4. 独立判定与覆盖

`../code/tests/oracle.*` 用 std::set 目录和 ID→直接父路径，查询逐 ID 判断归属，维护重建路径/绑定；不调用生产路径助手、posting、Inc 或 Trie，只共享接口类型/错误码。图 2 手工答案再次约束判定器，防止两份代码共同误解语义。

| 测试 | 已执行内容 |
|---|---|
| bitmap_contract | 9 项所有权/集合检查，含 0、65535、65536、UINT32_MAX，深复制、移动/自移动、复用及自并差 |
| fixed_semantics | 图 2 全 11 目录与独立 MOVE/MERGE；根/空/缺失、段边界、UTF-8 中文目录、源根条目、深冲突/不冲突子树、共同祖先、非法操作/no-op、快照所有权和节点身份 |
| random_7/42/2026/65536 | 每种子 1,000 混合步骤，含查询、写入、创建目录及合法或拒绝的 MOVE/MERGE；每步核对全目录两种集合、命名空间、catalog 和内部不变量 |
| time_pilot_correctness | 固定前 10,000 ID/time 输入；初始全 34 目录查询；MOVE→MERGE→同名 MOVE 拒绝后逐阶段全目录核对，未读取向量 |

每份最终配置累计 **1,056,726 次范围集合比较、1,138,509 项检查**。这些计数包含同状态多方案/两模式的反复核对，不是独立统计样本量。随机共 4,000 混合步骤不等于 4,000 次成功维护；日志字段 logical_mutations 也包含拒绝请求，且不计 pilot 批量装载。

时间视图序列及数量锚点见 operation-spec.md §7。完整 ID 集合与判定器核对，没有以数量相同替代成员一致。

## 5. 真实构建、结果与重跑

本机 MSVC 19.51.36260.0（工具目录 14.51.36231）、CMake 4.3.1-msvc1、Ninja 1.13.2.git.kitware.jobserver-pipe-1；Windows x64、C++17，细节见 environment.md。编译并行数 2，依赖已固定，构建无需联网。

PowerShell 命令：

```powershell
& 'D:\NewWorkspace\projects\P001-目录感知\code\scripts\build-test.cmd' Release
& 'D:\NewWorkspace\projects\P001-目录感知\code\scripts\build-test.cmd' RelWithDebInfo asan
```

| 配置 | 实际结果 | 原始证据（相对本笔记目录） |
|---|---|---|
| Release | 7/7，通过，命令退出码 0 | `core-implementation-20261026-01/release-final.log`、同目录 Release-LastTest.log |
| RelWithDebInfo-ASan | 7/7，通过，退出码 0；未报告地址内存错误 | `core-implementation-20261026-01/asan-build-test.log`、同目录 RelWithDebInfo-ASan-LastTest.log |

ASan 同时覆盖核心、测试与 CRoaring。它不证明不存在所有类型的内存/并发错误；本次没有单独作泄漏或 UndefinedBehaviorSanitizer 认证。CTest 总耗时是开发测试时间，不是三方案延迟或论文性能结果。

前一次 6/6 Release 通过保留在 release-build-test.log；最终审查后增加位图契约覆盖并纳入 pilot，采用最终 7/7 两配置记录。可选 roaring.hh 获取曾超时/传输失败，最终用已验证的官方 C API。初次中文文档辅助脚本解码失败，显式 UTF-8 读取后成功；失败尝试未当作通过。

依赖来源：[CRoaring 官方 v5.3.2 release](https://github.com/RoaringBitmap/CRoaring/releases/tag/v5.3.2)，元数据快照 core-implementation-20261026-01/croaring-release.json；C/h 本地哈希与官方 release digest 一致，许可证保留。此版本是工程固定版本，论文版本待确认。

## 6. 结论、限制及下一步

**已验证：**当前单父目录、串行合法域内，三种表示符合手工预期和逐条目判定器；维护前后拓扑、归属与集合保持一致。有源码快照与两配置真实测试证据。

**待验证或未执行：**真实多类别/跨命名空间维护、WIKI 原查询和作者 DSM 序列、ANN/质量/性能、全量完整性与规模；并发、持久化、分配失败事务回滚不在当前保证中。任意深度的递归栈与内存上限未验证。没有论文加速倍数或空间优越性结论。

下一项为 PLAN 的 **PROTO-01**：先定小规模目录性能协议，统一工作负载、复制/catalog 成本、重复、统计、重置和资源停止条件，再决定 DIR-01。真实类别缺口继续单列，不阻塞语义明确的时间视图诊断，也不能据此宣称全论文完成。
