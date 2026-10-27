"""Run the frozen DIR-01 matrix; --plan-only performs no measurement."""
import argparse, ctypes, datetime, hashlib, json, os, platform, re, shutil, subprocess, sys, time
from pathlib import Path

STRATEGIES=['pe_online','pe_offline','trie_hi']
WORKLOADS=[('figure2','build'),('figure2','dsq'),('figure2','move'),('figure2','merge'),('time','build'),('time','dsq'),('time','dsm')]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def matrix():
    for run in range(5):
        order=STRATEGIES[run%3:]+STRATEGIES[:run%3]
        for input_name,subload in WORKLOADS:
            for strategy in order:
                for instrumented in (False,True): yield run,input_name,subload,strategy,instrumented
def available_memory():
    class Memory(ctypes.Structure): _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('avail',ctypes.c_ulonglong),('total_page',ctypes.c_ulonglong),('avail_page',ctypes.c_ulonglong),('total_virtual',ctypes.c_ulonglong),('avail_virtual',ctypes.c_ulonglong),('avail_extended',ctypes.c_ulonglong)]
    m=Memory();m.length=ctypes.sizeof(m)
    return int(m.avail) if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)) else None
def copy_source(project,dest):
    (dest/'code').mkdir(parents=True)
    for src in sorted((project/'code').iterdir()):
        if src.name.startswith('build') or src.name=='__pycache__': continue
        target=dest/'code'/src.name
        if src.is_dir(): shutil.copytree(src,target,ignore=shutil.ignore_patterns('__pycache__'))
        else: shutil.copy2(src,target)
    shutil.copytree(project/'notes/benchmark-fixtures-20261026-01',dest/'fixtures')
    manifest={str(p.relative_to(dest)).replace('\\','/'):sha(p) for p in sorted(dest.rglob('*')) if p.is_file()}
    combined=hashlib.sha256(''.join(f'{k}\0{v}\n' for k,v in sorted(manifest.items())).encode()).hexdigest()
    (dest/'hashes.json').write_text(json.dumps({'source_snapshot_hash':combined,'files':manifest},indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return combined
def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=Path('.'));p.add_argument('--experiment-id');p.add_argument('--plan-only',action='store_true');a=p.parse_args();project=a.project.resolve()
    jobs=list(matrix());protocol=project/'notes/benchmark-protocol.md'
    if a.plan_only:
        print(json.dumps({'status':'plan_only_no_measurements','processes':len(jobs),'runs':5,'warmups':3,'measurements':20,'workloads':WORKLOADS,'strategy_rotation':'cyclic','instrumented_processes':105,'protocol_sha256':sha(protocol)},ensure_ascii=False,indent=2));return
    if not a.experiment_id: p.error('--experiment-id is required unless --plan-only')
    if a.experiment_id not in (project/'EXPERIMENTS.md').read_text(encoding='utf-8'): raise ValueError('Register the real experiment ID in EXPERIMENTS.md before running')
    out=project/'experiments'/a.experiment_id
    if out.exists(): raise ValueError(f'Refusing to mix with existing experiment: {out}')
    (out/'raw').mkdir(parents=True);(out/'logs').mkdir()
    shutil.copy2(protocol,out/'protocol.md')
    source_hash=copy_source(project,out/'source')
    fixture_hash=sha(project/'notes/benchmark-fixtures-20261026-01/manifest.json')
    binding_hashes={name:sha(project/'notes/benchmark-fixtures-20261026-01'/f'{name}-bindings.tsv') for name in ('figure2','time')}
    config={'build_command':'cmd /c code/scripts/build-test.cmd Release','experiment_id':a.experiment_id,'protocol':'PROTO-01-20261026','protocol_sha256':sha(protocol),'fixture_manifest_sha256':fixture_hash,
            'source_snapshot_hash':source_hash,'input_binding_sha256':binding_hashes,'runs':5,'warmups':3,'measurements':20,'processes':len(jobs),'single_process_timeout_seconds':120,
            'total_wall_limit_seconds':1800,'private_bytes_limit':2**31,'system_available_limit':2**31,'raw_output_limit':2**30,
            'default_executable':'code/build-Release/directory_benchmark.exe','instrumented_executable':'code/build-Release/directory_benchmark_instrumented.exe'}
    (out/'config.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    cache={}
    for line in (project/'code/build-Release/CMakeCache.txt').read_text(encoding='utf-8',errors='replace').splitlines():
        if line.startswith(('CMAKE_BUILD_TYPE:','CMAKE_CXX_COMPILER:','DIRECTORY_ENABLE_ASAN:')):
            key,value=line.split('=',1);cache[key]=value
    compiler_cmake=next((project/'code/build-Release/CMakeFiles').glob('*/CMakeCXXCompiler.cmake'),None)
    compiler_text=compiler_cmake.read_text(encoding='utf-8',errors='replace') if compiler_cmake else ''
    version=re.search(r'set\(CMAKE_CXX_COMPILER_VERSION "([^"]+)"',compiler_text)
    environment={'captured_at' :now(),'platform':platform.platform(),'python':sys.version,'processor':platform.processor(),
                 'processor_identifier':os.environ.get('PROCESSOR_IDENTIFIER'),'logical_cpu_count':os.cpu_count(),'system_available_physical_bytes':available_memory(),
                 'compiler_version':version.group(1) if version else 'not_determined','release_cmake_cache':cache,
                 'build_command':'cmd /c code/scripts/build-test.cmd Release','power_scheme':subprocess.run(['powercfg','/getactivescheme'],capture_output=True,text=True).stdout.strip(),
                 'baseline_affinity_or_priority_changed':False,'background_load':'not_controlled; available memory recorded; no idle-machine claim'}
    (out/'environment.json').write_text(json.dumps(environment,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    started=time.monotonic();started_iso=now();config['started_at']=started_iso;(out/'config.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8');order_path=out/'run-order.jsonl';status='running';failure=None
    try:
        for number,(run,input_name,subload,strategy,instrumented) in enumerate(jobs):
            if time.monotonic()-started>1800: raise TimeoutError('DIR-01 total wall limit reached')
            if available_memory() is not None and available_memory()<2**31: raise MemoryError('System available memory below stop limit')
            if sum(f.stat().st_size for f in out.rglob('*') if f.is_file())>=2**30: raise MemoryError('Raw output stop limit reached')
            exe=project/('code/build-Release/directory_benchmark_instrumented.exe' if instrumented else 'code/build-Release/directory_benchmark.exe')
            command=[str(exe),'run','--fixture-dir',str(project/'notes/benchmark-fixtures-20261026-01'),'--input',input_name,'--subload',subload,
                     '--strategy',strategy,'--output',str(out),'--experiment',a.experiment_id,'--run',str(run),'--code-hash',source_hash,'--input-hash',binding_hashes[input_name]]
            entry={'job':number,'started_at':now(),'run':run,'input':input_name,'subload':subload,'strategy':strategy,'instrumented':instrumented,'command':command}
            with (out/'logs'/f'job-{number:02d}.log').open('w',encoding='utf-8') as log:
                begin=time.monotonic()
                try: result=subprocess.run(command,cwd=project,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=False)
                except subprocess.TimeoutExpired as e:
                    entry.update(finished_at=now(),wall_seconds=time.monotonic()-begin,returncode=None,status='timeout')
                    with order_path.open('a',encoding='utf-8') as f:f.write(json.dumps(entry,ensure_ascii=False)+'\n')
                    raise TimeoutError(f'Process timeout: {e}') from e
            entry.update(finished_at=now(),wall_seconds=time.monotonic()-begin,returncode=result.returncode,status='passed' if result.returncode==0 else 'failed')
            with order_path.open('a',encoding='utf-8') as f:f.write(json.dumps(entry,ensure_ascii=False)+'\n')
            if result.returncode: raise RuntimeError(f'Benchmark job {number} failed; see {out}/logs/job-{number:02d}.log')
        subprocess.run([sys.executable,str(project/'code/scripts/summarize-dir01.py'),'--experiment',str(out)],check=True)
        status='complete'
    except Exception as e:
        status='failed';failure=str(e);raise
    finally:
        (out/'record.md').write_text(f"""# {a.experiment_id} — DIR-01

- 状态：{status}。
- 协议：PROTO-01-20261026，项目诊断工作负载，不是作者原始工作负载。
- 源码快照：`source/hashes.json`；环境与命令：`environment.json`、`config.json`、`run-order.jsonl`。
- 原始记录：`raw/`；进程日志：`logs/`。
- 完成时统计：`summary.json`、`correctness.json`；失败时不得据此声明正常性能结论。
- 失败/中断：{failure or '无'}。
""",encoding='utf-8')
        (out/'run-status.json').write_text(json.dumps({'status':status,'started_at':started_iso,'finished_at':now(),'wall_seconds':time.monotonic()-started,'failure':failure},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
