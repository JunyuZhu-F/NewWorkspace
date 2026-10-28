"""Frozen independent cost diagnostics. --plan-only never runs a measurement."""
import argparse
import contextlib
import ctypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time

STRATEGIES=['pe_online','pe_offline','trie_hi']
WORKLOADS=[('figure2','build'),('figure2','dsq'),('figure2','move'),('figure2','merge'),('time','build'),('time','dsq'),('time','dsm')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def matrix():
    for run in range(5):
        order=STRATEGIES[run%3:]+STRATEGIES[:run%3]
        for inp,sub in WORKLOADS:
            for strategy in order:yield dict(mode='phase',run=run,input=inp,subload=sub,strategy=strategy)
        for inp in ('figure2','time'):
            for strategy in order:yield dict(mode='allocation',run=run,input=inp,subload='allocation',strategy=strategy)
def plan():
    jobs=list(matrix())
    assert len(jobs)==135 and len({tuple(j.values()) for j in jobs})==135
    return {'status':'plan_only_no_measurements','processes':135,'phase_processes':105,'allocation_processes':30,
            'runs':5,'warmups':3,'measurements':20,'expected_rows':{'phases':33465,'allocation':3795,'overhead':135,'cost-process':135},'measurements_run':0}
@contextlib.contextmanager
def evidence(out):
    out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();status={'status':'running','started_at':now()};write(out/'run-status.json',status)
    try:
        (out/'raw').mkdir();(out/'logs').mkdir()
        yield
        status['status']='complete'
    except BaseException as e:
        status.update(status='interrupted' if isinstance(e,KeyboardInterrupt) else 'failed',failure=type(e).__name__+': '+str(e))
        raise
    finally:
        status.update(finished_at=now(),wall_seconds=time.monotonic()-started);write(out/'run-status.json',status)
        (out/'record.md').write_text('# '+out.name+' — cost diagnostics\n\n- Actual status: '+status['status']+'\n- See run-status.json, config.json, run-order.jsonl, raw/, logs/.\n- Project diagnostic workload, not author workload; no vectors or ANN.\n',encoding='utf-8')
def available_memory():
    class Memory(ctypes.Structure):_fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('avail',ctypes.c_ulonglong),('total_page',ctypes.c_ulonglong),('avail_page',ctypes.c_ulonglong),('total_virtual',ctypes.c_ulonglong),('avail_virtual',ctypes.c_ulonglong),('extended',ctypes.c_ulonglong)]
    m=Memory();m.length=ctypes.sizeof(m)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):raise OSError('Cannot read system memory stop limit')
    return m.avail
def source_files(project):
    for top in sorted((project/'code').iterdir()):
        if top.name.startswith('build') or top.name=='__pycache__':continue
        for p in ([top] if top.is_file() else sorted(top.rglob('*'))):
            if p.is_file() and '__pycache__' not in p.parts:yield p
def execute(project,experiment):
    if not re.fullmatch(r'EXP-\d{8}-\d{3}',experiment):raise ValueError('Invalid unique experiment ID')
    if experiment not in (project/'EXPERIMENTS.md').read_text(encoding='utf-8'):raise ValueError('Register actual experiment first')
    out=project/'experiments'/experiment
    run_started=time.monotonic()
    with evidence(out):
        protocol=project/'notes/benchmark-cost-protocol-20261027.md'
        preparation=project/'notes/cost02-preparation-20261027-01/source-hashes.json'
        # Even snapshot/protocol/environment errors occur within the failure envelope.
        frozen=json.loads(preparation.read_text(encoding='utf-8'))
        if sha(protocol)!=frozen['protocol_sha256']:raise ValueError('Cost protocol hash mismatch')
        actual={str(p.relative_to(project)).replace('\\','/'):sha(p) for p in source_files(project)}
        if actual!=frozen['files']:raise ValueError('Cost preparation source snapshot mismatch')
        build=project/'code/build-Release-Cost'
        executables={m:build/f'directory_cost_{m}.exe' for m in ('phase','allocation')}
        if any(not p.is_file() for p in executables.values()):raise FileNotFoundError('Build and admit Release cost executables first')
        cache=(build/'CMakeCache.txt').read_text(encoding='utf-8')
        if 'CMAKE_BUILD_TYPE:STRING=Release' not in cache or 'DIRECTORY_ENABLE_ASAN:BOOL=OFF' not in cache:raise ValueError('Only non-ASan Release diagnostics may be measured')
        for mode,path in executables.items():
            if sha(path)!=frozen['release_binary_sha256'][mode]:raise ValueError('Executable differs from admitted snapshot: '+mode)
        fixture=project/'notes/benchmark-fixtures-20261026-01'
        for name,digest in frozen['fixtures'].items():
            if sha(fixture/name)!=digest:raise ValueError('Fixture hash mismatch: '+name)
        shutil.copy2(protocol,out/'protocol.md');(out/'source/code').mkdir(parents=True)
        for p in source_files(project):
            dest=out/'source'/p.relative_to(project);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        shutil.copytree(fixture,out/'source/fixtures');write(out/'source/hashes.json',frozen)
        power=subprocess.run(['powercfg','/getactivescheme'],capture_output=True)
        env={'captured_at':now(),'platform':platform.platform(),'python':sys.version,'processor':platform.processor(),'logical_cpu_count':os.cpu_count(),
             'system_available_physical_bytes':available_memory(),'power_scheme_stdout_hex':power.stdout.hex(),'power_scheme_stderr_hex':power.stderr.hex(),'power_scheme_exit_code':power.returncode,
             'power_scheme':power.stdout.decode('utf-8',errors='backslashreplace'),'affinity_priority_or_power_changed':False,'background_load':'not controlled; no idle-machine claim',
             'compile_flags':sorted({line.strip() for line in (build/'build.ninja').read_text(encoding='utf-8').splitlines() if line.startswith('  FLAGS =')})}
        write(out/'environment.json',env)
        cfg=plan();cfg.update(status='running',experiment=experiment,source_snapshot_hash=frozen['source_snapshot_hash'],protocol_sha256=sha(protocol),
            stop_limits={'process_seconds':120,'total_seconds':1800,'private_bytes':2**31,'system_available_bytes_min':2**31,'output_bytes':2**30},executable_hashes={m:sha(p) for m,p in executables.items()})
        write(out/'config.json',cfg);started=run_started
        for number,job in enumerate(matrix()):
            if time.monotonic()-started>=1800:raise TimeoutError('Total wall stop limit')
            if available_memory()<2**31:raise MemoryError('System available memory stop limit')
            if sum(p.stat().st_size for p in out.rglob('*') if p.is_file())>=2**30:raise OSError('Output size stop limit')
            if any(sha(fixture/name)!=digest for name,digest in frozen['fixtures'].items()):raise ValueError('Frozen fixture changed during matrix')
            if sha(executables[job['mode']])!=frozen['release_binary_sha256'][job['mode']]:raise ValueError('Diagnostic executable changed during matrix')
            command=[str(executables[job['mode']]),'run',str(fixture),job['input'],job['subload'],job['strategy'],str(out),experiment,str(job['run']),frozen['source_snapshot_hash'],sha(fixture/(job['input']+'-bindings.tsv'))]
            entry=dict(job,job=number,command=command,started_at=now());begin=time.monotonic()
            try:
                with (out/'logs'/f'job-{number:03d}.log').open('w',encoding='utf-8') as log:result=subprocess.run(command,cwd=project,stdout=log,stderr=subprocess.STDOUT,timeout=min(120,max(.001,1800-(time.monotonic()-started))))
                entry.update(status='passed' if result.returncode==0 else 'failed',returncode=result.returncode)
            except BaseException as e:
                entry.update(status='interrupted' if isinstance(e,KeyboardInterrupt) else 'failed',failure=str(e),returncode=None);raise
            finally:
                entry.update(finished_at=now(),wall_seconds=time.monotonic()-begin)
                with (out/'run-order.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(entry,ensure_ascii=False)+'\n')
            if result.returncode:raise RuntimeError('Diagnostic process failed: '+str(number))
        subprocess.run([sys.executable,str(project/'code/scripts/summarize-cost02.py'),'--experiment',str(out)],check=True)
def self_test(out):
    # Synthetic fixture for failure-envelope testing, never a registered real EXP.
    target=out/'synthetic-preflight-failure'
    try:
        with evidence(target):raise FileNotFoundError('synthetic missing snapshot before process startup')
    except FileNotFoundError:pass
    state=json.loads((target/'run-status.json').read_text())
    assert state['status']=='failed' and not (target/'run-order.jsonl').exists()
    assert plan()['processes']==135
    print(json.dumps({'status':'passed','synthetic_failure_recorded':True,'measurement_processes':0}))
def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=Path('.'));p.add_argument('--plan-only',action='store_true');p.add_argument('--experiment-id');p.add_argument('--self-test',type=Path);a=p.parse_args()
    if a.plan_only:print(json.dumps(plan(),indent=2));return
    if a.self_test:self_test(a.self_test);return
    if not a.experiment_id:p.error('--experiment-id is required')
    execute(a.project.resolve(),a.experiment_id)
if __name__=='__main__':main()
