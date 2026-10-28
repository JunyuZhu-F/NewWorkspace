"""Bounded read-only fixture adapter. Does not read published ground truth."""
import argparse
import hashlib
import json
import pathlib
import struct
import sys
from datetime import datetime, timezone

import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', type=pathlib.Path, required=True)
    ap.add_argument('--output', type=pathlib.Path, required=True)
    args = ap.parse_args()
    project = args.project.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    raw = project / 'dataset/raw/ARXIV-Dir'
    source = project / 'notes/time-pilot-20261026-01/bindings.jsonl'
    assert digest(source) == '9aa84f093dfd4e9c4e1633c22ae7a9df424809fee9f45fc22fb96f85c04f36b6'
    bindings = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines()]
    assert len(bindings) == 10000
    for i, rec in enumerate(bindings):
        assert rec['row'] == rec['entry_id'] == i
        assert rec['directory'] == '/' + rec['raw_time'].strip('/') + '/'
    (out / 'bindings.tsv').write_text(''.join(f"{x['entry_id']}\t{x['directory']}\n" for x in bindings), encoding='utf-8')
    constraints = json.loads((raw / 'arxiv_query_constraint.json').read_text(encoding='utf-8'))
    assert [x['query_id'] for x in constraints] == list(range(1000))
    selected = []
    for depth in (1, 2):
        group = [x for x in constraints if 'time' in x['constraints'] and len(x['constraints']['time'].strip('/').split('/')) == depth]
        assert len(group) >= 8
        selected.extend(group[:8])
    qids = sorted({0} | {x['query_id'] for x in selected})
    qmap = {qid: row for row, qid in enumerate(qids)}
    dirs = {'/'}
    for rec in bindings:
        parts = rec['directory'].strip('/').split('/')
        dirs.update('/' + '/'.join(parts[:i]) + '/' for i in range(1, len(parts) + 1))
    assert len(dirs) == 34
    cases = []
    for rec in selected:
        for recursive in (False, True):
            cases.append(dict(case=f"original-{rec['query_id']}-{int(recursive)}", query_id=rec['query_id'], path='/' + rec['constraints']['time'].strip('/') + '/', recursive=recursive, k=100, origin='original-time-constraint-project-mode'))
    for i, path in enumerate(sorted(dirs | {'/__empty__/', '/__missing__/'})):
        for recursive in (False, True):
            cases.append(dict(case=f'diagnostic-{i}-{int(recursive)}', query_id=0, path=path, recursive=recursive, k=100, origin='project-diagnostic-scope'))
    assert len(cases) == 104
    for c in cases:
        c['query_row'] = qmap[c['query_id']]
    write_json(out / 'cases.json', cases)
    (out / 'cases.tsv').write_text(''.join(f"{c['case']}\t{c['query_row']}\t{c['path']}\t{int(c['recursive'])}\t{c['k']}\n" for c in cases), encoding='utf-8')
    inputs = {}
    # Explicit sequential record adapter; independent verifier uses a structured dtype.
    for name, limit, target, selection in [
        ('arxiv_corpus_vectors.fvecs', 10000, 'corpus.fvecs', None),
        ('arxiv_query_vectors.fvecs', 1000, 'queries.fvecs', set(qids)),
    ]:
        path = raw / name
        before = path.stat()
        h = hashlib.sha256()
        norms = []
        with path.open('rb') as handle, (out / target).open('xb') as dest:
            for i in range(limit):
                record = handle.read(4100)
                assert len(record) == 4100 and struct.unpack('<i', record[:4])[0] == 1024
                a = np.frombuffer(record[4:], dtype='<f4')
                assert np.isfinite(a).all()
                norms.append(float(np.linalg.norm(a.astype(np.float64))))
                h.update(record)
                if selection is None or i in selection:
                    dest.write(record)
            if selection is not None:
                assert handle.read(1) == b''
        after = path.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        inputs[name] = dict(records_read=limit, bytes_read=limit * 4100, read_region_sha256=h.hexdigest(), size=before.st_size, mtime_ns=before.st_mtime_ns, norm_min=min(norms), norm_max=max(norms), stat_unchanged=True)
    manifest = dict(status='prepared', created_utc=datetime.now(timezone.utc).isoformat(), python=sys.version, numpy=np.__version__, source_bindings_sha256=digest(source), constraints_sha256=digest(raw / 'arxiv_query_constraint.json'), query_ids=qids, records=10000, dimension=1024, cases=104, inputs=inputs, protocol_sha256=digest(project / 'notes/search01-protocol-20261027.md'), files={p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()})
    write_json(out / 'manifest.json', manifest)
    print(json.dumps(dict(status='prepared', cases=104, query_vectors=len(qids), corpus_records=10000)))


if __name__ == '__main__':
    main()
