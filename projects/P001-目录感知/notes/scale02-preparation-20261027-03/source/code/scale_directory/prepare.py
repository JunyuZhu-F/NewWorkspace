# -*- coding: utf-8 -*-
"""Pure-directory fixtures; no NumPy, vector payload, qrels or query loading."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

P=Path.cwd();HOLDER='/__scale_prep__/'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def valid(path):
    assert isinstance(path,str) and path.startswith('/') and path.endswith('/') and '\0' not in path and not any(c.isspace() for c in path)
    assert path=='/' or all(x not in ('','.','..') for x in path[1:-1].split('/'))
def build_fixture(out,rows,total,source,proof):
    out.mkdir(exist_ok=False);n=len(rows);assert 2<=n<=25000
    assert [r['global_id'] for r in rows]==[i*(total-1)//(n-1) for i in range(n)]
    recursive=Counter();local=Counter();children=Counter();descendants=Counter()
    for r in rows:
        path=r['path'];valid(path);local[path]+=1;recursive['/']+=1;prefix='/'
        if path!='/':
            for part in path.strip('/').split('/'):prefix+=part+'/';recursive[prefix]+=1
    assert HOLDER not in recursive
    for d in recursive:
        descendants['/']+=1
        if d!='/':
            children[d.rstrip('/').rsplit('/',1)[0]+'/']+=1;prefix='/'
            for part in d.strip('/').split('/'):prefix+=part+'/';descendants[prefix]+=1
    layers={k:sorted([d for d in recursive if d.count('/')-1==k],key=lambda d:(recursive[d],children[d],d.encode())) for k in (0,1,2,4,9,16,24,31)}
    anchors=set()
    for paths in layers.values():
        count=min(4,len(paths))
        if count:anchors.update(paths[0 if count==1 else i*(len(paths)-1)//(count-1)] for i in range(count))
    terminal=sorted(local,key=lambda p:p.encode());anchors.update((min(recursive,key=lambda d:(-children[d],d.encode())),terminal[0],terminal[-1]));assert len(anchors)<=32
    queries=[dict(case=f'd{i}-r{int(r)}',path=path,recursive=r,depth=path.count('/')-1,candidates=recursive[path] if r else local[path],children=children[path],descendant_directories=descendants[path]) for i,path in enumerate(sorted(anchors,key=lambda p:p.encode())) for r in (False,True)]
    large=None;target=None
    for d in sorted((d for d in recursive if d!='/'),key=lambda d:(-descendants[d],-recursive[d],d.encode())):
        possible=[t for t in recursive if not t.startswith(d) and not d.startswith(t)]
        if possible:large=d;target=max(possible,key=lambda t:t.encode());break
    assert large and target
    deep=min((d for d in local if not d.startswith(large) and not large.startswith(d) and not target.startswith(d)),key=lambda d:(-(d.count('/')-1),d.encode()))
    moved=lambda d:HOLDER+d.rstrip('/').rsplit('/',1)[1]+'/'
    ops=[dict(case='move-large',kind='move',source=large,target=HOLDER),dict(case='merge-large',kind='merge',source=moved(large),target=target),dict(case='move-deep',kind='move',source=deep,target=HOLDER),dict(case='merge-deep',kind='merge',source=moved(deep),target=target)]
    (out/'shape.tsv').write_text(f'{n}\t{total}\n',encoding='utf-8')
    (out/'bindings.tsv').write_text(''.join(f"{i}\t{r['global_id']}\t{r['path']}\n" for i,r in enumerate(rows)),encoding='utf-8')
    (out/'directory-cases.tsv').write_text(''.join(f"{q['case']}\t{q['path']}\t{int(q['recursive'])}\n" for q in queries),encoding='utf-8')
    (out/'operations.tsv').write_text(''.join(f"{x['case']}\t{x['kind']}\t{x['source']}\t{x['target']}\n" for x in ops),encoding='utf-8')
    save(out/'sample.json',rows);save(out/'directory-cases.json',queries);save(out/'operations.json',ops)
    save(out/'manifest.json',dict(records=n,source_records=total,source=source,source_proof=proof,queries=len(queries),directories=len(recursive),max_depth=max(d.count('/')-1 for d in recursive),missing_layers=[k for k,v in layers.items() if not v],holder=HOLDER,vector_payload_bytes_read=0,protocol_sha256=sha(P/'notes/scale-prep-protocol-20261027.md'),files={f.name:sha(f) for f in out.iterdir() if f.is_file()}))

def main():
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
    for ds,total in [('arxiv',2763543),('wiki',1941679)]:
        sizes=(5000,25000);wanted={n:{i*(total-1)//(n-1) for i in range(n)} for n in sizes};selected={n:[] for n in sizes}
        if ds=='arxiv':
            path=P/'notes/arxiv-time-full-audit-20261027-01/run-01/bindings.tsv';s=path.stat();h=hashlib.sha256()
            with path.open('rb') as f:
                for row,line in enumerate(f):
                    h.update(line)
                    if any(row in wanted[n] for n in sizes):
                        gid,p=line.decode('utf-8').rstrip('\n').split('\t');assert int(gid)==row
                        for n in sizes:
                            if row in wanted[n]:selected[n].append(dict(global_id=row,path=p))
            assert row+1==total and h.hexdigest()=='127a7d07902cb997489da526be1da973bc9bac09f0da133787f0c28323ea72a2'
            proof=dict(sha256=h.hexdigest(),size=s.st_size,mtime_ns=s.st_mtime_ns)
        else:
            path=P/'dataset/raw/WIKI-Dir/dbpedia_dir_2m_corpus_paths.json';s=path.stat();proof={}
            spec=importlib.util.spec_from_file_location('strict_metadata',P/'notes/arxiv-time-full-audit-20261027-01/audit.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            for row,obj in enumerate(module.strict_records(path,proof)):
                for n in sizes:
                    if row in wanted[n]:assert obj['id']==row;selected[n].append(dict(global_id=row,path=obj['path']))
            assert row+1==total and proof['sha256']=='d9642870803d14fa6d9193f743ed1d2a758ab643fcffe248d2d9009cf73a616a'
            proof.update(size=s.st_size,mtime_ns=s.st_mtime_ns)
        assert (s.st_size,s.st_mtime_ns)==(path.stat().st_size,path.stat().st_mtime_ns)
        for n in sizes:build_fixture(out/f'{ds}-{n}',selected[n],total,str(path.relative_to(P)),proof)
        print(ds,'pure directory fixtures passed',flush=True)
if __name__=='__main__':main()
