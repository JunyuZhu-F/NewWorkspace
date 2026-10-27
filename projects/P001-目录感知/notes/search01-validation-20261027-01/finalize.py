import pathlib,json,hashlib,subprocess,shutil,platform,re,sys,os
from datetime import datetime,timezone
p=pathlib.Path.cwd(); out=p/'notes/search01-validation-20261027-01'
def load(x):return json.loads(x.read_text(encoding='utf-8'))
def sha(x):return hashlib.sha256(x.read_bytes()).hexdigest()
def write(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
v=load(out/'verification.json'); r=load(out/'recovery-01/status.json'); old=load(out/'source-hashes.json')
assert v['status']==r['status']=='passed' and v['cross_build_equal']
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='6a66c9e06a5ac8b08724b36a0f4523edf649d71c'
for name,h in old['unchanged_core'].items():assert sha(p/name)==h,name
for name,h in old['new_sources'].items():
    assert sha(out/'source'/name)==h,name
    if name!='code/search/validate.py':assert sha(p/name)==h,name
assert sha(p/'code/search/validate.py')==r['runner_sha256']==sha(out/'recovery-01/validate.py')
for build,output in zip(('Release-Search','RelWithDebInfo-ASan-Search'),('release','asan')):
    assert sha(p/f'code/build-{build}/directory_search.exe')==r['binary_hashes'][build]
    for name,h in v['builds'][0]['hashes'].items():assert sha(out/output/name)==h
for label in ('build-release','build-asan'):
    assert '100% tests passed' in (out/(label+'.log')).read_text(encoding='utf-8',errors='replace')
for dirname in ('experiments/EXP-20261027-004','experiments/EXP-20261027-005'):
    assert not subprocess.check_output(['git','diff','HEAD','--',dirname]),dirname
sources=sorted(list((p/'code/search').glob('*.py'))+list((p/'code/search').glob('*.cpp'))+[p/'code/search/CMakeLists.txt',p/'code/search/README.md',p/'code/scripts/build-search.cmd',p/'notes/search01-protocol-20261027.md'])
final_source=out/'source-final'; final_source.mkdir(exist_ok=False)
for x in sources:
    target=final_source/x.relative_to(p);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,target)
write('source-final-hashes.json',{'files':{x.relative_to(p).as_posix():sha(x) for x in sources},'unchanged_core_files':old['unchanged_core'],'old_snapshot_preserved':True,'runner_environment_repair_only':True})
env={'captured_utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':sys.version,'numpy_version':__import__('numpy').__version__,'processor_identifier':os.environ.get('PROCESSOR_IDENTIFIER'),'logical_cpus':os.cpu_count(),'compiler_and_flags':{},'source_working_tree_start':'clean','core_algorithm_changed':False,'full_vectors_loaded':False}
for build in ('Release-Search','RelWithDebInfo-ASan-Search'):
    b=p/f'code/build-{build}';cache=(b/'CMakeCache.txt').read_text(encoding='utf-8');shutil.copyfile(b/'CMakeCache.txt',out/f'cmake-{build}.txt')
    env['compiler_and_flags'][build]={'compiler':re.search(r'^CMAKE_CXX_COMPILER:FILEPATH=(.+)$',cache,re.M).group(1),'flags':sorted({line.strip() for line in (b/'build.ninja').read_text(encoding='utf-8').splitlines() if line.startswith('  FLAGS =')})}
runtime=pathlib.Path(r['commands'][0]['added_runtime_path'])/'clang_rt.asan_dynamic-x86_64.dll'
env['asan_runtime']={'path':str(runtime),'sha256':sha(runtime),'applied_to_child_path_only':True}
write('environment.json',env)
final={'status':'passed','scope':'SEARCH-01 current time/exact-IVF admission only','cases':104,'nonempty_cases':64,'empty_cases':40,'original_constraint_cases_all_empty':32,'diagnostic_nonempty_query_ids':[0],'release_results':1248,'asan_results':1248,'scope_rows_each_build':312,'old_core_files_unchanged':len(old['unchanged_core']),'old_004_005_git_content_unchanged':True,'failed_initial_launch_preserved':'run-status.json','recovery_status':'recovery-01/status.json','independent_verification':'verification.json','protocol_sha256':sha(p/'notes/search01-protocol-20261027.md'),'sources':'source-final-hashes.json','binary_hashes':r['binary_hashes'],'no_query_latency_claim':True,'search02_started':False,'finished_utc':datetime.now(timezone.utc).isoformat()}
write('final-status.json',final)
print(json.dumps(final))
