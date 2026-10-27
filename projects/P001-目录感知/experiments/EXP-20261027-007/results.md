# WIKI独立小规模目录性能结果

真实WIKI 10000条样本，项目生成查询/连续维护，不是作者原始工作负载。默认/phase各5独立进程×20测量pass，预热排除。下表为默认API平均值，未扣catalog或探针开销。

| 操作 | PE-ONLINE μs | PE-OFFLINE μs | TrieHI μs |
|---|---:|---:|---:|
| 构建 | 139305.5060 | 199090.2470 | 55409.8690 |
| 递归DSQ | 1426.5076 | 2.0166 | 1.8258 |
| 非递归DSQ | 3.3797 | 25.6666 | 18.4308 |
| MOVE大子树 | 34273.8310 | 34593.8660 | 15.8720 |
| MERGE大子树 | 31356.3720 | 31694.6920 | 406.5670 |
| MOVE深末端 | 20.7790 | 51.8420 | 11.1660 |
| MERGE深末端 | 355.4560 | 248.2960 | 371.2900 |

全部均值/nearest-rank P90/P95/P99/P99.9及各阶段在analysis-01/statistics.csv，逐进程统计在verification文件，原始重复值在run-*/timings.tsv。查询按58case等权，包含空范围；目录深度/候选量/fanout见冻结fixture的directory-cases.json，4项维护规模见operations.csv。

phase直接catalog值只解释相应诊断构建，不从默认时间中相减；未观测区间不补造。portable.csv仅Roaring portable字节，不是完整索引大小、物理堆或进程独占；catalog为10000条的公共映射，时间由phase直接记录。每个pass重新构建索引，查询及连续维护共享该pass缓存状态，正确性判定在计时外仍可能影响缓存。

有限小样本和固定4操作不能证明一般加速；全部反例保留。未控制背景负载，不做显著性或尾部稳定性声明。独立统计/全部计时格位/全部候选状态由verification-directory-*.json验证。
