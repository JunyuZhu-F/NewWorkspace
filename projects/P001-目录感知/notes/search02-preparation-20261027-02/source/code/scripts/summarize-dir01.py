"""Summarize completed DIR-01 JSONL without interpolating quantiles."""
import argparse, json, math
from collections import defaultdict
from pathlib import Path

def mean(values): return sum(values)/len(values) if values else None
def quantile(values,p):
    values=sorted(values); return values[max(1,math.ceil(p*len(values)))-1]
def stats(values):
    return {"n":len(values),"mean":mean(values),"p90":quantile(values,.90),"p95":quantile(values,.95),
            "p99":quantile(values,.99),"p99_9":quantile(values,.999),
            "p99_9_stability":"unstable_descriptive_only" if len(values)<10000 else "limited_by_sample"}
def read(path):
    if not path.exists(): return []
    with path.open(encoding='utf-8') as f: return [json.loads(line) for line in f if line.strip()]
def grouped(rows,keys,value):
    groups=defaultdict(list); runs=defaultdict(lambda:defaultdict(list))
    for r in rows:
        if r["warmup"]: continue
        key=tuple(r[k] for k in keys); groups[key].append(r[value]); runs[key][r["run"]].append(r[value])
    result=[]
    for key,values in sorted(groups.items(),key=lambda x:repr(x[0])):
        item=dict(zip(keys,key)); item["pooled"]=stats(values)
        item["per_process_mean"]={str(run):mean(v) for run,v in sorted(runs[key].items())}
        result.append(item)
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--experiment',type=Path,required=True);a=p.parse_args();root=a.experiment
    build=read(root/'raw/build.jsonl');dsq=read(root/'raw/dsq.jsonl');dsm=read(root/'raw/dsm.jsonl');space=read(root/'raw/space.jsonl');process=read(root/'raw/process.jsonl')
    if len(process)!=210 or any(r.get('status')!='passed' for r in process): raise ValueError(f'Expected 210 passed processes, got {len(process)}')
    expected={'build':1380,'dsq':62100,'dsm':3450,'space':1380}
    actual={'build':len(build),'dsq':len(dsq),'dsm':len(dsm),'space':len(space)}
    if actual!=expected: raise ValueError(f'Raw count mismatch: {actual} != {expected}')
    for rows in (build,dsq,dsm,space):
        for r in rows:
            if r['instrumented'] and r['subload']=='dsq' and r.get('work_counters_status')!='collected': raise ValueError('Missing instrumented counters')
            if not r['instrumented'] and r['subload']=='dsq' and r.get('work_counters_status')!='not_collected_in_default_core': raise ValueError('Unexpected default counters')
    base=['input','strategy','subload','instrumented']
    summary={'protocol':'PROTO-01-20261026','status':'complete','quantile':'nearest-rank ceil(p*N), no interpolation',
             'scope':'project diagnostic workload; not original author workload; vectors/ANN excluded',
             'raw_counts':actual,'passed_processes':len(process),
             'build':grouped(build,base,'build_ns'),
             'dsq':grouped(dsq,base+['operation' if False else 'path','recursive'],'total_ns'),
             'dsm':grouped(dsm,base+['operation','source','target_or_new_parent','accepted'],'total_ns'),
             'space':grouped(space,base,'roaring_portable_bytes'),
             'process_memory_summary':{key:grouped(space,base,key) for key in ('working_set_bytes','private_bytes','peak_working_set_bytes')},
             'process_memory':{'raw_file':'raw/space.jsonl','api':'GetProcessMemoryInfo/GlobalMemoryStatusEx','not_serialized_index_size':True},
             'catalog':{'included_in_public_api_total':True,'separate_timing':'not_collected','catalog_entries_scanned_raw':'raw/dsm.jsonl'},
             'vector_bytes':0,'vector_loaded':False}
    (root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    correctness={'status':'passed','passed_processes':len(process),'raw_counts':actual,
                 'checks':'per-query frozen digest and independent per-ID oracle; full state after every DSM operation; rejection unchanged; existing Release/ASan gate recorded separately'}
    (root/'correctness.json').write_text(json.dumps(correctness,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'complete','raw_counts':actual,'summary':str(root/'summary.json')}))
if __name__=='__main__':main()
