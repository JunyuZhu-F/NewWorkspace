"""Read-only input check for independent cost builds; never regenerate aliases."""
import hashlib,json
from pathlib import Path
project=Path(__file__).resolve().parent.parent.parent
manifest=json.loads((project/'experiments/EXP-20261027-004/source/hashes.json').read_text())
checked=0
for name,expected in manifest['files'].items():
    if name.startswith('fixtures/'):
        path=project/'notes/benchmark-fixtures-20261026-01'/Path(name).name
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        if actual!=expected: raise ValueError('Frozen input mismatch: '+str(path))
        checked+=1
assert checked==10
assert hashlib.sha256((project/'notes/benchmark-protocol.md').read_bytes()).hexdigest()=='81ec16d0f07ea1c74715de2a4b6c049c9292766ddc0e36240a1668f3a21eed24'
print(json.dumps({'frozen_fixture_files_checked':checked,'status':'passed','writes':0}))
