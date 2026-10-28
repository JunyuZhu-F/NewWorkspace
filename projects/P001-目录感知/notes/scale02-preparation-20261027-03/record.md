# SCALE-02正式入口与恢复记录

**最终状态：已验证通过，009/010各5/5正式完成。** 总体事实见overall-status.json与final-review.json；真实恢复命令见orchestration-command.json。此处不复制正式结果正文，WIKI见../../experiments/EXP-20261027-009/record.md，ARXIV见010对应记录。

## 准入与恢复

- 初次01完成Release/ASan构建、ARXIV全部run0..4双pass、WIKI run1 Release/ASan双pass，共7个原生worker；两份独立Oracle、策略轮换、全部重复格位、跨构建答案/portable及四项指定错误原因合同通过。真实0.25秒单元截止测试终止了10秒sleep子进程，没有遗留子进程。不是原核心或旧正式实验重跑。
- 01收尾错误：用整文件SHA比较WIKI run1与旧run0，行顺序不同被误拒绝；ordering-audit逐行证明780个答案内容完全相同。02恢复的保护检查又误用正斜线字符串排除Windows反斜线清单中的pipeline.py，被保护拒绝。两次failed及原源码快照/日志均保留，不把failed改成passed。
- 修复仅限新编排器：答案按完整字段规范化比较并禁止重复、源码例外以Path.resolve身份判断。核对当前与01清单唯一差异为该编排器；所有原生源/二进制、core、guard和独立Oracle不变。
- 03复用01的7个原生worker及实际exe/flags/生成源，重新独立核验两组输出、核对既有5k答案并再验证截止保护；0原生worker重复。复用来源/原始hash见reuse-provenance.json。03的status表示准备通过，overall-status才表示正式总体状态。

## 正式执行和审查

按冻结协议先WIKI009后ARXIV010，各25000条、5独立子进程串行、每策略3预热20测量；没有正式失败/重试、减重复、换样或预算放宽。两单元分别895.606秒与151.523秒，均包含6个20秒启动门禁和独立核验/CSV分析。

合计31740原始计时（正式27600、预热4140），141450次原生完整集合核对；五状态树/catalog/bitmap/invariants、Python独立路径元组Oracle、全部run/pass/space/wall格位、跨进程答案/portable和轮换通过。50个worker文件、CSV、协议/fixture、15项当前入口源及53项旧源和实际归档exe全部重新核hash，见final-review与各review-check。

源快照记录运行时版本；旧53源码在正式前冻结hash并在后审查重核、归档，无核心/第三方/旧004–008结果修改。没有读取向量/qrels，没有ANN/nDCG或原作者目录约束恢复。Git main/2101c84f24b3cbbcd093b38073a5c9e372815f9d；本轮保留未提交修改，不提交/推送/重置/清理。最终检查无活动worker。

各正式record包含五进程均值SD、完整CSV及解释边界。独立case权重、空范围、深路径/维护几何与旧10k不同，不能直接当严格规模增长率，不能据此关闭全文目标。后续建议将当前25k结果纳入逐目标报告并审核与旧结果的可比性；不自动更大N或扩到检索。
