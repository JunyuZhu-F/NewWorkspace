"""Read existing EXP-20261027-004 only; write derived audit artifacts here."""
import collections
import hashlib
import json
import math
from pathlib import Path

out = Path(__file__).resolve().parent
project = out.parent.parent
exp = project/'experiments/EXP-20261027-004'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name): return [json.loads(line) for line in (exp/name).read_text(encoding='utf-8').splitlines() if line.strip()]
def stats(rows, field='total_ns'):
    vals=sorted(r[field] for r in rows)
    runs=collections.defaultdict(list)
    for r in rows: runs[r['run']].append(r[field])
    return {'n':len(vals),'mean_ns':sum(vals)/len(vals),'median_ns':vals[(len(vals)-1)//2],
            'p90_ns':vals[math.ceil(.9*len(vals))-1],'p99_ns':vals[math.ceil(.99*len(vals))-1],
            'per_run_mean_ns':{str(k):sum(v)/len(v) for k,v in sorted(runs.items())}}
raw_names=['raw/dsq.jsonl','raw/dsm.jsonl','raw/build.jsonl','raw/space.jsonl','raw/timing.jsonl',
           'raw/process.jsonl','run-order.jsonl','config.json','source/hashes.json','summary.json','protocol.md']
hashes={name:sha(exp/name) for name in raw_names}
snapshot=json.loads((exp/'source/hashes.json').read_text())
for name,digest in snapshot['files'].items():
    assert sha(exp/'source'/name)==digest
    current=project/name if name.startswith('code/') else project/'notes/benchmark-fixtures-20261026-01'/Path(name).name
    assert sha(current)==digest
dsq=load('raw/dsq.jsonl');dsm=load('raw/dsm.jsonl');build=load('raw/build.jsonl');space=load('raw/space.jsonl');timing=load('raw/timing.jsonl')
assert (len(dsq),len(dsm),len(build),len(space),len(timing))==(62100,3450,1380,1380,210)
summary={}; tables=[]
for kind,rows,keys,field in [('dsq',dsq,['input','strategy','instrumented','recursive'],'total_ns'),
                            ('dsm',dsm,['input','strategy','instrumented','operation','accepted'],'total_ns'),
                            ('build',build,['input','strategy','instrumented'],'build_ns')]:
    groups=collections.defaultdict(list)
    for r in rows:
        if not r['warmup']: groups[tuple(r[k] for k in keys)].append(r)
    summary[kind]=[dict(zip(keys,k),**stats(rr,field)) for k,rr in sorted(groups.items(),key=lambda x:repr(x[0]))]
path_groups=collections.defaultdict(list)
for r in dsq:
    if not r['warmup']: path_groups[(r['input'],r['strategy'],r['instrumented'],r['path'],r['recursive'])].append(r)
paths=[]
counter_fields=['directories_visited','bitmaps_read','bitmap_copies','bitmap_unions','bitmap_differences']
for key,rr in sorted(path_groups.items(),key=lambda x:repr(x[0])):
    entry=dict(zip(['input','strategy','instrumented','path','recursive'],key),**stats(rr))
    entry.update(depth=rr[0]['depth'],children=rr[0]['direct_children'],candidate_count=rr[0]['candidate_count'])
    if key[2]:
        for field in counter_fields:
            vals={r[field] for r in rr};assert len(vals)==1
            entry[field]=next(iter(vals))
    paths.append(entry)
summary['path_groups']=paths
published=json.loads((exp/'summary.json').read_text())
lookup={(p['input'],p['strategy'],p['instrumented'],p['path'],p['recursive']):p for p in paths}
assert len(paths)==len(published['dsq'])==540
for r in published['dsq']:
    p=lookup[(r['input'],r['strategy'],r['instrumented'],r['path'],r['recursive'])]
    assert p['n']==r['pooled']['n'] and math.isclose(p['mean_ns'],r['pooled']['mean'],rel_tol=1e-12)
maintenance=[]
for kind in ['figure2','time']:
    for strategy in ['pe_online','pe_offline','trie_hi']:
        groups=collections.defaultdict(list)
        for r in dsm:
            if r['input']==kind and r['strategy']==strategy and r['instrumented'] and not r['warmup']:
                groups[(r['operation'],r['source'],r['accepted'])].append(r)
        for key,rr in groups.items():
            e=dict(input=kind,strategy=strategy,operation=key[0],source=key[1],accepted=key[2])
            for field in ['source_subtree_directory_count','source_subtree_entry_count','target_entry_count','conflict_node_count','remapped_path_keys','relinked_subtrees','reconciled_nodes','catalog_entries_scanned']:
                vals={r[field] for r in rr};assert len(vals)==1
                e[field]=next(iter(vals))
            maintenance.append(e)
summary['maintenance_counters']=maintenance
comparison=[]
for inp in ['figure2','time']:
    for recursive in [True,False]:
        for baseline in ['pe_online','pe_offline']:
            bb=[p for p in paths if p['input']==inp and not p['instrumented'] and p['recursive']==recursive and p['strategy']==baseline]
            tt={p['path']:p for p in paths if p['input']==inp and not p['instrumented'] and p['recursive']==recursive and p['strategy']=='trie_hi'}
            comparison.append(dict(input=inp,recursive=recursive,baseline=baseline,trie_mean_lower_paths=sum(tt[p['path']]['mean_ns']<p['mean_ns'] for p in bb),paths=len(bb)))
summary['path_comparison']=comparison
default_timing=[r for r in timing if not r['instrumented']]
summary['clock_overhead']={'default_mean_ns_min':min(r['empty_interval_mean_ns'] for r in default_timing),
                          'default_mean_ns_max':max(r['empty_interval_mean_ns'] for r in default_timing),
                          'nominal_period_ns':sorted({r['clock_resolution_ns'] for r in timing}),
                          'warning':'clock_resolution_ns is Clock::period, not empirically observed minimum delta'}
default_roots=[p for p in paths if p['input']=='time' and not p['instrumented'] and p['path'] in ['/','/1992/','/1992/1/']]
summary['time_selected_paths']=default_roots
summary['time_internal_leaf']=[]
for s in ['pe_online','pe_offline','trie_hi']:
    for recursive in [True,False]:
        for internal in [True,False]:
            rr=[r for r in dsq if r['input']=='time' and r['strategy']==s and not r['instrumented'] and not r['warmup'] and r['recursive']==recursive and (r['direct_children']>0)==internal]
            summary['time_internal_leaf'].append(dict(strategy=s,recursive=recursive,internal=internal,**stats(rr)))
summary['memory_sampling_boundary']='space() called after make_oracle/check_state while oracle is alive; process bytes include fixture/oracle/validation/allocator effects'
summary['source_hash']=snapshot['source_snapshot_hash']
summary['raw_hashes']=hashes
assert hashes=={name:sha(exp/name) for name in raw_names}
(out/'analysis.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
lines=['# 现有结果的派生统计', '', '只读取 EXP-20261027-004；未运行新基准，未减计时开销。时间单位微秒。', '',
       '## 默认核心：均值、中位数和五进程均值范围', '', '| 输入/操作 | 方案 | 均值 | 中位数 | run均值范围 | N |','|---|---|---:|---:|---:|---:|']
for kind in ['dsq','dsm','build']:
    for r in summary[kind]:
        if r['instrumented']: continue
        op=('recursive' if r['recursive'] else 'nonrecursive') if kind=='dsq' else (r['operation']+(' accepted' if r['accepted'] else ' rejected')) if kind=='dsm' else 'build'
        runs=list(r['per_run_mean_ns'].values())
        lines.append(f"| {r['input']}/{op} | {r['strategy']} | {r['mean_ns']/1000:.4f} | {r['median_ns']/1000:.4f} | {min(runs)/1000:.4f}–{max(runs)/1000:.4f} | {r['n']} |")
lines+=['','## 插桩维护计数（不是耗时）','','| 输入/操作 | 方案 | 源目录数 | 源条目 | 路径重映射 | 子树重挂 | 协调节点 | catalog扫描 |','|---|---|---:|---:|---:|---:|---:|---:|']
for r in maintenance:
    lines.append(f"| {r['input']}/{r['operation']}/{'accepted' if r['accepted'] else 'rejected'} | {r['strategy']} | "+' | '.join(str(r[k]) for k in ['source_subtree_directory_count','source_subtree_entry_count','remapped_path_keys','relinked_subtrees','reconciled_nodes','catalog_entries_scanned'])+' |')
lines+=['','## 时间视图：根、年份、月份的默认查询均值','','| 路径/模式 | 方案 | 候选量 | 直接孩子 | 均值 | run均值范围 |','|---|---|---:|---:|---:|---:|']
for r in default_roots:
    runs=list(r['per_run_mean_ns'].values())
    lines.append(f"| {r['path']}/{'recursive' if r['recursive'] else 'nonrecursive'} | {r['strategy']} | {r['candidate_count']} | {r['children']} | {r['mean_ns']/1000:.4f} | {min(runs)/1000:.4f}–{max(runs)/1000:.4f} |")
lines+=['','## 时间视图：全部内部目录/叶目录分层','','| 方案 | 递归 | 内部目录 | N | 均值(微秒) |','|---|---|---|---:|---:|']
for r in summary['time_internal_leaf']:
    lines.append(f"| {r['strategy']} | {r['recursive']} | {r['internal']} | {r['n']} | {r['mean_ns']/1000:.4f} |")
lines+=['','## 逐路径均值比较（描述性，不作显著性推断）','']
for r in comparison: lines.append(f"- {r['input']} recursive={r['recursive']}：TrieHI 对 {r['baseline']} 均值更低的路径为 {r['trie_mean_lower_paths']}/{r['paths']}。")
(out/'statistics.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(out/'verification.json').write_text(json.dumps({'status':'passed','analysis_only':True,'new_benchmark_processes':0,'source_and_fixture_snapshot_files_checked':len(snapshot['files']),
    'all_540_path_group_means_match_published_summary':len(paths)==540,'raw_inputs_unchanged':True,'raw_hashes':hashes,'source_hash':snapshot['source_snapshot_hash']},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'passed','new_benchmark_processes':0,'path_groups_checked':len(paths),'source_files_checked':len(snapshot['files']),'experiment_files_hashed':len(hashes)}))
