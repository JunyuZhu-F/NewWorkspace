# -*- coding: utf-8 -*-
"""Final report/provenance checks; no experiment runner is imported."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

P=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def main():
    target=HERE/'review-check.json';assert not target.exists()
    v=json.loads((HERE/'run-02/verification.json').read_text(encoding='utf-8'));assert v['status']=='passed'
    for name,h in v['source_bindings'].items():assert sha(P/name)==h,name
    for name,h in v['export_files'].items():assert sha(HERE/'run-02'/name)==h,name
    pdf=next((P/'paper').glob('*.pdf'));assert sha(pdf)=='00c59850614b7c286d82669b5e1447bacb5fb7115cbd442d8b29c801bd65e968'
    query=P/'dataset/raw/WIKI-Dir/dbpedia_dir_2m_query.jsonl'
    rows=[json.loads(line) for line in query.read_text(encoding='utf-8-sig').splitlines()]
    assert len(rows)==456 and all(set(x)=={'_id','text','metadata'} and x['metadata']=={} for x in rows)
    assert sha(query)=='23d24dfd4e57130a87c71da6da87768d6ae81d75f81bb46e26acf9f68ba9a731'
    docs=[P/x for x in ('REPORT_SMALL_SCALE.md','TASK.md','REPRODUCTION_PLAN.md','STATE.md','README.md','EXPERIMENTS.md')]
    links=0
    for f in docs:
        for link in re.findall(r'\]\(([^)]+)\)',f.read_text(encoding='utf-8')):
            if '://' in link or link.startswith('#'):continue
            path=link.strip('<>').split('#')[0]
            if path:assert (f.parent/path).exists(),(f,path);links+=1
    changed=subprocess.check_output(['git','diff','--name-only'],cwd=P,text=True).splitlines()
    assert all('/code/' not in x and '/experiments/' not in x for x in changed)
    raw004={name:sha(P/'experiments/EXP-20261027-004/raw'/name) for name in ('dsq.jsonl','dsm.jsonl','build.jsonl')}
    result=dict(status='passed',report_sha256=sha(P/'REPORT_SMALL_SCALE.md'),
        audit_sha256=sha(HERE/'run-02/verification.json'),document_links_checked=links,
        source_bindings_unchanged=len(v['source_bindings']),wiki_query_rows=456,wiki_empty_metadata_rows=456,
        adopted_pdf_sha256=sha(pdf),raw_004_read_in_audit_sha256=raw004,
        changed_tracked_paths=changed,core_and_experiment_files_modified=False,
        measurements_started=0,full_report_parent_complete=False,small_report_complete=True,
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip(),
        document_hashes={str(x.relative_to(P)):sha(x) for x in docs},script_sha256=sha(Path(__file__)))
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='passed',links=links,source_bindings=len(v['source_bindings']))))
if __name__=='__main__':main()
