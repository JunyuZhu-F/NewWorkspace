from pathlib import Path
import difflib,hashlib,json
root=Path(r'D:\NewWorkspace\projects\P001-目录感知')
changes=[]
def change(rel,fn):
 p=root/rel;b=p.read_bytes();s=b.decode('utf-8-sig');t=fn(s);assert t!=s,rel;p.write_text(t,encoding='utf-8');changes.append({'path':rel,'before_sha256':hashlib.sha256(b).hexdigest(),'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'diff':''.join(difflib.unified_diff(s.splitlines(True),t.splitlines(True)))})
def once(s,a,b):
 assert s.count(a)==1,a
 return s.replace(a,b,1)
change('TASK.md',lambda s:once(s,'当前执行数据核查，不因范围获批跳过协议与正确性前置条件。','用户已明确授权进入单父目录核心正式实现，先走 ENV-01 → ORACLE-01 → CORE-01/02/03；完整 DATA/SPEC 保留未完成，不阻塞该已明确核心。').replace('- 当前先执行 DATA-01 的只读、小规模数据检查，不提前编写三方案正式算法；不启动训练、完整基准或大型数据下载。后续按已确认范围推进，扩大规模仍须另行批准。','- 用户已批准单父目录三方案正式实现、独立判定器、代码审查和小规模正确性测试；本轮不启动性能基准、训练或大型数据下载。真实多类别适配和完整规模仍受各自前置条件约束。')+'\n2026-10-26（正式实现授权）：用户明确同意按 ENV → ORACLE → CORE 三方案推进，并要求审查、更新文件。先单父目录核心，保留类别协议阻塞；没有将 DATA-01/SPEC-01 改为完成，也没有批准完整性能实验。\n')
change('AGENTS.md',lambda s:once(s,'当前按 TASK/PLAN 执行 DATA-01，不跳过数据/协议/正确性门槛，大规模运行另行批准。','用户已进一步授权单父目录核心正式实现与审查，按 ENV → ORACLE → CORE 推进；真实数据缺口保留，正确性验证先于性能，大规模运行另行批准。'))
change('REPRODUCTION_PLAN.md',lambda s:once(s,'当前进入 DATA-01 的小规模只读核查，未执行三方案算法实现或性能实验。','当前已获单父目录核心正式实现授权，进入 ENV-01 → ORACLE-01 → CORE-01/02/03。DATA/SPEC 未完成部分保留为相应真实数据实验前置；本轮不执行性能基准。').replace('当前主线仍是 **DATA-01 → SPEC-01**，两项都未完成，不能被 ENV-01 替代：','用户最新决定将实现主线调整为 **ENV-01 → ORACLE-01 → CORE-01/02/03 → CHECK-01**，范围为已明确的单父目录核心。DATA-01/SPEC-01 未完成部分保留，不作为该核心实现的整体关口：').replace('这是范围受限的准备分支','这是已批准的正式核心实现分支')+'\n2026-10-26（用户调整顺序）：允许先正式实现和审查单父目录三方案；ENV/ORACLE/CORE/CHECK 以核心正确性为本轮目标，不强制等待完整 DATA/SPEC 或真实时间样本协议。后者和真实类别阻塞均不被关闭。\n')
change('STATE.md',lambda s:s.replace('**尚未进入三方案算法实现或性能实验。**','**现已获得单父目录核心实现、审查与小规模正确性测试授权；尚未运行性能实验。**')+'\n最新执行指令：2026-10-26 用户明确同意正式实现并审查、更新文档。当前主线改为 ENV → ORACLE → CORE → CHECK（单父目录范围），历史数据核查结论保留。\n')
(root/'notes/core-implementation-20261026-01/authorization-changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
print('Updated TASK, AGENTS, PLAN and STATE; recorded implementation authorization.')
