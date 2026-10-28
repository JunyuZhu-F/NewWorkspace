# -*- coding: utf-8 -*-
"""Analytical resource scenarios from metadata geometry and historical telemetry."""
import csv
import hashlib
import json
from pathlib import Path
import statistics

P=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
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
    assert not (OUT/'assessment.json').exists()
    profile=load(OUT/'profile.json');assert profile['status']=='passed' and profile['vector_payload_bytes_read']==0
    bindings={str((OUT/'profile.json').relative_to(P)):sha(OUT/'profile.json')}
    historical={};rows=[]
    for num in ('006','007','008'):
        e=P/'experiments'/('EXP-20261027-'+num);events=[json.loads(x) for x in (e/'commands.jsonl').read_text().splitlines()]
        bindings[str((e/'commands.jsonl').relative_to(P))]=sha(e/'commands.jsonl')
        groups={}
        for x in events:
            label=x['label'];kind='verifier' if label.startswith('verify') else 'phase_worker' if label.startswith('run-phase') else 'worker'
            groups.setdefault(kind,[]).append(x)
        stats={k:dict(count=len(v),max_seconds=max(x['elapsed_seconds'] for x in v),mean_seconds=statistics.mean(x['elapsed_seconds'] for x in v),max_private_bytes_sampled=max(x['peak_private_bytes_sampled'] for x in v),minimum_available_bytes=min(x['minimum_available_bytes'] for x in v)) for k,v in groups.items()}
        historical[num]=stats
        for kind,r in stats.items():rows.append(dict(experiment=num,kind=kind,**r))
        if num!='007':
            setups=[]
            for f in e.glob('run-*/setup.csv'):
                bindings[str(f.relative_to(P))]=sha(f)
                v=list(csv.DictReader(f.open()));setups.append(dict(load_train_s=max(int(x['common_load_train_ns']) for x in v)/1e9,index_build_validate_s=sum(int(x['index_build_validate_ns']) for x in v)/1e9))
            historical[num]['setup_max']=dict(load_train_s=max(x['load_train_s'] for x in setups),index_build_validate_s=max(x['index_build_validate_s'] for x in setups))
    table('historical-telemetry.csv',rows)
    for name in ('code/search/search.cpp','code/search02/benchmark.cpp','code/search02/verify.py','code/search02/pipeline.py','code/wiki_experiment/prepare.py','code/wiki_experiment/directory.cpp','code/wiki_experiment/verify.py','code/wiki_experiment/pipeline.py','code/include/directory/bitmap.hpp'):
        bindings[name]=sha(P/name)
    stl=Path('D:/Microsoft Visual Studio/VC/Tools/MSVC/14.51.36231/include/vector');text=stl.read_text(encoding='utf-8');start=text.index('size_type _Calculate_growth(');snippet=text[start:text.index('    _CONSTEXPR20 void _Buy_raw',start)]
    assert '_Oldcapacity + _Oldcapacity / 2' in snippet
    (OUT/'stl-vector-growth.txt').write_text(str(stl)+'\nSHA256 '+sha(stl)+'\n'+snippet,encoding='utf-8')
    geometry=[];timings=[]
    for g in profile['geometry']:
        n=g['n'];baseline=next(x for x in profile['geometry'] if x['dataset']==g['dataset'] and x['n']==10000)
        for name,c in g['search_workload_geometry'].items():
            geometry.append(dict(dataset=g['dataset'],n=n,directories=g['directories'],query_set=name,cases=c['cases'],nonrecursive_nonempty=c['nonrecursive_nonempty'],
                fvecs_derived_bytes=4100*n,cpp_float_payload_bytes=4096*n,cpp_float_vector_reallocation_payload_scenario_bytes=10240*n,
                oracle_float64_matrix_bytes=8192*n,oracle_three_matrix_temporary_scenario_bytes=24576*n,
                candidates_plus_hits_min_bytes=c['baseline_candidate_and_hit_capacity_min_bytes'],candidates_plus_hits_stl_scenario_bytes=c['baseline_candidate_and_hit_payload_stl_1p5_scenario_bytes'],scopes_ascii_payload_scenario_bytes=c['scopes_ascii_worst_payload_bytes'],
                geometry_reference_pairs=n*g['directories'],vector_bytes_fit_2gib=4096*n<2**31,three_matrix_scenario_fits_2gib=24576*n<2**31))
            num='006' if g['dataset']=='ARXIV' else '008';h=historical[num];fullname='full501' if num=='006' else 'full456';base=baseline['search_workload_geometry'][fullname]
            n_ratio=n/10000;geometry_ratio=max(n_ratio,g['directories']/baseline['directories'],g['entry_path_utf8_bytes']/baseline['entry_path_utf8_bytes'])
            q_ratio=c['cases']/base['cases'];work_ratio=max(c['sum_candidate_ids_per_probe']/base['sum_candidate_ids_per_probe'],q_ratio,q_ratio*g['directories']/baseline['directories'])
            setup=h['setup_max'];remaining=max(0,h['worker']['max_seconds']-setup['load_train_s']-setup['index_build_validate_s'])
            worker=setup['load_train_s']*n_ratio+setup['index_build_validate_s']*geometry_ratio+remaining*work_ratio
            verifier=h['verifier']['max_seconds']*max(n_ratio,g['directories']/baseline['directories']*n_ratio)
            matrix=5*worker+verifier
            timings.append(dict(dataset=g['dataset'],n=n,query_set=name,kind='retrieval',worker_scenario_seconds=worker,matrix_scenario_seconds=matrix,stress_2x_matrix_seconds=2*matrix,worker_under_existing_600_scenario=worker<600,matrix_under_existing_1800_scenario=matrix<1800,qualification='heuristic scenario only; not an upper bound or a measured runtime'))
        if g['dataset']=='WIKI':
            h=historical['007'];ratio=max(n/10000,g['directories']/baseline['directories'],g['entry_path_utf8_bytes']/baseline['entry_path_utf8_bytes'])
            worker=h['worker']['max_seconds']*ratio;verify=h['verifier']['max_seconds']*(n*g['directories'])/(10000*baseline['directories'])
            timings.append(dict(dataset='WIKI',n=n,query_set='up_to64_directory_cases',kind='directory_default_only',worker_scenario_seconds=worker,matrix_scenario_seconds=5*worker+verify,stress_2x_matrix_seconds=2*(5*worker+verify),worker_under_existing_600_scenario=worker<600,matrix_under_existing_1800_scenario=5*worker+verify<1800,qualification='heuristic scenario only; no matching new-N run'))
    table('memory-and-geometry-scenarios.csv',geometry);table('time-scenarios.csv',timings)
    full=[]
    for ds,x in profile['vectors'].items():
        n=x['size']//4100;assert x['size']%4100==0
        full.append(dict(dataset=ds,records=n,file_bytes=x['size'],cpp_float_payload_bytes=4096*n,oracle_float64_matrix_bytes=8192*n,full_float_payload_exceeds_current_private_limit=4096*n>2**31))
    table('full-data-lower-bounds.csv',full)
    # Confirm the metadata-only calculation agrees with previously verified 10k scopes.
    for ds,num,folder in [('ARXIV','006','run-0'),('WIKI','008','run-search-0')]:
        e=P/'experiments'/('EXP-20261027-'+num);f=e/folder/'scopes.tsv';sums={}
        with f.open(encoding='utf-8') as h:
            for line in h:
                strategy,case,exists,ids=line.rstrip('\n').split('\t');count=ids.count(',')+1 if ids else 0;sums[strategy]=sums.get(strategy,0)+count
        expected=next(g for g in profile['geometry'] if g['dataset']==ds and g['n']==10000)['search_workload_geometry']['full501' if ds=='ARXIV' else 'full456']['sum_candidate_ids_per_probe']
        assert len(sums)==3 and all(x==expected for x in sums.values())
        bindings[str(f.relative_to(P))]=sha(f)
    decision=dict(status='assessment_complete_pending_approval',assessment_complete=True,scale01_parent_approval_complete=False,scale02_authorized=False,scale02_started=False,
        recommended_first_batch=dict(scope='pure directory default API only; diagnostics a separately decided extension',datasets=['ARXIV-time','WIKI'],records_per_dataset=25000,strategies_per_worker=3,processes_per_dataset=5,warmups=3,measurements=20,max_real_anchors=32,modes_per_anchor=2,continuous_maintenance_operations=4,
            start_available_bytes=4*2**30,minimum_available_bytes=2**31,worker_private_limit_bytes=2**31,worker_seconds=600,per_dataset_matrix_seconds=1800,disk_start_free_bytes=10*2**30,per_experiment_output_bytes=2**30,
            software_admission_required=True,formal_only_after_approval=True,new_n_release_admission_passes=1,asan_adapter_admission_max_records=5000,no_forced_pass_if_over_budget=True),
        later_retrieval_candidates=['ARXIV 25000 with 501 original time queries, conditional on oracle admission','WIKI 25000 with 64 preselected query IDs, new declared workload, conditional on admission'],
        rejected_first_batches=['full corpus with present in-memory loader and 2GiB private cap','100000 retrieval with existing float64 oracle','WIKI 25000 full456 unchanged matrix without time-budget review','50000/100000 automatic launch or new giant fixture before admission'],
        evidence=bindings,historical_telemetry=historical,full_data_bounds=full,profile_sha256=sha(OUT/'profile.json'),stl_source_sha256=sha(stl),analysis_script_sha256=sha(Path(__file__)),
        scenario_caveat='All new-N runtime and memory scenarios are analytical screens, not successful execution or guaranteed process peaks. No vector payload was read in this assessment.')
    save(OUT/'assessment.json',decision);print(json.dumps(dict(status=decision['status'],scenarios=len(timings),baseline_scope_geometry_matches=True)))
if __name__=='__main__':main()
