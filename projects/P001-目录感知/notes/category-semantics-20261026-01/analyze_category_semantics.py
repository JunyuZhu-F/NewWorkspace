"""DATA/SPEC category interpretation audit on saved metadata only.

No raw dataset write, no vector read, no index implementation, no DSM run.
"""
from __future__ import annotations
import collections
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'notes/category-semantics-20261026-01'
INPUT = ROOT / 'notes/arxiv-scope-audit-20261026-01/references.jsonl'
OUTPUT = OUT / 'analysis.json'


def split_path(path):
    clean = path.strip('/')
    return tuple(clean.split('/')) if clean else ()


def maximal_paths(paths):
    unique = set(paths)
    return {p for p in unique if not any(len(q) > len(p) and q[:len(p)] == p for q in unique)}


def ancestor_closure(paths):
    return {p[:depth] for p in paths for depth in range(len(p) + 1)}


def as_path(parts):
    return '/' + '/'.join(parts) + ('/' if parts else '')


def main():
    if OUTPUT.exists():
        raise FileExistsError('Refusing to overwrite category evidence')
    source = Path(__file__).read_bytes()
    source_hash = hashlib.sha256(source).hexdigest()
    records = {}
    for line in INPUT.read_text(encoding='utf-8').splitlines():
        ref = json.loads(line)
        item = ref['metadata']
        if item['id'] in records:
            assert records[item['id']] == item
        records[item['id']] = item
    raw_hist, maximal_hist = collections.Counter(), collections.Counter()
    removed_labels, affected_records, still_multi, equal_closures = 0, 0, 0, 0
    differing_examples = []
    for entry_id, item in sorted(records.items()):
        raw = {split_path(p) for p in item['categories']}
        leaves = maximal_paths(raw)
        assert raw and leaves
        raw_hist[len(raw)] += 1
        maximal_hist[len(leaves)] += 1
        removed = raw - leaves
        removed_labels += len(removed)
        affected_records += bool(removed)
        still_multi += len(leaves) > 1
        # Equality covers every possible prefix anchor, not just selected queries.
        assert ancestor_closure(raw) == ancestor_closure(leaves)
        equal_closures += 1
        if removed and len(differing_examples) < 5:
            differing_examples.append({'entry_id': entry_id,
                'raw_paths': sorted(as_path(p) for p in raw),
                'maximal_path_view': sorted(as_path(p) for p in leaves),
                'anchors_with_different_direct_membership': sorted(as_path(p) for p in removed)})
    # Independently verify the closure identity exhaustively on a tiny domain.
    domain = [('a',), ('a','x'), ('a','x','z'), ('a','y'), ('b',), ('b','x')]
    finite_checks = 0
    for mask in range(1, 1 << len(domain)):
        subset = {domain[i] for i in range(len(domain)) if mask & (1 << i)}
        leaves = maximal_paths(subset)
        for anchor in [()] + domain + [('ab',), ('a','missing')]:
            by_prefix = any(p[:len(anchor)] == anchor for p in subset)
            by_leaf_prefix = any(p[:len(anchor)] == anchor for p in leaves)
            assert by_prefix == by_leaf_prefix
            finite_checks += 1
    # A labelled logical example; not an execution of any paper DSM strategy.
    example = records[249848]
    old = {split_path(p) for p in example['categories']}
    src, old_ancestor, new_binding = split_path('Physics/gr-qc/'), ('Physics',), ('Mathematics','gr-qc')
    assert src in old
    after = (old - {src}) | {new_binding}
    before_contains = any(p[:1] == old_ancestor for p in old)
    expected_after_contains = any(p[:1] == old_ancestor for p in after)
    remove_whole_payload_from_old_ancestor = False
    assert before_contains and expected_after_contains
    tree = json.loads((OUT / 'dataset-repository-tree.json').read_text(encoding='utf-8-sig'))
    issues = json.loads((OUT / 'dataset-repository-issues.json').read_text(encoding='utf-8-sig'))
    result = {
        'started_and_completed_date_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Saved selected GT metadata only; alternative interpretations analysed in memory, not applied to raw data',
        'input_path': str(INPUT.relative_to(ROOT)), 'input_sha256': hashlib.sha256(INPUT.read_bytes()).hexdigest(),
        'script_sha256': source_hash, 'unique_records': len(records),
        'raw_distinct_paths_per_record_histogram': dict(raw_hist),
        'maximal_paths_per_record_histogram': dict(maximal_hist),
        'records_with_raw_ancestor_labels': affected_records,
        'raw_ancestor_labels_removed_in_hypothetical_view': removed_labels,
        'records_still_multibranch_in_maximal_path_view': still_multi,
        'records_with_equal_recursive_anchor_closures': equal_closures,
        'finite_synthetic_prefix_checks': finite_checks,
        'direct_membership_difference_examples': differing_examples,
        'logical_move_example': {'entry_id': example['id'], 'original_metadata': example,
            'assumption': 'Every listed path represents an independent direct membership of the same payload ID',
            'move_binding_from': as_path(src), 'move_binding_to': as_path(new_binding),
            'old_ancestor': as_path(old_ancestor), 'expected_payload_still_in_old_ancestor': expected_after_contains,
            'naive_remove_entire_payload_would_retain_it': remove_whole_payload_from_old_ancestor,
            'status': 'Conditional logical counterexample, not a measured failure of paper code'},
        'bounded_source_check': {'dataset_repo_fixed_tree_paths': [i['path'] for i in tree['tree']],
                                'issues_returned': len(issues), 'posted_messages': 0},
        'interpretation_status': 'Recursive observations cannot identify direct memberships; author construction/catalog/DSM protocol remains unresolved',
        'raw_data_modified': False,
    }
    (OUT / 'analyze_category_semantics.py').write_bytes(source)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('unique_records','records_with_raw_ancestor_labels','raw_ancestor_labels_removed_in_hypothetical_view','records_still_multibranch_in_maximal_path_view','records_with_equal_recursive_anchor_closures','finite_synthetic_prefix_checks','bounded_source_check')},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
