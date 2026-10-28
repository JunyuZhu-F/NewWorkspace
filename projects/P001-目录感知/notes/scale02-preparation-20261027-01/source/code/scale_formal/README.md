# SCALE-02：25k纯目录正式入口

仅执行用户已批准的两数据集25k、各5独立进程、每策略3预热20测量；WIKI优先，进程串行。协议`../../notes/scale02-protocol-20261027.md`；入口检查证据`../../notes/scale02-preparation-20261027-01/`；正式记录009（WIKI）/010（ARXIV）。无ANN/向量/qrels、无phase/allocation，原核心和旧入口不改。

项目根执行已安装解释器：

```powershell
D:/anaconda3/python.exe -B code/scale_formal/pipeline.py
```

该命令拒绝覆盖固定证据目录/实验编号。不要为查看结果重复执行。中断/失败保留现场，不自动重试；需要继续时先查overall-status、单元status、commands和原始日志，不擅自删除重开。

- generate：复用冻结准入生成器，额外2项替换处理正式迭代合同和label/N绑定；13项清单可审查。API计时和完整集合判定保持。
- verify：复用独立元组路径Oracle，额外核对全部run/pass/warmup/策略轮换/space和wall格位，导出逐case/逐进程CSV及5进程均值SD。不把内部重复当独立样本。
- guard：100ms整循环目标，保存实际间隔并要求≤250ms；运行private≤2GiB/available≥2GiB、600秒单命令、1800秒单元（含6个启动门禁和核验）。门禁失败即停止，样本仍不是精确峰值或OS配额。

正式前只对新增轮换/重复适配做5k双pass入口检查及WIKI跨Release/ASan核验，保留已有正确性证据。正式结果只统计pass3..22，旧10k与新25k的输入/查询不同，不直接宣称严格增长率；作者查询目录协议、nDCG和全文目标仍未解决。
