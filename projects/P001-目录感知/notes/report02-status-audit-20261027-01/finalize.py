# -*- coding: utf-8 -*-
"""Final document/link/evidence check. No measurement or benchmark invocation."""
import csv
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import psutil

P=Path.cwd();R=P/'notes/report02-status-audit-20261027-01'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    audit=read(R/'verification.json');assert audit['status']=='passed'
    assert all(sha(P/k)==h for k,h in audit['source_bindings'].items()),'evidence changed since audit'
    assert sha(R/'audit.py')==audit['audit_script_sha256']
    assert all(sha(R/k)==h for k,h in audit['exports'].items())
    strata=read(R/'stratification-check.json');assert strata['status']=='passed'
    assert sha(R/'scope-stratified.csv')==strata['output_sha256'] and sha(R/'stratify.py')==strata['script_sha256']
    assert sum(x['measurement_rows'] for x in audit['units'])==27600
    assert sum(x['full_scope_checks'] for x in audit['units'])==141450
    report=P/'REPORT_CURRENT.md';text=report.read_text(encoding='utf-8')
    mapping={
        'WIKI递归查询':('wiki','query-recursive'),'WIKI非递归查询（含空）':('wiki','query-local'),
        'WIKI large MOVE':('wiki','move-large'),'WIKI large MERGE':('wiki','merge-large'),'WIKI deep MERGE':('wiki','merge-deep'),
        'ARXIV递归查询':('arxiv','query-recursive'),'ARXIV非递归查询（含空）':('arxiv','query-local'),
        'ARXIV large MOVE':('arxiv','move-large'),'ARXIV large MERGE':('arxiv','merge-large'),'ARXIV deep MERGE':('arxiv','merge-deep')}
    with (R/'directory-25k-summary.csv').open(encoding='utf-8',newline='') as f:
        values={(r['dataset'],r['group'],r['strategy']):float(r['mean_us']) for r in csv.DictReader(f)}
    checked=0
    for label,(ds,group) in mapping.items():
        line=next(s for s in text.splitlines() if s.startswith('| '+label+' |'))
        columns=[s.strip() for s in line.split('|')][1:-1]
        for cell,strategy in zip(columns[1:4],['PE-ONLINE','PE-OFFLINE','TrieHI']):
            assert cell==f'{values[(ds,group,strategy)]:.4f}';checked+=1
    links=[]
    for doc in [report,R/'review.md']:
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',doc.read_text(encoding='utf-8')):
            if re.match(r'^[a-z]+://',target) or target.startswith('#'):continue
            file=target.split('#')[0].strip('<>');resolved=(doc.parent/file).resolve()
            assert resolved.is_relative_to(P) and resolved.exists(),(str(doc),target)
            links.append(dict(document=str(doc.relative_to(P)),target=target))
    plan=(P/'REPRODUCTION_PLAN.md').read_text(encoding='utf-8')
    assert next(s for s in plan.splitlines() if s.startswith('| REPORT-01-CURRENT-01 |')).split('|')[4].strip()=='已完成'
    assert next(s for s in plan.splitlines() if s.startswith('| REPORT-01 |')).split('|')[4].strip()=='进行中'
    assert 'REPORT_CURRENT.md' in (P/'STATE.md').read_text(encoding='utf-8')
    subprocess.run(['git','diff','--check'],cwd=P,check=True)
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip();assert head==audit['git_head']
    active=[]
    for proc in psutil.process_iter(['name','cmdline']):
        name=(proc.info['name'] or '').lower();args=' '.join(proc.info['cmdline'] or [])
        if name in ['scale_formal.exe','scale_directory.exe'] or (name.startswith('python') and any(s in args for s in ['scale_formal/pipeline.py','scale_directory/pipeline.py'])):active.append(proc.pid)
    assert not active
    docs=['REPORT_CURRENT.md','STATE.md','TASK.md','REPRODUCTION_PLAN.md','README.md','EXPERIMENTS.md'];hashes={}
    for name in docs:
        dest=R/'documentation'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(P/name,dest);hashes[name]=sha(P/name);assert sha(dest)==hashes[name]
    (R/'git-status-final.txt').write_bytes(subprocess.check_output(['git','-c','core.quotepath=false','status','--short'],cwd=P))
    (R/'git-diff-final.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=P))
    save(R/'command.json',dict(cwd=str(P),commands=[['D:/anaconda3/python.exe','-B',str((R/x).relative_to(P))] for x in ['audit.py','stratify.py','finalize.py']],scope='existing evidence/statistics only'))
    evidence={f.name:sha(f) for f in R.iterdir() if f.is_file() and f.name!='final-check.json'}
    save(R/'final-check.json',dict(status='passed',finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),git_head=head,report_numeric_cells_checked=checked,relative_links_checked=len(links),links=links,report_task_complete=True,full_report_parent_complete=False,source_bindings_unchanged=True,old_10k_report_unchanged=True,experiment_files_unchanged=True,new_measurements=0,vector_payload_bytes_read=0,active_tasks=active,git_diff_check='passed',documentation_sha256=hashes,evidence_sha256=evidence))
    print('PASS final document audit;',checked,'numeric cells;',len(links),'local links; report child complete, full-paper parent open')
if __name__=='__main__':main()
