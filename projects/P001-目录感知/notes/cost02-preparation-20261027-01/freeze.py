"""Save the admitted source/protocol version; does not run a benchmark."""
import hashlib,importlib.util,json,platform,re,subprocess,sys,zipfile
from pathlib import Path
here=Path(__file__).resolve().parent;project=here.parent.parent
spec=importlib.util.spec_from_file_location('runner',project/'code/scripts/run-cost02.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files={str(p.relative_to(project)).replace('\\','/'):sha(p) for p in runner.source_files(project)}
fixtures={p.name:sha(p) for p in (project/'notes/benchmark-fixtures-20261026-01').iterdir() if p.is_file()}
assert len(fixtures)==10
combined=hashlib.sha256(''.join(f'{k}\0{v}\n' for k,v in sorted(files.items())).encode()).hexdigest()
protocol=project/'notes/benchmark-cost-protocol-20261027.md'
frozen={'snapshot':'COST02-'+combined[:16],'source_snapshot_hash':combined,'hash_scope':'code files only, canonical sorted path NUL hash newline; protocol and fixtures separately hashed',
        'files':files,'fixtures':fixtures,'protocol_sha256':sha(protocol),
        'release_binary_sha256':{mode:sha(project/f'code/build-Release-Cost/directory_cost_{mode}.exe') for mode in ['phase','allocation']},
        'asan_binary_sha256':{mode:sha(project/f'code/build-RelWithDebInfo-ASan-Cost/directory_cost_{mode}.exe') for mode in ['phase','allocation']},
        'git_base_commit':subprocess.run(['git','rev-parse','HEAD'],cwd=project,capture_output=True,text=True,check=True).stdout.strip(),
        'formal_matrix_run':False}
archive=here/'source-snapshot.zip'
if archive.exists():raise FileExistsError('Refusing to overwrite a frozen snapshot')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for name in sorted(files):z.write(project/name,name)
    for name in sorted(fixtures):z.write(project/'notes/benchmark-fixtures-20261026-01'/name,'fixtures/'+name)
    z.write(protocol,'protocol.md')
frozen['snapshot_zip_sha256']=sha(archive)
(here/'source-hashes.json').write_text(json.dumps(frozen,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
(here/'source-diff.patch').write_bytes(subprocess.run(['git','diff','--binary','--','code'],cwd=project,capture_output=True,check=True).stdout)
builds={}
for name in ['build-Release-Cost','build-RelWithDebInfo-ASan-Cost']:
    root=project/'code'/name;cache=(root/'CMakeCache.txt').read_text(encoding='utf-8')
    compiler=next((root/'CMakeFiles').glob('*/CMakeCXXCompiler.cmake')).read_text(encoding='utf-8')
    version=re.search(r'set\(CMAKE_CXX_COMPILER_VERSION "([^"]+)"',compiler)
    builds[name]={'compiler_version':version.group(1),'cache':{s.split('=',1)[0]:s.split('=',1)[1] for s in cache.splitlines() if s.startswith(('CMAKE_BUILD_TYPE:','CMAKE_CXX_COMPILER:','DIRECTORY_ENABLE_ASAN:','DIRECTORY_BUILD_COST_DIAGNOSTICS:'))},
                  'flags':sorted({s.strip() for s in (root/'build.ninja').read_text(encoding='utf-8').splitlines() if s.startswith('  FLAGS =')})}
(here/'build-info.json').write_text(json.dumps({'platform':platform.platform(),'python':sys.version,'builds':builds},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'snapshot':frozen['snapshot'],'code_files':len(files),'protocol_sha256':frozen['protocol_sha256'],'formal_matrix_run':False}))
