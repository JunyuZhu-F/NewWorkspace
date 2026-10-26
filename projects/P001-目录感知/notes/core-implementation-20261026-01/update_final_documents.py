from pathlib import Path
import json, re, difflib
root=Path.cwd(); ev=root/'notes/core-implementation-20261026-01'
before_dir=ev/'documents-before-final'; before_dir.mkdir(exist_ok=True)
changes=[]
def save(name,content):
 p=root/name; old=p.read_text(encoding='utf-8-sig') if p.exists() else ''
 if p.exists():
  backup=before_dir/name; backup.parent.mkdir(parents=True,exist_ok=True)
  if backup.exists(): raise FileExistsError(str(backup))
  backup.write_bytes(p.read_bytes())
 content=re.sub(r'\n{3,}','\n\n',content).rstrip()+'\n'
 p.write_text(content,encoding='utf-8')
 changes.append({'path':name,'diff':''.join(difflib.unified_diff(old.splitlines(True),content.splitlines(True),fromfile=name+' before',tofile=name+' after'))})
def read(name): return (root/name).read_text(encoding='utf-8-sig')
def replace(text,old,new):
 if old not in text: raise ValueError('Missing replacement: '+old[:100])
 return text.replace(old,new)
s=read('TASK.md')
s=replace(s,'用户说明未提供源码；本地 `code/` 为空。','用户说明未提供源码；本地 `code/` 现为本项目独立实现（不是作者源码），审查和快照见 `notes/core-review.md`。')
s=replace(s,'下一份诊断输入固定为','已冻结的诊断输入为')
s=replace(s,'Roaring 和 ANN 后端未锁定；未安装/启动 Linux/WSL。','CRoaring 已锁定 v5.3.2 并通过普通/ASan 构建，作者使用版本未知；ANN 后端未选定，未安装/启动 Linux/WSL。')
s=replace(s,'本轮交付：`notes/paper-card.md`、`notes/materials-and-gaps.md`、材料支撑文件，以及本文件、计划和状态。后续交付实现/测试/配置、方法到源码对应表、协议说明、真实实验记录和验收报告；路径届时建立，不提前伪造运行入口。','当前交付包括精读/材料笔记、`code/` 单父目录三方案与独立判定器、`notes/core-review.md` 方法到源码对应表及审查记录、源码快照与两套正确性日志，以及目标、计划和状态。已通过的范围仅限该正确性分支；目录性能、ANN 与最终论文结果验收尚未执行。运行入口见 `code/README.md`。')
s+='\n2026-10-26（核心交付）：单父目录三方案、独立判定器和 10,000 条时间视图正确性验证完成；Release 与 AddressSanitizer 各 7/7。OBJ-02 仅在当前合法域获得证据，真实多类别缺口不关闭；OBJ-03/04 仍未执行。证据统一见 notes/core-review.md，不把测试耗时当性能结果。\n'
save('TASK.md',s)
s=read('REPRODUCTION_PLAN.md')
updates={
'SPEC-TIME-PILOT-01':('已完成','已固定 10,000 条时间视图全目录查询及 MOVE→MERGE→名称冲突拒绝序列；独立判定器逐阶段零差异。仅项目正确性协议，非作者工作负载；见 operation-spec.md §7、core-review.md。'),
'SPEC-01':('进行中','单父目录/时间小样本协议已落实并验证；真实类别非递归、多归属维护及 WIKI/作者工作负载仍有缺口。未将全部协议标为完成。'),
'ENV-01':('已完成','当前核心 MSVC/CMake/Ninja、CRoaring v5.3.2 来源/哈希及离线构建入口已固定；Release/ASan 构建测试通过。仅本机目录层，不含 ANN/大规模资源；见 environment.md、core-review.md。'),
'ORACLE-01':('已完成','独立 std::set 目录/ID→path 判定器，独立解析与全枚举，不调用生产路径助手或 posting/Trie；图 2 手工预期及逐步交叉验证通过；见 tests/oracle.*、core-review.md。'),
'CORE-01':('已完成','单父目录 PE-ONLINE：直接 posting、路径枚举及重映射；与判定器零差异。快照 SNAP-dd12b2f5ac546566，见 core-review.md；不代表性能通过。'),
'CORE-02':('已完成','单父目录 PE-OFFLINE：祖先物化、非递归子集合差、路径重映射及独有祖先更新通过；无 Local 查询缓存。证据同 CORE-01。'),
'CORE-03':('已完成','单父目录 TrieHI：Inc、parent/children、catalog 一致；MOVE 保留后代身份且无路径键重映射；MERGE 保留源根条目并协调冲突。证据同 CORE-01。'),
'CHECK-01':('已完成','当前单父目录范围：图 2/边界/拒绝操作、4 固定种子各 1,000 混合步骤、10,000 条时间样本与判定器一致；Release/ASan 各 7/7。日志/快照见 core-review.md；不覆盖真实多类别或并发。')}
lines=[]
for line in s.splitlines():
 cells=[x.strip() for x in line.split('|')]
 if len(cells)>=7 and cells[1] in updates:
  cells[4],cells[5]=updates[cells[1]]; line='| '+' | '.join(cells[1:6])+' |'
 if len(cells)>=7 and cells[1]=='SPEC-TREE-01': line=line.replace('仅书面验收，未运行算法。','已由 CHECK-01 核验当前实现；原文/项目约定的区别仍保留。')
 if len(cells)>=7 and cells[1]=='PROTO-01':
  cells[3]='CHECK-01、ENV-01；采用数据对应的 DATA/SPEC 子任务'
  cells[5]='先为已验证时间视图/人工树冻结小规模目录协议；统一计时、复制/catalog 扫描、重置/预热、重复/统计及资源上限。真实类别/WIKI 等各自前置，不强制等待全部 DATA/SPEC。预期 notes/benchmark-protocol.md；尚未制定或运行。'
  line='| '+' | '.join(cells[1:6])+' |'
 lines.append(line)
s='\n'.join(lines)
s=s.replace('进入 ENV-01 → ORACLE-01 → CORE-01/02/03。','ENV-01 → ORACLE-01 → CORE-01/02/03 → CHECK-01 已在单父目录正确性范围完成（见 notes/core-review.md）。')
a=s.index('### 当前主线与辅助工作'); b=s.index('## 3.',a)
s=s[:a]+'''### 当前主线与剩余前置

正式实现分支 ENV-01 → ORACLE-01 → CORE-01/02/03 → CHECK-01 已完成，包含人工树和固定时间小样本。审查、真实日志与源码快照统一见 `notes/core-review.md`。

- DATA-01、SPEC-01 继续进行中：全库审计、真实类别直接归属、两套真值协议、WIKI 查询目录与作者 DSM 工作负载没有因核心测试通过而解决。
- SPEC-ARXIV-CATEGORY-01 继续材料阻塞；不得将类别列表直接解释为 Local，或修改基线凑结果。
- 下一主线是 PROTO-01：先为明确语义的时间视图/人工树写清小规模性能测量方法，暂不运行基准。未明确真实工作负载不阻塞这份有边界的项目协议。
- DIR-01 仍未开始。输入、资源与计时协议冻结后才可执行；完整规模和云资源仍需单独决定。原文质量对照继续受对应 DATA/SPEC/SEARCH 前置约束。

'''+s[b:]
a=s.index('## 7.');b=s.index('## 8.',a)
s=s[:a]+'''## 7. 当前停止点和推荐下一任务

本轮停在 CHECK-01 完成：三方案在单父目录、串行规则下返回相同且正确的 ID 集合；没有性能、ANN 或论文数值结论。

建议下一项为 **PROTO-01：编写小规模目录性能协议**。先固定时间样本与人工树的查询/维护序列、重置方式、位图复制和 catalog 成本边界、至少五次独立进程重复及资源上限。当前 catalog 在冲突合并时扫描所有条目，须单列成本；std::map/位图复制等工程选择也需声明。协议完成再进入 DIR-01，不能把 CTest 总耗时当测量结果。

DATA-01/SPEC-01 保留真实材料缺口；这不要求继续无限抽样，也不等于所有后续工作都被阻塞。

'''+s[b:]
s+='\n2026-10-26（实现与审查完成）：依据源码、Release/ASan 日志和独立判定器证据，完成 ENV、ORACLE、CORE 三项、CHECK 与 SPEC-TIME-PILOT；快照 SNAP-dd12b2f5ac546566。父 DATA/SPEC 不关闭，性能任务均未开始；下一步 PROTO-01。\n'
save('REPRODUCTION_PLAN.md',s)
(ev/'documentation-changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'updated':[x['path'] for x in changes]},ensure_ascii=True))
