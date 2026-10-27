"""Bounded WIKI correctness runner; all original core source hashes must match."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

import psutil

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    out=HERE/'check-01'
    out.mkdir(exist_ok=False)
    state=dict(status='running',started_utc=now(),scope='WIKI small-sample directory correctness only')
    write(out/'status.json',state)
    def command(label,args,asan=False):
        env=os.environ.copy()
        if asan:
            cache=(PROJECT/'code/build-RelWithDebInfo-ASan-Wiki/CMakeCache.txt').read_text(encoding='utf-8')
            compiler=Path(re.search(r'^CMAKE_CXX_COMPILER:FILEPATH=(.+)$',cache,re.M).group(1).strip())
            assert (compiler.parent/'clang_rt.asan_dynamic-x86_64.dll').is_file()
            env['PATH']=str(compiler.parent)+os.pathsep+env.get('PATH','')
        event=dict(label=label,args=args,cwd=str(PROJECT),started_utc=now(),peak_private_bytes_sampled=0,
                   minimum_available_bytes_sampled=psutil.virtual_memory().available)
        started=time.monotonic()
        with (out/(label+'.log')).open('xb') as log:
            p=subprocess.Popen(args,cwd=PROJECT,stdout=log,stderr=subprocess.STDOUT,env=env)
            try:
                while p.poll() is None:
                    try:
                        proc=psutil.Process(p.pid)
                        members=[proc]+proc.children(recursive=True)
                        private=sum(getattr(c.memory_info(),'private',c.memory_info().rss) for c in members if c.is_running())
                        available=psutil.virtual_memory().available
                        event['peak_private_bytes_sampled']=max(private,event['peak_private_bytes_sampled'])
                        event['minimum_available_bytes_sampled']=min(available,event['minimum_available_bytes_sampled'])
                        if private>2*(1<<30) or available<2*(1<<30) or time.monotonic()-started>180:
                            raise RuntimeError('Resource/time stop limit')
                    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
                    time.sleep(0.2)
            except BaseException:
                for child in psutil.Process(p.pid).children(recursive=True):child.kill()
                p.kill();p.wait();event['stopped_by_runner']=True
                raise
            finally:
                event.update(exit_code=p.poll(),finished_utc=now(),elapsed_seconds=time.monotonic()-started)
                with (out/'commands.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
        if p.returncode:raise RuntimeError(label+' exit '+str(p.returncode))
        print(label,'passed',flush=True)
    try:
        audit=json.loads((HERE/'run-01/report.json').read_text(encoding='utf-8'))
        verified=json.loads((HERE/'run-01/verification.json').read_text(encoding='utf-8'))
        assert audit['status']==verified['status']=='passed'
        old=json.loads((PROJECT/'experiments/EXP-20261027-006/source-hashes.json').read_text(encoding='utf-8'))
        for name,h in old.items():assert sha(PROJECT/name)==h,name
        names=list(old)+['code/wiki/CMakeLists.txt','code/wiki/validate.cpp','code/tests/oracle.cpp',
            'code/tests/oracle.hpp','code/scripts/build-wiki.cmd',str(Path(__file__).relative_to(PROJECT)),
            str((HERE/'protocol.md').relative_to(PROJECT)),str((HERE/'run-01/sample-bindings.tsv').relative_to(PROJECT))]
        hashes={name:sha(PROJECT/name) for name in names}
        write(out/'source-hashes.json',hashes)
        for name in hashes:
            dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PROJECT/name,dest)
        write(out/'config.json',dict(records=10000,protocol_sha256=sha(HERE/'protocol.md'),
            input_sha256=sha(HERE/'run-01/sample-bindings.tsv'),timeout_seconds=180,
            private_bytes_limit=2*(1<<30),minimum_available_bytes=2*(1<<30),
            git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=PROJECT,text=True).strip(),
            python=sys.version,executable=sys.executable))
        (out/'git-status-before.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=PROJECT,text=True),encoding='utf-8')
        binding=str(HERE/'run-01/sample-bindings.tsv')
        command('build-release',['cmd.exe','/d','/c','code/scripts/build-wiki.cmd'])
        command('release',[str(PROJECT/'code/build-Release-Wiki/directory_wiki_validate.exe'),binding,str(out/'release-answers.tsv')])
        command('build-asan',['cmd.exe','/d','/c','code/scripts/build-wiki.cmd','asan'])
        command('asan',[str(PROJECT/'code/build-RelWithDebInfo-ASan-Wiki/directory_wiki_validate.exe'),binding,str(out/'asan-answers.tsv')],True)
        assert (out/'release-answers.tsv').read_bytes()==(out/'asan-answers.tsv').read_bytes()
        for name,h in hashes.items():assert sha(PROJECT/name)==h,name
        state.update(status='passed',finished_utc=now(),old_006_source_files_unchanged=len(old),
            release_asan_answers_equal=True,answers_sha256=sha(out/'release-answers.tsv'),
            query_scope_rows=len((out/'release-answers.tsv').read_bytes().splitlines()),
            binary_sha256={tag:sha(PROJECT/('code/build-'+tag+'/directory_wiki_validate.exe'))
                           for tag in ('Release-Wiki','RelWithDebInfo-ASan-Wiki')})
        write(out/'status.json',state)
    except BaseException as e:
        state.update(status='failed',finished_utc=now(),error=repr(e));write(out/'status.json',state);raise

if __name__=='__main__':main()
