# SCALE-PREP-01：隔离纯目录准入

这是新规模的软件准入入口，直接链接原核心和C++独立集合判定器，不改动旧10k实验。协议见`../../notes/scale-prep-protocol-20261027.md`，最终有效记录见`../../notes/scale-prep-20261027-02/record.md`；首次监控间隔偏差及修正保留于`../../notes/scale-prep-20261027-01/record.md`。

- `generate.py`：对冻结的`wiki_experiment/directory.cpp`执行11项严格匹配替换；生成源和替换清单存于独立构建目录。只放开N/全局ID合同、测试父目录和预算计时；API区间、全部集合检查和10000次时钟校准保留。二进制只接受run=0、warmups=0、repeats=1、label=admission，拒绝正式矩阵。
- `prepare.py`：只读元数据，生成ARXIV/WIKI各5k与25k绑定及固定查询/连续维护。没有NumPy、向量、qrels或ANN依赖。
- `source_check.py`：独立重新扫描两个固定hash的源，逐条复核新样本ID/路径。WIKI解析方式不同于prepare，且完整hash约束源格式。
- `verify.py`：独立路径元组/集合判定器，检查样本、选择规则、维护合法性、全部输出格位、五状态候选摘要、目录/条目/bitmap数量和Release/ASan一致性。原生驱动另执行每次完整集合比较。查询摘要不代替原生完整集合比较；portable bytes不等于物理堆。
- `pipeline.py`：串行资源门禁、两构建、6项指定失败原因测试、6个数据worker、4次独立核验和预算场景。拒绝覆盖证据目录；失败保留，不自动重试或放宽预算。依赖已有Python/psutil和已安装MSVC/CMake/Ninja，不安装依赖。
- `monitor_recheck.py`：首次监控修正的定向检查，复用已有输出、不执行数据worker。监控按100ms整循环目标调度，记录实际最大间隔；未来系统调度仍可能造成偏差，最终准入必须检查实际≤250ms，不能只检查sleep参数。

在项目根目录用已安装解释器运行，必须指定**新的**输出目录：

```powershell
D:/anaconda3/python.exe -B code/scale_directory/pipeline.py notes/<新的准入目录>
```

此命令属于受资源约束的新数据准入，不应为查看历史结果而重复执行。正式5进程、3预热20测量需要后续获批协议和单独入口；本入口不执行SCALE-02。原始WIKI查询约束缺口、nDCG与原版平台差异不因此解决。
