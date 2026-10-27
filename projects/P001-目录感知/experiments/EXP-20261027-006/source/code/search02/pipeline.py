"""Recoverable bounded SEARCH-02 admission and five-process experiment runner."""
import argparse
import hashlib
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np
import psutil


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def old_files(project):
    frozen=load(project/'notes/search01-validation-20261027-01/source-final-hashes.json')
    files={**frozen['files'],**frozen['unchanged_core_files']}
    for name,h in files.items():assert sha(project/name)==h,('previous frozen source changed',name)
    return files


def sources(project):
    result=list((project/'code/search02').glob('*.py'))+list((project/'code/search02').glob('*.cpp'))+[project/'code/search02/CMakeLists.txt',project/'code/scripts/build-search02.cmd',project/'notes/search02-protocol-20261027.md']
    return sorted(result)


def snapshot(project,out):
    dest=out/'source';dest.mkdir()
    files=old_files(project)
    files.update({p.relative_to(project).as_posix():sha(p) for p in sources(project)})
    for name,h in files.items():
        p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(project/name,p);assert sha(p)==h
    write(out/'source-hashes.json',files)
    (out/'git-diff.patch').write_bytes(subprocess.check_output(['git','diff','--binary','--','.']))
    return files


def checked_sources(project,path):
    for name,h in load(path).items():assert sha(project/name)==h,name


def child_environment(project,command):
    env=os.environ.copy();added=None
    if command[0].endswith('.exe') and 'ASan' in command[0]:
        cache=(project/pathlib.Path(command[0]).parent/'CMakeCache.txt').read_text(encoding='utf-8')
        compiler=re.search(r'^CMAKE_CXX_COMPILER:FILEPATH=(.+)$',cache,re.M).group(1).strip()
        added=pathlib.Path(compiler).parent;assert (added/'clang_rt.asan_dynamic-x86_64.dll').is_file()
        env['PATH']=str(added)+os.pathsep+env.get('PATH','')
    return env,str(added) if added else None


def size(path):return sum(p.stat().st_size for p in path.rglob('*') if p.is_file())


def command(project,evidence,label,args,formal_started=None):
    event=dict(label=label,command=args,cwd=str(project),started_utc=now(),peak_private_bytes_sampled=0,minimum_available_bytes=None)
    env,added=child_environment(project,args);event['added_runtime_path']=added
    start=time.monotonic();proc=None;monitor=[]
    try:
        with (evidence/(label+'.log')).open('xb') as log:
            proc=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env)
            observer=psutil.Process(proc.pid)
            while proc.poll() is None:
                available=psutil.virtual_memory().available
                try:
                    info=observer.memory_info();private=getattr(info,'private',info.rss)
                except psutil.NoSuchProcess:private=0
                event['peak_private_bytes_sampled']=max(event['peak_private_bytes_sampled'],private)
                event['minimum_available_bytes']=min(event['minimum_available_bytes'] or available,available)
                elapsed=time.monotonic()-start
                if formal_started is not None:
                    monitor.append(dict(elapsed_seconds=elapsed,private_bytes=private,available_bytes=available))
                    assert available>=2**31,'available memory below 2 GiB'
                    assert private<=2**31,'worker private memory above 2 GiB'
                    assert time.monotonic()-formal_started<=1800,'matrix time limit'
                    assert size(evidence)<=2**30,'output size limit'
                assert elapsed<=600,'command timeout'
                time.sleep(1)
            event['exit_code']=proc.returncode
            assert proc.returncode==0,f'{label} exit {proc.returncode}; see saved log'
    except BaseException as error:
        event['error']=repr(error)
        if proc is not None and proc.poll() is None:proc.kill();proc.wait()
        if proc is not None:event['exit_code']=proc.returncode
        raise
    finally:
        event.update(finished_utc=now(),elapsed_seconds=time.monotonic()-start)
        with (evidence/'commands.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
        if monitor:write(evidence/(label+'-monitor.json'),monitor)
    print(json.dumps(dict(label=label,status='passed',elapsed_seconds=event['elapsed_seconds'])),flush=True)


def environment(project):
    return dict(captured_utc=now(),platform=platform.platform(),python=sys.version,numpy=np.__version__,psutil=psutil.__version__,processor_identifier=os.environ.get('PROCESSOR_IDENTIFIER'),logical_cpu_count=os.cpu_count(),available_memory_bytes=psutil.virtual_memory().available,git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),git_status=subprocess.check_output(['git','status','--short'],text=True),background_load='not controlled',affinity_priority_power_changed=False)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=('prepare','run'),required=True);ap.add_argument('--preparation',type=pathlib.Path,required=True);ap.add_argument('--experiment',default='EXP-20261027-006');ap.add_argument('--reuse-fixture',type=pathlib.Path);a=ap.parse_args()
    project=pathlib.Path.cwd();prep=a.preparation
    if a.stage=='prepare':
        out=prep;out.mkdir(parents=True,exist_ok=False)
        (out/'.gitignore').write_text('fixture/*.fvecs\n',encoding='utf-8')
    else:
        assert load(prep/'status.json')['status']=='passed'
        checked_sources(project,prep/'source-hashes.json')
        assert a.experiment in (project/'EXPERIMENTS.md').read_text(encoding='utf-8'),'register experiment first'
        out=pathlib.Path('experiments')/a.experiment;out.mkdir(parents=True,exist_ok=False)
    fixture=a.reuse_fixture or prep/'fixture' if a.stage=='prepare' else pathlib.Path(load(prep/'status.json')['fixture'])
    state=dict(status='running',stage=a.stage,started_utc=now(),measurements_completed=0,fixture=str(fixture))
    write(out/'status.json',state)
    try:
        snapshot(project,out);write(out/'environment.json',environment(project));shutil.copyfile(project/'notes/search02-protocol-20261027.md',out/'protocol.md')
        if a.stage=='prepare':
            if a.reuse_fixture:
                manifest=load(fixture/'manifest.json')
                assert manifest['protocol_sha256']==sha(project/'notes/search02-protocol-20261027.md')
                for name,h in manifest['files'].items():assert sha(fixture/name)==h
                write(out/'reused-fixture.json',dict(path=str(fixture),manifest_sha256=sha(fixture/'manifest.json'),reason='Reuse valid input after generated-include newline guard failure; no data or scientific protocol changes'))
            else:
                command(project,out,'prepare',[sys.executable,'code/search02/prepare.py','--output',str(fixture)])
            for mode,arg in [('Release',''),('ASan','asan')]:
                args=['cmd.exe','/d','/c','code\\scripts\\build-search02.cmd']+([arg] if arg else [])
                command(project,out,'build-'+mode.lower(),args)
                build='Release-Search02' if mode=='Release' else 'RelWithDebInfo-ASan-Search02'
                generated=project/f'code/build-{build}/search01_backend.inc'
                assert generated.read_bytes()==(project/'code/search/search.cpp').read_bytes().split(b'int main(',1)[0]
                command(project,out,'admit-'+mode.lower(),[f'code/build-{build}/directory_search02.exe',str(fixture),str(prep/mode.lower()),'0','0','1','admission'])
            command(project,out,'verify-admission',[sys.executable,'code/search02/verify.py','--fixture',str(fixture),'--outputs',str(prep/'release'),str(prep/'asan'),'--report',str(prep/'verification.json')])
            state['binary_hashes']={build:sha(project/f'code/build-{build}/directory_search02.exe') for build in ('Release-Search02','RelWithDebInfo-ASan-Search02')}
        else:
            manifest=load(fixture/'manifest.json');executable='code/build-Release-Search02/directory_search02.exe'
            assert sha(project/executable)==load(prep/'status.json')['binary_hashes']['Release-Search02']
            for name,h in manifest['files'].items():assert sha(fixture/name)==h
            shutil.copyfile(fixture/'manifest.json',out/'input-manifest.json')
            write(out/'config.json',dict(experiment=a.experiment,preparation=str(prep),protocol_sha256=sha(project/'notes/search02-protocol-20261027.md'),fixture_manifest_sha256=sha(fixture/'manifest.json'),binary_sha256=sha(project/executable),runs=5,warmups=3,measurements=20,cases=1002,probes=[0,1,4,16],expected_timing_rows=1202400,limits=dict(worker_seconds=600,matrix_seconds=1800,private_bytes=2**31,minimum_available_bytes=2**31,output_bytes=2**30)))
            cache=project/'code/build-Release-Search02/CMakeCache.txt';shutil.copyfile(cache,out/'CMakeCache.txt')
            write(out/'compile-flags.json',sorted({line.strip() for line in (project/'code/build-Release-Search02/build.ninja').read_text(encoding='utf-8').splitlines() if line.startswith('  FLAGS =')}))
            started=time.monotonic()
            for run in range(5):
                command(project,out,f'run-{run}',[executable,str(fixture),str(out/f'run-{run}'),str(run),'3','20','formal'],started)
                state['measurements_completed']+=1;write(out/'status.json',state)
            command(project,out,'verify-results',[sys.executable,'code/search02/verify.py','--fixture',str(fixture),'--outputs',*[str(out/f'run-{i}') for i in range(5)],'--report',str(out/'verification.json'),'--formal'])
        checked_sources(project,out/'source-hashes.json');old_files(project);state['status']='passed'
    except BaseException as error:
        state.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',failure=repr(error));raise
    finally:
        state['finished_utc']=now();write(out/'status.json',state)


if __name__=='__main__':main()
