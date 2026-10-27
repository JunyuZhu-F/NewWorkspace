# DIR-01 实测结果

仅适用于本项目 Windows 单父目录诊断工作负载，不是作者原始负载或原版数值复现。

210/210 进程成功；独立核对矩阵、23 次迭代、源码/输入/协议哈希及汇总均值和 nearest-rank 分位数通过。

下表只使用默认核心，3 次预热已排除。时间单位为微秒；均值来自原始测量，未减计时开销。

| 输入/操作 | PE-ONLINE 均值 | PE-OFFLINE 均值 | TrieHI 均值 | 每方案 N |
|---|---:|---:|---:|---:|
| figure2 build | 18.4000 | 20.7140 | 11.7500 | 100 |
| figure2 DSQ recursive | 3.1697 | 1.9427 | 1.7859 | 1100 |
| figure2 DSQ nonrecursive | 1.7010 | 3.9460 | 2.5137 | 1100 |
| figure2 move accepted | 6.0960 | 7.9750 | 1.5400 | 100 |
| figure2 merge accepted | 4.1200 | 5.2870 | 2.0530 | 100 |
| time build | 7085.1290 | 9494.2390 | 4748.6720 | 100 |
| time DSQ recursive | 6.5276 | 2.6992 | 2.7203 | 3400 |
| time DSQ nonrecursive | 2.4195 | 5.4386 | 5.4071 | 3400 |
| time move accepted | 6.4590 | 13.8530 | 6.9070 | 100 |
| time merge accepted | 207.2880 | 191.2200 | 162.5300 | 100 |
| time move rejected | 21.3480 | 20.7770 | 19.5040 | 100 |

DSQ 表为同一输入全部路径的等权合并描述；逐路径分布、各进程均值和 P90/P95/P99/P99.9 见 summary.json。重复 sweep 不能当独立实验，小样本 P99.9 不稳定。

空间包含 Roaring portable bitmap 大小及进程 working set/private/peak，不是完整堆或完整序列化索引大小。catalog 已包含在公开维护总延迟，独立 catalog/阶段耗时未采集，不能据此给出目录净时间。

失败记录 EXP-20261027-001/002/003 保留；正式矩阵只使用修复后的 004，不混入失败或 ASan 数据。

## 当前观测及限制

- time 递归 DSQ：TrieHI 2.7203 µs、PE-OFFLINE 2.6992 µs、PE-ONLINE 6.5276 µs；TrieHI 未优于 PE-OFFLINE 的该组均值。
- time 非递归 DSQ：PE-ONLINE 2.4195 µs，TrieHI 5.4071 µs；未出现 TrieHI 全面占优。
- time 成功 MOVE：PE-ONLINE 6.4590 µs，TrieHI 6.9070 µs；成功 MERGE 则分别为 207.2880 和 162.5300 µs。这是特定操作序列的观测，不能推断所有树形或规模。
- DIR-01 冻结矩阵运行及正确性/完整性验证已完成；OBJ-03 完整成本分解仍缺独立 catalog/目录净耗时及完整逻辑 live bytes，不把矩阵成功等同最终目标验收。

| 初始空间：输入/方案 | 目录数 | catalog 条目 | Roaring portable bytes |
|---|---:|---:|---:|
| figure2/pe_online | 11 | 9 | 178 |
| figure2/pe_offline | 11 | 9 | 220 |
| figure2/trie_hi | 11 | 9 | 220 |
| time/pe_online | 34 | 10000 | 20512 |
| time/pe_offline | 34 | 10000 | 44062 |
| time/trie_hi | 34 | 10000 | 44062 |
