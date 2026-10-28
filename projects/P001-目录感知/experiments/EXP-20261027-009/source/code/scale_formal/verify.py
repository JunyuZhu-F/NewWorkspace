# -*- coding: utf-8 -*-
"""All-run/all-pass verifier plus process-level summaries; no production path helpers."""
import csv
from collections import defaultdict
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time

spec=importlib.util.spec_from_file_location('independent_paths',Path(__file__).resolve().parent.parent/'scale_directory/verify.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
ORDER=['PE-ONLINE','PE-OFFLINE','TrieHI'];PHASE=['directory_misc_ns','locate_ns','bitmap_copy_ns','bitmap_sets_ns','ancestors_ns','catalog_ns','cleanup_ns']
def read(p):return oracle.read(p)
def write(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def csvout(p,rows):
    assert rows
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def quantile(v,q):
    a=sorted(v);x=(len(a)-1)*q;i=int(x);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i)

def check(out,run,warm,repeats,m,queries,ops,states,expected):
    passes=warm+repeats;strategies=set(ORDER);seen=set();canonical={}
    for r in oracle.table(out/'answers.tsv'):
        key=(r['strategy'],r['stage'],r['case']);assert key not in seen and key[0] in strategies;seen.add(key)
        value=(r['exists'],r['count'],r['digest']);assert value==expected[key[1:]];canonical[key]=value
    assert seen=={(s,st,c) for s in ORDER for st,c in expected}
    units={('build','build')}|{('query',q['case']) for q in queries}|{(o['kind'],o['case']) for o in ops}
    timings=oracle.table(out/'timings.tsv');seen=set();observed=[]
    for r in timings:
        s=r['strategy'];p=int(r['pass']);key=(s,p,r['kind'],r['case'])
        assert key not in seen and s in strategies;seen.add(key)
        assert int(r['run'])==run and int(r['warmup'])==int(p<warm) and int(r['total_ns'])>=0 and all(int(r[x])==0 for x in PHASE)
        if not observed or observed[-1]!=s:observed.append(s)
    rotation=ORDER[run%3:]+ORDER[:run%3];assert observed==rotation
    assert seen=={(s,p,k,c) for s in ORDER for p in range(passes) for k,c in units}
    space=oracle.table(out/'space.tsv');seen=set();portable={}
    for r in space:
        s=r['strategy'];p=int(r['pass']);stage=int(r['stage']);key=(s,p,stage)
        assert key not in seen and s in strategies and 0<=p<passes and 0<=stage<5;seen.add(key)
        assert int(r['run'])==run and int(r['directories'])==int(r['bitmaps'])==len(states[stage][0]) and int(r['catalog_entries'])==m['records'] and int(r['portable_bytes'])>=0
        k=(s,stage);assert k not in portable or portable[k]==r['portable_bytes'];portable[k]=r['portable_bytes']
    assert seen=={(s,p,st) for s in ORDER for p in range(passes) for st in range(5)}
    clock=oracle.table(out/'clock.tsv');assert len(clock)==10000 and all(int(x['nanoseconds'])>=0 for x in clock) and any(int(x['nanoseconds'])>0 for x in clock)
    wall=oracle.table(out/'wall.tsv');assert len(wall)==2+3*passes
    assert (wall[0]['kind'],wall[0]['strategy'],wall[0]['pass'])==('setup','all','-1') and (wall[-1]['kind'],wall[-1]['strategy'],wall[-1]['pass'])==('total','all','-1')
    assert [(r['kind'],r['strategy'],int(r['pass'])) for r in wall[1:-1]]==[('pass',s,p) for s in rotation for p in range(passes)]
    ns=[int(r['elapsed_ns']) for r in wall];assert min(ns)>=0 and ns[-1]>=sum(ns[:-1])
    return canonical,portable,timings,dict(run=run,order=rotation,timing_rows=len(timings),measurement_rows=sum(int(r['warmup'])==0 for r in timings),warmup_rows=sum(int(r['warmup'])==1 for r in timings),answers=len(canonical),space_rows=len(space),full_scope_checks=3*passes*5*len(queries),files={f.name:oracle.sha(f) for f in out.iterdir() if f.is_file()})

def main():
    start=time.perf_counter();config=read(Path(sys.argv[1]));dest=Path(sys.argv[2]);assert not dest.exists();dest.mkdir(parents=True)
    m,qs,ops,states,expected,geometry=oracle.fixture(Path(config['fixture']));prior=None;stats=[];allrows=[]
    for unit in config['outputs']:
        out=Path(unit['path']);a,p,rows,st=check(out,unit['run'],config['warmups'],config['repeats'],m,qs,ops,states,expected)
        if prior is not None:assert prior==(a,p),'cross-process/build answer or portable mismatch'
        prior=(a,p);stats.append(dict(path=str(out),**st));allrows.extend(rows)
    assert stats
    groups=defaultdict(list);casegroups=defaultdict(list);bycase={q['case']:q for q in qs}
    for r in allrows:
        if r['warmup']=='1':continue
        group=('query-recursive' if bycase[r['case']]['recursive'] else 'query-local') if r['kind']=='query' else r['case']
        groups[(r['strategy'],group,int(r['run']))].append(int(r['total_ns'])/1000)
        casegroups[(r['strategy'],r['kind'],r['case'],int(r['run']))].append(int(r['total_ns'])/1000)
    perrun=[dict(strategy=s,group=g,run=run,count=len(v),mean_us=statistics.fmean(v),p50_us=quantile(v,.5),p95_us=quantile(v,.95)) for (s,g,run),v in sorted(groups.items())]
    csvout(dest/'per-run.csv',perrun)
    pooled=defaultdict(list)
    for r in perrun:pooled[(r['strategy'],r['group'])].append(r['mean_us'])
    summary=[dict(strategy=s,group=g,processes=len(v),mean_us=statistics.fmean(v),sd_process_means_us=statistics.stdev(v) if len(v)>1 else None) for (s,g),v in sorted(pooled.items())]
    csvout(dest/'summary.csv',summary)
    csvout(dest/'per-case-run.csv',[dict(strategy=s,kind=k,case=c,run=run,count=len(v),mean_us=statistics.fmean(v),p50_us=quantile(v,.5),p95_us=quantile(v,.95),path=bycase[c]['path'] if k=='query' else '',recursive=bycase[c]['recursive'] if k=='query' else '',candidates=bycase[c]['candidates'] if k=='query' else '',depth=bycase[c]['depth'] if k=='query' else '') for (s,k,c,run),v in sorted(casegroups.items())])
    result=dict(status='passed',records=m['records'],queries=len(qs),directories=m['directories'],geometry=geometry,runs=stats,timing_rows=sum(s['timing_rows'] for s in stats),measurement_rows=sum(s['measurement_rows'] for s in stats),warmup_rows=sum(s['warmup_rows'] for s in stats),full_scope_checks=sum(s['full_scope_checks'] for s in stats),verification_s=time.perf_counter()-start,summary=summary,verifier_sha256=oracle.sha(Path(__file__)),independent_oracle_sha256=oracle.sha(Path(oracle.__file__)),csv_files={p.name:oracle.sha(p) for p in dest.glob('*.csv')})
    write(dest/'verification.json',result);print('PASS formal grid and independent oracle',m['records'],len(stats),'outputs',result['timing_rows'],'timings',flush=True)
if __name__=='__main__':main()
