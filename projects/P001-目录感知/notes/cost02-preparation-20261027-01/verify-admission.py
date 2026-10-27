"""Collect and independently check actual admission records (not performance)."""
import collections,hashlib,importlib.util,json,shutil,tempfile
from pathlib import Path
here=Path(__file__).resolve().parent;project=here.parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]
summary={}
for label,build in [('release','build-Release-Cost'),('asan','build-RelWithDebInfo-ASan-Cost')]:
    for mode in ['phase','allocation']:
        candidates=sorted((project/'code'/build/'cost-admission'/mode).glob('attempt-*'))
        assert candidates
        latest=candidates[-1];dest=here/'admission'/label/mode
        if dest.exists():
            assert (dest/'origin.txt').read_text(encoding='utf-8')==str(latest)
        else:
            shutil.copytree(latest,dest);(dest/'origin.txt').write_text(str(latest),encoding='utf-8')
        rows=load(dest/'raw'/('phases.jsonl' if mode=='phase' else 'allocation.jsonl'))
        assert len(rows)==(291 if mode=='phase' else 33)
        assert all(r['experiment']=='admission_only' and r['protocol']=='PROTO-COST-02-20261027' for r in rows)
        assert {r['strategy'] for r in rows}=={'pe_online','pe_offline','trie_hi'}
        if mode=='phase':
            assert len({(r['input'],r['strategy'],r['subload'],r['sample']) for r in rows})==291
            for r in rows:
                assert sum(r['phase_ns'].values())<=r['diagnostic_total_ns']
                assert r['directory_core_observed_ns']==sum(v for k,v in r['phase_ns'].items() if k!='catalog')
                assert r['phase_calls']['directory_misc']>0
                if r['sample']=='build':assert r['phase_calls']['catalog']>=2*r['entry_count']
                if 'operation' in r:assert (r['phase_calls']['catalog']>0)==(r['operation']=='merge' and r['accepted'])
        else:
            assert len({(r['input'],r['strategy'],r['series'],r['state']) for r in rows})==33
            for r in rows:
                assert r['ledger_complete'] and r['requested_live_bytes'][0]==0
                assert r['private_bytes']>0 and r['process_memory_includes_observer_storage']
                if r['state']=='after_destroy':assert r['requested_live_bytes']==r['live_blocks']==[0,0,0,0]
                else:assert all(v>0 for v in r['requested_live_bytes'][1:])
            for strategy in ['pe_online','pe_offline','trie_hi']:
                rr=[r for r in rows if r['strategy']==strategy and r['input']=='time']
                assert next(r for r in rr if r['state']=='after_merge')['requested_live_bytes']==next(r for r in rr if r['state']=='after_move_rejected')['requested_live_bytes']
            for inp in ['figure2','time']:
                assert len({r['requested_live_bytes'][2] for r in rows if r['input']==inp and r['state']!='after_destroy'})==1
        calibration=load(dest/'raw/overhead.jsonl');assert len(calibration)==1
        assert calibration[0]['empty']['n']==calibration[0]['phase_frame']['n']==10000
        summary[label+'_'+mode]={'status':'passed','admission_rows':len(rows),'origin':str(latest.relative_to(project)),
                                'file_sha256':{p.name:sha(p) for p in (dest/'raw').iterdir()}}
old=json.loads((project/'notes/dir01-cost-review-20261027-01/verification.json').read_text())
for name,digest in old['raw_hashes'].items():assert sha(project/'experiments/EXP-20261027-004'/name)==digest
scripts=project/'code/scripts'
for name in ['run-cost02.py','summarize-cost02.py','verify-cost-fixtures.py']:
    compile((scripts/name).read_text(encoding='utf-8'),name,'exec')
spec=importlib.util.spec_from_file_location('cost_summary',scripts/'summarize-cost02.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert module.stats([1,2,3,4,5])['mean']==3 and module.stats([1,2,3,4,5])['p99_9']==5
# Incomplete synthetic inputs must fail closed, never produce normal summary.
with tempfile.TemporaryDirectory(prefix='synthetic-summary-only-') as temp:
    root=Path(temp);(root/'raw').mkdir()
    for name in ['phases','allocation','cost-process','overhead']:(root/'raw'/(name+'.jsonl')).write_text('')
    (root/'run-order.jsonl').write_text('')
    rejected=False
    try:module.summarise(root)
    except AssertionError:rejected=True
    assert rejected and not (root/'summary.json').exists()
result={'status':'passed','scope':'admission only, not formal 135-process measurements','admissions':summary,'old_experiment_files_hashed_unchanged':len(old['raw_hashes']),
        'python_syntax':'passed','known_quantile_check':'passed','incomplete_summary_rejected':True,'formal_matrix_processes_run':0}
(here/'admission-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'passed','admission_sets':4,'old_files_unchanged':len(old['raw_hashes']),'formal_processes':0}))
