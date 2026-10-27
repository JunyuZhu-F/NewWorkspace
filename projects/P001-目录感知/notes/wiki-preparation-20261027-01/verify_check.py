"""Independent Python path-state oracle for all emitted WIKI scope summaries."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent

def fnv(ids):
    value=14695981039346656037
    for x in sorted(ids):
        for b in x.to_bytes(4,'little'):value=((value^b)*1099511628211)&((1<<64)-1)
    return value

def main():
    out=HERE/'check-02'
    if (out/'independent-verification.json').exists():raise FileExistsError('Preserve earlier verification')
    status=json.loads((out/'status.json').read_text())
    assert status['status']=='passed'
    records=json.loads((HERE/'run-01/sample.json').read_text(encoding='utf-8'))
    entries={x['global_id']:x['path'] for x in records}
    dirs={'/','/__wiki_check__/','/__wiki_empty__/'}
    for path in entries.values():
        while path!='/':
            dirs.add(path);path=path[:path.rfind('/',0,len(path)-1)+1]
    terminals=sorted(set(entries.values()))
    source=terminals[0]
    target=next(p for p in reversed(terminals) if not p.startswith(source) and not source.startswith(p))
    moved='/__wiki_check__/'+source.rstrip('/').rsplit('/',1)[1]+'/'
    lines=(out/'release-answers.tsv').read_text(encoding='utf-8').splitlines()
    assert (out/'release-answers.tsv').read_bytes()==(out/'asan-answers.tsv').read_bytes()
    parsed=[x.split('\t') for x in lines]
    counts={}
    for stage in ('initial','move','merge','reject'):
        if stage=='move':
            entries={i:(moved+p[len(source):] if p.startswith(source) else p) for i,p in entries.items()}
            dirs={moved+p[len(source):] if p.startswith(source) else p for p in dirs}
        elif stage=='merge':
            entries={i:(target+p[len(moved):] if p.startswith(moved) else p) for i,p in entries.items()}
            dirs={target+p[len(moved):] if p.startswith(moved) else p for p in dirs}
        levels={}
        for p in sorted(dirs):levels.setdefault(p.count('/')-1,[]).append(p)
        queries={'/','/__wiki_check__/','/__wiki_empty__/','/__wiki_missing__/',source,target,moved}
        for group in levels.values():
            n=min(8,len(group))
            queries.update(group[0 if n==1 else j*(len(group)-1)//(n-1)] for j in range(n))
        expected={}
        for p in queries:
            for recursive in (False,True):
                found=[i for i,path in entries.items() if (path.startswith(p) if recursive else path==p)] if p in dirs else []
                expected[(p,str(int(recursive)))]=(str(int(p in dirs)),str(len(found)),str(fnv(found)))
        seen=set()
        for row in parsed:
            if row[0]!=stage:continue
            _,strategy,p,recursive,exists,n,digest=row
            assert strategy in ('PE-ONLINE','PE-OFFLINE','TrieHI')
            key=(strategy,p,recursive)
            assert key not in seen and tuple(row[4:])==expected[(p,recursive)],row
            seen.add(key)
        assert len(seen)==3*len(expected)
        counts[stage]=dict(directories=len(dirs),queries=len(queries),scope_checks=len(seen))
    assert len(parsed)==sum(x['scope_checks'] for x in counts.values())==status['query_scope_rows']
    result=dict(status='passed',stages=counts,scope_checks_per_build=len(parsed),
                release_asan_equal=True,independent_python_path_state_oracle=True,
                comparison='C++ oracle compares complete ID sets; Python independently checks all emitted counts/FNV ID digests and full case coverage',
                answers_sha256=hashlib.sha256((out/'release-answers.tsv').read_bytes()).hexdigest(),
                verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'independent-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
