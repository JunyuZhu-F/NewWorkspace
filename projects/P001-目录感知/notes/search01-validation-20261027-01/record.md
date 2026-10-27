# SEARCH-01：时间小数据 exact/IVF 检索准入

**已验证：当前时间/独立IVF分支准入完成。** 最终入口为 `final-status.json`、`verification.json` 和 `recovery-01/status.json`。根 `run-status.json` 保留第一次启动失败，不是最终状态。这里是正确性准入，不是SEARCH-02性能实验，不分配新EXP编号。

## 范围、代码和输入

2026-10-27用户指定先执行SEARCH-01，在小数据上打通检索链路。已读适用规则、STATE/TASK/PLAN相关依赖、材料缺口、数据审计/loader核对、PDF第9页本地文本及目录API/CMake/构建入口。

开始时Git main，HEAD `6a66c9e06a5ac8b08724b36a0f4523edf649d71c`，工作树干净；旧STATE的37981aa/未提交描述已过时，按现场修正。本轮未提交、推送、重置或清理。

新增 `code/search/` 和 `code/scripts/build-search.cmd`，不改旧目录核心、第三方库、30文件COST冻结内容或004/005结果。独立CMake入口复用相同directory_core，单独构建Release/ASan；三方案共用同一只读向量矩阵、训练后后端和参数。科学协议 `../search01-protocol-20261027.md` SHA-256为 `0c55425189553c2b3bc9a2d4843a4cb538287984f6548a7deb6a60dbf6b315ee`。

- 固定旧样本ID0..9999，corpus读取41,000,000字节，每条1024D/有限值验证；ID到向量行号是项目明确采用的映射，不证明每条embedding的内容语义。
- 完整验证1000条混合查询向量（4,100,000字节），预设选择16个真实query_id。query_id与向量行号对应是适配约定，不宣称恢复作者生成脚本。原始读区域独立重新hash/比对，size/mtime未变；未加载全量corpus。
- 16原始time约束×两种模式=32case；query_id0真实向量配34个样本目录+空/不存在目录×两种模式=72个项目诊断case。选样不看答案；详情fixture/cases.json、manifest.json。
- 原始float32，不归一化，double平方L2，同分ID升序，k100。独立NumPy在子集内过滤后穷举真值，不使用发布的全库GT。空GT记null并排除宏平均。
- 独立IVF-Flat：16中心、mt19937种子42、8次Lloyd，nprobe1/4/16；exact编码probes0。原型迭代允许ID并检查分区再评分，尚非优化倒排列表遍历，未来计时必须注明。不是Viking或作者IVF。

## 实际命令和失败恢复

工作目录为项目根：

```powershell
.\code\scripts\build-search.cmd
python code/search/prepare.py --project . --output notes/search01-validation-20261027-01/fixture
python code/search/validate.py --output notes/search01-validation-20261027-01 --resume-prepared
python code/search/validate.py --output notes/search01-validation-20261027-01 --recover-asan-launch
```

前两项日志build-release.log、prepare.log均退出0。首次驱动2026-10-27 10:41:12+08开始：ASan构建/契约成功、Release数据成功；ASan数据进程启动退出3221225781（0xC0000135），日志0字节，未进入main/创建ASan结果目录。真实命令和退出码见commands.jsonl，失败run-status.json保留。

已核实MSVC目录存在clang_rt.asan_dynamic-x86_64.dll。修复只从CMakeCache获取编译器目录并追加到ASan子进程PATH，不改全局环境或协议。旧驱动source/保留，修复版另存recovery-01/validate.py；后端、适配器、判定器不变。

恢复10:43:07–10:45:55+08，只补做ASan数据和独立核验，均退出0。原Release未重跑，三个输出hash保持不变。recovery-01/status.json有实际命令/环境路径/时间/二进制hash。以上为验证进程时间，**不是查询延迟**。

## 结果与证据

- Release/ASan各1/1契约通过：同分/重复向量、k0、少于k、空范围、先过滤后top-k、非法ID/重复候选/NaN/探测越界、路径段边界、三目录MOVE/MERGE后稳定向量ID。
- 每构建312条scope、1248条结果（104case×3策略×4配置）；两构建共2496条均与独立判定一致。无重复、越界或范围外返回。两构建model/scopes/results三个文件分别字节hash一致。
- 共20000条最终分区归属独立检查通过，探测分区/候选内排名/距离独立重算；没有独立重写整个Lloyd训练循环，不扩大声明。
- 104case：64非空、40空。**32原始约束case全部为空，Recall宏平均为null，不能报1**。72诊断case中64非空、8空。

| 配置 | 诊断64个非空case宏平均Recall@100 |
|---|---:|
| exact | 1.000000 |
| IVF nprobe1 | 0.126397 |
| IVF nprobe4 | 0.455629 |
| IVF nprobe16 | 1.000000 |

三目录方案相同，低召回保留，不调参迎合。这64case共用query_id0、目录范围可能重叠，不是64条独立自然查询；不作置信区间/论文质量曲线或代表性结论。

source-hashes.json/source为初始源码；recovery-01为启动修复；source-final-hashes.json为最终可重跑入口和新增README；environment.json含编译缓存/flags/运行时hash；fixture/release/asan为输入和原始结果，verification.json/verification-truth.json为独立核验/子集GT。大派生fvecs本地保留，.gitignore避免误提交，可由只读原数据重建。失败证据不删除。

## 下一步与未解决边界

下一项SEARCH-02当前IVF分支：冻结能覆盖非空检索、含多条真实查询的小规模工作负载和同后端总延迟计时协议，再运行质量—总延迟对照。32个空原始约束不能用来宣称高召回。若改跨年份小样本/后端遍历，另存输入和协议版本，保留本次结果。不先跳全量SCALE，不追查1995年。

PG/Viking原设置、作者距离确认、真实类别直接归属、WIKI约束/nDCG仍缺，整体OBJ-04和全文复现未完成。本轮未启动SEARCH-02正式性能矩阵、全量加载或embedding训练。
