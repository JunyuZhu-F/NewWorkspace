"""Convert the already frozen time pilot to a checked TSV test input."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=a.project.resolve();output=a.output.resolve()
assert output.is_relative_to(root/'code')
pilot=root/'notes/time-pilot-20261026-01';manifest=json.loads((pilot/'manifest.json').read_text(encoding='utf-8'))
source=pilot/'bindings.jsonl';digest=hashlib.sha256(source.read_bytes()).hexdigest()
assert digest==manifest['outputs']['bindings.jsonl']
rows=[json.loads(line) for line in source.read_text(encoding='utf-8').splitlines()]
assert len(rows)==10000 and [r['entry_id'] for r in rows]==list(range(10000))
assert all(r['namespace']=='time' and not any(c in r['directory'] for c in '\t\n\r') for r in rows)
data=''.join(str(r['entry_id'])+'\t'+r['directory']+'\n' for r in rows).encode('utf-8')
output.parent.mkdir(parents=True,exist_ok=True)
if output.exists() and output.read_bytes()!=data: raise ValueError('Existing fixture differs; refusing overwrite')
output.write_bytes(data)
meta={'source':str(source),'source_sha256':digest,'output_sha256':hashlib.sha256(data).hexdigest(),'rows':len(rows),'scope':'correctness fixture only; no original workload or quality claim'}
output.with_suffix('.meta.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print('Prepared verified time-pilot TSV: 10000 bindings')
