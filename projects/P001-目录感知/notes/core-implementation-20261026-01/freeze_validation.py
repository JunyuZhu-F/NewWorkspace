from pathlib import Path
import hashlib,json,re,shutil,zipfile
root=Path.cwd();code=root/'code';evidence=root/'notes/core-implementation-20261026-01'
files=['CMakeLists.txt','.gitignore','AGENTS.md','README.md','include/directory/index.hpp','include/directory/bitmap.hpp','src/path.cpp','src/index.cpp','tests/oracle.hpp','tests/oracle.cpp','tests/core_tests.cpp','scripts/build-test.cmd','scripts/prepare-time-fixture.py','third_party/croaring/roaring.c','third_party/croaring/roaring.h','third_party/croaring/LICENSE','third_party/croaring/LOCK.json','third_party/croaring/README.md']
manifest=[{'path':name,'bytes':(code/name).stat().st_size,'sha256':hashlib.sha256((code/name).read_bytes()).hexdigest()} for name in files]
version=hashlib.sha256(''.join(i['path']+'\0'+i['sha256']+'\n' for i in manifest).encode()).hexdigest()
archive=evidence/'source-snapshot.zip'
if archive.exists(): raise FileExistsError('Snapshot already exists')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for item in manifest:z.write(code/item['path'],'code/'+item['path'])
configurations={}
for tag,logname in [('Release','release-final.log'),('RelWithDebInfo-ASan','asan-build-test.log')]:
 build=code/('build-'+tag);last=build/'Testing/Temporary/LastTest.log'
 text=last.read_text(encoding='utf-8',errors='replace')
 cases=[]
 for block in re.split(r'\n\d+/\d+ Testing: ',text)[1:]:
  name=block.splitlines()[0].strip();m=re.search(r'^\{"status".*\}$',block,re.M)
  assert m and 'Test Passed.' in block,name
  item=json.loads(m.group());assert item['status']=='pass';item['name']=name;cases.append(item)
 assert len(cases)==7 and all(c['status']=='pass' for c in cases)
 shutil.copy2(last,evidence/(tag+'-LastTest.log'))
 exe=build/'directory_core_tests.exe'
 configurations[tag]={'status':'pass','cases':cases,'tests_passed':len(cases),
   'scope_comparisons':sum(c['scope_comparisons'] for c in cases),'checks':sum(c['checks'] for c in cases),
   'binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'binary_path':str(exe.relative_to(root)),
   'build_log':logname,'last_test_log':tag+'-LastTest.log',
   'fixture':json.loads((build/'time-pilot.meta.json').read_text(encoding='utf-8'))}
assert configurations['Release']['scope_comparisons']==configurations['RelWithDebInfo-ASan']['scope_comparisons']
assert configurations['Release']['checks']==configurations['RelWithDebInfo-ASan']['checks']
record={'date':'2026-10-26','source_snapshot_id':'SNAP-'+version[:16],'source_manifest_sha256':version,
 'snapshot_zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'source_files':manifest,
 'configurations':configurations,'scope':'single-parent sequential directory correctness only; no ANN, training or timing benchmark',
 'random_steps_per_seed':1000,'random_seeds':[7,42,2026,65536],'time_pilot_entries':10000,
 'review':'self-review plus independent set/path oracle, active Release checks, node identity tests and AddressSanitizer',
 'limitations':['No real multi-category DSM protocol recovered','No performance reproduction claimed','Catalog rebind scans counted separately','No allocation-failure rollback or concurrent consistency proof'],
 'development_attempts':['Initial Unicode documentation helper failed source decoding; explicit UTF-8 decode/compile succeeded before source implementation','Optional upstream roaring.hh download timed out/transport failed; use verified official C API with a tested ownership adapter','Initial 6-test Release run passed; final reviewed source rerun with 7 tests including time pilot'],
 'dependency_pin':'CRoaring v5.3.2; author version unspecified'}
(evidence/'validation-record.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'snapshot':record['source_snapshot_id'],'files':len(manifest),'configurations':{k:{'tests_passed':v['tests_passed'],'scope_comparisons':v['scope_comparisons'],'checks':v['checks']} for k,v in configurations.items()}},indent=2))
