# 正式入口首次准备：收尾比对错误，保留失败

实际状态见overall-status.json：failed；009/010正式单元均未启动。Release/ASan构建、四项指定原因合同、真实deadline杀子进程、ARXIV run0..4双pass、WIKI Release/ASan run1双pass与两份独立核验均通过。

收尾误用整文件SHA比较新WIKI run1与旧准入run0的answers.tsv；run1按协议轮换策略输出，行顺序自然变化，不能据此判定答案不一致。ordering-audit.json逐行规范化复核ARXIV300行、WIKI780行：无重复、内容完全相同，只有WIKI行顺序不同。不是算法/数据错误。

修正仅限新编排器的答案比较与恢复入口，按策略/stage/case/答案内容比较。原二进制、生成源、判定器及7个原生入口worker保持；源快照/失败/日志不覆盖。恢复02被Windows路径保护误拒绝，最终03复用已验证worker和二进制，重新独立核验，不重编译/重跑原生入口，不重试任何正式实验。当前代码与本次源码归档的pipeline.py会不同，原归档用于忠实记录失败版本。
