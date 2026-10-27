"""Independent pretty-JSON object framing + per-row binding comparison; no vector read."""
import argparse,collections,datetime,hashlib,json,tempfile,time
from pathlib import Path

def object_fields(pairs):
    result=dict(pairs)
    if len(result)!=len(pairs):raise ValueError('Repeated metadata key')
    return result
def bad_number(value):raise ValueError('Invalid JSON number '+value)
def framed_records(path,proof):
    # Independent of audit.py's JSONDecoder buffer parser. Check actual pretty-file layout.
    state='start';pieces=[];size=0;h=hashlib.sha256();total=0
    with path.open('rb') as f:
        for line in f:
            h.update(line);total+=len(line);stripped=line.strip()
            if not stripped:continue
            if state=='start':
                if line.decode('utf-8-sig').strip()!='[':raise ValueError('Missing array opener')
                state='first';continue
            if state=='done':raise ValueError('Trailing JSON content')
            if state in ('first','next','close'):
                if stripped==b']':
                    if state=='next':raise ValueError('Trailing comma')
                    state='done';continue
                if state=='close':raise ValueError('Missing outer separator/end')
                if stripped!=b'{' or len(line)-len(line.lstrip(b' '))!=4:raise ValueError('Unexpected top-level object framing')
                pieces=[line];size=len(line);state='object';continue
            pieces.append(line);size+=len(line)
            if size>8*(1<<20):raise ValueError('Object framing exceeds 8MiB cap')
            if len(line)-len(line.lstrip(b' '))==4 and stripped in (b'}',b'},'):
                payload=b''.join(pieces).rstrip()
                if payload.endswith(b','):payload=payload[:-1]
                value=json.loads(payload,object_pairs_hook=object_fields,parse_constant=bad_number)
                if type(value) is not dict:raise ValueError('Expected record dict')
                state='next' if stripped.endswith(b',') else 'close';pieces=[];size=0
                yield value
    if state!='done':raise ValueError('Missing closed array/EOF')
    proof.update(sha256=h.hexdigest(),bytes_read=total,closed_array_and_eof=True)
def canonical_independent(value):
    if type(value) is not str or '//' in value:raise ValueError('Time type/slashes')
    fields=value.strip('/').split('/')
    if len(fields)!=2 or len(fields[0])!=4 or not all('0'<=c<='9' for part in fields for c in part) or not fields[1]:raise ValueError('Time spelling')
    if int(fields[1])<1 or int(fields[1])>12:raise ValueError('Month range')
    return '/'+fields[0]+'/'+fields[1]+'/'
def stat(p):
    s=p.stat();return {'size':s.st_size,'mtime_ns':s.st_mtime_ns}
def filehash(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()
def self_test():
    with tempfile.TemporaryDirectory(prefix='independent-framer-') as temp:
        p=Path(temp)/'array.json';records=[{'id':0,'time':'1991/07/','categories':['中"}文']},{'id':1,'time':'/1992/1/'}]
        p.write_text(json.dumps(records,indent=4,ensure_ascii=False),encoding='utf-8');proof={}
        assert list(framed_records(p,proof))==records and proof['bytes_read']==p.stat().st_size
        p.write_bytes(p.read_bytes()+b'x');failed=False
        try:list(framed_records(p,{}))
        except ValueError:failed=True
        assert failed
    print(json.dumps({'independent_framer_contract':'passed','synthetic_only':True}))
def verify(project,out):
    start=time.monotonic();manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    if (out/'verification.json').exists():raise FileExistsError('Do not overwrite prior independent verification')
    path=project/manifest['input_metadata'];before=stat(path);assert before==manifest['input_stat_before']
    proof={};binding_hash=hashlib.sha256();local=collections.Counter();parent=collections.Counter();rows=0
    with (out/'bindings.tsv').open('rb',buffering=1<<20) as bindings:
        for row,obj in enumerate(framed_records(path,proof)):
            assert type(obj.get('id')) is int and obj['id']==row,('ID/row/uniqueness',row)
            path_value=canonical_independent(obj.get('time'));expected=f'{row}\t{path_value}\n'.encode('utf-8')
            actual=bindings.readline();assert actual==expected,('Binding mismatch',row)
            binding_hash.update(actual);local[path_value]+=1;parent['/'+path_value.split('/')[1]+'/']+=1;rows+=1
            if rows%500000==0:print(json.dumps({'verified_records':rows,'elapsed_seconds':round(time.monotonic()-start,2)}),flush=True)
        assert bindings.readline()==b'', 'Extra bindings'
    assert manifest['status']=='passed'
    assert proof['sha256']==manifest['metadata_read_proof']['sha256'] and proof['bytes_read']==before['size']
    assert binding_hash.hexdigest()==manifest['outputs']['bindings.tsv']
    assert rows==manifest['counts']['records']==manifest['counts']['unique_ids']==manifest['vector_structure']['rows_implied_by_length']
    dirs=json.loads((out/'directory-counts.json').read_text())
    expected_dirs={'/':(0,rows),**{p:(0,n) for p,n in parent.items()},**{p:(n,n) for p,n in local.items()}}
    assert {r['path']:(r['direct'],r['recursive']) for r in dirs}==expected_dirs
    assert sum(local.values())==sum(parent.values())==rows
    with (out/'bindings.tsv').open('rb') as f:prefix=b''.join(f.readline() for _ in range(10000))
    assert prefix==(project/'notes/benchmark-fixtures-20261026-01/time-bindings.tsv').read_bytes()
    for name,digest in manifest['outputs'].items():assert filehash(out/name)==digest
    assert stat(path)==before
    assert stat(project/manifest['vector_structure']['file'])==manifest['vector_structure']['stat']
    assert filehash(project/manifest['time_query_coverage']['file'])==manifest['time_query_coverage']['sha256']
    result={'status':'passed','method':'independent line-framed JSON loads; full per-row ID/time binding comparison; independently recomputed directory totals',
        'records_verified':rows,'metadata_sha256':proof['sha256'],'bindings_sha256':binding_hash.hexdigest(),'year_directories':len(parent),'month_directories':len(local),'directories_including_root':len(expected_dirs),
        'id_equals_row_for_all_records':True,'unique_contiguous_ids_proved_by_per_row_equality':True,'all_binding_rows_verified':True,'first_10000_matches_frozen_pilot':True,
        'metadata_stat_before_after_equal':True,'metadata_full_hash_matches_primary_pass':True,'vector_bytes_read':0,'vector_all_record_dimensions_or_finiteness_verified':False,'index_or_performance_run':False,
        'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-start,'script_sha256':filehash(Path(__file__))}
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path);p.add_argument('--output',type=Path);p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test();return
    if a.project is None or a.output is None:p.error('--project and --output required')
    verify(a.project.resolve(),a.output.resolve())
if __name__=='__main__':main()
