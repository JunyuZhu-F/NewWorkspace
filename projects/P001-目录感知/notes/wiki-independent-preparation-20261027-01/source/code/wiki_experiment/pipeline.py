"""Isolated recoverable WIKI admission and frozen five-process matrices."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

P=Path.cwd()
spec=importlib.util.spec_from_file_location('shared_runtime',P/'code/search02/pipeline.py')
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
sha,load,write=shared.sha,shared.load,shared.write
PROTOCOL=P/'notes/wiki-independent-protocol-20261027.md'

def original():
    files=load(P/'experiments/EXP-20261027-006/source-hashes.json')
    for n,h in files.items():assert sha(P/n)==h,n
    return files

def sources():
    files=original()
    for p in (P/'code/wiki_experiment').iterdir():
        if p.is_file():files[str(p.relative_to(P))]=sha(p)
    for n in ('code/tests/oracle.cpp','code/tests/oracle.hpp','code/scripts/build-wiki-experiment.cmd',str(PROTOCOL.relative_to(P))):files[n]=sha(P/n)
    return files

def snapshot(out):
    files=sources();write(out/'source-hashes.json',files)
    for n in files:
        dest=out/'source'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(P/n,dest)
    shutil.copyfile(PROTOCOL,out/'protocol.md');write(out/'environment.json',shared.environment(P))

def unchanged(out):
    for n,h in load(out/'source-hashes.json').items():assert sha(P/n)==h,n
    original()

def generated(tag):
    build=P/f'code/build-{tag}-WikiExperiment'
    assert (build/'search01_backend.inc').read_bytes()==(P/'code/search/search.cpp').read_bytes().split(b'int main(',1)[0]
    expected=(P/'code/search02/benchmark.cpp').read_bytes().replace(b'queries.n==501',b'queries.n==456').replace(b'cases.size()==1002',b'cases.size()==912').replace(b'search02_contract',b'wiki_search_contract')
    assert (build/'wiki_search.cpp').read_bytes()==expected,'unexpected generated wrapper changes'

def command(out,label,args,start=None):shared.command(P,out,label,args,time.monotonic() if start is None else start)
def verify(out,kind,fixture,outputs,formal=False,suffix=''):
    command(out,'verify-'+kind+suffix,[sys.executable,'-B','code/wiki_experiment/verify.py','--kind',kind,'--fixture',str(fixture),'--outputs',*[str(x) for x in outputs],'--report',str(out/('verification-'+kind+suffix+'.json'))]+(['--formal'] if formal else []))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=('prepare','directory','search'),required=True);ap.add_argument('--preparation',type=Path,required=True);ap.add_argument('--experiment');a=ap.parse_args()
    prep=a.preparation
    if a.stage=='prepare':
        out=prep;out.mkdir(parents=True,exist_ok=False);(out/'.gitignore').write_text('fixture/*.fvecs\n')
        fixture=out/'fixture'
    else:
        assert load(prep/'status.json')['status']=='passed';unchanged(prep)
        assert a.experiment and a.experiment in (P/'EXPERIMENTS.md').read_text(encoding='utf-8')
        out=Path('experiments')/a.experiment;out.mkdir(parents=True,exist_ok=False);fixture=prep/'fixture'
    state=dict(status='running',stage=a.stage,started_utc=shared.now(),measurements_completed=0,fixture=str(fixture));write(out/'status.json',state)
    try:
        snapshot(out)
        if a.stage=='prepare':
            command(out,'prepare-fixture',[sys.executable,'-B','code/wiki_experiment/prepare.py',str(fixture)])
            for name,arg in [('Release',''),('RelWithDebInfo-ASan','asan')]:
                command(out,'build-'+name,['cmd.exe','/d','/c',r'code\scripts\build-wiki-experiment.cmd']+([arg] if arg else []));generated(name)
                root=f'code/build-{name}-WikiExperiment/'
                command(out,'contract-'+name,[root+'wiki_search.exe','self-test'])
                for target in ('wiki_directory','wiki_directory_phase','wiki_search'):
                    command(out,'admit-'+name+'-'+target,[root+target+'.exe',str(fixture),str(out/(name+'-'+target)),'0','0','1','admission'])
            for target in ('wiki_directory','wiki_directory_phase'):
                verify(out,'directory',fixture,[out/(tag+'-'+target) for tag in ('Release','RelWithDebInfo-ASan')],suffix='-'+target)
            verify(out,'search',fixture,[out/(tag+'-wiki_search') for tag in ('Release','RelWithDebInfo-ASan')])
            state['binary_hashes']={tag:{target:sha(P/f'code/build-{tag}-WikiExperiment/{target}.exe') for target in ('wiki_directory','wiki_directory_phase','wiki_search')} for tag in ('Release','RelWithDebInfo-ASan')}
        else:
            manifest=load(fixture/'manifest.json')
            for n,h in manifest['files'].items():assert sha(fixture/n)==h,n
            shutil.copyfile(fixture/'manifest.json',out/'input-manifest.json')
            write(out/'config.json',dict(experiment=a.experiment,preparation=str(prep),runs=5,warmups=3,measurements=20,protocol_sha256=sha(PROTOCOL),fixture_manifest_sha256=sha(fixture/'manifest.json'),cases=manifest['directory_cases'] if a.stage=='directory' else 912,limits=dict(worker_seconds=600,matrix_seconds=1800,private_bytes=2**31,minimum_available_bytes=2**31,output_bytes=2**30)))
            root='code/build-Release-WikiExperiment/'
            shutil.copyfile(P/root/'CMakeCache.txt',out/'CMakeCache.txt')
            write(out/'compile-flags.json',sorted({line.strip() for line in (P/root/'build.ninja').read_text(encoding='utf-8').splitlines() if line.startswith('  FLAGS =')}))
            started=time.monotonic()
            targets=('wiki_directory','wiki_directory_phase') if a.stage=='directory' else ('wiki_search',)
            for target in targets:
                assert sha(P/root/(target+'.exe'))==load(prep/'status.json')['binary_hashes']['Release'][target]
                prefix='default' if target=='wiki_directory' else 'phase' if target=='wiki_directory_phase' else 'search'
                for run in range(5):
                    command(out,f'run-{prefix}-{run}',[root+target+'.exe',str(fixture),str(out/f'run-{prefix}-{run}'),str(run),'3','20','formal'],started)
                    state['measurements_completed']+=1;write(out/'status.json',state)
                verify(out,a.stage,fixture,[out/f'run-{prefix}-{r}' for r in range(5)],True,suffix='-'+prefix)
        unchanged(out);state['status']='passed'
    except BaseException as e:
        state.update(status='interrupted' if isinstance(e,KeyboardInterrupt) else 'failed',failure=repr(e));raise
    finally:state['finished_utc']=shared.now();write(out/'status.json',state)

if __name__=='__main__':main()
