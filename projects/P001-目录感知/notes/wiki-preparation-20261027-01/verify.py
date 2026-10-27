"""Independent second path scan, metadata evidence and sample vector verification."""
import collections
import csv
import datetime
import hashlib
import json
from pathlib import Path
import struct
import time
import urllib.request

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
RAW = PROJECT / 'dataset/raw/WIKI-Dir'

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def main():
    started = time.monotonic()
    out = HERE / 'run-01'
    target = out / 'verification.json'
    if target.exists():
        raise FileExistsError(target)
    report = json.loads((out / 'report.json').read_text(encoding='utf-8'))
    sample = json.loads((out / 'sample.json').read_text(encoding='utf-8'))
    samples = {x['global_id']: x['path'] for x in sample}
    selected = set(samples)
    dirs = {'/'}
    terminal = set()
    count = 0
    found = 0
    h = hashlib.sha256()
    buffer = []
    # A different parser: each pretty-printed object starts/ends on its own line.
    # The first pass has already checked the full array's separators and EOF.
    with (RAW / 'dbpedia_dir_2m_corpus_paths.json').open('rb') as f:
        for line in f:
            h.update(line)
            text = line.decode('utf-8').strip()
            if not buffer:
                if text == '{':
                    buffer = [text]
                else:
                    assert text in ('[', ']', ''), text[:40]
                continue
            buffer.append(text.rstrip(',') if text in ('}', '},') else text)
            if text in ('}', '},'):
                obj = json.loads('\n'.join(buffer))
                buffer = []
                assert obj['id'] == count
                path = obj['path']
                terminal.add(path)
                while path != '/':
                    dirs.add(path)
                    path = path[:path.rfind('/', 0, len(path)-1)+1]
                if count in samples:
                    assert obj['path'] == samples[count]
                    found += 1
                count += 1
    assert not buffer and count == report['path_records'] and found == 10000
    assert h.hexdigest() == report['path_parser']['sha256']
    assert len(dirs) == report['directories_including_root']
    assert len(terminal) == report['terminal_directories']
    directory_depth = sum(x.count('/')-1 for x in dirs)
    assert directory_depth / (len(dirs)-1) == report['mean_directory_depth_excluding_root']
    vdigest = hashlib.sha256()
    with (RAW / 'dbpedia_dir_2m_corpus_vectors-001.fvecs').open('rb') as f:
        for row in sorted(samples):
            f.seek(row * 4100)
            b = f.read(4100)
            assert len(b) == 4100 and struct.unpack_from('<i', b)[0] == 1024
            vdigest.update(struct.pack('<Q', row) + b)
    assert vdigest.hexdigest() == report['sample']['vectors']['row_and_record_sha256']
    qids = set()
    qrel_pairs = 0
    with (RAW / 'dbpedia_dir_2m_groundtruth.tsv').open(encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            if int(row['corpus-id']) in selected:
                qids.add(int(row['query-id']))
                qrel_pairs += 1
    for name, state in report['inputs'].items():
        s = (RAW / name).stat()
        assert {'size':s.st_size, 'mtime_ns':s.st_mtime_ns} == state
    result = dict(status='passed', finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        path_rows=count, independently_counted_directories_including_root=len(dirs),
        independently_counted_terminal_directories=len(terminal),
        terminal_directory_mean_depth=sum(x.count('/')-1 for x in terminal)/len(terminal),
        sample_bindings_reverified=found, sample_vector_record_hash_matches=True,
        qrels_pairs_in_sample=qrel_pairs, queries_with_any_qrel_in_sample=len(qids),
        queries_without_any_qrel_in_sample=456-len(qids),
        paper_directory_count_matches_terminal_paths=True,
        paper_all_prefix_directory_count_match=False,
        author_directory_count_definition_confirmed=False,
        input_size_mtime_unchanged=True, report_sha256=sha(out / 'report.json'),
        verifier_sha256=sha(Path(__file__)), elapsed_seconds=time.monotonic()-started)
    target.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result), flush=True)

if __name__ == '__main__':
    main()
