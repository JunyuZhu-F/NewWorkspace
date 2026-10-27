"""Run frozen small-data SEARCH-01 admission with recoverable per-command records.

Run from project root, e.g. python code/search/validate.py --output notes/search01-validation-YYYYMMDD-NN
Never replaces existing evidence. Does not run SEARCH-02 timing experiments.
"""
import argparse
import hashlib
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=pathlib.Path, required=True)
    ap.add_argument('--resume-prepared', action='store_true', help='Only for registered fixture with no backend output; preserves earlier build/prepare logs')
    args = ap.parse_args()
    project = pathlib.Path.cwd()
    out = args.output
    if args.resume_prepared:
        assert (out / 'run-status.json').is_file() and (out / 'fixture/manifest.json').is_file()
        assert not (out / 'release').exists() and not (out / 'asan').exists()
        assert not (out / 'commands.jsonl').exists()
    else:
        out.mkdir(parents=True, exist_ok=False)
    (out / '.gitignore').write_text('fixture/*.fvecs\n', encoding='utf-8')
    status_path = out / 'run-status.json'
    old_registration = json.loads(status_path.read_text(encoding='utf-8')) if status_path.exists() else None
    sources = list((project / 'code/search').glob('*.py')) + list((project / 'code/search').glob('*.cpp')) + [project / 'code/search/CMakeLists.txt', project / 'code/scripts/build-search.cmd', project / 'notes/search01-protocol-20261027.md']
    old_sources = json.loads((project / 'notes/cost02-preparation-20261027-01/source-hashes.json').read_text(encoding='utf-8'))['files']
    for name, h in old_sources.items():
        assert digest(project / name) == h, f'Frozen COST02 source changed: {name}'
    source_dir = out / 'source'
    source_dir.mkdir(exist_ok=False)
    for p in sources:
        dest = source_dir / p.relative_to(project)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dest)
    source_hashes = {p.relative_to(project).as_posix(): digest(p) for p in sources}
    (out / 'source-hashes.json').write_text(json.dumps(dict(new_sources=source_hashes, unchanged_core=old_sources), indent=2), encoding='utf-8')
    (out / 'git-diff.patch').write_bytes(subprocess.check_output(['git', 'diff', '--binary', '--', '.']))
    state = dict(status='running', started_utc=datetime.now(timezone.utc).isoformat(), git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(), git_status=subprocess.check_output(['git', 'status', '--short'], text=True), platform=platform.platform(), python=sys.version, previous_registration=old_registration, commands_completed=0, formal_performance=False)
    def persist():
        status_path.write_text(json.dumps(state, indent=2), encoding='utf-8')
    persist()
    # Record actual commands/exit codes, including failures/timeouts, before rethrowing.
    def run(label, command, timeout=600):
        event = dict(label=label, command=command, cwd=str(project), started_utc=datetime.now(timezone.utc).isoformat())
        start = time.perf_counter()
        try:
            with (out / (label + '.log')).open('xb') as log:
                completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False)
            event['exit_code'] = completed.returncode
            if completed.returncode:
                raise RuntimeError(f'{label}: exit {completed.returncode}; see saved log')
        except BaseException as error:
            event['error'] = repr(error)
            raise
        finally:
            event['finished_utc'] = datetime.now(timezone.utc).isoformat()
            event['elapsed_seconds_validation_only'] = time.perf_counter() - start
            with (out / 'commands.jsonl').open('a', encoding='utf-8') as log:
                log.write(json.dumps(event) + '\n')
        state['commands_completed'] += 1
        persist()
        print(json.dumps(dict(label=label, status='passed')), flush=True)
    try:
        if not args.resume_prepared:
            run('build-release', ['cmd.exe', '/d', '/c', 'code\\scripts\\build-search.cmd'])
            run('prepare', [sys.executable, 'code/search/prepare.py', '--project', '.', '--output', str(out / 'fixture')])
        run('build-asan', ['cmd.exe', '/d', '/c', 'code\\scripts\\build-search.cmd', 'asan'])
        for build, label in [('Release-Search', 'release'), ('RelWithDebInfo-ASan-Search', 'asan')]:
            run(label + '-run', [f'code/build-{build}/directory_search.exe', str(out / 'fixture'), str(out / label)])
        run('verify', [sys.executable, 'code/search/verify.py', '--project', '.', '--fixture', str(out / 'fixture'), '--outputs', str(out / 'release'), str(out / 'asan'), '--report', str(out / 'verification.json')])
        for name, h in source_hashes.items():
            assert digest(project / name) == h and digest(source_dir / name) == h
        for name, h in old_sources.items():
            assert digest(project / name) == h
        state['binary_hashes'] = {name: digest(project / f'code/build-{name}/directory_search.exe') for name in ('Release-Search', 'RelWithDebInfo-ASan-Search')}
        state['old_core_files_unchanged'] = len(old_sources)
        state['status'] = 'passed'
    except BaseException as error:
        state['status'] = 'failed'
        state['error'] = repr(error)
        raise
    finally:
        state['finished_utc'] = datetime.now(timezone.utc).isoformat()
        persist()


if __name__ == '__main__':
    main()
