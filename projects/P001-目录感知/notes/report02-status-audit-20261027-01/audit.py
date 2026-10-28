# -*- coding: utf-8 -*-
"""Evidence and descriptive-statistics audit only. Never runs a benchmark."""
import csv
from collections import defaultdict
import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import psutil

P=Path.cwd();R=P/'notes/report02-status-audit-20261027-01'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def rows(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f,delimiter='\t' if p.suffix=='.tsv' else ','))
def export(name,data):
    with (R/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
def q(v,p):
    a=sorted(v);rank=(len(a)-1)*p;i=int(rank)
    return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(rank-i)
def eq(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-7),(a,b)
def main():
    result=R/'verification.json';assert not result.exists(),'refuse to overwrite audit'
    audit=dict(status='running',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='REPORT-01-CURRENT-01; no new experiments, vector reads, compilation or algorithm edits')
    save(R/'status.json',audit)
    bindings={};nchecks=0
    def bind(path,expected=None):
        nonlocal nchecks
        h=sha(path)
        if expected is not None:assert h==expected,str(path)
        bindings[str(path.relative_to(P))]=h;nchecks+=1;return h
    old=read(P/'notes/report01-audit-20261027-01/run-02/verification.json');assert old['status']=='passed'
    for key,h in old['source_bindings'].items():bind(P/key,h)
    bind(P/'REPORT_SMALL_SCALE.md')
    old_sources=read(P/'experiments/EXP-20261027-007/source-hashes.json')
    for key,h in old_sources.items():bind(P/key,h)
    bundle=P/'notes/reading-20261026/source_bundle.json';paper=read(bundle);bind(P/paper['source_path'] if not Path(paper['source_path']).is_absolute() else Path(paper['source_path']),paper['source_sha256']);bind(bundle)
    save(R/'paper-excerpts.json',dict(source_sha256=paper['source_sha256'],pdf_page_numbering=True,pages=[p for p in paper['pages'] if p['pdf_page'] in [9,10,11,12]]))
    summary_rows=[];quantiles=[];depth_rows=[];profiles=[];stats=[];worker_files=0;per_run_cells=0;case_cells=0
    for dataset,exp,want in [('wiki','EXP-20261027-009',(23115,20100,3015)),('arxiv','EXP-20261027-010',(8625,7500,1125))]:
        root=P/'experiments'/exp;verification=read(root/'analysis-01/verification.json');assert verification['status']=='passed' and read(root/'final-check.json')['post_review']=='passed'
        for key in ['record.md','review.md','results.md','review-check.json','final-check.json','status.json','config.json','protocol.md','source-hashes.json','old-source-hashes.json','analysis-01/verification.json']:bind(root/key)
        for key,h in read(root/'source-hashes.json').items():bind(P/key,h);bind(root/'source'/key,h)
        for key,h in read(root/'old-source-hashes.json').items():bind(root/'source'/key,h)
        bind(root/'build/scale_formal.exe',read(root/'build/binary.json')['sha256'])
        bind(root/'build/scale_formal.cpp',read(root/'build/binary.json')['generated_sha256'])
        fixture=Path(read(root/'config.json')['fixture']);manifest=read(fixture/'manifest.json');bind(fixture/'manifest.json')
        for key,h in manifest['files'].items():bind(fixture/key,h)
        cases=read(fixture/'directory-cases.json');bycase={c['case']:c for c in cases};local=[c for c in cases if not c['recursive']];recursive=[c for c in cases if c['recursive']]
        profiles.append(dict(dataset=dataset,experiment=exp,records=manifest['records'],directories=manifest['directories'],max_depth=manifest['max_depth'],recursive_cases=len(recursive),local_cases=len(local),root_recursive_cases=sum(c['path']=='/' for c in recursive),empty_recursive_cases=sum(c['candidates']==0 for c in recursive),empty_local_cases=sum(c['candidates']==0 for c in local),missing_layers=manifest['missing_layers'],sample_selection='floor(i*(total-1)/(N-1)); not a nested growth experiment'))
        groups=defaultdict(list);casegroups=defaultdict(list);depthgroups=defaultdict(list);raw_count=0;warm_count=0;seen=set()
        for run in verification['runs']:
            out=Path(run['path'])
            for key,h in run['files'].items():bind(out/key,h);worker_files+=1
            for row in rows(out/'timings.tsv'):
                raw_count+=1;pid=int(row['run']);iteration=int(row['pass']);warm=int(row['warmup']);assert pid==run['run'] and warm==int(iteration<3) and 0<=iteration<23
                cell=(pid,row['strategy'],iteration,row['kind'],row['case']);assert cell not in seen;seen.add(cell)
                if warm:warm_count+=1;continue
                ns=int(row['total_ns']);assert ns>=0
                group=('query-recursive' if bycase[row['case']]['recursive'] else 'query-local') if row['kind']=='query' else row['case']
                groups[(row['strategy'],group,pid)].append(ns)
                casegroups[(row['strategy'],row['kind'],row['case'],pid)].append(ns)
                if row['kind']=='query':
                    case=bycase[row['case']];depthgroups[(row['strategy'],case['recursive'],case['depth'],pid)].append(ns)
        assert (raw_count,raw_count-warm_count,warm_count)==want
        for row in rows(root/'analysis-01/per-run.csv'):
            v=groups[(row['strategy'],row['group'],int(row['run']))];assert len(v)==int(row['count'])
            eq(sum(v)/len(v)/1000,row['mean_us']);eq(q(v,.5)/1000,row['p50_us']);eq(q(v,.95)/1000,row['p95_us']);per_run_cells+=1
        for row in rows(root/'analysis-01/per-case-run.csv'):
            v=casegroups[(row['strategy'],row['kind'],row['case'],int(row['run']))];assert len(v)==int(row['count'])==20
            eq(sum(v)/len(v)/1000,row['mean_us']);eq(q(v,.5)/1000,row['p50_us']);eq(q(v,.95)/1000,row['p95_us']);case_cells+=1
        for row in rows(root/'analysis-01/summary.csv'):
            s,g=row['strategy'],row['group'];means=[sum(groups[(s,g,i)])/len(groups[(s,g,i)])/1000 for i in range(5)]
            assert int(row['processes'])==5;eq(statistics.fmean(means),row['mean_us']);eq(statistics.stdev(means),row['sd_process_means_us'])
            summary_rows.append(dict(dataset=dataset,experiment=exp,strategy=s,group=g,processes=5,mean_us=statistics.fmean(means),sd_process_means_us=statistics.stdev(means)))
            if g.startswith('query-'):
                allns=[n for i in range(5) for n in groups[(s,g,i)]]
                quantiles.append(dict(dataset=dataset,strategy=s,mode=g,calls=len(allns),independent_processes=5,anchors=len(recursive) if g=='query-recursive' else len(local),mean_us=sum(allns)/len(allns)/1000,p90_us=q(allns,.9)/1000,p95_us=q(allns,.95)/1000,p99_us=q(allns,.99)/1000,p999_us=q(allns,.999)/1000,quantile_rule='linear on pooled measured calls; finite sample; not independent queries'))
        for s,mode,depth in sorted({k[:3] for k in depthgroups}):
            means=[sum(depthgroups[(s,mode,depth,i)])/len(depthgroups[(s,mode,depth,i)])/1000 for i in range(5)]
            selected=[c for c in cases if c['recursive']==mode and c['depth']==depth]
            depth_rows.append(dict(dataset=dataset,strategy=s,recursive=mode,depth=depth,anchors=len(selected),mean_candidates=statistics.fmean(c['candidates'] for c in selected),mean_direct_children=statistics.fmean(c['children'] for c in selected),mean_subtree_directories_including_self=statistics.fmean(c['descendant_directories'] for c in selected),mean_us=statistics.fmean(means),sd_process_means_us=statistics.stdev(means)))
        for key,h in verification['csv_files'].items():bind(root/'analysis-01'/key,h)
        stats.append(dict(experiment=exp,raw_rows=raw_count,measurement_rows=raw_count-warm_count,warmup_rows=warm_count,full_scope_checks=verification['full_scope_checks'],processes=5,geometry=verification['geometry']))
    export('directory-25k-summary.csv',summary_rows);export('directory-25k-quantiles.csv',quantiles);export('directory-25k-depth.csv',depth_rows);save(R/'scope-profile.json',profiles)
    active=[]
    for proc in psutil.process_iter(['name','cmdline']):
        name=(proc.info['name'] or '').lower();args=' '.join(proc.info['cmdline'] or [])
        if name in ['scale_formal.exe','scale_directory.exe'] or (name.startswith('python') and any(s in args for s in ['scale_formal/pipeline.py','scale_directory/pipeline.py'])):active.append(proc.pid)
    assert not active
    audit.update(status='passed',finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip(),hash_checks=nchecks,worker_files=worker_files,old_report_source_bindings_checked=len(old['source_bindings']),old_53_current_sources_unchanged=True,per_run_statistic_cells_checked=per_run_cells,per_case_statistic_cells_checked=case_cells,units=stats,active_tasks=[],new_measurements=0,vector_payload_bytes_read=0,source_bindings=bindings,exports={f.name:sha(f) for f in R.glob('*.csv')},audit_script_sha256=sha(Path(__file__)))
    save(result,audit);save(R/'status.json',{k:v for k,v in audit.items() if k not in ['source_bindings','units','exports']})
    print('PASS report audit;',worker_files,'worker files;',per_run_cells,'run cells;',case_cells,'case cells;',nchecks,'hash checks; no measurements')
if __name__=='__main__':main()
