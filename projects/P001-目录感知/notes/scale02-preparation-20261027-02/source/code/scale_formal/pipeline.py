# -*- coding: utf-8 -*-
"""Approved 25k matrix, WIKI first. No retries or adaptive workload changes."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
import psutil
from guard import Guard,P,G,now,load,save,sha

C=P/'code/scale_formal';PREVIOUS=P/'notes/scale-prep-20261027-02';PROTOCOL=P/'notes/scale02-protocol-20261027.md'
RESUME=Path(sys.argv[1]).resolve() if len(sys.argv)==2 else None
ROOT=P/('notes/scale02-preparation-20261027-02' if RESUME else 'notes/scale02-preparation-20261027-01')
UNITS=[('wiki','EXP-20261027-009'),('arxiv','EXP-20261027-010')]
def snapshot(root,paths):
    hashes={str(p.relative_to(P)):sha(p) for p in paths};save(root/'source-hashes.json',hashes)
    for p in paths:
        dest=root/'source'/p.relative_to(P);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    (root/'git-status-entry.txt').write_bytes(subprocess.check_output(['git','status','--short'],cwd=P))
    (root/'git-diff-entry.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=P))
    return hashes
def intact(hashes):assert all(sha(P/k)==v for k,v in hashes.items()),'frozen source changed'
def config(path,f,outputs,warm,repeats):save(path,dict(fixture=str(f),outputs=[dict(path=str(out),run=run) for out,run in outputs],warmups=warm,repeats=repeats))
def main():
    assert not ROOT.exists(),'refuse to overwrite preparation'
    assert all(not (P/'experiments'/exp).exists() for ds,exp in UNITS),'refuse to overwrite experiment'
    root=ROOT;prep=Guard(root);active=None;overall=dict(status='preparing',started_utc=now(),formal_completed=[],formal_not_started=[exp for ds,exp in UNITS])
    save(root/'overall-status.json',overall)
    try:
        assert load(PREVIOUS/'review-check.json')['status']=='passed' and load(PREVIOUS/'review-check.json')['reviewed_budget_pass']
        intact(load(PREVIOUS/'source-hashes.json'))
        old=load(P/'experiments/EXP-20261027-007/source-hashes.json');intact(old);assert len(old)==53
        paths=list(C.glob('*.py'))+[C/'CMakeLists.txt',C/'README.md',P/'code/scripts/build-scale-formal.cmd',PROTOCOL]
        paths+=list((P/'code/scale_directory').glob('*.py'))+[P/'notes/scale-prep-protocol-20261027.md']
        hashes=snapshot(root,paths);save(root/'old-53-source-hashes.json',old)
        save(root/'environment.json',dict(python=sys.version,executable=sys.executable,git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip(),platform=sys.platform,vector_payload_bytes_read=0))
        deadline_test=Guard(root/'deadline-contract',.25)
        try:
            deadline_test.run('sleep-child',[sys.executable,'-B','-c','import time;time.sleep(10)'],stable=False)
            raise AssertionError('unit deadline did not stop child')
        except RuntimeError as error:
            assert 'resource runtime stop' in str(error)
            row=deadline_test.commands[0];assert row['violation']['remaining_s']<=0 and row['elapsed_s']<2 and not psutil.pid_exists(row['pid'])
            deadline_test.finish('passed_expected_stop',reason='actual unit deadline terminated sleep child; not an experiment')
        if RESUME is not None:
            assert RESUME==P/'notes/scale02-preparation-20261027-01'
            previous=load(RESUME/'overall-status.json');assert previous['status']=='failed' and previous['formal_completed']==[]
            assert load(RESUME/'ordering-audit.json')['wiki']['canonical_answers_equal']
            prior_hashes=load(RESUME/'source-hashes.json')
            assert all(sha(P/k)==v for k,v in prior_hashes.items() if k!='code/scale_formal/pipeline.py')
            for build in ['release','asan']:
                old_build=RESUME/'builds'/build;assert sha(old_build/'scale_formal.exe')==load(old_build/'binary.json')['sha256']
                shutil.copytree(old_build,root/'builds'/build)
            for ds in ['arxiv','wiki']:
                shutil.copyfile(RESUME/f'entry-{ds}.json',root/f'entry-{ds}.json')
                prep.run(f'verify-reused-entry-{ds}',[sys.executable,'-B',C/'verify.py',root/f'entry-{ds}.json',root/f'entry-{ds}-analysis'])
            save(root/'reuse-provenance.json',dict(source=str(RESUME),entry_workers_reused=7,native_workers_repeated=0,reason='Initial byte hash comparison rejected rotated row order; canonical contents independently equal; only orchestrator fixed.',previous_source_hashes=prior_hashes))
        else:
            exe={};env={}
            for build,arg in [('release',[]),('asan',['asan'])]:
                prep.run('build-'+build,['cmd.exe','/d','/c',r'code\scripts\build-scale-formal.cmd']+arg)
                b=P/('code/build-Release-ScaleFormal' if build=='release' else 'code/build-RelWithDebInfo-ASan-ScaleFormal');exe[build]=b/'scale_formal.exe';assert exe[build].exists()
                d=root/'builds'/build;d.mkdir(parents=True)
                for name in ['scale_formal.exe','scale_formal.cpp','scale_formal.changes.json','CMakeCache.txt','build.ninja']:
                    shutil.copyfile(b/name,d/name)
                gen=load(d/'scale_formal.changes.json');assert len(gen['changes'])==13 and gen['source_sha256']==sha(P/'code/wiki_experiment/directory.cpp')
                save(d/'binary.json',dict(path=str(exe[build]),sha256=sha(exe[build]),generated_sha256=sha(d/'scale_formal.cpp')))
                env[build]=os.environ.copy()
                if build=='asan':
                    compiler=next(s.split('=',1)[1] for s in (b/'CMakeCache.txt').read_text(encoding='utf-8').splitlines() if s.startswith('CMAKE_CXX_COMPILER:FILEPATH='))
                    dll=Path(compiler).parent/'clang_rt.asan_dynamic-x86_64.dll';assert dll.exists();env[build]['PATH']=str(dll.parent)+os.pathsep+env[build].get('PATH','')
                    save(d/'runtime.json',dict(path=str(dll),sha256=sha(dll),scope='child PATH only'))
            # Negative guard checks must fail at the intended reason, prior to reading fixture shape.
            fixture=PREVIOUS/'fixtures/arxiv-5000'
            for name,args in [('bad-run',['5','0','2','entry-check']),('bad-repeat',['0','0','1','entry-check']),('bad-warmup',['0','2','20','formal'])]:
                prep.run(name,[exe['release'],fixture,root/'negative'/name]+args,stable=False,expected=1,marker='FAIL formal iteration contract')
            prep.run('bad-shape',[exe['release'],fixture,root/'negative/bad-shape','0','3','20','formal'],stable=False,expected=1,marker='FAIL label shape contract')
            outputs=[]
            for run in range(5):
                out=root/'entry'/f'arxiv-run-{run}';prep.run(f'entry-arxiv-{run}',[exe['release'],fixture,out,str(run),'0','2','entry-check'],stable=run==0,env=env['release']);outputs.append((out,run))
            config(root/'entry-arxiv.json',fixture,outputs,0,2)
            prep.run('verify-entry-arxiv',[sys.executable,'-B',C/'verify.py',root/'entry-arxiv.json',root/'entry-arxiv-analysis'])
            outputs=[];fixture=PREVIOUS/'fixtures/wiki-5000'
            for build in ['release','asan']:
                out=root/'entry'/f'wiki-{build}';prep.run('entry-wiki-'+build,[exe[build],fixture,out,'1','0','2','entry-check'],env=env[build]);outputs.append((out,1))
            config(root/'entry-wiki.json',fixture,outputs,0,2)
            prep.run('verify-entry-wiki',[sys.executable,'-B',C/'verify.py',root/'entry-wiki.json',root/'entry-wiki-analysis'])
        intact(hashes);intact(old)
        # Same 5k answers as the frozen admission; new checks specifically test iteration/rotation.
        entry_root=RESUME if RESUME is not None else root
        for ds,entry in [('arxiv',entry_root/'entry/arxiv-run-0'),('wiki',entry_root/'entry/wiki-release')]:
            import csv
            def canonical(path):
                with path.open(encoding='utf-8',newline='') as stream:rows=list(csv.DictReader(stream,delimiter='\t'))
                values={tuple(sorted(row.items())) for row in rows};assert len(values)==len(rows);return values
            assert canonical(entry/'answers.tsv')==canonical(PREVIOUS/'outputs'/f'{ds}-5000-release'/'answers.tsv')
        prep.finish('passed',entry_checks=7,reused_entry_workers=7 if RESUME else 0,negative_contracts=4,formal_matrix_started=False)
        save(root/'entry-final-check.json',dict(status='passed',entry_workers=7,arxiv_all_five_run_ids=True,wiki_release_asan_two_pass=True,reused_entry_workers=7 if RESUME else 0,negative_contracts_provenance=str(RESUME) if RESUME else str(root),answers_match_frozen_admission=True,old_53_sources_unchanged=True))
        overall['status']='formal_running';save(root/'overall-status.json',overall)
        for ds,exp in UNITS:
            unit=P/'experiments'/exp;unit.mkdir();shutil.copyfile(PROTOCOL,unit/'protocol.md');snapshot(unit,paths)
            inp=unit/'input'/f'{ds}-25000';inp.parent.mkdir();shutil.copytree(PREVIOUS/'fixtures'/f'{ds}-25000',inp)
            manifest=load(inp/'manifest.json');assert all(sha(inp/k)==v for k,v in manifest['files'].items())
            b=unit/'build';b.mkdir()
            for f in (root/'builds/release').iterdir():
                if f.is_file():shutil.copyfile(f,b/f.name)
            binary=b/'scale_formal.exe';assert sha(binary)==load(b/'binary.json')['sha256']
            outputs=[(unit/f'run-{run}',run) for run in range(5)]
            config(unit/'config.json',inp,outputs,3,20)
            save(unit/'budget.json',dict(worker_seconds=600,unit_seconds=1800,private_bytes=2*G,available_floor_bytes=2*G,start_available_bytes=4*G,start_stable_seconds=20,output_bytes=G,previous_forecast=load(PREVIOUS/'budget-reviewed.json'),unit_includes_preflights_and_verification=True))
            (unit/'record.md').write_text('# '+exp+' — '+ds+' 25k纯目录\n\n状态：待启动。配置、输入、协议、源码和二进制已冻结；真实运行以status/commands为准。\n',encoding='utf-8')
            active=Guard(unit,1800);overall['formal_not_started'].remove(exp);overall['active']=exp;save(root/'overall-status.json',overall)
            for out,run in outputs:
                intact(hashes);intact(old);assert sha(binary)==load(b/'binary.json')['sha256']
                active.run(f'run-{run}',[binary,inp,out,str(run),'3','20','formal'])
            active.run('verify-results',[sys.executable,'-B',C/'verify.py',unit/'config.json',unit/'analysis-01'])
            v=load(unit/'analysis-01/verification.json');expected=(23115,20100,3015) if ds=='wiki' else (8625,7500,1125)
            assert (v['timing_rows'],v['measurement_rows'],v['warmup_rows'])==expected and len(v['runs'])==5
            intact(hashes);intact(old);assert active.remaining()>0
            active.finish('passed',formal_workers=5,timing_rows=v['timing_rows'],measurement_rows=v['measurement_rows'],warmup_rows=v['warmup_rows'],full_scope_checks=v['full_scope_checks'],old_53_sources_unchanged=True)
            save(unit/'final-check.json',dict(status='passed',five_independent_processes=True,complete_grid=True,independent_oracle=True,resource_checks=True,unit_budget=True,source_and_input_frozen=True,old_53_sources_unchanged=True,verification_sha256=sha(unit/'analysis-01/verification.json')))
            overall['formal_completed'].append(exp);overall['active']=None;save(root/'overall-status.json',overall);active=None
        overall.update(status='passed',finished_utc=now());save(root/'overall-status.json',overall)
    except Exception as e:
        overall.update(status='resource_blocked' if 'resource' in str(e).lower() else 'failed',error=repr(e),finished_utc=now())
        if active is not None:active.finish(overall['status'],error=repr(e))
        elif prep.status['status']=='running':prep.finish(overall['status'],error=repr(e))
        save(root/'overall-status.json',overall);(root/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8');print(traceback.format_exc(),flush=True);raise
if __name__=='__main__':main()
