"""Full metadata-only audit. Raw corpus is opened rb; vector read is 4-byte header only."""
import argparse,codecs,collections,datetime,hashlib,json,re,struct,time
from pathlib import Path

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def reject_constant(value):raise ValueError('Non-JSON numeric constant: '+value)
def unique_object(pairs):
    out={}
    for key,value in pairs:
        if key in out:raise ValueError('Duplicate object key: '+key)
        out[key]=value
    return out
def strict_records(path,proof,chunk_size=1<<20):
    """Bounded full-array parser: require commas, closing ], EOF, no duplicate keys."""
    decoder=json.JSONDecoder(object_pairs_hook=unique_object,parse_constant=reject_constant)
    text_decoder=codecs.getincrementaldecoder('utf-8-sig')()
    digest=hashlib.sha256();buf='';pos=0;eof=False;read_bytes=0;state='open';maximum=0
    with path.open('rb') as f:
        def refill():
            nonlocal buf,pos,eof,read_bytes,maximum
            data=f.read(chunk_size);digest.update(data);read_bytes+=len(data)
            buf=buf[pos:]+text_decoder.decode(data,final=not data);pos=0;eof=not data
            maximum=max(maximum,len(buf))
            if len(buf)>8*(1<<20):raise ValueError('Single JSON item exceeds bounded 8MiB buffer')
        while True:
            while pos<len(buf) and buf[pos].isspace():pos+=1
            if pos==len(buf):
                if eof:
                    if state!='end':raise ValueError('Unexpected EOF without closed JSON array')
                    break
                refill();continue
            c=buf[pos]
            if state=='open':
                if c!='[':raise ValueError('Expected top-level array')
                pos+=1;state='first';continue
            if state=='end':raise ValueError('Trailing non-whitespace after JSON array')
            if state in ('first','value'):
                if c==']':
                    if state=='value':raise ValueError('Trailing comma')
                    pos+=1;state='end';continue
                try:item,end=decoder.raw_decode(buf,pos)
                except json.JSONDecodeError:
                    if eof:raise
                    refill();continue
                if not isinstance(item,dict):raise ValueError('Metadata record is not an object')
                pos=end;state='separator';yield item;continue
            if c==',':pos+=1;state='value';continue
            if c==']':pos+=1;state='end';continue
            raise ValueError('Expected comma or ] after metadata object')
    proof.update(sha256=digest.hexdigest(),bytes_read=read_bytes,max_text_buffer_chars=maximum,closed_array_and_eof=True)
def canonical_time(raw):
    if not isinstance(raw,str):raise ValueError('time is not string')
    match=re.fullmatch(r'/?([0-9]{4})/([0-9]+)/?',raw)
    if not match or not 1<=int(match[2])<=12:raise ValueError('Invalid year/month time path')
    return '/'+match[1]+'/'+match[2]+'/'
def stat(path):
    s=path.stat();return {'size':s.st_size,'mtime_ns':s.st_mtime_ns}
def sha_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()
def self_test():
    import tempfile
    with tempfile.TemporaryDirectory(prefix='metadata-parser-synthetic-') as tmp:
        p=Path(tmp)/'input.json'
        for value in [[],[{'id':0,'time':'1991/7/','text':'中"\\文'}]]:
            p.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8');proof={}
            assert list(strict_records(p,proof,7))==value and proof['closed_array_and_eof']
        for bad in ['','[','[{}','[{},]','[{} {}]','[]x','[{"id":0,"id":1}]','[NaN]','[1]']:
            p.write_text(bad);failed=False
            try:list(strict_records(p,{},7))
            except ValueError:failed=True
            assert failed,bad
    assert canonical_time('1991/07/')=='/1991/07/'
    for bad in ['1991/0/','1991/13/','1991//1/','1991/1/x','1991/1/\n']:
        failed=False
        try:canonical_time(bad)
        except ValueError:failed=True
        assert failed,bad
    print(json.dumps({'parser_contract':'passed','synthetic_only':True}))
def audit(project,out):
    if out.exists():raise FileExistsError('Preserve prior audit; use a new run directory')
    out.mkdir(parents=True);started=time.monotonic();status={'status':'running','started_at':utc()}
    (out/'run-status.json').write_text(json.dumps(status,indent=2)+'\n')
    try:
        raw=project/'dataset/raw/ARXIV-Dir';metadata=raw/'arxiv_corpus_metadata.json';vectors=raw/'arxiv_corpus_vectors.fvecs'
        before=stat(metadata);vector_before=stat(vectors)
        with vectors.open('rb') as f:header=f.read(4)
        if len(header)!=4:raise ValueError('Missing vector dimension header')
        dimension=struct.unpack('<i',header)[0]
        if not 1<=dimension<=65536:raise ValueError('Invalid first vector dimension')
        stride=4*(dimension+1);vector_rows,remainder=divmod(vector_before['size'],stride)
        pilot_dir=project/'notes/time-pilot-20261026-01'
        pilot=[json.loads(line) for line in (pilot_dir/'source-metadata.jsonl').read_text(encoding='utf-8').splitlines()]
        old_binding_prefix=(project/'notes/benchmark-fixtures-20261026-01/time-bindings.tsv').read_bytes()
        counts=collections.Counter();months=collections.Counter();years=collections.Counter();schemas=collections.Counter();formats=collections.Counter();issues=[]
        seen={};min_id=None;max_id=None;proof={};binding_hash=hashlib.sha256();prefix_hash=hashlib.sha256();prefix_size=0
        def issue(kind,row,value):
            counts[kind]+=1
            if len(issues)<100:issues.append({'kind':kind,'row':row,'value':repr(value)[:200]})
        with (out/'bindings.tsv').open('wb',buffering=1<<20) as bindings:
            for row,item in enumerate(strict_records(metadata,proof)):
                counts['records']+=1;schemas[','.join(sorted(item))]+=1
                ident=item.get('id');valid_id=type(ident) is int and 0<=ident<=0xffffffff
                if not valid_id:issue('invalid_id',row,ident)
                else:
                    min_id=ident if min_id is None else min(min_id,ident);max_id=ident if max_id is None else max(max_id,ident)
                    if ident!=row:issue('id_row_mismatch',row,ident)
                    if ident>=vector_rows:issue('id_outside_vector_size_range',row,ident)
                    key=ident>>16;chunk=seen.get(key)
                    if chunk is None:
                        if len(seen)>=16384:raise MemoryError('Sparse uint32 ID coverage exceeds 128MiB audit bound')
                        chunk=seen[key]=bytearray(8192)
                    offset=(ident&65535)>>3;mask=1<<(ident&7)
                    if chunk[offset]&mask:issue('duplicate_id',row,ident)
                    else:
                        chunk[offset]|=mask;counts['unique_ids']+=1
                        if ident<vector_rows:counts['unique_ids_in_vector_size_range']+=1
                raw_time=item.get('time');path=None
                try:path=canonical_time(raw_time)
                except ValueError:issue('invalid_time',row,raw_time)
                if row<len(pilot):
                    counts['pilot_rows_compared']+=1
                    if item!=pilot[row]:issue('pilot_full_object_mismatch',row,ident)
                if valid_id and path is not None:
                    counts['bindings_written']+=1;months[path]+=1;years['/'+path.split('/')[1]+'/']+=1
                    formats['leading_slash='+str(raw_time.startswith('/'))+',trailing_slash='+str(raw_time.endswith('/'))]+=1
                    month=path.split('/')[2];formats['month_spelling_digits='+str(len(month))]+=1
                    encoded=f'{ident}\t{path}\n'.encode('utf-8');bindings.write(encoded);binding_hash.update(encoded)
                    if row<10000:prefix_hash.update(encoded);prefix_size+=len(encoded)
                if counts['records']%250000==0:
                    print(json.dumps({'progress_records':counts['records'],'elapsed_seconds':round(time.monotonic()-started,2)}),flush=True)
                    if time.monotonic()-started>900:raise TimeoutError('Metadata audit exceeded 15-minute guard')
        after=stat(metadata)
        if before!=after:raise ValueError('Raw metadata stat changed during read')
        prefix_matches=(prefix_size==len(old_binding_prefix) and prefix_hash.hexdigest()==hashlib.sha256(old_binding_prefix).hexdigest())
        dirs=[{'path':'/','direct':0,'recursive':counts['bindings_written']}]
        dirs += [{'path':p,'direct':0,'recursive':n} for p,n in sorted(years.items())]
        dirs += [{'path':p,'direct':n,'recursive':n} for p,n in sorted(months.items())]
        (out/'directory-counts.json').write_text(json.dumps(dirs,indent=2)+'\n',encoding='utf-8')
        (out/'anomalies.json').write_text(json.dumps({'counts':{k:v for k,v in counts.items() if k in ['invalid_id','id_row_mismatch','id_outside_vector_size_range','duplicate_id','invalid_time','pilot_full_object_mismatch']},'examples_first_100':issues},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        issue_keys=['invalid_id','id_row_mismatch','id_outside_vector_size_range','duplicate_id','invalid_time','pilot_full_object_mismatch']
        ready=(all(counts[k]==0 for k in issue_keys) and counts['records']==counts['unique_ids']==counts['bindings_written']==vector_rows and not remainder and prefix_matches and counts['pilot_rows_compared']==10000)
        # Query ranges are checked, never used to select metadata or synthesize relevance truth.
        query_path=raw/'arxiv_query_constraint.json';query_before=stat(query_path);queries=json.loads(query_path.read_text(encoding='utf-8'))
        recursive={r['path']:r['recursive'] for r in dirs};direct={r['path']:r['direct'] for r in dirs};query_rows=[]
        for q in queries:
            constraint=q.get('constraints',{})
            if 'time' not in constraint:continue
            value=constraint['time'];canonical='/'+value.strip('/')+'/' if isinstance(value,str) and value.strip('/') else '/'
            query_rows.append({'query_id':q.get('query_id'),'raw_constraint':value,'path':canonical,'exists':canonical in recursive,'recursive_members':recursive.get(canonical,0),'direct_members':direct.get(canonical,0),'mode_not_inferred':True})
        (out/'time-query-coverage.json').write_text(json.dumps(query_rows,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        if query_before!=stat(query_path) or vector_before!=stat(vectors):raise ValueError('Raw query/vector stat changed during audit')
        result={'status':'passed' if ready else 'anomalies_found','scope':'full ARXIV metadata time view only; not author workload or full vector validation',
            'input_metadata':str(metadata.relative_to(project)).replace('\\','/'),'input_stat_before':before,'input_stat_after':after,'metadata_read_proof':proof,
            'counts':dict(counts),'id_min':min_id,'id_max':max_id,'missing_ids_in_vector_size_range':vector_rows-counts['unique_ids_in_vector_size_range'],
            'year_directories':len(years),'month_directories':len(months),'directories_including_root':len(dirs),'max_directory_depth':2,
            'schema_counts':dict(schemas),'time_formats':dict(formats),'id_coverage_memory_bytes':len(seen)*8192,
            'first_10000_binding_bytes_equal_frozen_pilot':prefix_matches,
            'vector_structure':{'file':str(vectors.relative_to(project)).replace('\\','/'),'stat':vector_before,'first_dimension':dimension,'header_bytes_read':4,'rows_implied_by_length':vector_rows,'trailing_bytes_under_constant_dimension_assumption':remainder,'payload_bytes_read':0,'all_record_dimensions_or_finiteness_verified':False,'id_row_relationship':'metadata ID equals its row; compatibility with vector row count only, not semantic vector-ID proof'},
            'time_query_coverage':{'file':str(query_path.relative_to(project)).replace('\\','/'),'sha256':sha_file(query_path),'total_queries':len(queries),'time_constraints':len(query_rows),'missing_directory_constraints':sum(not r['exists'] for r in query_rows),'gt_read':False,'recursive_vs_nonrecursive_protocol_recovered':False},
            'outputs':{'bindings.tsv':binding_hash.hexdigest(),**{name:sha_file(out/name) for name in ['directory-counts.json','anomalies.json','time-query-coverage.json']}},
            'mapping_rule':'leading/trailing slash only, preserve original year/month spelling; no category conversion','performance_or_index_run':False,'vectors_payload_loaded':False,'author_fulltext_or_original_workload_recovered':False,
            'script_sha256':sha_file(Path(__file__)),'elapsed_seconds':time.monotonic()-started}
        (out/'manifest.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        status['status']='complete' if ready else 'completed_with_anomalies'
        print(json.dumps({'status':result['status'],'records':counts['records'],'year_directories':len(years),'month_directories':len(months),'bindings_sha256':binding_hash.hexdigest(),'elapsed_seconds':round(result['elapsed_seconds'],3)}),flush=True)
    except BaseException as e:
        status.update(status='interrupted' if isinstance(e,KeyboardInterrupt) else 'failed',failure=type(e).__name__+': '+str(e));raise
    finally:
        status.update(finished_at=utc(),wall_seconds=time.monotonic()-started)
        (out/'run-status.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path);p.add_argument('--output',type=Path);p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test();return
    if a.project is None or a.output is None:p.error('--project and --output required')
    audit(a.project.resolve(),a.output.resolve())
if __name__=='__main__':main()
