"""Independent NumPy search oracle; no production scope helpers or backend calls."""
import argparse
import hashlib
import json
import pathlib
from collections import Counter, defaultdict

import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def vectors(path):
    records = np.fromfile(path, dtype=np.dtype([('d', '<i4'), ('v', '<f4', (1024,))]))
    assert path.stat().st_size == len(records) * 4100
    assert (records['d'] == 1024).all() and np.isfinite(records['v']).all()
    return records['v'].astype(np.float64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', type=pathlib.Path, required=True)
    ap.add_argument('--fixture', type=pathlib.Path, required=True)
    ap.add_argument('--outputs', type=pathlib.Path, nargs='+', required=True)
    ap.add_argument('--report', type=pathlib.Path, required=True)
    args = ap.parse_args()
    assert not args.report.exists(), 'verification evidence already exists'
    fixture, project = args.fixture, args.project
    manifest = load(fixture / 'manifest.json')
    assert manifest['protocol_sha256'] == digest(project / 'notes/search01-protocol-20261027.md')
    for name, expected in manifest['files'].items():
        assert digest(fixture / name) == expected, name
    # Independently re-read the actual source records and compare bytes, not just derived vectors.
    raw = project / 'dataset/raw/ARXIV-Dir'
    for name, info in manifest['inputs'].items():
        src = raw / name
        stat = src.stat()
        assert (stat.st_size, stat.st_mtime_ns) == (info['size'], info['mtime_ns'])
        with src.open('rb') as handle:
            data = handle.read(info['bytes_read'])
        assert hashlib.sha256(data).hexdigest() == info['read_region_sha256']
        if name == 'arxiv_corpus_vectors.fvecs':
            assert data == (fixture / 'corpus.fvecs').read_bytes()
        else:
            assert b''.join(data[i*4100:(i+1)*4100] for i in manifest['query_ids']) == (fixture / 'queries.fvecs').read_bytes()
    original = [json.loads(x) for x in (project / 'notes/time-pilot-20261026-01/bindings.jsonl').read_text(encoding='utf-8').splitlines()]
    lines = (fixture / 'bindings.tsv').read_text(encoding='utf-8').splitlines()
    assert len(lines) == 10000
    paths = []
    directories = {'/', '/__empty__/'}
    for i, line in enumerate(lines):
        idstr, path = line.split('\t')
        assert int(idstr) == original[i]['entry_id'] == i and path == original[i]['directory']
        paths.append(path)
        segments = path.strip('/').split('/')
        directories.update('/' + '/'.join(segments[:j]) + '/' for j in range(1, len(segments)+1))
    corpus, queries = vectors(fixture / 'corpus.fvecs'), vectors(fixture / 'queries.fvecs')
    cases = load(fixture / 'cases.json')
    assert len(cases) == 104 and len({c['case'] for c in cases}) == 104
    constraints = load(raw / 'arxiv_query_constraint.json')
    assert digest(raw / 'arxiv_query_constraint.json') == manifest['constraints_sha256']
    selected = []
    for depth in (1, 2):
        selected += [x for x in constraints if 'time' in x['constraints'] and len(x['constraints']['time'].strip('/').split('/')) == depth][:8]
    expected_cases = []
    qids = sorted({0} | {x['query_id'] for x in selected})
    assert qids == manifest['query_ids']
    for rec in selected:
        for recursive in (False, True):
            expected_cases.append(dict(case=f"original-{rec['query_id']}-{int(recursive)}", query_id=rec['query_id'], path='/' + rec['constraints']['time'].strip('/') + '/', recursive=recursive, k=100, origin='original-time-constraint-project-mode', query_row=qids.index(rec['query_id'])))
    for i, path in enumerate(sorted(directories | {'/__missing__/'})):
        for recursive in (False, True):
            expected_cases.append(dict(case=f'diagnostic-{i}-{int(recursive)}', query_id=0, path=path, recursive=recursive, k=100, origin='project-diagnostic-scope', query_row=qids.index(0)))
    assert cases == expected_cases, 'adapter case selection mismatch'
    assert (fixture / 'cases.tsv').read_text(encoding='utf-8') == ''.join(f"{c['case']}\t{c['query_row']}\t{c['path']}\t{int(c['recursive'])}\t{c['k']}\n" for c in cases)
    by_case = {c['case']: c for c in cases}
    scores = {i: np.sum(np.square(corpus - q), axis=1) for i, q in enumerate(queries)}
    scope_ids, truth = {}, {}
    for c in cases:
        anchor = c['path'].strip('/').split('/') if c['path'] != '/' else []
        def member(path):
            parts = path.strip('/').split('/')
            return parts[:len(anchor)] == anchor if c['recursive'] else parts == anchor
        ids = np.array([i for i, path in enumerate(paths) if member(path)], dtype=np.int64)
        scope_ids[c['case']] = ids
        order = np.lexsort((ids, scores[c['query_row']][ids]))
        truth[c['case']] = ids[order[:c['k']]].tolist()
    # Hand checks prevent metrics/empty handling from merely echoing the implementation.
    def recall(actual, expected):
        return len(set(actual) & set(expected)) / len(expected) if expected else None
    assert recall([1, 9], [1, 2, 3, 4]) == .25 and recall([], []) is None
    assert np.lexsort((np.array([5, 1]), np.array([2., 2.]))).tolist() == [1, 0]
    strategies = ['PE-ONLINE', 'PE-OFFLINE', 'TrieHI']
    build_reports, previous = [], None
    for output in args.outputs:
        model = load(output / 'model.json')
        assert model['clusters'] == 16 and model['dimension'] == 1024
        centers = np.asarray(model['centers']).reshape(16, 1024)
        assignment = np.asarray(model['assignment'])
        assert np.isfinite(centers).all() and assignment.shape == (10000,)
        coarse_corpus = np.stack([np.sum(np.square(corpus - center), axis=1) for center in centers], axis=1)
        assert np.array_equal(np.argmin(coarse_corpus, axis=1), assignment), 'incorrect IVF final assignments'
        rows = [json.loads(x) for x in (output / 'results.jsonl').read_text(encoding='utf-8').splitlines()]
        assert len(rows) == 104 * 3 * 4
        scopes = (output / 'scopes.tsv').read_text(encoding='utf-8').splitlines()
        assert len(scopes) == 104 * 3
        seen_scopes = set()
        for line in scopes:
            strategy, caseid, exists, values = line.split('\t')
            key = (strategy, caseid)
            assert strategy in strategies and key not in seen_scopes
            seen_scopes.add(key)
            assert bool(int(exists)) == (by_case[caseid]['path'] in directories)
            assert ([int(x) for x in values.split(',')] if values else []) == scope_ids[caseid].tolist()
        seen, results, metrics = set(), {}, defaultdict(list)
        for row in rows:
            strategy, caseid, probes = row['strategy'], row['case'], row['probes']
            key = (strategy, caseid, probes)
            assert strategy in strategies and probes in (0, 1, 4, 16) and key not in seen
            seen.add(key)
            c = by_case[caseid]
            ids = scope_ids[caseid]
            if probes:
                coarse = np.sum(np.square(centers - queries[c['query_row']]), axis=1)
                chosen = np.lexsort((np.arange(16), coarse))[:probes]
                ids = ids[np.isin(assignment[ids], chosen)]
            order = np.lexsort((ids, scores[c['query_row']][ids]))
            expected = ids[order[:c['k']]].tolist()
            assert row['ids'] == expected, ('ranking mismatch', key)
            assert len(row['ids']) == len(set(row['ids']))
            assert np.allclose(row['distances'], scores[c['query_row']][expected], rtol=1e-11, atol=1e-11), ('score mismatch', key)
            r = recall(row['ids'], truth[caseid])
            if probes in (0, 16):
                assert row['ids'] == truth[caseid] and r in (1., None)
            results[key] = row
            if strategy == strategies[0]:
                metrics[(c['origin'], probes)].append(r)
        for c in cases:
            for probes in (0, 1, 4, 16):
                base = results[(strategies[0], c['case'], probes)]
                for strategy in strategies[1:]:
                    other = results[(strategy, c['case'], probes)]
                    assert base['ids'] == other['ids'] and base['distances'] == other['distances']
        canonical = (model, sorted(rows, key=lambda x: (x['strategy'], x['case'], x['probes'])), sorted(scopes))
        if previous is not None:
            assert canonical == previous, 'Release/ASan mismatch'
        previous = canonical
        build_reports.append(dict(output=str(output), status='passed', scope_rows=len(scopes), result_rows=len(rows), metrics=[dict(origin=origin, probes=probes, cases=len(values), nonempty=sum(x is not None for x in values), empty=sum(x is None for x in values), mean_recall_nonempty=float(np.mean([x for x in values if x is not None])) if any(x is not None for x in values) else None) for (origin, probes), values in sorted(metrics.items())], hashes={p.name: digest(p) for p in output.iterdir() if p.is_file()}))
    report = dict(status='passed', scope_case_counts=dict(Counter('nonempty' if truth[c['case']] else 'empty' for c in cases)), cases=104, raw_read_regions_reverified=True, published_gt_used=False, independent_final_assignments_checked=10000 * len(args.outputs), builds=build_reports, cross_build_equal=True, timing_claim=False)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    args.report.with_name(args.report.stem + '-truth.json').write_text(json.dumps(truth, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='passed', cases=104, builds=len(args.outputs), counts=report['scope_case_counts'])))


if __name__ == '__main__':
    main()
