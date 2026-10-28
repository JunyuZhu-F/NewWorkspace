# -*- coding: utf-8 -*-
"""Serial, guarded SCALE-PREP admission. Explicitly cannot run the formal matrix."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import psutil

P=Path.cwd();G=1<<30;PY=Path(sys.executable);CODE=P/'code/scale_directory'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def frozen():
    old=load(P/'experiments/EXP-20261027-006/source-hashes.json')
    assert len(old)==46 and all(sha(P/k)==v for k,v in old.items()),'old 46 source hashes changed'
    return old
def spec_module(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class Runner:
    def __init__(self,root):
        self.root=root;root.mkdir(parents=True,exist_ok=False);self.commands=[]
        self.status=dict(status='running',started_utc=now(),scope='SCALE-PREP-01 only; no formal matrix',git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip())
        save(root/'status.json',self.status)
    def gate(self,name,stable=True):
        samples=[];started=time.perf_counter()
        try:
            while True:
                a=psutil.virtual_memory().available;free=shutil.disk_usage(P).free
                samples.append(dict(elapsed_s=time.perf_counter()-started,utc=now(),available_bytes=a,disk_free_bytes=free))
                if a<4*G or free<10*G:raise RuntimeError('resource preflight: requires available >=4GiB and disk >=10GiB')
                if not stable or time.perf_counter()-started>=20:break
                time.sleep(1)
        finally:save(self.root/f'{name}-preflight.json',dict(required_stable_s=20 if stable else 0,samples=samples))
    def run(self,name,cmd,stable=True,env=None,expected=0,marker=None):
        self.gate(name,stable);log=self.root/f'{name}.log';assert not log.exists()
        row=dict(name=name,command=[str(x) for x in cmd],started_utc=now(),expected_exit=expected)
        self.commands.append(row);save(self.root/'commands.json',self.commands)
        start=time.perf_counter();samples=[];violation=None;peak=0;low=psutil.virtual_memory().available;process=None
        with log.open('wb') as stream:
            try:
                process=subprocess.Popen(row['command'],cwd=P,stdout=stream,stderr=subprocess.STDOUT,env=env)
                rootproc=psutil.Process(process.pid)
                while True:
                    elapsed=time.perf_counter()-start;private=0
                    try:
                        tree=[rootproc]+rootproc.children(recursive=True)
                        for p in tree:
                            try:private+=p.memory_info().private
                            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
                    except psutil.NoSuchProcess:tree=[]
                    available=psutil.virtual_memory().available;peak=max(peak,private);low=min(low,available)
                    samples.append(dict(elapsed_s=elapsed,private_tree_bytes=private,available_bytes=available))
                    # Evidence root and current isolated build outputs only; no old datasets/results.
                    output_bytes=sum(f.stat().st_size for f in self.root.rglob('*') if f.is_file())
                    if private>2*G or available<2*G or elapsed>600 or output_bytes>G:
                        violation=dict(private=private,available=available,elapsed=elapsed,output_bytes=output_bytes)
                        for p in reversed(tree):
                            try:p.kill()
                            except psutil.NoSuchProcess:pass
                        if process.poll() is None:process.kill()
                        process.wait();raise RuntimeError('runtime resource guard '+str(violation))
                    if process.poll() is not None:break
                    time.sleep(.20)
                row.update(exit_code=process.returncode,elapsed_s=time.perf_counter()-start,private_peak_sampled_bytes=peak,available_min_sampled_bytes=low)
                assert process.returncode==expected,'unexpected exit '+str(process.returncode)
            finally:
                if process is not None and process.poll() is None:process.kill();process.wait()
                row.update(finished_utc=now(),violation=violation)
                save(self.root/f'{name}-monitor.json',dict(**row,sampling_note='target <=250ms; filesystem traversal/scheduler may increase intervals; samples not a quota or exact peak',samples=samples))
                save(self.root/'commands.json',self.commands)
        if marker:assert marker in log.read_text(encoding='utf-8',errors='replace'),'expected error marker absent'
        print('PASS',name,round(row['elapsed_s'],3),'s',flush=True)
        return row

def main():
    r=Runner(Path(sys.argv[1]));root=r.root
    try:
        old=frozen();save(root/'old-46-source-hashes.json',old)
        paths=list(CODE.glob('*.py'))+[CODE/'CMakeLists.txt',P/'code/scripts/build-scale-directory.cmd',P/'notes/scale-prep-protocol-20261027.md']
        hashes={str(p.relative_to(P)):sha(p) for p in paths};save(root/'source-hashes.json',hashes)
        for p in paths:
            d=root/'source'/p.relative_to(P);d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d)
        (root/'git-status-entry.txt').write_bytes(subprocess.check_output(['git','status','--short'],cwd=P))
        (root/'git-diff-entry.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=P))
        save(root/'environment.json',dict(utc=now(),python=sys.version,executable=str(PY),psutil=psutil.__version__,logical_cpus=psutil.cpu_count(),ram_bytes=psutil.virtual_memory().total,available_bytes=psutil.virtual_memory().available,disk_free_bytes=shutil.disk_usage(P).free,resource_scope='private sum of child process tree; output evidence root capped',vector_payload_bytes_read=0))
        exe={};envs={};generator=spec_module('scale_generation',CODE/'generate.py')
        for build,arg in [('release',[]),('asan',['asan'])]:
            r.run('build-'+build,['cmd.exe','/d','/c',r'code\scripts\build-scale-directory.cmd']+arg)
            b=P/('code/build-Release-ScaleDirectory' if build=='release' else 'code/build-RelWithDebInfo-ASan-ScaleDirectory')
            exe[build]=b/'scale_directory.exe';assert exe[build].exists()
            generated,changes=generator.render((P/'code/wiki_experiment/directory.cpp').read_bytes())
            assert (b/'scale_directory.cpp').read_bytes()==generated
            d=root/'builds'/build;d.mkdir(parents=True)
            for name in ['scale_directory.cpp','scale_directory.changes.json','CMakeCache.txt','compile_commands.json','build.ninja']:
                if (b/name).exists():shutil.copyfile(b/name,d/name)
            save(d/'binary.json',dict(path=str(exe[build]),sha256=sha(exe[build]),generated_sha256=sha(b/'scale_directory.cpp'),whitelist_count=len(changes)))
            envs[build]=os.environ.copy()
            if build=='asan':
                compiler=[line.split('=',1)[1] for line in (b/'CMakeCache.txt').read_text(encoding='utf-8').splitlines() if line.startswith('CMAKE_CXX_COMPILER:FILEPATH=')][0]
                dll=Path(compiler).parent/'clang_rt.asan_dynamic-x86_64.dll';assert dll.exists()
                envs[build]['PATH']=str(dll.parent)+os.pathsep+envs[build].get('PATH','')
                save(d/'asan-runtime.json',dict(path=str(dll),sha256=sha(dll),scope='child PATH only'))
        # Must fail at the intended admission adapter contract, not a missing DLL/fixture.
        negatives=[('shape-zero','0\t3\n','0\t0\t/a/\n1\t1\t/b/\n','q\t/\t1\n','shape range'),('shape-mismatch','2\t3\n','0\t0\t/a/\n','q\t/\t1\n','bindings'),('global-duplicate','2\t3\n','0\t0\t/a/\n1\t0\t/b/\n','q\t/\t1\n','global IDs must be increasing and in range'),('global-descending','2\t3\n','0\t1\t/a/\n1\t0\t/b/\n','q\t/\t1\n','global IDs must be increasing and in range'),('global-outside','2\t3\n','0\t0\t/a/\n1\t3\t/b/\n','q\t/\t1\n','global IDs must be increasing and in range'),('query-mode','2\t3\n','0\t0\t/a/\n1\t1\t/b/\n','q\t/\t2\n','mode')]
        results=[]
        for name,shape,bindings,cases,marker in negatives:
            f=root/'negative-fixtures'/name;f.mkdir(parents=True)
            for fn,text in [('shape.tsv',shape),('bindings.tsv',bindings),('directory-cases.tsv',cases)]: (f/fn).write_text(text,encoding='utf-8')
            row=r.run('negative-'+name,[exe['release'],f,root/'negative-outputs'/name,'0','0','1','admission'],stable=False,expected=1,marker='FAIL '+marker)
            results.append(dict(name=name,status='passed',expected_marker=marker,observed_exit=row['exit_code']))
        save(root/'negative-contracts.json',dict(status='passed',tests=results))
        r.run('prepare',[PY,'-B',CODE/'prepare.py',root/'fixtures'])
        r.run('source-check',[PY,'-B',CODE/'source_check.py',root/'fixtures',root/'source-verification.json'])
        for ds in ['arxiv','wiki']:
            for n in [5000,25000]:
                f=root/'fixtures'/f'{ds}-{n}';outputs=[]
                for build in (['release','asan'] if n==5000 else ['release']):
                    name=f'{ds}-{n}-{build}';out=root/'outputs'/name;outputs.append(out)
                    r.run(name,[exe[build],f,out,'0','0','1','admission'],env=envs[build])
                r.run(f'verify-{ds}-{n}',[PY,'-B',CODE/'verify.py',f,root/f'verification-{ds}-{n}.json']+outputs)
        assert frozen()==old
        assert all(sha(P/k)==v for k,v in hashes.items()),'admission sources changed'
        for build in exe:assert sha(exe[build])==load(root/'builds'/build/'binary.json')['sha256']
        forecasts=[]
        for ds in ['arxiv','wiki']:
            v=load(root/f'verification-{ds}-25000.json');native=v['runs'][0];cmd=next(c for c in r.commands if c['name']==f'{ds}-25000-release')
            residual=max(0,cmd['elapsed_s']-native['setup_s']-native['cycle_s'])
            worker=native['setup_s']+23*native['cycle_s']+residual
            verification=5*next(c for c in r.commands if c['name']==f'verify-{ds}-25000')['elapsed_s']
            estimate=5*worker+verification;screen=1.5*estimate
            forecasts.append(dict(dataset=ds,worker_s=worker,verification_scenario_s=verification,matrix_s=estimate,screen_1_5x_s=screen,observed_private_bytes=cmd['private_peak_sampled_bytes'],admission_memory_pass=cmd['private_peak_sampled_bytes']<=1.5*G,worker_budget_pass=worker<=600,matrix_budget_pass=screen<=1440,assumptions='5 independent workers; each 3 warmup +20 measured cycles; setup +23*single measured validated cycle incl destruction + observed residual; verifier scenario 5*measured full one-output verifier; 1.5x time margin. Not a bound/proof; warm-cache single admission; no formal matrix run.'))
        save(root/'budget-forecast.json',dict(status='estimate_only',forecasts=forecasts))
        r.status.update(status='passed',finished_utc=now(),old_46_sources_unchanged=True,admission_sources_unchanged=True,binaries_unchanged=True,formal_runs=0,workers=6)
        save(root/'final-check.json',dict(status='passed',independent_source=True,negative_contracts=6,fixtures=4,workers=6,release_asan_pairs=2,old_46_sources_unchanged=True,formal_matrix_started=False))
    except Exception as e:
        r.status.update(status='resource_blocked' if 'resource' in str(e).lower() else 'failed',finished_utc=now(),error=repr(e))
        (root/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8');print(traceback.format_exc(),flush=True)
    finally:save(root/'status.json',r.status)
    if r.status['status']!='passed':sys.exit(1)
if __name__=='__main__':main()
