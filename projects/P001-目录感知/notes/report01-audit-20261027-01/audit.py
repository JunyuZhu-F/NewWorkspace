# -*- coding: utf-8 -*-
"""Read-only evidence audit and descriptive aggregation; no benchmark invocation."""
from collections import defaultdict
import csv
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

P=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'run-02'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def table(name,rows):
    with (OUT/name).open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    OUT.mkdir(exist_ok=False)
    assert not (OUT/'verification.json').exists()
    result=dict(status='running',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip(),
                scope='read-only 004-008 evidence audit and report; no simulation, compilation or experiments')
    counts=defaultdict(int);bindings={}
    def check(p,h):
        assert p.is_file() and sha(p)==h,str(p);counts['hash_checks']+=1
    # Bind reports and protocols without rewriting any experiment artifacts.
    for num in ('004','005','006','007','008'):
        e=P/'experiments'/('EXP-20261027-'+num)
        state=load(e/('run-status.json' if num in ('004','005') else 'status.json'))
        assert state['status'] in ('complete','completed','passed'),(num,state)
        for name in ('results.md','record.md','config.json','protocol.md','summary.json','independent-verification.json','final-check.json'):
            f=e/name
            if f.exists():bindings[str(f.relative_to(P))]=sha(f)
        if num=='005':
            proof=load(e/'independent-verification.json');assert proof['status']=='passed'
            for name,h in proof['raw_hashes'].items():check(e/name,h)
        if num in ('006','007','008'):
            for name,h in load(e/'source-hashes.json').items():
                check(P/name,h);check(e/'source'/name,h);counts['source_entries']+=1
            reports=[e/'verification.json'] if num=='006' else list(e.glob('verification-*.json'))
            for path in reports:
                r=load(path);assert r['status']=='passed';bindings[str(path.relative_to(P))]=sha(path)
                for w in r['workers']:
                    for name,h in w['files'].items():check(P/w['output']/name,h);counts['worker_files']+=1
            for directory in ('analysis-01','analysis-02/figures'):
                prov=e/directory/'provenance.json'
                if prov.exists():
                    r=load(prov)
                    for name,h in r.get('source_reports',{}).items():check(e/name,h)
                    for name,h in r.get('exports',{}).items():check(prov.parent/name,h)
    # Recompute only the raw 004 time/default claims being cited, not its entire verifier.
    e=P/'experiments/EXP-20261027-004';pools=defaultdict(list)
    for name in ('dsq','dsm','build'):
        with (e/'raw'/(name+'.jsonl')).open(encoding='utf-8') as f:
            for line in f:
                r=json.loads(line)
                if r['input']!='time' or r['instrumented'] or r['warmup']:continue
                if name=='dsm' and not r['accepted']:continue
                kind=('recursive' if r['recursive'] else 'nonrecursive') if name=='dsq' else r['operation'] if name=='dsm' else 'build'
                pools[(r['strategy'],kind)].append(r['build_ns'] if name=='build' else r['total_ns'])
    expected={'pe_online':[6.5276,2.4195,6.4590,207.2880,7085.1290],
              'pe_offline':[2.6992,5.4386,13.8530,191.2200,9494.2390],
              'trie_hi':[2.7203,5.4071,6.9070,162.5300,4748.6720]}
    rows=[]
    for strategy,values in expected.items():
        for kind,want in zip(('recursive','nonrecursive','move','merge','build'),values):
            v=pools[(strategy,kind)];mean=sum(v)/len(v)/1000;assert abs(mean-want)<0.000051
            rows.append(dict(experiment='004',strategy=strategy,kind=kind,n=len(v),mean_us=mean))
    table('arxiv-directory-recomputed.csv',rows)
    # Recompute the 005 catalog evidence from its own phase pool only.
    e=P/'experiments/EXP-20261027-005';groups=defaultdict(list)
    with (e/'raw/phases.jsonl').open(encoding='utf-8') as f:
        for line in f:
            r=json.loads(line)
            if r['input']=='time' and not r['warmup'] and r.get('operation')=='merge' and r.get('accepted'):groups[r['strategy']].append(r)
    phase=[];proof=load(e/'independent-verification.json')
    for s,v in groups.items():
        cat=sum(x['phase_ns']['catalog'] for x in v)/len(v);other=sum(x['directory_core_observed_ns'] for x in v)/len(v)
        old=next(x for x in proof['maintenance'] if x['operation']=='merge' and x['strategy']==s)
        assert abs(cat-old['catalog_mean_ns'])<1e-8 and abs(other-old['directory_observed_mean_ns'])<1e-8
        phase.append(dict(experiment='005',strategy=s,n=len(v),catalog_us=cat/1000,non_catalog_observed_us=other/1000,catalog_fraction_observed=cat/(cat+other)))
    assert len(phase)==3;table('arxiv-catalog-recomputed.csv',phase)
    # Capture all three strategies, both modes, and empty/nonempty aggregation at probe4.
    points=[];paired=[]
    for num in ('006','008'):
        e=P/'experiments'/('EXP-20261027-'+num);r=load(e/('verification.json' if num=='006' else 'verification-search-search.json'))
        for recursive in (True,False):
            q=next(x for x in r['quality'] if x['recursive']==recursive and x['probes']==4)
            for strategy in ('PE-ONLINE','PE-OFFLINE','TrieHI'):
                g=[x for x in r['groups'] if x['recursive']==recursive and x['probes']==4 and x['strategy']==strategy]
                nonempty=next(x for x in g if not x['empty']);empty=next((x for x in g if x['empty']),None)
                n=sum(x['total']['count'] for x in g);allmean=sum(x['total']['mean_ns']*x['total']['count'] for x in g)/n
                points.append(dict(experiment=num,k=100 if num=='006' else 10,recursive=recursive,strategy=strategy,nonempty=q['nonempty'],empty=q['empty'],recall_nonempty=q['mean_recall_nonempty'],nonempty_mean_us=nonempty['total']['mean_ns']/1000,empty_mean_us=empty['total']['mean_ns']/1000 if empty else None,all_request_mean_us=allmean/1000,directory_nonempty_us=nonempty['directory']['mean_ns']/1000,materialize_nonempty_us=nonempty['materialize']['mean_ns']/1000,ranking_nonempty_us=nonempty['ranking']['mean_ns']/1000))
            for strategy in ('PE-OFFLINE','TrieHI'):
                deltas=[]
                for w in r['workers']:
                    def mean(s):return next(x['total']['mean_ns'] for x in w['groups'] if x['recursive']==recursive and x['probes']==4 and x['strategy']==s and not x['empty'])
                    deltas.append((mean(strategy)-mean('PE-ONLINE'))/1000)
                paired.append(dict(experiment=num,recursive=recursive,strategy=strategy,negative_runs=sum(x<0 for x in deltas),positive_runs=sum(x>0 for x in deltas),zero_runs=sum(x==0 for x in deltas),mean_delta_us=sum(deltas)/len(deltas),min_delta_us=min(deltas),max_delta_us=max(deltas)))
    table('retrieval-probe4-comparison.csv',points);table('paired-signs.csv',paired)
    # Count workload root weights and empty cases; no query or scope regeneration.
    d=load(P/'notes/wiki-independent-preparation-20261027-01/fixture/directory-cases.json')
    s=load(P/'notes/wiki-independent-preparation-20261027-01/fixture/cases.json')
    roots=dict(directory_root_recursive=sum(x['path']=='/' and x['recursive'] for x in d),directory_recursive_cases=sum(x['recursive'] for x in d),search_root_recursive=sum(x['path']=='/' and x['recursive'] for x in s),search_recursive_cases=sum(x['recursive'] for x in s))
    result.update(status='passed',finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),counts=dict(counts),wiki_workload_root_weights=roots,
                  source_bindings=bindings,export_files={x.name:sha(x) for x in OUT.glob('*.csv')},
                  script_sha256=sha(Path(__file__)),measurements_started=0,core_modified=False,
                  full_report_parent_complete=False,small_scope_report_evidence_complete=True)
    save(OUT/'verification.json',result);print(json.dumps(dict(status='passed',counts=dict(counts),roots=roots)))
if __name__=='__main__':main()
