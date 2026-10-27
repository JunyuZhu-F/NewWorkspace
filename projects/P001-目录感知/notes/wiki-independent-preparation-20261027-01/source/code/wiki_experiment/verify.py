"""Independent WIKI path-state and scoped exhaustive L2 verification."""
import argparse
from array import array
from collections import defaultdict
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

P=Path.cwd()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def stats(v):
    a=np.sort(np.asarray(v,dtype=np.int64));assert len(a)
    return dict(count=len(a),mean_ns=float(a.mean()),**{f'p{q}_ns':int(a[math.ceil(float(q)/100*len(a))-1]) for q in ('90','95','99','99.9')})
def digest(ids):
    h=14695981039346656037
    for x in sorted(ids):
        for b in int(x).to_bytes(4,'little'):h=((h^b)*1099511628211)&((1<<64)-1)
    return h
def fixture(f):
    m=load(f/'manifest.json');assert m['protocol_sha256']==sha(P/'notes/wiki-independent-protocol-20261027.md')
    for n,h in m['files'].items():assert sha(f/n)==h,n
    old=P/'notes/wiki-preparation-20261027-01/run-01/sample.json';assert sha(old)==m['sample_source_sha256']
    sample=load(f/'sample.json');assert [dict(global_id=x['global_id'],path=x['path']) for x in sample]==load(old)
    assert [x['row'] for x in sample]==list(range(10000))
    for n,dest in [('dbpedia_dir_2m_corpus_vectors-001.fvecs','corpus.fvecs'),('dbpedia_dir_2m_query_vectors.fvecs','queries.fvecs')]:
        source=P/'dataset/raw/WIKI-Dir'/n;info=m['inputs'][n];s=source.stat();assert (s.st_size,s.st_mtime_ns)==(info['size'],info['mtime_ns'])
        h=hashlib.sha256()
        with source.open('rb') as raw,(f/dest).open('rb') as derived:
            for row in info['rows']:
                raw.seek(4100*row);b=raw.read(4100);assert len(b)==4100 and derived.read(4100)==b;h.update(b)
            assert not derived.read(1)
        assert h.hexdigest()==info['records_sha256']
    # Reconstruct all directory descriptors independently of the preparation counters.
    entries={x['global_id']:x['path'] for x in sample};dirs={'/'}
    for path in entries.values():
        while path!='/':dirs.add(path);path=path[:path.rfind('/',0,len(path)-1)+1]
    assert len(dirs)==23025
    children=defaultdict(int)
    for d in dirs-{'/'}:children[d.rstrip('/').rsplit('/',1)[0]+'/']+=1
    candidates={d:sum(p.startswith(d) for p in entries.values()) for d in dirs}
    levels={n:sorted((d for d in dirs if d.count('/')-1==n),key=lambda d:(candidates[d],children[d],d.encode())) for n in (0,1,2,4,9,16,24,31)}
    expected_cases=[]
    for q in range(456):
        group=levels[(0,1,2,4,9,16,24,31)[q%8]];h=hashlib.sha256(f'WIKI-SCOPE-v1|{q}'.encode()).digest();d=group[int.from_bytes(h[:8],'little')%len(group)]
        for r in (False,True):expected_cases.append(dict(case=f'q{q}-r{int(r)}',query_id=q,query_row=q,path=d,recursive=r,k=10))
    assert load(f/'cases.json')==expected_cases
    anchors=set()
    for group in levels.values():
        n=min(4,len(group));anchors.update(group[0 if n==1 else j*(len(group)-1)//(n-1)] for j in range(n))
    terminal=sorted(set(entries.values()),key=lambda d:d.encode());anchors.update((min(dirs,key=lambda d:(-children[d],d.encode())),terminal[0],terminal[-1]))
    dq=load(f/'directory-cases.json');assert [(x['path'],x['recursive']) for x in dq]==[(d,r) for d in sorted(anchors,key=lambda d:d.encode()) for r in (False,True)]
    assert (f/'bindings.tsv').read_text(encoding='utf-8')==''.join(f"{x['row']}\t{x['global_id']}\t{x['path']}\n" for x in sample)
    assert (f/'cases.tsv').read_text(encoding='utf-8')==''.join(f"{x['case']}\t{x['query_row']}\t{x['path']}\t{int(x['recursive'])}\t10\n" for x in expected_cases)
    assert (f/'directory-cases.tsv').read_text(encoding='utf-8')==''.join(f"{x['case']}\t{x['path']}\t{int(x['recursive'])}\n" for x in dq)
    ops=load(f/'operations.json');assert (f/'operations.tsv').read_text(encoding='utf-8')==''.join(f"{x['case']}\t{x['kind']}\t{x['source']}\t{x['target']}\n" for x in ops)
    a=min(levels[2],key=lambda d:(-candidates[d],d.encode()));b=max([d for d in levels[1] if not d.startswith(a) and not a.startswith(d)],key=lambda d:d.encode())
    c=min([d for d in terminal if not d.startswith(a) and not a.startswith(d) and not b.startswith(d)],key=lambda d:(-(d.count('/')-1),d.encode()))
    moved=lambda d:'/__wiki_bench__/'+d.rstrip('/').rsplit('/',1)[1]+'/'
    assert [(o['case'],o['kind'],o['source'],o['target']) for o in ops]==[('move-large','move',a,'/__wiki_bench__/'),('merge-large','merge',moved(a),b),('move-deep','move',c,'/__wiki_bench__/'),('merge-deep','merge',moved(c),b)]
    return m,sample,entries,dirs

def directory(f,outputs,formal):
    m,sample,entries,dirs=fixture(f);dirs.add('/__wiki_bench__/')
    queries=load(f/'directory-cases.json');qmap={x['case']:x for x in queries};ops=load(f/'operations.json')
    expected={};spaces={};opmetrics=[]
    def snapshot(stage):
        spaces[stage]=(len(dirs),len(entries))
        for q in queries:
            ids=[i for i,p in entries.items() if (p.startswith(q['path']) if q['recursive'] else p==q['path'])] if q['path'] in dirs else []
            expected[(stage,q['case'])]=(str(int(q['path'] in dirs)),str(len(ids)),str(digest(ids)))
    snapshot(0)
    for stage,op in enumerate(ops,1):
        a,b=op['source'],op['target'];assert a in dirs and b in dirs and a!='/' and not b.startswith(a)
        if op['kind']=='move':
            replacement=b+a.rstrip('/').rsplit('/',1)[1]+'/';assert replacement not in dirs
        else:assert not a.startswith(b);replacement=b
        opmetrics.append(dict(**op,source_directories=sum(d.startswith(a) for d in dirs),source_entries=sum(p.startswith(a) for p in entries.values()),source_depth=a.count('/')-1,target_depth=b.count('/')-1,conflict_directories=sum(replacement+d[len(a):] in dirs for d in dirs if d.startswith(a))))
        dirs={replacement+d[len(a):] if d.startswith(a) else d for d in dirs}
        entries={i:(replacement+p[len(a):] if p.startswith(a) else p) for i,p in entries.items()};snapshot(stage)
    pools=defaultdict(lambda:[array('q') for _ in range(8)]);workers=[];canonical=None
    for output in outputs:
        answers={}
        for row in csv.DictReader((output/'answers.tsv').open(encoding='utf-8'),delimiter='\t'):
            k=(row['strategy'],int(row['stage']),row['case']);assert k not in answers
            assert tuple(row[x] for x in ('exists','count','digest'))==expected[(k[1],k[2])];answers[k]=tuple(row[x] for x in ('exists','count','digest'))
        assert len(answers)==3*5*len(queries)
        if canonical is None:canonical=answers
        else:assert canonical==answers
        seen=set();per=defaultdict(list);n=0
        grid={(s,p,k,c) for s in ('PE-ONLINE','PE-OFFLINE','TrieHI') for p in range(23 if formal else 1) for k,c in [('build','build')]+[('query',x['case']) for x in queries]+[(x['kind'],x['case']) for x in ops]}
        for row in csv.DictReader((output/'timings.tsv').open(encoding='utf-8'),delimiter='\t'):
            key=(row['strategy'],int(row['pass']),row['kind'],row['case']);assert key in grid and key not in seen;seen.add(key)
            assert row['strategy'] in ('PE-ONLINE','PE-OFFLINE','TrieHI')
            assert row['kind'] in ('build','query','move','merge')
            assert (row['case'] in qmap if row['kind']=='query' else row['case']=='build' if row['kind']=='build' else row['case'] in {x['case'] for x in ops})
            assert 0<=key[1]<(23 if formal else 1) and int(row['warmup'])==int(formal and key[1]<3)
            vals=[int(row[x]) for x in ('total_ns','directory_misc_ns','locate_ns','bitmap_copy_ns','bitmap_sets_ns','ancestors_ns','catalog_ns','cleanup_ns')]
            assert min(vals)>=0 and sum(vals[1:])<=vals[0]
            if 'phase' not in output.name:assert not any(vals[1:])
            if row['warmup']=='0':
                group=(row['strategy'],row['kind'],str(qmap[row['case']]['recursive']) if row['kind']=='query' else row['case'])
                for array_,v in zip(pools[group],vals):array_.append(v)
                per[group].append(vals[0])
            n+=1
        assert seen==grid and n==3*(23 if formal else 1)*(5+len(queries))
        clocks=np.loadtxt(output/'clock.tsv',skiprows=1,dtype=np.int64);assert clocks.shape==(10000,) and np.min(clocks)>=0
        space_seen=set();space_values={}
        for row in csv.DictReader((output/'space.tsv').open(encoding='utf-8'),delimiter='\t'):
            stage=int(row['stage']);key=(row['strategy'],int(row['pass']),stage);assert key[0] in ('PE-ONLINE','PE-OFFLINE','TrieHI') and 0<=key[1]<(23 if formal else 1) and key not in space_seen;space_seen.add(key)
            assert (int(row['directories']),int(row['catalog_entries']))==spaces[stage]
            assert int(row['bitmaps'])==int(row['directories'])
            value=int(row['portable_bytes']);k=(row['strategy'],stage)
            assert space_values.setdefault(k,value)==value
        assert len(space_seen)==3*5*(23 if formal else 1)
        workers.append(dict(output=str(output),rows=n,files={x.name:sha(x) for x in output.iterdir() if x.is_file()},groups=[dict(strategy=k[0],kind=k[1],case=k[2],total=stats(v)) for k,v in sorted(per.items())],portable=[dict(strategy=k[0],stage=k[1],bytes=v) for k,v in sorted(space_values.items())]))
    return dict(status='passed',formal=formal,kind='directory',directory_cases=len(queries),operations=opmetrics,workers=workers,raw_rows=sum(x['rows'] for x in workers),groups=[dict(strategy=k[0],kind=k[1],case=k[2],**{name:stats(v) for name,v in zip(('total','directory_misc','locate','bitmap_copy','bitmap_sets','ancestors','catalog','cleanup'),arrays)}) for k,arrays in sorted(pools.items())])

def matrix(p):
    a=np.fromfile(p,dtype=np.dtype([('d','<i4'),('v','<f4',(1024,))]));assert (a['d']==1024).all() and np.isfinite(a['v']).all();return a['v'].astype(np.float64)

def search(f,outputs,formal):
    m,sample,entries,dirs=fixture(f);cases=load(f/'cases.json');x,q=matrix(f/'corpus.fvecs'),matrix(f/'queries.fvecs');assert x.shape==(10000,1024) and q.shape==(456,1024)
    model_hash=sha(outputs[0]/'model.json');model=load(outputs[0]/'model.json');assert model['clusters']==16 and model['dimension']==1024
    centers=np.asarray(model['centers']).reshape(16,1024);assignment=np.asarray(model['assignment']);assert assignment.shape==(10000,) and np.isfinite(centers).all()
    assert np.array_equal(np.argmin(np.stack([np.sum((x-c)**2,axis=1) for c in centers],axis=1),axis=1),assignment)
    global_ids=np.array([b['global_id'] for b in sample]);paths=[tuple(b['path'].strip('/').split('/')) for b in sample]
    truth={};scopes={};expected={};quality=defaultdict(list);bycase={c['case']:c for c in cases};caseindex={c['case']:i for i,c in enumerate(cases)}
    for c in cases:
        parts=tuple(c['path'].strip('/').split('/')) if c['path']!='/' else ()
        ids=np.array([i for i,p in enumerate(paths) if (p[:len(parts)]==parts if c['recursive'] else p==parts)],dtype=np.int64)
        scopes[c['case']]=(c['path'] in dirs,global_ids[ids].tolist())
        dist=np.sum((x[ids]-q[c['query_row']])**2,axis=1);rank=np.lexsort((global_ids[ids],dist))[:10];gt=global_ids[ids[rank]].tolist();truth[c['case']]=gt
        coarse=np.sum((centers-q[c['query_row']])**2,axis=1);order=np.lexsort((np.arange(16),coarse))
        for probe in (0,1,4,16):
            keep=np.ones(len(ids),dtype=bool) if probe==0 else np.isin(assignment[ids],order[:probe]);retained=ids[keep];values=dist[keep];ranking=np.lexsort((global_ids[retained],values))[:10]
            found=global_ids[retained[ranking]].tolist();expected[(c['case'],probe)]=(found,values[ranking]);recall=len(set(found)&set(gt))/len(gt) if gt else None
            if probe in (0,16):assert found==gt and recall in (1.,None)
            quality[(c['recursive'],probe)].append(recall)
    strategies=('PE-ONLINE','PE-OFFLINE','TrieHI');pi={p:i for i,p in enumerate((0,1,4,16))};pools=defaultdict(lambda:[array('q') for _ in range(4)]);workers=[];canonical=None
    for output in outputs:
        assert sha(output/'model.json')==model_hash
        seen_scopes=set()
        for line in (output/'scopes.tsv').read_text(encoding='utf-8').splitlines():
            s,c,e,ids=line.split('\t');assert s in strategies and (s,c) not in seen_scopes;seen_scopes.add((s,c));assert (bool(int(e)),[int(i) for i in ids.split(',')] if ids else [])==scopes[c]
        assert len(seen_scopes)==3*912
        answers={}
        with (output/'answers.jsonl').open(encoding='utf-8') as h:
            for line in h:
                r=json.loads(line);k=(r['strategy'],r['case'],r['probes']);assert k not in answers and k[0] in strategies and k[2] in pi
                ids,dist=expected[(k[1],k[2])];assert r['ids']==ids and np.allclose(r['distances'],dist,rtol=1e-11,atol=1e-11),k;answers[k]=(r['ids'],r['distances'])
        assert len(answers)==3*912*4
        if canonical is None:canonical=answers
        else:assert answers==canonical
        repetitions=20 if formal else 1;seen=np.zeros((3,912,4,repetitions),dtype=bool);per=defaultdict(list);run=None;n=0
        with (output/'timings.csv').open(newline='',encoding='utf-8') as h:
            for r in csv.DictReader(h):
                s,c,probe,rep=r['strategy'],bycase[r['case']],int(r['probes']),int(r['repeat']);idx=(strategies.index(s),caseindex[c['case']],pi[probe],rep);assert 0<=rep<repetitions and not seen[idx];seen[idx]=True
                v=[int(r[k]) for k in ('directory_ns','materialize_ns','ranking_ns','total_ns')];assert min(v)>=0 and sum(v[:3])==v[3]
                rr=int(r['run']);run=rr if run is None else run;assert rr==run
                k=(s,c['recursive'],probe,not bool(truth[c['case']]))
                for array_,value in zip(pools[k],v):array_.append(value)
                per[k].append(v[3]);n+=1
        assert seen.all() and n==3*912*4*repetitions
        order=[(a,int(b)) for a,b in (line.split() for line in (output/'order.tsv').read_text().splitlines())];assert len(order)==len(set(order))==3648 and set(order)==set(expected)
        workers.append(dict(output=str(output),run=run,rows=n,files={x.name:sha(x) for x in output.iterdir() if x.is_file()},groups=[dict(strategy=k[0],recursive=k[1],probes=k[2],empty=k[3],total=stats(v)) for k,v in sorted(per.items())]))
    if formal:assert len(outputs)==5 and sorted(w['run'] for w in workers)==list(range(5))
    return dict(status='passed',kind='search',formal=formal,cases=912,model_sha256=model_hash,ndcg_reported=False,published_gt_used=False,source_regions_reverified=True,quality=[dict(recursive=k[0],probes=k[1],nonempty=sum(x is not None for x in v),empty=sum(x is None for x in v),mean_recall_nonempty=float(np.mean([x for x in v if x is not None])) if any(x is not None for x in v) else None) for k,v in sorted(quality.items())],groups=[dict(strategy=k[0],recursive=k[1],probes=k[2],empty=k[3],**{name:stats(v) for name,v in zip(('directory','materialize','ranking','total'),arrays)}) for k,arrays in sorted(pools.items())],workers=workers,raw_rows=sum(x['rows'] for x in workers))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--kind',choices=('directory','search'),required=True);ap.add_argument('--fixture',type=Path,required=True);ap.add_argument('--outputs',type=Path,nargs='+',required=True);ap.add_argument('--report',type=Path,required=True);ap.add_argument('--formal',action='store_true');a=ap.parse_args();assert not a.report.exists()
    report=(directory if a.kind=='directory' else search)(a.fixture,a.outputs,a.formal);save(a.report,report);print(json.dumps({k:report[k] for k in ('status','kind','raw_rows')}))
if __name__=='__main__':main()
