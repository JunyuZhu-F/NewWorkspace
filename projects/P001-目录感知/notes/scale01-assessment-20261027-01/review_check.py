# -*- coding: utf-8 -*-
"""Review resource arithmetic, provenance and document scope without new workloads."""
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

P=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    assert not (OUT/'review-check.json').exists()
    a=load(OUT/'assessment.json');p=load(OUT/'profile.json');assert a['assessment_complete'] and p['status']=='passed'
    assert not a['scale01_parent_approval_complete'] and not a['scale02_authorized'] and not a['scale02_started']
    assert p['vector_payload_bytes_read']==0 and len(p['geometry'])==8
    for name,h in a['evidence'].items():assert sha(P/name)==h,name
    assert sha(OUT/'profile.json')==a['profile_sha256']
    for name,h in load(P/'experiments/EXP-20261027-006/source-hashes.json').items():assert sha(P/name)==h,name
    constraints=P/'dataset/raw/ARXIV-Dir/arxiv_query_constraint.json';original=load(P/'experiments/EXP-20261027-006/input-manifest.json')
    assert sha(constraints)==original['constraints_sha256']
    # Different ancestor enumeration on the already-frozen baseline samples.
    for ds,source in [('ARXIV','notes/search02-preparation-20261027-01/fixture/sample.json'),('WIKI','notes/wiki-preparation-20261027-01/run-01/sample.json')]:
        sample=load(P/source);dirs={'/'};bytecount=0;depthsum=0
        assert len(sample)==10000
        for row in sample:
            path=row['path'];bytecount+=len(path.encode());depthsum+=path.count('/')-1
            while path!='/':dirs.add(path);path=path[:path.rfind('/',0,len(path)-1)+1]
        g=next(g for g in p['geometry'] if g['dataset']==ds and g['n']==10000)
        assert len(dirs)==g['directories'] and bytecount==g['entry_path_utf8_bytes']
        assert abs(depthsum/10000-g['mean_entry_depth'])<1e-12
    rows=list(csv.DictReader((OUT/'memory-and-geometry-scenarios.csv').open(encoding='utf-8')))
    for r in rows:
        n=int(r['n']);assert int(r['fvecs_derived_bytes'])==4100*n and int(r['cpp_float_payload_bytes'])==4096*n
        assert int(r['oracle_float64_matrix_bytes'])==8192*n and int(r['oracle_three_matrix_temporary_scenario_bytes'])==24576*n
        g=next(g for g in p['geometry'] if g['dataset']==r['dataset'] and g['n']==n)
        assert int(r['geometry_reference_pairs'])==n*g['directories']
        c=g['search_workload_geometry'][r['query_set']]['sum_candidate_ids_per_probe']
        assert int(r['candidates_plus_hits_min_bytes'])==48*c and int(r['candidates_plus_hits_stl_scenario_bytes'])==112*c
    assert len(rows)==16
    full=load(OUT/'assessment.json')['full_data_bounds']
    for row in full:assert row['file_bytes']==4100*row['records'] and row['cpp_float_payload_bytes']==4096*row['records']>2**31
    for ds,info in p['vectors'].items():
        s=(P/info['path']).stat();assert (s.st_size,s.st_mtime_ns)==(info['size'],info['mtime_ns'])
    expected={'ARXIV':[423,428,431,432],'WIKI':[23025,43589,69160,106921]}
    for ds,values in expected.items():assert [g['directories'] for g in p['geometry'] if g['dataset']==ds]==values
    docs=[P/name for name in ('SCALE_ASSESSMENT.md','TASK.md','REPRODUCTION_PLAN.md','STATE.md','README.md','EXPERIMENTS.md')]
    links=0
    for f in docs:
        for link in re.findall(r'\]\(([^)]+)\)',f.read_text(encoding='utf-8')):
            if '://' in link or link.startswith('#'):continue
            path=link.strip('<>').split('#')[0]
            if path:assert (f.parent/path).exists(),(str(f),path);links+=1
    plan=(P/'REPRODUCTION_PLAN.md').read_text(encoding='utf-8')
    assert re.search(r'\| SCALE-01 \|[^\n]+\| 进行中 \|',plan)
    assert re.search(r'\| SCALE-01-ASSESS \|[^\n]+\| 已完成 \|',plan)
    assert re.search(r'\| SCALE-02 \|[^\n]+\| 未开始 \|',plan)
    changed=subprocess.check_output(['git','diff','--name-only'],cwd=P,text=True).splitlines();assert all('/code/' not in x and '/experiments/' not in x for x in changed)
    result=dict(status='passed',assessment_only=True,approval_received=False,scale02_started=False,
                metadata_profiles=8,baseline_10k_geometry_crosschecked=True,memory_scenario_rows_checked=len(rows),
                source_bindings_checked=len(a['evidence']),old_source_entries_checked=46,document_links_checked=links,
                current_git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip(),
                assessment_sha256=sha(OUT/'assessment.json'),profile_sha256=sha(OUT/'profile.json'),
                output_hashes={x.name:sha(x) for x in OUT.iterdir() if x.is_file() and x.name!='review-console.log'},
                document_hashes={str(x.relative_to(P)):sha(x) for x in docs},
                changed_tracked_paths=changed,core_and_experiment_files_modified=False,
                caveat='Scenario arithmetic and provenance passed; no new-N index/ANN/runtime/peak-memory admission was performed.')
    (OUT/'review-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='passed',profiles=8,memory_rows=len(rows),links=links,approval_received=False)))
if __name__=='__main__':main()
