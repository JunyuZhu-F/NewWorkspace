# -*- coding: utf-8 -*-
"""Independent path-tuple/set oracle. Does not import preparation or native helpers."""
import csv
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

P=Path.cwd();STRATEGIES={'PE-ONLINE','PE-OFFLINE','TrieHI'}
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def table(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f,delimiter='\t'))
def parts(s):
    assert s.startswith('/') and s.endswith('/') and not any(c.isspace() or c=='\0' for c in s)
    a=tuple(s[1:-1].split('/')) if s!='/' else ()
    assert all(x not in ('','.','..') for x in a)
    return a
def path(t):return '/'+'/'.join(t)+'/' if t else '/'
def below(a,b):return a[:len(b)]==b
def digest(ids):
    h=14695981039346656037
    for i in ids:
        for b in i.to_bytes(4,'little'):h=((h^b)*1099511628211)&((1<<64)-1)
    return str(h)

def fixture(f):
    m=read(f/'manifest.json');assert m['vector_payload_bytes_read']==0
    assert m['protocol_sha256']==sha(P/'notes/scale-prep-protocol-20261027.md')
    assert all(sha(f/k)==v for k,v in m['files'].items())
    source=P/m['source'];s=source.stat();assert (s.st_size,s.st_mtime_ns)==(m['source_proof']['size'],m['source_proof']['mtime_ns'])
    pinned={'arxiv':'127a7d07902cb997489da526be1da973bc9bac09f0da133787f0c28323ea72a2','wiki':'d9642870803d14fa6d9193f743ed1d2a758ab643fcffe248d2d9009cf73a616a'}
    ds=f.name.split('-')[0];assert m['source_proof']['sha256']==pinned[ds]
    rows=read(f/'sample.json');n=m['records'];total=m['source_records']
    assert len(rows)==n and [r['global_id'] for r in rows]==[i*(total-1)//(n-1) for i in range(n)]
    assert (f/'shape.tsv').read_text().split()==[str(n),str(total)]
    assert (f/'bindings.tsv').read_text(encoding='utf-8').splitlines()==[f"{i}\t{r['global_id']}\t{r['path']}" for i,r in enumerate(rows)]
    entries={r['global_id']:parts(r['path']) for r in rows};dirs={()};rec=Counter();local=Counter(entries.values())
    # Derive ancestors by removing final components, independently of preparation's prefix construction.
    for t in entries.values():
        while True:
            dirs.add(t);rec[t]+=1
            if not t:break
            t=t[:-1]
    children=Counter();desc=Counter()
    for t in dirs:
        if t:children[t[:-1]]+=1
        while True:
            desc[t]+=1
            if not t:break
            t=t[:-1]
    assert len(dirs)==m['directories'] and max(map(len,dirs))==m['max_depth']
    anchors=set();missing=[]
    for depth in [0,1,2,4,9,16,24,31]:
        layer=sorted((t for t in dirs if len(t)==depth),key=lambda t:(rec[t],children[t],path(t).encode()))
        if not layer:missing.append(depth);continue
        k=min(4,len(layer));anchors.update(layer[0 if k==1 else j*(len(layer)-1)//(k-1)] for j in range(k))
    terminals=sorted(local,key=lambda t:path(t).encode())
    anchors.update([min(dirs,key=lambda t:(-children[t],path(t).encode())),terminals[0],terminals[-1]])
    assert missing==m['missing_layers'] and len(anchors)<=32
    queries=read(f/'directory-cases.json');assert len(queries)==m['queries']==2*len(anchors)
    expected=[]
    for i,t in enumerate(sorted(anchors,key=lambda t:path(t).encode())):
        for r in [False,True]:expected.append(dict(case=f'd{i}-r{int(r)}',path=path(t),recursive=r,depth=len(t),candidates=rec[t] if r else local[t],children=children[t],descendant_directories=desc[t]))
    assert queries==expected
    assert (f/'directory-cases.tsv').read_text(encoding='utf-8').splitlines()==[f"{q['case']}\t{q['path']}\t{int(q['recursive'])}" for q in queries]
    large=target=None
    for t in sorted(dirs-{()},key=lambda t:(-desc[t],-rec[t],path(t).encode())):
        others=[v for v in dirs if not below(v,t) and not below(t,v)]
        if others:large=t;target=max(others,key=lambda v:path(v).encode());break
    assert large and target
    deep=min((t for t in local if not below(t,large) and not below(large,t) and not below(target,t)),key=lambda t:(-len(t),path(t).encode()))
    holder=parts(m['holder']);assert holder==('__scale_prep__',) and holder not in dirs
    ops=read(f/'operations.json')
    expected_ops=[('move-large','move',large,holder),('merge-large','merge',holder+(large[-1],),target),('move-deep','move',deep,holder),('merge-deep','merge',holder+(deep[-1],),target)]
    assert ops==[dict(case=c,kind=k,source=path(s),target=path(t)) for c,k,s,t in expected_ops]
    assert (f/'operations.tsv').read_text(encoding='utf-8').splitlines()==[f"{o['case']}\t{o['kind']}\t{o['source']}\t{o['target']}" for o in ops]
    dirs.add(holder);states=[(dirs.copy(),entries.copy())];geometry=[]
    for c,k,s,t in expected_ops:
        assert s in dirs and t in dirs and s
        if k=='move':
            assert not below(t,s) and s[:-1]!=t
            replacement=t+(s[-1],);assert replacement not in dirs
        else:
            assert not below(s,t) and not below(t,s)
            replacement=t
        moved_dirs=sum(below(d,s) for d in dirs);moved_entries=sum(below(p,s) for p in entries.values())
        before=len(dirs)
        dirs={replacement+d[len(s):] if below(d,s) else d for d in dirs}
        entries={i:replacement+p[len(s):] if below(p,s) else p for i,p in entries.items()}
        assert all(p in dirs for p in entries.values())
        assert all(not d or d[:-1] in dirs for d in dirs)
        geometry.append(dict(case=c,source_directories=moved_dirs,source_entries=moved_entries,directories_before=before,directories_after=len(dirs)))
        states.append((dirs.copy(),entries.copy()))
    answers={}
    for stage,(ds,es) in enumerate(states):
        for q in queries:
            t=parts(q['path']);exists=t in ds
            ids=sorted(i for i,p in es.items() if exists and (below(p,t) if q['recursive'] else p==t))
            answers[(str(stage),q['case'])]=(str(int(exists)),str(len(ids)),digest(ids))
    return m,queries,ops,states,answers,geometry

def output(out,m,queries,ops,states,expected):
    rows=table(out/'answers.tsv');seen=set();canonical={}
    for row in rows:
        key=(row['strategy'],row['stage'],row['case']);assert key not in seen;seen.add(key)
        assert row['strategy'] in STRATEGIES and (row['exists'],row['count'],row['digest'])==expected[key[1:]]
        canonical[key]=(row['exists'],row['count'],row['digest'])
    assert seen=={(s,stage,c) for s in STRATEGIES for stage,c in expected}
    rows=table(out/'timings.tsv');seen=set()
    phase=['directory_misc_ns','locate_ns','bitmap_copy_ns','bitmap_sets_ns','ancestors_ns','catalog_ns','cleanup_ns']
    for r in rows:
        assert r['strategy'] in STRATEGIES and r['run']==r['pass']==r['warmup']=='0' and int(r['total_ns'])>=0 and all(int(r[p])==0 for p in phase)
        key=(r['strategy'],r['kind'],r['case']);assert key not in seen;seen.add(key)
    units={('build','build')}|{('query',q['case']) for q in queries}|{(o['kind'],o['case']) for o in ops}
    assert seen=={(s,k,c) for s in STRATEGIES for k,c in units}
    space=table(out/'space.tsv');seen=set();portable={}
    for r in space:
        s=r['strategy'];stage=int(r['stage']);key=(s,stage);assert key not in seen and s in STRATEGIES;seen.add(key)
        assert r['run']==r['pass']=='0' and int(r['directories'])==len(states[stage][0]) and int(r['catalog_entries'])==m['records']
        assert int(r['bitmaps'])==len(states[stage][0]) and int(r['portable_bytes'])>=0
        portable[key]=r['portable_bytes']
    assert seen=={(s,i) for s in STRATEGIES for i in range(5)}
    clocks=table(out/'clock.tsv');assert len(clocks)==10000 and all(int(r['nanoseconds'])>=0 for r in clocks) and any(int(r['nanoseconds'])>0 for r in clocks)
    wall=table(out/'wall.tsv');assert len(wall)==5
    assert (wall[0]['kind'],wall[0]['strategy'],wall[0]['pass'])==('setup','all','-1')
    assert (wall[-1]['kind'],wall[-1]['strategy'],wall[-1]['pass'])==('total','all','-1')
    assert {r['strategy'] for r in wall[1:4]}==STRATEGIES and all(r['kind']=='pass' and r['pass']=='0' for r in wall[1:4])
    ns=[int(r['elapsed_ns']) for r in wall];assert all(v>=0 for v in ns) and ns[-1]>=sum(ns[:-1])
    return canonical,portable,dict(answers=len(expected)*3,timings=len(rows),space=len(space),scope_checks=len(expected)*3,setup_s=ns[0]/1e9,cycle_s=sum(ns[1:4])/1e9,total_s=ns[-1]/1e9,files={p.name:sha(p) for p in out.iterdir() if p.is_file()})

def main():
    started=time.perf_counter();f=Path(sys.argv[1]);dest=Path(sys.argv[2]);assert not dest.exists()
    m,qs,ops,states,expected,geometry=fixture(f);runs=[];prior=None
    for arg in sys.argv[3:]:
        out=Path(arg);a,p,stats=output(out,m,qs,ops,states,expected)
        if prior is not None:assert prior==(a,p),'Release/ASan mismatch'
        prior=(a,p);runs.append(dict(output=str(out),**stats))
    assert runs
    result=dict(status='passed',fixture=str(f),records=m['records'],queries=len(qs),directories=m['directories'],geometry=geometry,runs=runs,independent_oracle='tuple-prefix enumeration; full native sets independently checked in C++',source_check='pinned metadata hash from preparation; unchanged size/mtime, selected-source independent scan performed by pipeline',verification_s=time.perf_counter()-started,verifier_sha256=sha(Path(__file__)))
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('PASS',f.name,'outputs',len(runs),flush=True)
if __name__=='__main__':main()
