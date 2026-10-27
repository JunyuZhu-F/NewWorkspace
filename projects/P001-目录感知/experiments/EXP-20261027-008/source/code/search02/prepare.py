"""New deterministic cross-time sample, read-only source adapter; no published GT."""
import argparse
import hashlib
import json
import pathlib
import struct
from datetime import datetime, timezone

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def dump(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=pathlib.Path, required=True)
    a = ap.parse_args()
    root = pathlib.Path.cwd()
    a.output.mkdir(parents=True, exist_ok=False)
    selected = [i * (2763543 - 1) // 9999 for i in range(10000)]
    assert len(set(selected)) == 10000
    source = root / 'notes/arxiv-time-full-audit-20261027-01/run-01/bindings.tsv'
    before = source.stat()
    wanted = set(selected)
    bindings = []
    h = hashlib.sha256()
    with source.open('rb') as f:
        for row, line in enumerate(f):
            h.update(line)
            if row in wanted:
                gid, path = line.decode('utf-8').strip().split('\t')
                assert int(gid) == row and path.startswith('/') and path.endswith('/')
                bindings.append(dict(row=len(bindings), global_id=row, path=path))
    assert row + 1 == 2763543 and len(bindings) == 10000
    assert h.hexdigest() == '127a7d07902cb997489da526be1da973bc9bac09f0da133787f0c28323ea72a2'
    assert before.st_mtime_ns == source.stat().st_mtime_ns
    (a.output / 'bindings.tsv').write_text(''.join(f"{x['row']}\t{x['global_id']}\t{x['path']}\n" for x in bindings), encoding='utf-8')
    dump(a.output / 'sample.json', bindings)
    raw = root / 'dataset/raw/ARXIV-Dir'
    constraints = json.loads((raw / 'arxiv_query_constraint.json').read_text(encoding='utf-8'))
    assert [x['query_id'] for x in constraints] == list(range(1000))
    selected_queries = [x for x in constraints if 'time' in x['constraints']]
    assert len(selected_queries) == 501
    qids = [x['query_id'] for x in selected_queries]
    cases = []
    for qrow, record in enumerate(selected_queries):
        for recursive in (False, True):
            cases.append(dict(case=f"q{record['query_id']}-r{int(recursive)}", query_id=record['query_id'], query_row=qrow, path='/' + record['constraints']['time'].strip('/') + '/', recursive=recursive, k=100))
    dump(a.output / 'cases.json', cases)
    (a.output / 'cases.tsv').write_text(''.join(f"{c['case']}\t{c['query_row']}\t{c['path']}\t{int(c['recursive'])}\t{c['k']}\n" for c in cases), encoding='utf-8')
    inputs = {}
    for name, rows, output in [('arxiv_corpus_vectors.fvecs', selected, 'corpus.fvecs'), ('arxiv_query_vectors.fvecs', list(range(1000)), 'queries.fvecs')]:
        p = raw / name
        stat = p.stat()
        content_hash = hashlib.sha256()
        norm_min, norm_max = float('inf'), 0.
        with p.open('rb') as f, (a.output / output).open('xb') as dest:
            for i in rows:
                f.seek(i * 4100)
                record = f.read(4100)
                assert len(record) == 4100 and struct.unpack('<i', record[:4])[0] == 1024
                v = np.frombuffer(record[4:], dtype='<f4')
                assert np.isfinite(v).all()
                norm = float(np.linalg.norm(v.astype(np.float64)))
                norm_min, norm_max = min(norm_min, norm), max(norm_max, norm)
                content_hash.update(record)
                if name.startswith('arxiv_corpus') or i in qids:
                    dest.write(record)
        assert (stat.st_size, stat.st_mtime_ns) == (p.stat().st_size, p.stat().st_mtime_ns)
        inputs[name] = dict(size=stat.st_size, mtime_ns=stat.st_mtime_ns, records_read=len(rows), bytes_read=len(rows)*4100, selected_read_regions_sha256=content_hash.hexdigest(), norm_min=norm_min, norm_max=norm_max)
    directories = {'/'}
    for b in bindings:
        parts = b['path'].strip('/').split('/')
        directories.update('/' + '/'.join(parts[:j]) + '/' for j in range(1, len(parts)+1))
    coverage = dict(directories=len(directories), years=len({b['path'].split('/')[1] for b in bindings}), months=len({b['path'] for b in bindings}))
    manifest = dict(status='prepared', created_utc=datetime.now(timezone.utc).isoformat(), selection='floor(i*(2763543-1)/9999), i=0..9999; no GT/query-dependent sampling', corpus_records=10000, query_ids=qids, cases=1002, full_bindings_sha256=h.hexdigest(), constraints_sha256=sha(raw / 'arxiv_query_constraint.json'), protocol_sha256=sha(root / 'notes/search02-protocol-20261027.md'), inputs=inputs, coverage=coverage, files={p.name: sha(p) for p in sorted(a.output.iterdir()) if p.is_file()})
    dump(a.output / 'manifest.json', manifest)
    print(json.dumps(dict(status='prepared', records=10000, cases=1002, coverage=coverage)))


if __name__ == '__main__':
    main()
