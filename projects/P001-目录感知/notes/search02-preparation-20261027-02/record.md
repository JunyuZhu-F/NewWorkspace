# SEARCH-02 新输入准入

状态passed，正式测量不在此目录。命令与时间commands.jsonl，源码source/source-hashes.json，生成片段与旧SEARCH-01前缀逐字节一致；旧目录/core和SEARCH-01冻结文件hash均未变。状态status.json，独立验证verification.json。

命令：`python code/search02/pipeline.py --stage prepare --preparation notes/search02-preparation-20261027-02 --reuse-fixture notes/search02-preparation-20261027-01/fixture`。复用首次准备的有效输入，不回改协议或失败记录。

Release/ASan各契约1/1；各数据准入12024条结果，合计24048条与独立Python候选/子集真值/IVF探测/排名/距离/global-dense行映射完全一致，模型与结果跨构建一致。每种构建都有3006条候选记录；最终中心对应分区归属独立检查10000条。

全部501个真实time查询两模式：501递归非空、235月份非递归非空、266年份非递归为空。原始输入读区域重新比对，源文件size/mtime保持，未使用发布全库GT。不为准入计时填论文成绩，后续正式矩阵登记为EXP-20261027-006。

figure-source-preflight.json记录首次绘图静态检查：无实际图输出，低DPI误报来自校验器将末尾figures=2误匹配为res=2。修改日志键名后v2检查20PASS/1WARN/0FAIL；剩余WARN为报告图127mm而非默认89/183mm，当前无指定投稿期刊，记录自定义尺寸依据，不假称投稿规范验收。
