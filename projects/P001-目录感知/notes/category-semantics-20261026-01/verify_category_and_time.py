"""Independent validation of category-view analysis and metadata-only time pilot."""
import collections
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'notes/category-semantics-20261026-01'
TIME=ROOT/'notes/time-pilot-20261026-01'
OUTPUT=CAT/'verification.json'
if OUTPUT.exists():
    raise FileExistsError('Refusing to overwrite verification')
analysis=json.loads((CAT/'analysis.json').read_text(encoding='utf-8'))
input_path=ROOT/analysis['input_path']
assert hashlib.sha256(input_path.read_bytes()).hexdigest()==analysis['input_sha256']
records={}
for line in input_path.read_text(encoding='utf-8').splitlines():
    ref=json.loads(line);records[ref['entry_id']]=ref['metadata']
affected=removed=multi=0
for item in records.values():
    paths={tuple(p.strip('/').split('/')) for p in item['categories']}
    # Descending-length retention, independent of the original all-pairs filter.
    kept=[]
    for p in sorted(paths,key=lambda p:(-len(p),p)):
        if not any(q[:len(p)]==p for q in kept):
            kept.append(p)
    affected+=len(kept)<len(paths)
    removed+=len(paths)-len(kept)
    multi+=len(kept)>1
assert affected==analysis['records_with_raw_ancestor_labels']==1035
assert removed==analysis['raw_ancestor_labels_removed_in_hypothetical_view']==1223
assert multi==analysis['records_still_multibranch_in_maximal_path_view']==1014
manifest=json.loads((TIME/'manifest.json').read_text(encoding='utf-8'))
for name,digest in manifest['outputs'].items():
    assert hashlib.sha256((TIME/name).read_bytes()).hexdigest()==digest
raw=[json.loads(line) for line in (TIME/'source-metadata.jsonl').read_text(encoding='utf-8').splitlines()]
bindings=[json.loads(line) for line in (TIME/'bindings.jsonl').read_text(encoding='utf-8').splitlines()]
nodes=json.loads((TIME/'directory-counts.json').read_text(encoding='utf-8'))
assert len(raw)==len(bindings)==10000
assert [b['entry_id'] for b in bindings]==list(range(10000))
for item,binding in zip(raw,bindings):
    assert item['id']==binding['entry_id'] and item['time']==binding['raw_time']
    assert isinstance(item['categories'],list) and binding['namespace']=='time'
    assert binding['directory']=='/'+item['time'].strip('/')+'/'
for node in nodes:
    p=node['directory']
    assert sum(b['directory']==p for b in bindings)==node['direct_entries']
    assert sum(b['directory'].startswith(p) for b in bindings)==node['recursive_entries']
assert len(nodes)==manifest['counts']['directories_including_root']==34
category_script=ROOT/'notes/analyze_category_semantics.py'
time_script=ROOT/'notes/prepare_time_pilot.py'
assert hashlib.sha256(category_script.read_bytes()).hexdigest()==analysis['script_sha256']
assert hashlib.sha256(time_script.read_bytes()).hexdigest()==manifest['script_sha256']
result={'status':'pass','category_records_verified':len(records),'category_recomputed_affected':affected,
        'category_recomputed_removed_labels':removed,'category_recomputed_still_multibranch':multi,
        'time_entries_verified':len(bindings),'time_directory_counts_independently_verified':len(nodes),
        'source_category_fields_preserved':True,'manifest_output_hashes_match':True,'script_hashes_match':True,
        'vector_search_run':False,'paper_strategy_implementation_tested':False}
(CAT/'verify_category_and_time.py').write_bytes(Path(__file__).read_bytes())
OUTPUT.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
