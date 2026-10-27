import pathlib,json,hashlib,subprocess,csv,math
from datetime import datetime,timezone
p=pathlib.Path.cwd();e=p/'experiments/EXP-20261027-006'
def load(x):return json.loads(x.read_text(encoding='utf-8'))
def sha(x):
 h=hashlib.sha256()
 with x.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def dump(x,v):x.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
s=load(e/'status.json');v=load(e/'verification.json');cfg=load(e/'config.json');frozen=load(e/'source-hashes.json')
assert s['status']==v['status']=='passed' and s['measurements_completed']==5 and v['raw_timing_rows']==1202400
for name,h in frozen.items():assert sha(p/name)==sha(e/'source'/name)==h,name
for worker in v['workers']:
 d=p/worker['output']
 for name,h in worker['files'].items():assert sha(d/name)==h,(name,d)
fixture=p/s['fixture'];manifest=load(fixture/'manifest.json')
assert sha(fixture/'manifest.json')==cfg['fixture_manifest_sha256']
for name,h in manifest['files'].items():assert sha(fixture/name)==h,name
for name,info in manifest['inputs'].items():
 stat=(p/'dataset/raw/ARXIV-Dir'/name).stat();assert (stat.st_size,stat.st_mtime_ns)==(info['size'],info['mtime_ns'])
assert sha(e/'protocol.md')==sha(p/'notes/search02-protocol-20261027.md')==cfg['protocol_sha256']
assert sha(p/'code/build-Release-Search02/directory_search02.exe')==cfg['binary_sha256']
assert sha(e/'verification.json')==sha(e/'analysis-02/verification.json')
qa={'source_static':'20 PASS, 1 WARN (127mm custom report size), 0 FAIL','backend':'Python only; existing environment, no installation','visual_review':'Both final figures inspected; readable labels/units/error bars/legends, no clipping. Near-overlap of OFFLINE/TrieHI is genuine; no coordinate jitter or observations removed.','exclusion':'Only 266 empty year-local cases omitted from primary Recall curves, latency retained separately.','figures':{}}
for name in ('recursive','nonrecursive'):
 base=e/'analysis-02/figures';collision=load(base/(name+'.collision-audit.json'));text=load(base/(name+'.text-audit.json'));align=load(base/(name+'.alignment.json'))
 assert collision['auditable'] and collision['verdict']=='PASS' and collision['summary']['fail']==0 and collision['summary']['warn']==0
 assert text['auditable'] and text['below_minimum_count']==0 and text['minimum_found_pt']>=5
 assert align['verdict']=='NOT APPLICABLE' and not align['applicable']
 qa['figures'][name]={'collision':'PASS, 0 fail / 0 warn','minimum_pdf_font_pt':text['minimum_found_pt'],'alignment':'NOT APPLICABLE: single axis','exports':{ext:sha(base/(name+'.'+ext)) for ext in ('pdf','svg','png','tiff')}}
dump(e/'figure-qa.json',qa)
curves=list(csv.DictReader((e/'analysis-02/figures/curves.csv').open(encoding='utf-8')));assert len(curves)==24
for row in curves:
 recursive=row['recursive']=='True';probes=int(row['probes']);strategy=row['strategy']
 q=next(x for x in v['quality'] if x['recursive']==recursive and x['probes']==probes)
 g=next(x for x in v['groups'] if (x['strategy'],x['recursive'],x['probes'],x['empty'])==(strategy,recursive,probes,False))
 assert math.isclose(float(row['recall']),q['mean_recall_nonempty'],rel_tol=1e-12)
 assert math.isclose(float(row['mean_us'])*1000,g['total']['mean_ns'],rel_tol=1e-12)
for directory in ('experiments/EXP-20261027-004','experiments/EXP-20261027-005'):
 assert subprocess.check_output(['git','diff','HEAD','--',directory])==b''
old=load(p/'notes/search01-validation-20261027-01/source-final-hashes.json')
for name,h in {**old['files'],**old['unchanged_core_files']}.items():assert sha(p/name)==h
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='6a66c9e06a5ac8b08724b36a0f4523edf649d71c'
commands=[json.loads(x) for x in (e/'commands.jsonl').read_text(encoding='utf-8').splitlines()]
assert len(commands)==6 and all(x['exit_code']==0 for x in commands)
combined=hashlib.sha256(''.join(k+'\0'+h+'\n' for k,h in sorted(frozen.items())).encode()).hexdigest()
summary={'status':'passed','finished_utc':datetime.now(timezone.utc).isoformat(),'formal_workers':5,'raw_timing_rows':1202400,'baseline_answers':60120,'scope_records':15030,'protocol_sha256':cfg['protocol_sha256'],'source_files_reverified':len(frozen),'source_snapshot_hash':combined,'old_core_files_unchanged':30,'old_search01_frozen_files_unchanged':8,'old_004_005_unchanged':True,'source_raw_vector_size_mtime_unchanged':True,'fixture_and_all_worker_output_hashes_reverified':True,'figure_source_rows_checked':24,'plot_qa':'figure-qa.json','plot_copy_matches_verification':True,'no_dependencies_installed':True,'no_full_scale_started':True,'peak_private_bytes_sampled':max(x['peak_private_bytes_sampled'] for x in commands[:5]),'minimum_available_bytes_sampled':min(x['minimum_available_bytes'] for x in commands[:5]),'output_bytes_at_close':sum(x.stat().st_size for x in e.rglob('*') if x.is_file()),'next':'SCALE-01 resource/protocol/budget assessment; no automatic SCALE-02'}
dump(e/'final-check.json',summary)
print(json.dumps(summary))
