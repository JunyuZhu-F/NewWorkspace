"""Read-only WIKI prerequisite audit; no retrieval or performance experiment.

Full path array and corpus JSONL are streamed. Only 10000 predetermined corpus
vectors plus all query vectors are read. No qrels-derived query scopes.
"""
import collections
import csv
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import struct
import sys
import time
import traceback
import urllib.request

import numpy as np
import psutil

PROJECT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RAW = PROJECT / 'dataset/raw/WIKI-Dir'

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def write(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def stat(p):
    s = p.stat()
    return dict(size=s.st_size, mtime_ns=s.st_mtime_ns)

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    out = HERE / 'run-01'
    out.mkdir(exist_ok=False)
    started = time.monotonic()
    status = dict(status='running', started_utc=now())
    write(out / 'status.json', status)
    try:
        paths = RAW / 'dbpedia_dir_2m_corpus_paths.json'
        corpus = RAW / 'dbpedia_dir_2m_corpus.jsonl'
        vectors = RAW / 'dbpedia_dir_2m_corpus_vectors-001.fvecs'
        query = RAW / 'dbpedia_dir_2m_query.jsonl'
        qvectors = RAW / 'dbpedia_dir_2m_query_vectors.fvecs'
        qrels = RAW / 'dbpedia_dir_2m_groundtruth.tsv'
        files = [paths, corpus, vectors, query, qvectors, qrels]
        before = {p.name: stat(p) for p in files}
        dependency = PROJECT / 'notes/arxiv-time-full-audit-20261027-01/audit.py'
        spec = importlib.util.spec_from_file_location('strict_metadata', dependency)
        parser = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parser)
        (out / 'strict-parser.reference.py').write_bytes(dependency.read_bytes())
        parser.self_test()
        with vectors.open('rb') as f:
            dim = struct.unpack('<i', f.read(4))[0]
        if dim != 1024:
            raise ValueError('Unexpected corpus dimension')
        width = 4 * (dim + 1)
        total, remainder = divmod(vectors.stat().st_size, width)
        if remainder or total < 10000:
            raise ValueError('Corpus fixed-width size mismatch')
        selected = {i * (total - 1) // 9999 for i in range(10000)}
        query_rows = [json.loads(line) for line in query.read_text(encoding='utf-8-sig').splitlines()]
        qids = [x['_id'] for x in query_rows]
        if qids != list(range(len(qids))):
            raise ValueError('Query ID differs from vector row')
        query_constraints = [{k: x[k] for k in x if k not in ('_id', 'text')}
                             for x in query_rows]
        relevant = set()
        pairs = set()
        grades = collections.Counter()
        qrel_counts = collections.Counter()
        with qrels.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            if reader.fieldnames != ['query-id', 'corpus-id', 'score']:
                raise ValueError('Unexpected qrels header')
            for row in reader:
                q, d, score = (int(row[k]) for k in reader.fieldnames)
                if q not in qids or not 0 <= d < total or score not in (1, 2) or (q, d) in pairs:
                    raise ValueError('Invalid/duplicate qrel')
                pairs.add((q, d))
                relevant.add(d)
                grades[score] += 1
                qrel_counts[q] += 1
        if set(qrel_counts) != set(qids):
            raise ValueError('Missing qrels query')
        directories = {'/': 0}
        local_counts = collections.Counter()
        depths = collections.Counter()
        sample = []
        relevant_bindings = []
        proof = {}
        count = 0
        print('Full streaming path/ID audit', flush=True)
        for row, obj in enumerate(parser.strict_records(paths, proof)):
            if set(obj) != {'id', 'path'} or type(obj['id']) is not int or obj['id'] != row:
                raise ValueError('Path ID/schema mismatch at row ' + str(row))
            path = obj['path']
            if not isinstance(path, str) or not path.startswith('/') or not path.endswith('/') or '\0' in path:
                raise ValueError('Unsupported path at row ' + str(row))
            parts = path[1:-1].split('/') if path != '/' else []
            if any(s in ('', '.', '..') for s in parts) or any(c in path for c in '\t\r\n'):
                raise ValueError('Unsupported path segment/TSV at row ' + str(row))
            depths[len(parts)] += 1
            prefix = '/'
            for depth, part in enumerate(parts, 1):
                prefix += part + '/'
                directories[prefix] = depth
            local_counts[path] += 1
            if row in selected:
                sample.append(dict(global_id=row, path=path))
            if row in relevant:
                relevant_bindings.append(dict(global_id=row, path=path))
            count = row + 1
            if count % 500000 == 0:
                print('paths', count, 'directories', len(directories), flush=True)
        if count != total or len(sample) != 10000 or len(relevant_bindings) != len(relevant):
            raise ValueError('Path/sample/qrels target coverage mismatch')
        print('Full streaming corpus ID audit', flush=True)
        corpus_hash = hashlib.sha256()
        corpus_count = 0
        sample_titles = {}
        with corpus.open('rb') as f:
            for row, line in enumerate(f):
                corpus_hash.update(line)
                obj = json.loads(line)
                if type(obj['_id']) is not int or obj['_id'] != row:
                    raise ValueError('Corpus ID mismatch at row ' + str(row))
                if row in selected:
                    sample_titles[row] = dict(title=obj.get('title'), metadata=obj.get('metadata'))
                corpus_count = row + 1
        if corpus_count != total:
            raise ValueError('Corpus/path/vector inferred row mismatch')
        def check_vectors(p, ids):
            norms = []
            digest = hashlib.sha256()
            with p.open('rb') as f:
                for row in ids:
                    f.seek(row * width)
                    b = f.read(width)
                    if len(b) != width or struct.unpack_from('<i', b)[0] != dim:
                        raise ValueError('Bad vector header/length at ' + str(row))
                    a = np.frombuffer(b, dtype='<f4', offset=4)
                    if not np.isfinite(a).all():
                        raise ValueError('Nonfinite vector at ' + str(row))
                    norm = float(np.linalg.norm(a.astype(np.float64)))
                    if norm == 0:
                        raise ValueError('Zero vector at ' + str(row))
                    norms.append(norm)
                    digest.update(struct.pack('<Q', row) + b)
            return dict(checked_records=len(norms), dimension=dim, finite_nonzero=True,
                        norm_min=min(norms), norm_max=max(norms), row_and_record_sha256=digest.hexdigest())
        print('Checking fixed sample and all query vectors', flush=True)
        sample_vectors = check_vectors(vectors, sorted(selected))
        if qvectors.stat().st_size != len(qids) * width:
            raise ValueError('Query vector size mismatch')
        query_vectors = check_vectors(qvectors, range(len(qids)))
        after = {p.name: stat(p) for p in files}
        if after != before:
            raise ValueError('Raw input size/mtime changed during audit')
        sample_dirs = {'/'}
        for x in sample:
            parts = x['path'].strip('/').split('/') if x['path'] != '/' else []
            prefix = '/'
            for part in parts:
                prefix += part + '/'
                sample_dirs.add(prefix)
        write(out / 'sample.json', sample)
        write(out / 'sample-corpus-metadata.json', sample_titles)
        write(out / 'qrels-target-bindings.json', relevant_bindings)
        (out / 'sample-bindings.tsv').write_text(''.join(str(x['global_id']) + '\t' + x['path'] + '\n' for x in sample), encoding='utf-8')
        report = dict(status='passed', started_utc=status['started_utc'], finished_utc=now(),
            scope='Full path/corpus metadata audit; sample corpus vectors; all query vectors. No DSQ/DSM/search/performance run.',
            inputs=before, raw_size_mtime_unchanged=True,
            path_records=count, corpus_records=corpus_count, dimension=dim,
            vector_rows_inferred_from_size=total, full_corpus_vector_integrity_verified=False,
            path_parser=proof, corpus_sha256=corpus_hash.hexdigest(),
            directories_including_root=len(directories), directories_excluding_root=len(directories)-1,
            terminal_directories=len(local_counts),
            mean_directory_depth_excluding_root=sum(directories.values())/(len(directories)-1),
            mean_directory_depth_including_root=sum(directories.values())/len(directories),
            mean_entry_path_depth=sum(k*v for k,v in depths.items())/count,
            entry_depth_histogram=dict(sorted(depths.items())),
            queries=len(qids), query_metadata_empty=sum(x.get('metadata') == {} for x in query_rows),
            query_non_text_fields=query_constraints, query_scope_recovered=False,
            qrels_pairs=len(pairs), qrels_unique_documents=len(relevant), qrels_grades=dict(grades),
            qrels_are_relevance_labels_not_exact_nearest_neighbors=True,
            sample=dict(selection='floor(i*(N-1)/9999), i=0..9999; independent of queries and qrels',
                        records=len(sample), directories_including_root=len(sample_dirs),
                        qrels_documents_in_sample=len(selected & relevant),
                        vectors=sample_vectors), query_vectors=query_vectors,
            small_file_sha256={p.name: sha(p) for p in (query, qvectors, qrels)},
            script_sha256=sha(Path(__file__)), strict_parser_sha256=sha(dependency),
            python=sys.version, executable=sys.executable, numpy=np.__version__, platform=platform.platform(),
            process_peak_working_set_bytes=getattr(psutil.Process().memory_info(), 'peak_wset', None),
            elapsed_seconds=time.monotonic()-started)
        write(out / 'report.json', report)
        status.update(status='passed', finished_utc=now(), elapsed_seconds=report['elapsed_seconds'])
        write(out / 'status.json', status)
        print(json.dumps({k:report[k] for k in ('status','path_records','directories_including_root','mean_directory_depth_excluding_root','elapsed_seconds')}), flush=True)
    except BaseException:
        status.update(status='failed', finished_utc=now(), error=traceback.format_exc())
        write(out / 'status.json', status)
        raise

if __name__ == '__main__':
    main()
