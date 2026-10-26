"""Prepare a fixed metadata-only ARXIV time-namespace pilot. No vector read.
The first 10,000 corpus rows are chosen independently of query relevance/GT.
"""
import collections
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from audit_data_01 import json_prefix

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'dataset/raw/ARXIV-Dir/arxiv_corpus_metadata.json'
OUT=ROOT/'notes/time-pilot-20261026-01'


def main():
    if OUT.exists():
        raise FileExistsError('Refusing to overwrite a frozen pilot')
    OUT.mkdir(parents=True)
    before=RAW.stat()
    source=Path(__file__).read_bytes()
    parser=Path(__file__).with_name('audit_data_01.py').read_bytes()
    rows=list(json_prefix(RAW,10000))
    assert len(rows)==10000
    bindings=[]
    local=collections.Counter()
    inclusive=collections.Counter()
    for row,item in enumerate(rows):
        assert item['id']==row and isinstance(item['time'],str)
        raw_path=item['time']
        pieces=raw_path.strip('/').split('/')
        assert len(pieces)==2 and len(pieces[0])==4 and pieces[0].isdigit()
        assert pieces[1].isdigit() and 1<=int(pieces[1])<=12
        assert '//' not in raw_path
        canonical='/'+'/'.join(pieces)+'/'
        bindings.append({'row':row,'entry_id':item['id'],'namespace':'time','raw_time':raw_path,'directory':canonical})
        local[canonical]+=1
        inclusive['/']+=1
        inclusive['/'+pieces[0]+'/']+=1
        inclusive[canonical]+=1
    assert len({b['entry_id'] for b in bindings})==10000
    assert sum(local.values())==inclusive['/']==10000
    with (OUT/'source-metadata.jsonl').open('w',encoding='utf-8') as handle:
        for item in rows:
            handle.write(json.dumps(item,ensure_ascii=False)+'\n')
    with (OUT/'bindings.jsonl').open('w',encoding='utf-8') as handle:
        for item in bindings:
            handle.write(json.dumps(item,ensure_ascii=False)+'\n')
    directories=[{'directory':p,'direct_entries':local[p],'recursive_entries':inclusive[p]}
                 for p in sorted(inclusive)]
    (OUT/'directory-counts.json').write_text(json.dumps(directories,ensure_ascii=False,indent=2),encoding='utf-8')
    after=RAW.stat()
    counts={'selected_entries':10000,'unique_ids':10000,'year_directories':sum(p.count('/')==2 for p in inclusive),
            'month_directories':len(local),'directories_including_root':len(inclusive)}
    result={'date_utc':datetime.now(timezone.utc).isoformat(),'purpose':'Project diagnostic input only; not author workload',
            'selection':'First 10000 metadata rows, IDs 0..9999; independent of all query/GT results',
            'namespace':'time only; categories preserved in source snapshot but not assigned in this view',
            'counts':counts,'mapping':'Add leading/trailing slash only; preserve month spelling and original raw_time',
            'input_metadata':str(RAW.relative_to(ROOT)),
            'input_size':before.st_size,'input_size_and_mtime_unchanged':(before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),
            'corpus_vectors_read':False,'queries_or_gt_read':False,'index_or_benchmark_run':False,
            'script_sha256':hashlib.sha256(source).hexdigest(),'parser_sha256':hashlib.sha256(parser).hexdigest(),
            'outputs':{name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in ('source-metadata.jsonl','bindings.jsonl','directory-counts.json')},
            'full_corpus_integrity_checked':False}
    (OUT/'prepare_time_pilot.py').write_bytes(source)
    (OUT/'audit_data_01.py').write_bytes(parser)
    (OUT/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
