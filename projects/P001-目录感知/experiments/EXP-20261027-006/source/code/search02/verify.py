"""Independent scoped exhaustive L2 oracle and measurement accounting verifier."""
import argparse
import csv
import hashlib
import json
import math
import pathlib
from array import array
from collections import defaultdict

import numpy as np


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def write(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def matrix(p):
    a = np.fromfile(p, dtype=np.dtype([('d', '<i4'), ('v', '<f4', (1024,))]))
    assert p.stat().st_size == len(a)*4100 and (a['d'] == 1024).all() and np.isfinite(a['v']).all()
    return a['v'].astype(np.float64)


def stats(values):
    a = np.asarray(values, dtype=np.int64)
    assert len(a)
    ordered = np.sort(a)
    return dict(count=len(a), mean_ns=float(np.mean(a)), **{f'p{q}_ns': int(ordered[math.ceil(float(q)/100*len(a))-1]) for q in ('90','95','99','99.9')})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixture', type=pathlib.Path, required=True)
    ap.add_argument('--outputs', type=pathlib.Path, nargs='+', required=True)
    ap.add_argument('--report', type=pathlib.Path, required=True)
    ap.add_argument('--formal', action='store_true')
    args = ap.parse_args()
    assert not args.report.exists(), 'report already exists'
    project = pathlib.Path.cwd()
    manifest = load(args.fixture / 'manifest.json')
    assert manifest['protocol_sha256'] == sha(project / 'notes/search02-protocol-20261027.md')
    for name, h in manifest['files'].items():
        assert sha(args.fixture/name) == h, name
    selected = [i*(2763543-1)//9999 for i in range(10000)]
    sample = load(args.fixture / 'sample.json')
    assert [b['global_id'] for b in sample] == selected and [b['row'] for b in sample] == list(range(10000))
    # Source matching is independent of the adapter, including sparse vector record bytes.
    source = project / 'notes/arxiv-time-full-audit-20261027-01/run-01/bindings.tsv'
    assert sha(source) == manifest['full_bindings_sha256']
    selected_set = set(selected)
    independently_read = []
    with source.open(encoding='utf-8') as f:
        for row, line in enumerate(f):
            if row in selected_set:
                idstr, path = line.rstrip('\n').split('\t')
                assert int(idstr) == row
                independently_read.append(path)
    assert independently_read == [b['path'] for b in sample]
    raw = project / 'dataset/raw/ARXIV-Dir'
    constraints = load(raw / 'arxiv_query_constraint.json')
    assert sha(raw/'arxiv_query_constraint.json') == manifest['constraints_sha256']
    queries = [r for r in constraints if 'time' in r['constraints']]
    assert [r['query_id'] for r in queries] == manifest['query_ids']
    expected_cases = [dict(case=f"q{q['query_id']}-r{int(recursive)}",query_id=q['query_id'],query_row=i,path='/' + q['constraints']['time'].strip('/') + '/',recursive=recursive,k=100) for i,q in enumerate(queries) for recursive in (False,True)]
    cases = load(args.fixture/'cases.json')
    assert cases == expected_cases and len(cases) == 1002
    assert (args.fixture/'cases.tsv').read_text(encoding='utf-8') == ''.join(f"{c['case']}\t{c['query_row']}\t{c['path']}\t{int(c['recursive'])}\t{c['k']}\n" for c in cases)
    assert (args.fixture/'bindings.tsv').read_text(encoding='utf-8') == ''.join(f"{b['row']}\t{b['global_id']}\t{b['path']}\n" for b in sample)
    for name, rows, dest in [('arxiv_corpus_vectors.fvecs',selected,'corpus.fvecs'),('arxiv_query_vectors.fvecs',list(range(1000)),'queries.fvecs')]:
        source_file = raw/name
        info = manifest['inputs'][name]
        assert (source_file.stat().st_size,source_file.stat().st_mtime_ns) == (info['size'],info['mtime_ns'])
        h = hashlib.sha256()
        with source_file.open('rb') as original,(args.fixture/dest).open('rb') as derived:
            for row in rows:
                original.seek(4100*row); block=original.read(4100); assert len(block)==4100
                h.update(block)
                if name.startswith('arxiv_corpus') or row in manifest['query_ids']:
                    assert derived.read(4100)==block
            assert derived.read(1)==b''
        assert h.hexdigest()==info['selected_read_regions_sha256']
    x,q = matrix(args.fixture/'corpus.fvecs'),matrix(args.fixture/'queries.fvecs')
    global_ids=np.array(selected,dtype=np.int64)
    model_hash = sha(args.outputs[0]/'model.json')
    model=load(args.outputs[0]/'model.json')
    assert model['clusters']==16 and model['dimension']==1024
    centers=np.asarray(model['centers']).reshape(16,1024)
    assign=np.asarray(model['assignment'])
    assert centers.shape==(16,1024) and np.isfinite(centers).all() and assign.shape==(10000,)
    coarse=np.stack([np.sum(np.square(x-center),axis=1) for center in centers],axis=1)
    assert np.array_equal(np.argmin(coarse,axis=1),assign)
    by_case={c['case']:c for c in cases}; case_index={c['case']:i for i,c in enumerate(cases)}
    paths=[b['path'].strip('/').split('/') for b in sample]
    directories={()}
    for parts in paths:
        directories.update(tuple(parts[:j]) for j in range(1,len(parts)+1))
    expected_scopes,truth,expected={}, {}, {}
    quality=defaultdict(list)
    for c in cases:
        parts=c['path'].strip('/').split('/')
        ids=np.array([i for i,p in enumerate(paths) if (p[:len(parts)]==parts if c['recursive'] else p==parts)],dtype=np.int64)
        expected_scopes[c['case']]=(tuple(parts) in directories,global_ids[ids].tolist())
        distances=np.sum(np.square(x[ids]-q[c['query_row']]),axis=1)
        order=np.lexsort((global_ids[ids],distances))
        gt=global_ids[ids[order[:100]]].tolist();truth[c['case']]=gt
        qr=np.sum(np.square(centers-q[c['query_row']]),axis=1)
        coarse_order=np.lexsort((np.arange(16),qr))
        for probes in (0,1,4,16):
            keep=np.ones(len(ids),dtype=bool) if probes==0 else np.isin(assign[ids],coarse_order[:probes])
            retained=ids[keep];values=distances[keep]
            rank=np.lexsort((global_ids[retained],values))[:100]
            result=global_ids[retained[rank]].tolist()
            expected[(c['case'],probes)]=(result,values[rank])
            recall=len(set(result)&set(gt))/len(gt) if gt else None
            if probes in (0,16):assert result==gt and recall in (1.,None)
            quality[(c['recursive'],probes)].append(recall)
    strategies=('PE-ONLINE','PE-OFFLINE','TrieHI'); pi={p:i for i,p in enumerate((0,1,4,16))}
    pools=defaultdict(lambda:[array('q') for _ in range(4)])
    reports=[];canonical=None
    for output in args.outputs:
        assert sha(output/'model.json')==model_hash
        seen_scopes=set()
        with (output/'scopes.tsv').open(encoding='utf-8') as f:
            for line in f:
                strategy,caseid,exists,text=line.rstrip('\n').split('\t')
                key=(strategy,caseid);assert strategy in strategies and key not in seen_scopes;seen_scopes.add(key)
                assert (bool(int(exists)),[int(v) for v in text.split(',')] if text else [])==expected_scopes[caseid]
        assert len(seen_scopes)==3006
        seen_answers=set();answers={}
        with (output/'answers.jsonl').open(encoding='utf-8') as f:
            for line in f:
                r=json.loads(line);key=(r['strategy'],r['case'],r['probes'])
                assert r['strategy'] in strategies and r['probes'] in pi and key not in seen_answers
                seen_answers.add(key);ids,dist=expected[(r['case'],r['probes'])]
                assert r['ids']==ids and np.allclose(r['distances'],dist,rtol=1e-11,atol=1e-11),key
                answers[key]=(r['ids'],r['distances'])
        assert len(seen_answers)==12024
        if canonical is None:canonical=answers
        else:assert canonical==answers,'cross-build/run ranking mismatch'
        clocks=np.loadtxt(output/'clock.csv',delimiter=',',skiprows=1,dtype=np.int64)
        assert clocks.shape==(10000,) and np.min(clocks)>=0
        order=[tuple(line.split()) for line in (output/'order.tsv').read_text().splitlines()]
        assert len(order)==4008 and {(x,int(p)) for x,p in order}==set(expected)
        repeats=20 if args.formal else 1
        seen=np.zeros((3,1002,4,repeats),dtype=bool);run=None;rows=0
        per_run=defaultdict(lambda:[array('q') for _ in range(4)])
        with (output/'timings.csv').open(newline='',encoding='utf-8') as f:
            for r in csv.DictReader(f):
                strategy=r['strategy'];c=by_case[r['case']];probes=int(r['probes']);repeat=int(r['repeat'])
                assert 0<=repeat<repeats
                index=(strategies.index(strategy),case_index[c['case']],pi[probes],repeat)
                assert not seen[index];seen[index]=True
                run_value=int(r['run']);run=run_value if run is None else run;assert run==run_value
                values=[int(r[k]) for k in ('directory_ns','materialize_ns','ranking_ns','total_ns')]
                assert min(values)>=0 and sum(values[:3])==values[3]
                key=(strategy,c['recursive'],probes,not bool(truth[c['case']]))
                for component,value in enumerate(values):
                    pools[key][component].append(value);per_run[key][component].append(value)
                rows+=1
        assert seen.all() and rows==3*1002*4*repeats
        reports.append(dict(output=str(output),run=run,rows=rows,clock=stats(clocks),groups=[dict(strategy=k[0],recursive=k[1],probes=k[2],empty=k[3],total=stats(v[3])) for k,v in sorted(per_run.items())],files={p.name:sha(p) for p in output.iterdir() if p.is_file()}))
    if args.formal:assert len(args.outputs)==5 and sorted(r['run'] for r in reports)==list(range(5))
    groups=[]
    for (strategy,recursive,probes,empty),v in sorted(pools.items()):
        groups.append(dict(strategy=strategy,recursive=recursive,probes=probes,empty=empty,**{name:stats(values) for name,values in zip(('directory','materialize','ranking','total'),v)}))
    report=dict(status='passed',formal=args.formal,cases=1002,unique_query_vectors=501,model_sha256=model_hash,source_regions_reverified=True,published_gt_used=False,groups=groups,quality=[dict(recursive=k[0],probes=k[1],requests=len(v),nonempty=sum(x is not None for x in v),empty=sum(x is None for x in v),mean_recall_nonempty=float(np.mean([x for x in v if x is not None])) if any(x is not None for x in v) else None) for k,v in sorted(quality.items())],workers=reports,raw_timing_rows=sum(r['rows'] for r in reports))
    write(args.report,report)
    write(args.report.with_name(args.report.stem+'-truth.json'),truth)
    print(json.dumps(dict(status='passed',formal=args.formal,rows=report['raw_timing_rows'],quality=report['quality'])))


if __name__=='__main__':
    main()
