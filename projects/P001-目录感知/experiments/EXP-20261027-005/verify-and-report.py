"""Independent recheck and meeting-ready report; consumes existing measurements only."""
import collections,hashlib,importlib.util,json,math
from pathlib import Path
root=Path(__file__).resolve().parent;project=root.parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return [json.loads(line) for line in (root/name).read_text(encoding='utf-8').splitlines() if line.strip()]
def avg(values):return sum(values)/len(values)
def job(r):return r['run'],r['input'],r['subload'],r['strategy'],r.get('diagnostic_kind',r.get('mode'))
def statcheck(entry,values):
    v=sorted(values);assert entry['n']==len(v) and math.isclose(entry['mean'],avg(v),rel_tol=1e-12)
    for name,p in [('p90',.9),('p95',.95),('p99',.99),('p99_9',.999)]:assert entry[name]==v[math.ceil(p*len(v))-1]
names=['raw/phases.jsonl','raw/allocation.jsonl','raw/overhead.jsonl','raw/cost-process.jsonl','run-order.jsonl','summary.json','config.json','protocol.md']
hashes={n:sha(root/n) for n in names}
phase=read(names[0]);memory=read(names[1]);overhead=read(names[2]);process=read(names[3]);order=read(names[4]);summary=json.loads((root/'summary.json').read_text(encoding='utf-8'))
status=json.loads((root/'run-status.json').read_text());assert status['status']=='complete'
config=json.loads((root/'config.json').read_text());frozen=json.loads((root/'source/hashes.json').read_text())
for name,digest in frozen['files'].items():assert sha(root/'source'/name)==sha(project/name)==digest
for name,digest in frozen['fixtures'].items():assert sha(root/'source/fixtures'/name)==sha(project/'notes/benchmark-fixtures-20261026-01'/name)==digest
assert sha(root/'protocol.md')==frozen['protocol_sha256']==sha(project/'notes/benchmark-cost-protocol-20261027.md')
spec=importlib.util.spec_from_file_location('cost_runner',project/'code/scripts/run-cost02.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
expected={job(j) for j in runner.matrix()}
assert len(expected)==len(order)==len(process)==len(overhead)==135
assert {job(r) for r in order}=={job(r) for r in process}==expected
assert all(r['status']=='passed' and r['returncode']==0 for r in order)
assert len(phase)==33465 and len(memory)==3795
assert all(r['source_hash']==frozen['source_snapshot_hash'] and r['experiment']==root.name and r['warmup']==(r['iteration']<3) for r in phase+memory)
groups=collections.defaultdict(list);memgroups=collections.defaultdict(list)
for r in phase:
    assert sum(r['phase_ns'].values())<=r['diagnostic_total_ns']
    assert r['directory_core_observed_ns']==sum(v for k,v in r['phase_ns'].items() if k!='catalog')
    if not r['warmup']:
        for stage,ns in r['phase_ns'].items():groups[(r['input'],r['strategy'],r['subload'],r['sample'],stage)].append((r['run'],ns))
for entry in summary['phases']:
    rr=groups[tuple(entry[k] for k in ['input','strategy','subload','sample','stage'])]
    statcheck(entry['pooled'],[v for _,v in rr])
    for run,value in entry['per_run_mean'].items():assert math.isclose(value,avg([v for n,v in rr if str(n)==run]),rel_tol=1e-12)
for r in memory:
    assert r['ledger_complete']
    if r['state']=='after_destroy':assert r['requested_live_bytes']==r['live_blocks']==[0,0,0,0]
    if not r['warmup']:memgroups[(r['run'],r['input'],r['strategy'],r['series'],r['iteration'])].append(r)
for key,rr in memgroups.items():
    if key[1]=='time':assert next(r for r in rr if r['state']=='after_merge')['requested_live_bytes']==next(r for r in rr if r['state']=='after_move_rejected')['requested_live_bytes']
for entry in summary['allocation']:
    rr=[r for r in memory if not r['warmup'] and all(r[k]==entry[k] for k in ['input','strategy','series','state'])]
    for i,key in enumerate(['observer_excluded','directory','catalog','bitmap']):statcheck(entry['requested_live_bytes'][key],[r['requested_live_bytes'][i] for r in rr])
old=json.loads((project/'notes/dir01-cost-review-20261027-01/verification.json').read_text())
for name,digest in old['raw_hashes'].items():assert sha(project/'experiments/EXP-20261027-004'/name)==digest
report={'status':'passed','processes':135,'phase_rows':len(phase),'allocation_rows':len(memory),'source_files_checked':len(frozen['files']),
        'source_protocol_fixture_hashes_match':True,'summary_means_quantiles_per_run_recomputed':True,'destroy_zero_and_rejection_unchanged':True,
        'old_experiment_files_unchanged':len(old['raw_hashes']),'wall_seconds':status['wall_seconds'],'raw_hashes':hashes}
lines=['# DIR-01-COST-RUN-01 正式补测结果','','135/135进程成功，精确矩阵、源码/输入/协议hash、原始数量和派生统计核验通过。',
       f"运行器总耗时 {status['wall_seconds']:.3f} 秒。这是独立诊断构建，不与004默认总时延混池。",'',
       '## 时间视图维护阶段（诊断构建，单位微秒）','',
       '| 操作 | 方案 | 公开调用均值 | 直接目录区间合计 | 直接catalog | catalog/已观测核心区间 |','|---|---|---:|---:|---:|---:|']
maintenance=[]
for operation in ['move','merge']:
    for strategy in runner.STRATEGIES:
        rr=[r for r in phase if r['input']=='time' and r['strategy']==strategy and r.get('operation')==operation and r['accepted'] and not r['warmup']]
        total=avg([r['diagnostic_total_ns'] for r in rr]);directory=avg([r['directory_core_observed_ns'] for r in rr]);catalog=avg([r['phase_ns']['catalog'] for r in rr]);ratio=catalog/(directory+catalog)
        item={'operation':operation,'strategy':strategy,'n':len(rr),'diagnostic_total_mean_ns':total,'directory_observed_mean_ns':directory,'catalog_mean_ns':catalog,'catalog_fraction_observed_core':ratio}
        ordered=sorted(r['diagnostic_total_ns'] for r in rr)
        item.update(diagnostic_total_median_nearest_rank_ns=ordered[math.ceil(.5*len(rr))-1],diagnostic_total_max_ns=ordered[-1],per_run_diagnostic_total_mean_ns={str(run):avg([r['diagnostic_total_ns'] for r in rr if r['run']==run]) for run in range(5)})
        maintenance.append(item)
        lines.append(f'| {operation} | {strategy} | {total/1000:.4f} | {directory/1000:.4f} | {catalog/1000:.4f} | {ratio:.1%} |')
lines+=['','比例分母是同一诊断构建直接观测的目录区间+catalog区间，不是004默认总时间。各阶段含探针影响；未用总时间减catalog伪造目录时间。拒绝异常传播未完整覆盖，不列为完整净维护时间。', '',
        '所有原始尾部样本保留。诊断MOVE的均值不能代替004默认MOVE成绩；中位数、最大值及五run均值另见independent-verification.json，异常高值原因未经额外测量不推断。', '',
        '## 初始逻辑存活内存（请求字节，非物理堆）','',
        '| 输入 | 方案 | 目录结构 | catalog | 位图实际分配 | 三类合计 |','|---|---|---:|---:|---:|---:|']
initial=[]
for inp in ['figure2','time']:
    for strategy in runner.STRATEGIES:
        rr=[r for r in memory if r['input']==inp and r['strategy']==strategy and r['state']=='initial' and not r['warmup']]
        unique={tuple(r['requested_live_bytes']) for r in rr};assert len(unique)==1
        _,directory,catalog,bitmap=next(iter(unique));initial.append(dict(input=inp,strategy=strategy,directory_bytes=directory,catalog_bytes=catalog,bitmap_bytes=bitmap,total_bytes=directory+catalog+bitmap))
        lines.append(f'| {inp} | {strategy} | {directory:,} | {catalog:,} | {bitmap:,} | {directory+catalog+bitmap:,} |')
lines+=['','三类互斥，不叠加portable大小；不含分配器元数据、碎片和observer账本。全部销毁记录归零，时间序列拒绝操作前后存活字节一致。进程private/working set另在raw/allocation.jsonl，不能当索引净值。', '',
        '## 本轮完成的证据与保留边界','',
        '- 004默认性能结果仍有效；本轮补齐了实际阶段与请求分配证据，并保留所有样本，没有选择性删行。',
        '- source/保存实际30文件源码、输入和清单，protocol.md为冻结协议副本，run-order.jsonl为全部命令/状态，summary.json保存分阶段/路径/状态及五run统计。',
        '- 当前仅人工树及10,000条单父目录时间视图，Windows串行独立实现；不是作者原始工作负载或原版Viking数值复现。',
        '- 阶段探针会增加成本；小时段可能接近框架开销，不能宣称精细占比可靠。请求字节不是完整物理堆或论文序列化大小。',
        '- 此处验收是当前小规模目录分支；真实类别/WIKI、ANN检索质量和全库规模仍未完成。']
report['maintenance']=maintenance;report['initial_memory']=initial
assert hashes=={n:sha(root/n) for n in names}
(root/'independent-verification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
(root/'results.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','processes','phase_rows','allocation_rows','wall_seconds','maintenance','initial_memory']}))
