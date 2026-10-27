"""Freeze WIKI project scopes without reading qrels or query text."""
import collections
import hashlib
import json
from pathlib import Path
import struct
import sys

import numpy as np

P=Path.cwd()
PROTOCOL=P/'notes/wiki-independent-protocol-20261027.md'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
    rows=json.loads((P/'notes/wiki-preparation-20261027-01/run-01/sample.json').read_text(encoding='utf-8'))
    assert [x['global_id'] for x in rows]==[i*(1941679-1)//9999 for i in range(10000)]
    dirs={'/'};recursive=collections.Counter({'/':10000});local=collections.Counter();children=collections.Counter()
    for x in rows:
        path=x['path'];assert not any(c.isspace() for c in path)
        local[path]+=1
        segments=path.strip('/').split('/')
        for n in range(1,len(segments)+1):
            d='/'+'/'.join(segments[:n])+'/'
            recursive[d]+=1;dirs.add(d)
    for d in dirs-{'/'}:children[d.rstrip('/').rsplit('/',1)[0]+'/']+=1
    def depth(d):return d.count('/')-1
    levels={n:sorted([d for d in dirs if depth(d)==n],key=lambda d:(recursive[d],children[d],d.encode('utf-8'))) for n in (0,1,2,4,9,16,24,31)}
    assert all(levels.values()) and len(dirs)==23025 and '/__wiki_bench__/' not in dirs
    anchors=set()
    for group in levels.values():
        n=min(4,len(group));anchors.update(group[0 if n==1 else j*(len(group)-1)//(n-1)] for j in range(n))
    terminals=sorted(local,key=lambda x:x.encode('utf-8'))
    anchors.update([min(dirs,key=lambda d:(-children[d],d.encode('utf-8'))),terminals[0],terminals[-1]])
    dq=[dict(case=f'd{i}-r{int(r)}',path=d,recursive=r,depth=depth(d),candidates=recursive[d] if r else local[d],children=children[d],descendant_directories=sum(x.startswith(d) for x in dirs)) for i,d in enumerate(sorted(anchors,key=lambda d:d.encode('utf-8'))) for r in (False,True)]
    source0=min(levels[2],key=lambda d:(-recursive[d],d.encode('utf-8')))
    target=max([d for d in levels[1] if not d.startswith(source0) and not source0.startswith(d)],key=lambda d:d.encode('utf-8'))
    source1=min([d for d in local if not d.startswith(source0) and not source0.startswith(d) and not target.startswith(d)],key=lambda d:(-depth(d),d.encode('utf-8')))
    holder='/__wiki_bench__/'
    moved=lambda d:holder+d.rstrip('/').rsplit('/',1)[1]+'/'
    ops=[dict(case='move-large',kind='move',source=source0,target=holder),dict(case='merge-large',kind='merge',source=moved(source0),target=target),dict(case='move-deep',kind='move',source=source1,target=holder),dict(case='merge-deep',kind='merge',source=moved(source1),target=target)]
    cases=[]
    for q in range(456):
        group=levels[(0,1,2,4,9,16,24,31)[q%8]]
        h=hashlib.sha256(f'WIKI-SCOPE-v1|{q}'.encode()).digest()
        path=group[int.from_bytes(h[:8],'little')%len(group)]
        for r in (False,True):cases.append(dict(case=f'q{q}-r{int(r)}',query_id=q,query_row=q,path=path,recursive=r,k=10))
    assert len(cases)==912
    save(out/'sample.json',[dict(row=i,**x) for i,x in enumerate(rows)])
    (out/'bindings.tsv').write_text(''.join(f"{i}\t{x['global_id']}\t{x['path']}\n" for i,x in enumerate(rows)),encoding='utf-8')
    save(out/'directory-cases.json',dq);save(out/'operations.json',ops);save(out/'cases.json',cases)
    (out/'directory-cases.tsv').write_text(''.join(f"{x['case']}\t{x['path']}\t{int(x['recursive'])}\n" for x in dq),encoding='utf-8')
    (out/'operations.tsv').write_text(''.join(f"{x['case']}\t{x['kind']}\t{x['source']}\t{x['target']}\n" for x in ops),encoding='utf-8')
    (out/'cases.tsv').write_text(''.join(f"{x['case']}\t{x['query_row']}\t{x['path']}\t{int(x['recursive'])}\t10\n" for x in cases),encoding='utf-8')
    raw=P/'dataset/raw/WIKI-Dir';inputs={}
    for name,ids,dest in [('dbpedia_dir_2m_corpus_vectors-001.fvecs',[x['global_id'] for x in rows],'corpus.fvecs'),('dbpedia_dir_2m_query_vectors.fvecs',list(range(456)),'queries.fvecs')]:
        source=raw/name;before=source.stat();h=hashlib.sha256()
        with source.open('rb') as f,(out/dest).open('xb') as g:
            for row in ids:
                f.seek(4100*row);b=f.read(4100)
                assert len(b)==4100 and struct.unpack_from('<i',b)[0]==1024
                assert np.isfinite(np.frombuffer(b,dtype='<f4',offset=4)).all()
                h.update(b);g.write(b)
        assert (before.st_size,before.st_mtime_ns)==(source.stat().st_size,source.stat().st_mtime_ns)
        inputs[name]=dict(size=before.st_size,mtime_ns=before.st_mtime_ns,rows=ids,records_sha256=h.hexdigest())
    manifest=dict(status='prepared',protocol_sha256=sha(PROTOCOL),records=10000,search_cases=912,directory_cases=len(dq),
                  operations=4,initial_directories_with_holder=23026,inputs=inputs,
                  sample_source_sha256=sha(P/'notes/wiki-preparation-20261027-01/run-01/sample.json'),
                  qrels_used=False,ndcg_reported=False,files={x.name:sha(x) for x in out.iterdir() if x.is_file()})
    save(out/'manifest.json',manifest)
    print(json.dumps({k:manifest[k] for k in ('status','records','search_cases','directory_cases','operations')}))

if __name__=='__main__':main()
