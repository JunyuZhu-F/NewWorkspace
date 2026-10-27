"""Final read-only audit of source, protocol, ZIP and admission log anchors."""
import hashlib,json,zipfile
from pathlib import Path
here=Path(__file__).resolve().parent;project=here.parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
frozen=json.loads((here/'source-hashes.json').read_text())
for name,digest in frozen['files'].items():assert sha(project/name)==digest,name
for name,digest in frozen['fixtures'].items():assert sha(project/'notes/benchmark-fixtures-20261026-01'/name)==digest,name
assert sha(project/'notes/benchmark-cost-protocol-20261027.md')==frozen['protocol_sha256']
assert sha(here/'source-snapshot.zip')==frozen['snapshot_zip_sha256']
with zipfile.ZipFile(here/'source-snapshot.zip') as z:
    assert z.testzip() is None
    assert len(z.namelist())==41
    for name,digest in frozen['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
    for name,digest in frozen['fixtures'].items():assert hashlib.sha256(z.read('fixtures/'+name)).hexdigest()==digest
    assert hashlib.sha256(z.read('protocol.md')).hexdigest()==frozen['protocol_sha256']
for label,build in [('release','build-Release-Cost'),('asan','build-RelWithDebInfo-ASan-Cost')]:
    for mode,digest in frozen[label+'_binary_sha256'].items():assert sha(project/'code'/build/f'directory_cost_{mode}.exe')==digest
for name in ['release-final.log','asan-final-attempt2.log']:
    text=(here/name).read_text(encoding='utf-8',errors='replace')
    assert '100% tests passed, 0 tests failed out of 23' in text
    assert 'DIR-01 self-test passed; instrumented=0' in text and 'DIR-01 self-test passed; instrumented=1' in text
    assert 'ERROR: AddressSanitizer' not in text
for name in ['release-schema-admission.log','asan-schema-admission.log']:
    assert '100% tests passed, 0 tests failed out of 2' in (here/name).read_text(encoding='utf-8',errors='replace')
alias=here/'shared-fixture-race-leftovers/time-dsm-queries.tsv'
assert sha(alias)==frozen['fixtures']['time-queries.tsv']
result={'status':'passed','snapshot':frozen['snapshot'],'current_code_files':len(frozen['files']),'frozen_inputs':len(frozen['fixtures']),
        'zip_members':41,'source_zip_and_protocol_hashes_match':True,'binary_hashes_match':True,'log_anchors_valid':True,'race_leftover_preserved_and_identical_to_base':True,'formal_matrix_run':False}
(here/'final-check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
