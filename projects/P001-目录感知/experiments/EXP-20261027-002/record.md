# EXP-20261027-002 — DIR-01 环境采集失败

- 状态：失败，测量进程 0；不生成性能结论。
- 日期：2026-10-27，Asia/Hong_Kong。
- 命令：`python code/scripts/run-dir01.py --project . --experiment-id EXP-20261027-002`，退出码 1。
- 源码：`source/hashes.json`；配置及协议：config.json、protocol.md。
- 原始错误：powercfg 子进程读取线程按 gbk 解码失败：`UnicodeDecodeError: 'gbk' codec can't decode byte 0xa1 in position 10: illegal multibyte sequence`；随后 `.stdout.strip()` 抛出 `AttributeError: 'NoneType' object has no attribute 'strip'`。
- 发生于环境采集、矩阵启动及状态 try/finally 之前；本记录根据实际 traceback 手工补记。source/ 快照与其他已有产物保留。
- 修复：powercfg 使用二进制捕获，UTF-8 加反斜杠转义展示，并保存 stdout/stderr 原始十六进制字节及退出码。未修改算法、输入或测量协议。
- 后续：新编号 EXP-20261027-003 重试。
