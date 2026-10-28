# -*- coding: utf-8 -*-
"""Read-only metadata geometry/resource assessment. No vector payloads or indexes."""
from collections import Counter
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import subprocess
import time

import psutil

P=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
SIZES=(10000,25000,50000,100000)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def stat(p):s=p.stat();return dict(size=s.st_size,mtime_ns=s.st_mtime_ns)

class Profile:
    def __init__(self,n,total):
        self.n=n;self.wanted={i*(total-1)//(n-1) for i in range(n)};self.rec=Counter();self.local=Counter();self.depth=Counter();self.path_bytes=0;self.max_path=0;self.count=0
    def add(self,row,path):
        if row not in self.wanted:return
        self.count+=1;self.path_bytes+=len(path.encode());self.max_path=max(self.max_path,len(path.encode()));parts=path.strip('/').split('/');self.depth[len(parts)]+=1;self.local[path]+=1
        self.rec['/']+=1;prefix='/'
        for part in parts:prefix+=part+'/';self.rec[prefix]+=1
    def finish(self,dataset):
        assert self.count==self.n
        child=Counter()
        for p in self.rec:
            if p!='/':child[p.rstrip('/').rsplit('/',1)[0]+'/']+=1
        def depth(p):return p.count('/')-1
        result=dict(dataset=dataset,n=self.n,selection='floor(i*(total-1)/(n-1))',directories=len(self.rec),terminal_directories=len(self.local),entry_path_utf8_bytes=self.path_bytes,unique_directory_utf8_bytes=sum(len(p.encode()) for p in self.rec),mean_entry_depth=sum(k*v for k,v in self.depth.items())/self.n,max_depth=max(self.depth),max_path_utf8_bytes=self.max_path,max_children=max(child.values()))
        if dataset=='WIKI':
            levels={d:sorted((p for p in self.rec if depth(p)==d),key=lambda p:(self.rec[p],child[p],p.encode())) for d in (0,1,2,4,9,16,24,31)}
            assert all(levels.values())
            ids=list(range(456))
            compact=[]
            for residue in range(8):
                group=list(range(residue,456,8));compact.extend(group[i*(len(group)-1)//7] for i in range(8))
            case_sets={}
            for name,qids in [('full456',ids),('compact64',sorted(compact))]:
                cases=[]
                for q in qids:
                    group=levels[(0,1,2,4,9,16,24,31)[q%8]];h=hashlib.sha256(f'WIKI-SCOPE-v1|{q}'.encode()).digest();path=group[int.from_bytes(h[:8],'little')%len(group)]
                    for r in (False,True):cases.append((path,r))
                case_sets[name]=self.case_stats(cases)
        else:
            queries=json.loads((P/'dataset/raw/ARXIV-Dir/arxiv_query_constraint.json').read_text(encoding='utf-8'))
            queries=[x for x in queries if 'time' in x['constraints']];assert len(queries)==501
            bydepth={d:[q for q in queries if len(q['constraints']['time'].strip('/').split('/'))==d] for d in (1,2)}
            compact=[group[i*(len(group)-1)//31] for group in bydepth.values() for i in range(32)]
            case_sets={name:self.case_stats([('/'+q['constraints']['time'].strip('/')+'/',r) for q in qs for r in (False,True)]) for name,qs in [('full501',queries),('compact64',compact)]}
        result['search_workload_geometry']=case_sets
        return result
    def case_stats(self,cases):
        counts=[self.rec[p] if r else self.local[p] for p,r in cases]
        return dict(cases=len(cases),recursive_nonempty=sum(r and c>0 for (_,r),c in zip(cases,counts)),nonrecursive_nonempty=sum(not r and c>0 for (_,r),c in zip(cases,counts)),sum_candidate_ids_per_probe=sum(counts),max_candidates=max(counts),root_recursive=sum(p=='/' and r for p,r in cases),
                    baseline_candidates_min_bytes=16*sum(counts),baseline_hits_full_probe_min_bytes=32*sum(counts),
                    baseline_candidate_and_hit_capacity_min_bytes=48*sum(counts),
                    baseline_candidate_and_hit_payload_stl_1p5_scenario_bytes=112*sum(counts),
                    scopes_ascii_worst_payload_bytes=24*sum(counts))

def main():
    assert not (OUT/'profile.json').exists()
    start=time.monotonic();status=dict(status='running',started_utc=now(),purpose='metadata-only resource profile, not latency measurement');save(OUT/'status.json',status)
    try:
        hardware=dict(platform=platform.platform(),logical_cpus=psutil.cpu_count(),physical_cpus=psutil.cpu_count(logical=False),disk_D=shutil.disk_usage('D:/')._asdict(),memory_total=psutil.virtual_memory().total,samples=[])
        for _ in range(5):
            cpu=psutil.cpu_percent(interval=1);v=psutil.virtual_memory();hardware['samples'].append(dict(at=now(),available=v.available,used=v.used,cpu_percent=cpu))
        save(OUT/'hardware.json',hardware)
        max_private=0;minimum_available=psutil.virtual_memory().available
        def gate():
            nonlocal max_private,minimum_available
            v=psutil.virtual_memory();private=getattr(psutil.Process().memory_info(),'private',psutil.Process().memory_info().rss);max_private=max(max_private,private);minimum_available=min(minimum_available,v.available)
            assert private<2**31 and v.available>=2**31,'Assessment resource stop'
            assert time.monotonic()-start<180,'Metadata assessment timeout'
        allresults=[];proofs={};inputs={}
        for dataset,total in [('ARXIV',2763543),('WIKI',1941679)]:
            profiles=[Profile(n,total) for n in SIZES]
            if dataset=='ARXIV':
                source=P/'notes/arxiv-time-full-audit-20261027-01/run-01/bindings.tsv';before=stat(source);h=hashlib.sha256()
                with source.open('rb') as f:
                    for row,line in enumerate(f):
                        h.update(line)
                        for profile in profiles:
                            if row in profile.wanted:
                                id_,path=line.decode().rstrip('\n').split('\t');assert int(id_)==row;profile.add(row,path)
                        if row%250000==0:gate()
                assert row+1==total and h.hexdigest()=='127a7d07902cb997489da526be1da973bc9bac09f0da133787f0c28323ea72a2'
                proof=dict(sha256=h.hexdigest(),records=total)
            else:
                source=P/'dataset/raw/WIKI-Dir/dbpedia_dir_2m_corpus_paths.json';before=stat(source)
                dependency=P/'notes/arxiv-time-full-audit-20261027-01/audit.py';spec=importlib.util.spec_from_file_location('strict_metadata',dependency);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);proof={}
                for row,obj in enumerate(module.strict_records(source,proof)):
                    for profile in profiles:
                        if row in profile.wanted:assert obj['id']==row;profile.add(row,obj['path'])
                    if row%250000==0:gate()
                assert row+1==total and proof['sha256']=='d9642870803d14fa6d9193f743ed1d2a758ab643fcffe248d2d9009cf73a616a'
                proof['parser_sha256']=sha(dependency)
            assert stat(source)==before;inputs[dataset]=dict(path=str(source.relative_to(P)),stat=before);proofs[dataset]=proof
            for profile in profiles:allresults.append(profile.finish(dataset));gate()
            del profiles
        vectors={}
        for ds,name in [('ARXIV','arxiv_corpus_vectors.fvecs'),('WIKI','dbpedia_dir_2m_corpus_vectors-001.fvecs')]:
            path=P/'dataset/raw'/(ds+'-Dir')/name;vectors[ds]=dict(path=str(path.relative_to(P)),**stat(path),payload_bytes_read=0)
        result=dict(status='passed',started_utc=status['started_utc'],finished_utc=now(),elapsed_seconds=time.monotonic()-start,geometry=allresults,source_proofs=proofs,inputs=inputs,vectors=vectors,vector_payload_bytes_read=0,assessment_peak_private_bytes_sampled=max_private,assessment_minimum_available_bytes_sampled=minimum_available,
                    current_git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip(),script_sha256=sha(Path(__file__)))
        save(OUT/'profile.json',result);status.update(status='passed',finished_utc=now());save(OUT/'status.json',status)
        print(json.dumps(dict(status='passed',profiles=len(allresults),seconds=result['elapsed_seconds'],peak_private=max_private)))
    except BaseException as e:status.update(status='failed',error=repr(e),finished_utc=now());save(OUT/'status.json',status);raise
if __name__=='__main__':main()
