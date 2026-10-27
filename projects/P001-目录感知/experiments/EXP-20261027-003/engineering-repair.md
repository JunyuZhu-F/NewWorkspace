# 首个正式进程失败与工程修复

- 原运行器记录见 record.md、run-status.json、run-order.jsonl 和 logs/job-00.log；退出码 1。
- 首个进程（figure2/build/pe_online/default）未能读取 `figure2-build-operations.tsv`，尚未进入计时/测量循环。冻结输入实际使用 `figure2-operations.tsv`，build/dsq 为初始状态别名；准备自检只使用 base 名称，遗漏了正式入口别名。
- 修复边界：benchmark.cpp 的 load_fixture 将 `<base>-build`/`<base>-dsq` 的 operation 文件映射到 `<base>-operations.tsv`；不生成新输入，不修改原始文件或测量循环。self_test 增加 figure2/time 的 build/dsq 别名加载和全状态 oracle 检查。
- 运行器另有两处已保留的启动失败：001 的快照目录缺失，002 的 powercfg 解码失败；详见各自 record.md。
- 仅修改基准文件解析/自检与运行器环境采集，不修改 code/src/、目录核心、第三方依赖、冻结协议、输入及重复矩阵。
- 修复后准入命令：`code/scripts/build-test.cmd Release`、`code/scripts/build-test.cmd RelWithDebInfo asan`；真实日志为 repair-release.log、repair-asan.log。退出状态待两命令实际结束后统一记录，不以文件存在声称通过。
- 后续正式实验使用 EXP-20261027-004，不覆盖本次失败。
