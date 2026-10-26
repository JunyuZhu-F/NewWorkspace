from pathlib import Path
import hashlib,json,zipfile,re,datetime
root=Path.cwd();ev=root/'notes/core-implementation-20261026-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
record=json.loads((ev/'validation-record.json').read_text(encoding='utf-8'))
errors=[];checks={}
def check(name,value):
 checks[name]=bool(value)
 if not value:errors.append(name)
check('source_manifest_matches',all(sha(root/'code'/i['path'])==i['sha256'] and (root/'code'/i['path']).stat().st_size==i['bytes'] for i in record['source_files']))
check('snapshot_zip_hash',sha(ev/'source-snapshot.zip')==record['snapshot_zip_sha256'])
with zipfile.ZipFile(ev/'source-snapshot.zip') as z:
 check('snapshot_content_matches',all(hashlib.sha256(z.read('code/'+i['path'])).hexdigest()==i['sha256'] for i in record['source_files']))
lock=json.loads((root/'code/third_party/croaring/LOCK.json').read_text(encoding='utf-8'))
check('vendor_files_match',all(sha(root/'code/third_party/croaring'/i['file'])==i['sha256'] for i in lock['files']))
check('official_c_h_digests_match',all(i.get('official_release_digest')=='sha256:'+i['sha256'] for i in lock['files'] if i['file'] in ['roaring.c','roaring.h']))
for tag,cfg in record['configurations'].items():
 log=(ev/cfg['last_test_log']).read_text(encoding='utf-8',errors='replace')
 check(tag+'_seven_tests',cfg['tests_passed']==7 and log.count('Test Passed.')==7 and 'Test Failed.' not in log)
 check(tag+'_binary_hash',sha(root/cfg['binary_path'])==cfg['binary_sha256'])
 build=root/'code'/('build-'+tag)
 check(tag+'_fixture_hash',sha(build/'time-pilot.tsv')==cfg['fixture']['output_sha256'])
check('asan_no_address_error_report','ERROR: AddressSanitizer' not in (ev/'asan-build-test.log').read_text(encoding='utf-8',errors='replace'))
manifest=json.loads((root/'notes/time-pilot-20261026-01/manifest.json').read_text(encoding='utf-8'))
check('frozen_pilot_outputs_unchanged',all(sha(root/'notes/time-pilot-20261026-01'/name)==digest for name,digest in manifest['outputs'].items()))
check('paper_hash_unchanged',sha(root/'paper/Wang 等 - 2026 - Directory-Aware Query and Maintenance in Vector Databases.pdf')=='00c59850614b7c286d82669b5e1447bacb5fb7115cbd442d8b29c801bd65e968')
inventory=json.loads((root/'notes/reading-20261026/local-data-inventory.json').read_text(encoding='utf-8'))
raw=[]
for item in inventory:
 p=root/item['relative_path'];st=p.stat()
 expected=datetime.datetime.fromisoformat(re.sub(r'(\.\d{6})\d+',r'\1',item['last_write_time'])).timestamp()
 raw.append({'path':item['relative_path'],'size_same':st.st_size==item['bytes'],'mtime_same_to_2us':abs(st.st_mtime-expected)<0.000002})
check('original_raw_sizes_mtimes_unchanged',all(x['size_same'] and x['mtime_same_to_2us'] for x in raw))
# Independent arithmetic cross-check of the written pilot anchors, not a new benchmark.
entries={x['entry_id']:x['directory'] for x in map(json.loads,(root/'notes/time-pilot-20261026-01/bindings.jsonl').read_text(encoding='utf-8').splitlines())}
def counts(paths):return {p:sum(v.startswith(p) for v in entries.values()) for p in paths}
initial=counts(['/','/1991/','/1992/','/1993/','/1992/1/','/1991/7/','/1992/7/','/1991/8/','/1992/8/'])
check('initial_pilot_anchors',list(initial.values())==[10000,306,3261,6433,193,2,296,28,226])
entries={i:('/1991/1/'+p[len('/1992/1/'):] if p.startswith('/1992/1/') else p) for i,p in entries.items()}
after_move=counts(['/1991/1/','/1991/','/1992/','/'])
check('move_pilot_anchors',list(after_move.values())==[193,499,3068,10000])
entries={i:('/1991/7/'+p[len('/1992/7/'):] if p.startswith('/1992/7/') else p) for i,p in entries.items()}
after_merge=counts(['/1991/7/','/1991/','/1992/','/'])
check('merge_pilot_anchors',list(after_merge.values())==[298,795,2772,10000])
docs=['TASK.md','REPRODUCTION_PLAN.md','STATE.md','README.md','EXPERIMENTS.md','AGENTS.md','notes/core-review.md','notes/operation-spec.md','notes/environment.md','notes/materials-and-gaps.md','code/README.md','code/AGENTS.md']
badlinks=[];doc_hashes=[]
for name in docs:
 p=root/name;s=p.read_text(encoding='utf-8-sig')
 check(name+'_no_replacement_character','\ufffd' not in s)
 doc_hashes.append({'path':name,'sha256':sha(p)})
 for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)',s):
  link=link.split('#')[0].strip('<>')
  if not link or '://' in link or link.startswith('mailto:'):continue
  if not (p.parent/link).exists():badlinks.append({'document':name,'target':link})
check('markdown_file_links_resolve',not badlinks)
plan=(root/'REPRODUCTION_PLAN.md').read_text(encoding='utf-8')
statuses={}
for line in plan.splitlines():
 c=[v.strip() for v in line.split('|')]
 if len(c)==7:statuses[c[1]]=c[4]
check('completed_core_statuses',all(statuses.get(k)=='已完成' for k in ['ENV-01','ORACLE-01','CORE-01','CORE-02','CORE-03','CHECK-01','SPEC-TIME-PILOT-01']))
check('unresolved_parent_statuses',statuses.get('DATA-01')=='进行中' and statuses.get('SPEC-01')=='进行中' and statuses.get('SPEC-ARXIV-CATEGORY-01')=='阻塞')
check('performance_not_started',all(statuses.get(k)=='未开始' for k in ['PROTO-01','DIR-01','SEARCH-01','SEARCH-02','SCALE-01','SCALE-02']))
result={'date':'2026-10-26','source_snapshot_id':record['source_snapshot_id'],'status':'pass' if not errors else 'fail','checks':checks,'errors':errors,'raw_inventory_comparison':raw,'raw_check_boundary':'sizes and mtimes only; not a full raw-data checksum','pilot_anchor_crosscheck':{'initial':initial,'after_move':after_move,'after_merge':after_merge},'documentation_hashes':doc_hashes,'broken_links':badlinks,'tool_attempts':['One oversized combined document-write command was rejected by tool policy before execution; smaller apply_patch writes and bounded Python updates completed the same authorized task. No permission escalation.'],'scope':'handoff consistency only; no new algorithm or performance run'}
(ev/'handoff-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':result['status'],'checks':len(checks),'errors':errors,'snapshot':record['source_snapshot_id']},ensure_ascii=True))
if errors:raise SystemExit(1)
