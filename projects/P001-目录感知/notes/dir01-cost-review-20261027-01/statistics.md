# 现有结果的派生统计

只读取 EXP-20261027-004；未运行新基准，未减计时开销。时间单位微秒。

## 默认核心：均值、中位数和五进程均值范围

| 输入/操作 | 方案 | 均值 | 中位数 | run均值范围 | N |
|---|---|---:|---:|---:|---:|
| figure2/nonrecursive | pe_offline | 3.9460 | 2.5000 | 2.7005–7.7268 | 1100 |
| figure2/recursive | pe_offline | 1.9427 | 1.7000 | 1.6800–2.8391 | 1100 |
| figure2/nonrecursive | pe_online | 1.7010 | 1.6000 | 1.6382–1.7645 | 1100 |
| figure2/recursive | pe_online | 3.1697 | 2.5000 | 3.0318–3.3695 | 1100 |
| figure2/nonrecursive | trie_hi | 2.5137 | 2.2000 | 2.3345–2.7977 | 1100 |
| figure2/recursive | trie_hi | 1.7859 | 1.7000 | 1.6845–1.9009 | 1100 |
| time/nonrecursive | pe_offline | 5.4386 | 2.9000 | 5.1093–5.7090 | 3400 |
| time/recursive | pe_offline | 2.6992 | 2.4000 | 2.5135–2.8446 | 3400 |
| time/nonrecursive | pe_online | 2.4195 | 2.2000 | 2.1084–2.6306 | 3400 |
| time/recursive | pe_online | 6.5276 | 2.9000 | 5.7018–7.5001 | 3400 |
| time/nonrecursive | trie_hi | 5.4071 | 2.5000 | 4.5226–7.9537 | 3400 |
| time/recursive | trie_hi | 2.7203 | 2.4000 | 2.6026–2.9994 | 3400 |
| figure2/merge accepted | pe_offline | 5.2870 | 5.1000 | 5.0150–5.7950 | 100 |
| figure2/move accepted | pe_offline | 7.9750 | 7.4000 | 7.1950–9.9300 | 100 |
| figure2/merge accepted | pe_online | 4.1200 | 4.0000 | 3.9800–4.3950 | 100 |
| figure2/move accepted | pe_online | 6.0960 | 5.8000 | 5.6950–7.2150 | 100 |
| figure2/merge accepted | trie_hi | 2.0530 | 1.9000 | 1.7450–2.2350 | 100 |
| figure2/move accepted | trie_hi | 1.5400 | 1.3000 | 1.2450–1.9350 | 100 |
| time/merge accepted | pe_offline | 191.2200 | 160.3000 | 165.2600–257.8150 | 100 |
| time/move rejected | pe_offline | 20.7770 | 20.3000 | 19.9300–23.0450 | 100 |
| time/move accepted | pe_offline | 13.8530 | 13.0000 | 13.4800–14.0700 | 100 |
| time/merge accepted | pe_online | 207.2880 | 152.3000 | 154.0450–308.1750 | 100 |
| time/move rejected | pe_online | 21.3480 | 20.2000 | 19.9450–23.4450 | 100 |
| time/move accepted | pe_online | 6.4590 | 6.2000 | 6.2000–6.8100 | 100 |
| time/merge accepted | trie_hi | 162.5300 | 149.5000 | 145.5050–179.6500 | 100 |
| time/move rejected | trie_hi | 19.5040 | 18.9000 | 18.9600–20.2250 | 100 |
| time/move accepted | trie_hi | 6.9070 | 6.6000 | 6.3950–7.2300 | 100 |
| figure2/build | pe_offline | 20.7140 | 19.9000 | 19.3400–23.2500 | 100 |
| figure2/build | pe_online | 18.4000 | 16.8000 | 16.5250–19.6800 | 100 |
| figure2/build | trie_hi | 11.7500 | 10.3000 | 9.3200–16.4300 | 100 |
| time/build | pe_offline | 9494.2390 | 9001.6000 | 8984.1350–10254.3150 | 100 |
| time/build | pe_online | 7085.1290 | 6176.8000 | 6511.3450–8002.8750 | 100 |
| time/build | trie_hi | 4748.6720 | 4200.5000 | 4138.4900–5568.1350 | 100 |

## 插桩维护计数（不是耗时）

| 输入/操作 | 方案 | 源目录数 | 源条目 | 路径重映射 | 子树重挂 | 协调节点 | catalog扫描 |
|---|---|---:|---:|---:|---:|---:|---:|
| figure2/move/accepted | pe_online | 2 | 2 | 2 | 0 | 0 | 0 |
| figure2/merge/accepted | pe_online | 2 | 2 | 2 | 0 | 2 | 18 |
| figure2/move/accepted | pe_offline | 2 | 2 | 2 | 0 | 0 | 0 |
| figure2/merge/accepted | pe_offline | 2 | 2 | 2 | 0 | 2 | 18 |
| figure2/move/accepted | trie_hi | 2 | 2 | 0 | 1 | 0 | 0 |
| figure2/merge/accepted | trie_hi | 2 | 2 | 0 | 0 | 2 | 18 |
| time/move/accepted | pe_online | 1 | 193 | 1 | 0 | 0 | 0 |
| time/merge/accepted | pe_online | 1 | 296 | 1 | 0 | 1 | 10000 |
| time/move/rejected | pe_online | 1 | 226 | 0 | 0 | 0 | 0 |
| time/move/accepted | pe_offline | 1 | 193 | 1 | 0 | 0 | 0 |
| time/merge/accepted | pe_offline | 1 | 296 | 1 | 0 | 1 | 10000 |
| time/move/rejected | pe_offline | 1 | 226 | 0 | 0 | 0 | 0 |
| time/move/accepted | trie_hi | 1 | 193 | 0 | 1 | 0 | 0 |
| time/merge/accepted | trie_hi | 1 | 296 | 0 | 0 | 1 | 10000 |
| time/move/rejected | trie_hi | 1 | 226 | 0 | 0 | 0 | 0 |

## 时间视图：根、年份、月份的默认查询均值

| 路径/模式 | 方案 | 候选量 | 直接孩子 | 均值 | run均值范围 |
|---|---|---:|---:|---:|---:|
| //nonrecursive | pe_offline | 0 | 3 | 25.8810 | 21.8450–34.2450 |
| //recursive | pe_offline | 10000 | 3 | 3.1760 | 2.7550–3.8000 |
| /1992//nonrecursive | pe_offline | 0 | 12 | 27.9250 | 23.1600–32.6200 |
| /1992//recursive | pe_offline | 3261 | 12 | 3.4420 | 2.9950–4.1300 |
| /1992/1//nonrecursive | pe_offline | 193 | 0 | 3.0230 | 2.8550–3.1850 |
| /1992/1//recursive | pe_offline | 193 | 0 | 2.7810 | 2.5200–2.9900 |
| //nonrecursive | pe_online | 0 | 3 | 1.2290 | 1.1600–1.3050 |
| //recursive | pe_online | 10000 | 3 | 47.4120 | 45.9150–48.9700 |
| /1992//nonrecursive | pe_online | 0 | 12 | 1.6380 | 1.5450–1.8900 |
| /1992//recursive | pe_online | 3261 | 12 | 27.8360 | 25.2700–30.5700 |
| /1992/1//nonrecursive | pe_online | 193 | 0 | 2.6930 | 2.2750–3.4650 |
| /1992/1//recursive | pe_online | 193 | 0 | 3.2850 | 3.0550–3.5300 |
| //nonrecursive | trie_hi | 0 | 3 | 27.6020 | 17.7300–44.6650 |
| //recursive | trie_hi | 10000 | 3 | 2.8710 | 2.2200–3.6700 |
| /1992//nonrecursive | trie_hi | 0 | 12 | 24.3970 | 20.9150–26.5350 |
| /1992//recursive | trie_hi | 3261 | 12 | 5.3330 | 2.9500–8.8050 |
| /1992/1//nonrecursive | trie_hi | 193 | 0 | 4.2110 | 2.6800–8.1050 |
| /1992/1//recursive | trie_hi | 193 | 0 | 2.8630 | 2.5700–3.4800 |

## 时间视图：全部内部目录/叶目录分层

| 方案 | 递归 | 内部目录 | N | 均值(微秒) |
|---|---|---|---:|---:|
| pe_online | True | True | 400 | 28.0968 |
| pe_online | True | False | 3000 | 3.6517 |
| pe_online | False | True | 400 | 1.5653 |
| pe_online | False | False | 3000 | 2.5334 |
| pe_offline | True | True | 400 | 3.2277 |
| pe_offline | True | False | 3000 | 2.6288 |
| pe_offline | False | True | 400 | 23.7125 |
| pe_offline | False | False | 3000 | 3.0021 |
| trie_hi | True | True | 400 | 3.5740 |
| trie_hi | True | False | 3000 | 2.6065 |
| trie_hi | False | True | 400 | 22.4982 |
| trie_hi | False | False | 3000 | 3.1283 |

## 逐路径均值比较（描述性，不作显著性推断）

- figure2 recursive=True：TrieHI 对 pe_online 均值更低的路径为 11/11。
- figure2 recursive=True：TrieHI 对 pe_offline 均值更低的路径为 6/11。
- figure2 recursive=False：TrieHI 对 pe_online 均值更低的路径为 0/11。
- figure2 recursive=False：TrieHI 对 pe_offline 均值更低的路径为 11/11。
- time recursive=True：TrieHI 对 pe_online 均值更低的路径为 31/34。
- time recursive=True：TrieHI 对 pe_offline 均值更低的路径为 18/34。
- time recursive=False：TrieHI 对 pe_online 均值更低的路径为 11/34。
- time recursive=False：TrieHI 对 pe_offline 均值更低的路径为 30/34。
