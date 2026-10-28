# -*- coding: utf-8 -*-
"""Separate empty/nonempty directory requests from already audited case means."""
import csv
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics

P=Path.cwd();R=P/'notes/report02-status-audit-20261027-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def rows(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def main():
    assert not (R/'scope-stratified.csv').exists()
    verified=read(R/'verification.json');assert verified['status']=='passed';out=[];bindings={}
    for ds,exp in [('wiki','EXP-20261027-009'),('arxiv','EXP-20261027-010')]:
        root=P/'experiments'/exp;source=root/'analysis-01/per-case-run.csv';key=str(source.relative_to(P));assert sha(source)==verified['source_bindings'][key];bindings[key]=sha(source)
        fixture=Path(read(root/'config.json')['fixture']);cases={c['case']:c for c in read(fixture/'directory-cases.json')};pools=defaultdict(list)
        for row in rows(source):
            if row['kind']!='query':continue
            c=cases[row['case']];pools[(row['strategy'],c['recursive'],c['candidates']==0,int(row['run']))].append(float(row['mean_us']))
        summaries=rows(root/'analysis-01/summary.csv')
        for s,mode,empty in sorted({k[:3] for k in pools}):
            v=[statistics.fmean(pools[(s,mode,empty,run)]) for run in range(5)];anchors=len(pools[(s,mode,empty,0)])
            out.append(dict(dataset=ds,strategy=s,recursive=mode,empty=empty,anchors=anchors,processes=5,calls=anchors*20*5,mean_us=statistics.fmean(v),sd_process_means_us=statistics.stdev(v)))
        for s in ['PE-ONLINE','PE-OFFLINE','TrieHI']:
            for mode in [False,True]:
                group='query-recursive' if mode else 'query-local';original=next(float(x['mean_us']) for x in summaries if x['strategy']==s and x['group']==group)
                strata=[x for x in out if x['dataset']==ds and x['strategy']==s and x['recursive']==mode]
                weighted=sum(x['anchors']*x['mean_us'] for x in strata)/sum(x['anchors'] for x in strata)
                assert math.isclose(original,weighted,rel_tol=1e-12,abs_tol=1e-7)
    with (R/'scope-stratified.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    result=dict(status='passed',source_bindings=bindings,strata=len(out),weighted_means_reconstruct_original=True,script_sha256=sha(Path(__file__)),output_sha256=sha(R/'scope-stratified.csv'),new_measurements=0)
    (R/'stratification-check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('PASS empty/nonempty strata and weighted-mean reconstruction')
if __name__=='__main__':main()
