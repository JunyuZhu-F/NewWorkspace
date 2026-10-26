from pathlib import Path
import re,json,difflib
root=Path.cwd(); ev=root/'notes/core-implementation-20261026-01'
changes=json.loads((ev/'documentation-changes.json').read_text(encoding='utf-8'))
def read(name):return (root/name).read_text(encoding='utf-8-sig')
def save(name,content):
 p=root/name;old=read(name);back=ev/'documents-before-final'/name
 if back.exists():raise FileExistsError(str(back))
 back.parent.mkdir(parents=True,exist_ok=True);back.write_bytes(p.read_bytes())
 content=re.sub(r'\n{3,}','\n\n',content).rstrip()+'\n';p.write_text(content,encoding='utf-8')
 changes.append({'path':name,'diff':''.join(difflib.unified_diff(old.splitlines(True),content.splitlines(True),fromfile=name+' before',tofile=name+' after'))})
save('STATE.md','''# STATE.md — 单父目录核心已实现并验证

更新时间：2026-10-26，Asia/Hong_Kong。项目：`D:/NewWorkspace/projects/P001-目录感知`。

## 当前结果与计划位置

用户已授权正式核心实现、审查与小规模正确性验证；本轮已完成三方案 C++17 目录层和独立判定器。**Release 与 AddressSanitizer 各 7/7 测试通过**，覆盖图 2、边界/拒绝操作、四个固定种子各 1,000 混合步骤，以及前 10,000 条 ARXIV 时间视图。三方案集合与判定器零差异，ASan 未报告地址内存错误。

这是单父目录、串行核心的正确性结果；未测论文性能、检索质量或全库规模。测试成功不代表整篇论文复现成功。

- 已完成：既有材料/精读/范围审核、SPEC-TREE-01、DATA-ARXIV-SCOPE-01、DATA-CATEGORY-MEANING-01、DATA-TIME-PILOT-01；本轮新增 ENV-01、ORACLE-01、CORE-01/02/03、CHECK-01、SPEC-TIME-PILOT-01。
- 进行中：DATA-01、SPEC-01 的剩余真实数据与协议核验。
- 材料阻塞：SPEC-ARXIV-CATEGORY-01（真实类别非递归/多归属 DSM）。
- 未开始：PROTO-01、DIR-01、SEARCH、SCALE、REPORT；未运行训练、性能基准或完整实验，未购买资源。

## 恢复工作应先看

| 内容 | 唯一详细记录 |
|---|---|
| 目标、授权及验收 | `TASK.md` |
| 顺序、依赖与状态 | `REPRODUCTION_PLAN.md` |
| 本轮方法映射、审查及验证边界 | `notes/core-review.md` |
| 实现入口/可执行命令 | `code/README.md`、`code/scripts/build-test.cmd` |
| 源码版本/测试原始证据 | `notes/core-implementation-20261026-01/validation-record.json`，快照 SNAP-dd12b2f5ac546566；同目录源码 zip、Release/ASan 构建及 CTest 日志 |
| 语义约定/时间样本序列 | `notes/operation-spec.md` §1–7 |
| 环境/依赖 | `notes/environment.md`、`code/third_party/croaring/LOCK.json` |
| 原文理解/材料缺口 | `notes/paper-card.md`、`notes/materials-and-gaps.md` |
| 只读数据核查 | `notes/data-audit.md`、`notes/category-semantics.md` |

## 尚未解决与影响

1. ARXIV 类别列表祖先/后代同时出现，递归观测不能唯一确定直接归属。时间视图通过不能解除真实类别非递归/维护缺口，不取首类别或静默去祖先。
2. WIKI 原查询目录、作者 DSM 序列缺失；距离/归一化、质量真值与 Viking 配置未完整恢复。不得将项目诊断说成作者工作负载或声明原版数值对齐。
3. 公共 catalog 冲突合并刷新采用扫描，计数单列；PE 用稳定目录对象关联 catalog。后续性能须说明这些工程选择和成本边界。没有微秒延迟、内存对比或加速倍数结论。
4. 不覆盖并发、持久化、内存分配失败回滚、真实多归属；未验证任意深度/全量规模。

## 下一步与资源保护

推荐 **PROTO-01**：先写小规模目录性能协议，明确数据/序列、重置、预热、五次独立进程重复、分段计时/复制/catalog、空间统计和停止上限；本轮不自动执行基准。时间视图可作为项目诊断，真实类别/WIKI 等各自材料前置。

当前 Windows 11、约 15.81 GiB 内存，MSVC/CMake/Ninja 与 CRoaring v5.3.2 可构建；未安装/启动 Linux/WSL，ANN 未接入。大规模运行仍须用户另行决定。

原始 dataset/raw/ 只读；复用冻结 metadata，未读取全量向量。git status 返回 not a git repository；没有 commit，未初始化、提交或推送。源码快照/hash 代替 Git 版本。构建目录含真实二进制，可再生成；不能以文件存在代替日志。

旧状态和本轮文档差异保存在 notes/core-implementation-20261026-01/documents-before-final/、documentation-changes.json（同目录）；交付一致性检查见同目录 handoff-check.json。
''')
s=read('notes/operation-spec.md')
s=s.replace('供后续实现使用。不是三方案实现，不含任何运行结果。','作为当前实现语义规范。源码、审查和运行结果统一见 core-review.md，本笔记保留规则与手工预期，不复制日志。')
s=s.replace('## 7. 已固定的时间目录诊断输入，操作案例待冻结','## 7. SPEC-TIME-PILOT-01：固定时间目录正确性协议')
old='下一步 SPEC-TIME-PILOT-01 只把第 3 节已有单父目录规则落实为这个样本的固定查询锚点、合法 MOVE/MERGE 案例和人工/独立预期；不新增多归属算法。当前尚未执行这些操作，也没有将数据准备写成算法通过。'
assert old in s
s=s.replace(old,'''当前接口在 `../code/include/directory/index.hpp`：ID 为 uint32；insert 只接收 ID 和父目录，向量由外部维护，本轮不装载。query 返回 exists 与独立位图；ErrorCode 明确拒绝行为，重复 ID 检查先于建目录。预条件拒绝保证逻辑状态不变，不保证 bad_alloc 后事务回滚。

以下序列在首轮 pilot 执行前写入固定测试源码；属于项目诊断，不是作者 DSM 序列。初始与每一步后，比较全目录两种 ID 集合、命名空间、catalog 和不变量。数量锚点由固定绑定独立推导；正确性检查逐成员比较，不能只比较数量。

| 阶段 | 固定输入 | 数量锚点及完成条件 |
|---|---|---|
| 初始 | ID 0…9999，34 目录 | 根=10,000；1991=306、1992=3,261、1993=6,433；年/根 Local 空，月份 Local=递归 |
| MOVE | /1992/1/ → 新父 /1991/ | 源 193 条；新 /1991/1/=193，1991=499，1992=3,068；旧月路径不存在，根不变 |
| 接着 MERGE | /1992/7/ → 目标 /1991/7/ | 296 条并入原有 2 条，目标=298；1991=795、1992=2,772；源月路径不存在；34 目录变 33，根不变 |
| 拒绝 | MOVE /1992/8/ → 新父 /1991/ | 已存在同名 8 月（源 226、目标 28）；拒绝，所有绑定/目录/集合保持前一步 |

输入 SHA-256：9aa84f093dfd4e9c4e1633c22ae7a9df424809fee9f45fc22fb96f85c04f36b6；构建脚本只验证并转换此 bindings.jsonl 为 TSV，不重新选样。实际记录见 core-review.md §4–5；当前单父范围已通过，但 SPEC-01 真实类别等余项不关闭。''')
save('notes/operation-spec.md',s)
s=read('notes/environment.md').replace('未下载依赖或大型数据。','初始探针未下载依赖；后续只获取轻量 CRoaring 源码，未下载大型数据。')
s=s[:s.index('## 仍未验证')]+'''## 核心实现环境锁定与实际验证

2026-10-26 后续：ENV-01 已在当前目录核心范围完成。MSVC 实际版本 19.51.36260.0，64 位；C++17/C11，Release 与 RelWithDebInfo-ASan 分目录构建。现有 ASan 运行库可用，没有额外安装系统/工具。

- 依赖：官方 CRoaring v5.3.2 轻量 C/h 与许可证，来源/哈希见 `../code/third_party/croaring/LOCK.json`；C/h 与官方 release digest 对齐。作者版本未给，只是工程固定版本。
- 位图适配用 C API 与项目 RAII；核心、测试、CRoaring 均纳入 ASan 构建。
- 构建入口 `../code/scripts/build-test.cmd` 加载现有 vcvars64 子进程环境，CMake/Ninja 编译并行数 2；配置/编译/CTest 失败均返回非零。时间样本转换先验 hash，不访问向量。
- 实际结果：Release 7/7、RelWithDebInfo-ASan 7/7，退出码均 0；ASan 未报告地址内存错误。命令/审查/日志/快照见 core-review.md §5、core-implementation-20261026-01/validation-record.json。
- 上游 roaring.h:6110 的 C4702 警告已审查并保留，不宣称零警告。

## 尚未完成的环境或实验条件

ANN 未选定/接入；性能计时、全量峰值内存、正式预算未验证。WSL 发行版没有检查，本轮未启动 WSL。Linux/125GB 原文机器与当前 Windows/15.81GiB 不可视为同条件。ENV-01 完成只证明当前核心可构建测试，不解除 DATA/SPEC 或规模审批。
'''
save('notes/environment.md',s)
s=read('README.md')
s=s.replace('当前进行小规模数据核查；没有三方案正式算法实现或性能实验结果。','单父目录三方案已实现并完成审查，Release/ASan 各 7/7 正确性测试通过；尚无性能或 ANN 复现结果。')
s=s.replace('最新检查：[DATA-01 小规模数据核查](notes/data-audit.md)。','最新交付：[核心实现与审查](notes/core-review.md)、[构建和使用入口](code/README.md)。数据边界见 [DATA-01 小规模核查](notes/data-audit.md)。')
s=s[:s.index('## 环境与运行')]+'''## 环境与运行

现有 Windows x64、MSVC/CMake/Ninja，CRoaring v5.3.2 已固定。代码和命令见 [code/README.md](code/README.md)，真实验证、源码快照与原始日志见 [core-review.md](notes/core-review.md)。本轮仅处理目录和 ID，未接入向量搜索。

原始数据在 dataset/raw/，保持只读；前 10,000 条时间视图用于正确性。DATA-01/SPEC-01 的真实类别、WIKI/作者工作负载缺口仍保留，关联 OpenViking 不能直接视为完整原文实验包。

下一任务是 PROTO-01：先写小规模目录性能协议，暂不执行基准。大规模运行由用户以后单独决定。
'''
save('README.md',s)
s=read('EXPERIMENTS.md').replace('## 2. 实验索引','''## 2. 实验索引

2026-10-26 当前没有论文性能/检索实验登记。核心开发正确性测试统一在 notes/core-review.md 与 notes/core-implementation-20261026-01/ 记录，不把 CTest 耗时当论文延迟，不为单元/交叉检查虚构 EXP 结果。
''')
save('EXPERIMENTS.md',s)
s=read('notes/materials-and-gaps.md')
s=s.replace('本轮无正式算法实现、无检索/维护性能实验、无大型数据下载。','初次核验时无正式实现；后续已获授权完成单父目录独立实现/正确性测试，见 core-review.md。仍无检索/维护性能实验或大型数据下载。')
s=s.replace('下方材料清单保留初次阅读覆盖范围；GAP 状态按后续证据更新。','下方材料清单保留初次阅读时的历史现场，不代表当前 code 仍为空；当前状态以 STATE.md/core-review.md 为准。GAP 状态按后续证据更新。')
save('notes/materials-and-gaps.md',s)
(ev/'documentation-changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'updated':[x['path'] for x in changes]},ensure_ascii=True))
