# EXP-20261027-001 — DIR-01 启动失败

- 状态：失败，未开始任何测量进程；不生成性能结论。
- 日期：2026-10-27，Asia/Hong_Kong。
- 命令：`python code/scripts/run-dir01.py --project . --experiment-id EXP-20261027-001`，退出码 1。
- 基线：Git 37981aa4b187d69aa8ca8c56bbb068fe068de00d，SNAP-0b110bb7dee8280f；启动前 32 个清单文件哈希匹配，Release 增量构建返回 `ninja: no work to do.`，退出码 0。
- 失败位置：`code/scripts/run-dir01.py` 的 `copy_source`，创建了 source/ 却未创建 source/code/，首次复制 code/.gitignore 时抛出 FileNotFoundError。该步骤位于矩阵调度及运行状态 try/finally 之前，所以未生成运行器的 run-status.json；本记录如实补记。
- 错误：`FileNotFoundError: [Errno 2] No such file or directory: .../experiments/EXP-20261027-001/source/code/.gitignore`。
- 已有产物：protocol.md、raw/、logs/、source/；不覆盖或删除。
- 修复：只将快照目标创建改为 `(dest/'code').mkdir(parents=True)`；不修改算法、输入、计时或统计协议。
- 后续：新编号 EXP-20261027-002 重试，原失败保留。
