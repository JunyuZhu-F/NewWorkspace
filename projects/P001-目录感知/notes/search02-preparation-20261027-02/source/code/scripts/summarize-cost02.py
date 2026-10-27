"""Validate the exact cost matrix before generating descriptive diagnostics."""
import argparse
import collections
import json
import math
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec

def rows(root,name):
    return [json.loads(line) for line in (root/'raw'/name).read_text(encoding='utf-8').splitlines() if line.strip()]
def stats(v):
    v=sorted(v)
    return {'n':len(v),'mean':sum(v)/len(v),**{name:v[math.ceil(p*len(v))-1] for name,p in [('p90',.9),('p95',.95),('p99',.99),('p99_9',.999)]},'p99_9_stability':'unstable_descriptive_only'}
def ident(r):return r['run'],r['input'],r['subload'],r['strategy'],r['diagnostic_kind']
def summarise(root):
    spec=spec_from_file_location('cost_runner',Path(__file__).with_name('run-cost02.py'));runner=module_from_spec(spec);spec.loader.exec_module(runner)
    expected={(j['run'],j['input'],j['subload'],j['strategy'],j['mode']) for j in runner.matrix()}
    phase=rows(root,'phases.jsonl');allocation=rows(root,'allocation.jsonl');process=rows(root,'cost-process.jsonl');overhead=rows(root,'overhead.jsonl')
    order=[json.loads(s) for s in (root/'run-order.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
    assert len(process)==len(order)==len(overhead)==135
    assert all(cal['allocation_mode']==(job['mode']=='allocation') for cal,job in zip(overhead,order))
    assert {ident(r) for r in process}==expected
    assert all(r['status']=='passed' for r in process) and all(r['status']=='passed' and r['returncode']==0 for r in order)
    assert (len(phase),len(allocation))==(33465,3795)
    config=json.loads((root/'config.json').read_text())
    grouped=collections.defaultdict(list);memory_groups=collections.defaultdict(list)
    phase_keys=set();memory_keys=set()
    for r in phase:
        assert r['protocol']=='PROTO-COST-02-20261027'
        assert r['source_hash']==config['source_snapshot_hash'] and r['diagnostic_kind']=='phase'
        assert r['warmup']==(r['iteration']<3)
        key=ident(r)+(r['iteration'],r['sample']);assert key not in phase_keys;phase_keys.add(key)
        assert r['phase_calls']['directory_misc']>0
        assert sum(r['phase_ns'].values())<=r['diagnostic_total_ns']
        assert r['directory_core_observed_ns']==sum(v for k,v in r['phase_ns'].items() if k!='catalog')
        assert (r['catalog_status']=='no_call')==(r['phase_calls']['catalog']==0)
        if r['sample']=='build':assert r['phase_calls']['catalog']>=2*r['entry_count']
        if 'operation' in r:assert (r['phase_calls']['catalog']>0)==(r['operation']=='merge' and r['accepted'])
        if not r['warmup']:
            for stage,value in r['phase_ns'].items():grouped[(r['input'],r['strategy'],r['subload'],r['sample'],stage)].append((r['run'],value))
    for r in allocation:
        assert r['protocol']=='PROTO-COST-02-20261027'
        assert r['source_hash']==config['source_snapshot_hash'] and r['diagnostic_kind']=='allocation'
        assert r['warmup']==(r['iteration']<3) and r['ledger_complete']
        key=ident(r)+(r['series'],r['state'],r['iteration']);assert key not in memory_keys;memory_keys.add(key)
        if r['state']=='after_destroy':assert r['requested_live_bytes']==[0,0,0,0] and r['live_blocks']==[0,0,0,0]
        if not r['warmup']:memory_groups[(r['input'],r['strategy'],r['series'],r['state'])].append(r)
    for job in expected:
        if job[-1]=='phase':
            samples=['build'] if job[2]=='build' else None
            found=[r for r in phase if ident(r)==job]
            per_iteration=22 if job[1]=='figure2' and job[2]=='dsq' else 68 if job[2]=='dsq' else 3 if job[2]=='dsm' else 1
            assert collections.Counter(r['iteration'] for r in found)=={i:per_iteration for i in range(23)}
        else:
            found=[r for r in allocation if ident(r)==job]
            assert collections.Counter(r['iteration'] for r in found)=={i:6 if job[1]=='figure2' else 5 for i in range(23)}
    result={'status':'complete','scope':'independent diagnostics, not default-core performance or author workload','processes':135,
        'raw_rows':{'phases':len(phase),'allocation':len(allocation),'overhead':len(overhead)},'phases':[],'allocation':[],
        'rejected_operation_exception_propagation':'not included in core scopes; no full rejected net-time claim',
        'memory_scope':'requested allocation payloads, excluding allocator metadata, fragmentation, observer storage; no process-byte subtraction'}
    for key,values in sorted(grouped.items()):
        per_run=collections.defaultdict(list)
        for run,value in values:per_run[run].append(value)
        result['phases'].append(dict(zip(['input','strategy','subload','sample','stage'],key),pooled=stats([v for _,v in values]),per_run_mean={str(k):sum(v)/len(v) for k,v in per_run.items()}))
    for key,rr in sorted(memory_groups.items()):
        entry=dict(zip(['input','strategy','series','state'],key))
        entry['requested_live_bytes']={name:stats([r['requested_live_bytes'][i] for r in rr]) for i,name in enumerate(['observer_excluded','directory','catalog','bitmap'])}
        result['allocation'].append(entry)
    (root/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (root/'correctness.json').write_text(json.dumps({'status':'passed','exact_matrix':True,'rows_checked':result['raw_rows'],'iterations':23,'per_sample_oracle':'checked in executable'},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'complete','processes':135,'raw_rows':result['raw_rows']}))
def main():
    p=argparse.ArgumentParser();p.add_argument('--experiment',type=Path,required=True);a=p.parse_args();summarise(a.experiment)
if __name__=='__main__':main()
