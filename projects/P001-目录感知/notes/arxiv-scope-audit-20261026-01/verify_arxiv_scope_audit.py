"""Independent checks and structural interpretation diagnostics for DATA-01.

Reads only the saved small evidence; never opens raw corpus/vector files.
"""
import collections
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notes" / "arxiv-scope-audit-20261026-01"
summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
selection = json.loads((OUT / "selection.json").read_text(encoding="utf-8"))
refs = [json.loads(line) for line in (OUT / "references.jsonl").read_text(encoding="utf-8").splitlines()]
assert len(refs) == 2000
cases = {(key, case["query_row"]): case for key, value in summary["sets"].items() for case in value["cases"]}
per_case = collections.defaultdict(list)
by_id = collections.defaultdict(list)
metadata = {}
independent_mismatches = []
for ref in refs:
    per_case[(ref["dataset"], ref["query_row"])].append(ref)
    by_id[ref["entry_id"]].append({"dataset": ref["dataset"], "query_row": ref["query_row"],
                                   "type": ref["constraint_type"], "anchor": ref["anchor"]})
    if ref["entry_id"] in metadata:
        assert metadata[ref["entry_id"]] == ref["metadata"]
    metadata[ref["entry_id"]] = ref["metadata"]
    paths = ref["metadata"]["categories"] if ref["constraint_type"] == "category" else [ref["metadata"]["time"]]
    anchor = ref["anchor"].strip("/")
    matcher = re.compile("^" + re.escape(anchor) + r"(?:/|$)")
    recur = any(matcher.match(path.strip("/")) for path in paths)
    direct = any(path.strip("/") == anchor for path in paths)
    if recur != ref["recursive_match"] or direct != ref["direct_match"]:
        independent_mismatches.append({"dataset": ref["dataset"], "query_row": ref["query_row"], "entry_id": ref["entry_id"]})
for key, rows in per_case.items():
    assert len(rows) == 100
    assert [r["entry_id"] for r in rows] == cases[key]["ground_truth_ids"]
    assert sum(r["recursive_match"] for r in rows) == cases[key]["counts"]["recursive_matches"]
    assert sum(r["direct_match"] for r in rows) == cases[key]["counts"]["direct_matches"]
assert len(cases) == len(per_case) == 20
assert not independent_mismatches
assert hashlib.sha256((ROOT / "notes" / "check_arxiv_scope_truth.py").read_bytes()).hexdigest() == selection["script_sha256"]

overlap_count = 0
overlap_examples = []
for entry_id, item in sorted(metadata.items()):
    paths = item["categories"]
    pairs = [(a, b) for a in paths for b in paths if a != b and b.strip("/").startswith(a.strip("/") + "/")]
    if pairs:
        overlap_count += 1
        if len(overlap_examples) < 5:
            overlap_examples.append({"entry_id": entry_id, "ancestor_descendant_path_pairs": pairs, "metadata": item})
groups = {}
for dataset, _ in cases:
    rows = [r for r in refs if r["dataset"] == dataset]
    groups[dataset] = {"queries": len([key for key in cases if key[0] == dataset]),
                       "gt_references": len(rows), "recursive_matches": sum(r["recursive_match"] for r in rows),
                       "direct_matches": sum(r["direct_match"] for r in rows),
                       "descendant_only_matches": sum(r["recursive_match"] and not r["direct_match"] for r in rows),
                       "lost_if_first_category_only": sum(r["first_category_only_would_lose_match"] for r in rows)}
result = {
    "status": "pass", "verified_cases": len(cases), "verified_gt_references": len(refs),
    "independent_regex_check_mismatches": independent_mismatches,
    "counts_and_order_match_summary": True, "script_hash_matches_record": True,
    "per_set": groups,
    "unique_metadata_records": len(metadata),
    "unique_records_with_ancestor_and_descendant_category_paths": overlap_count,
    "ancestor_descendant_examples": overlap_examples,
    "repeated_ids_across_selected_cases": [{"entry_id": entry_id, "cases": values, "metadata": metadata[entry_id]}
                                            for entry_id, values in by_id.items() if len(values) > 1],
    "limits": "Verification of membership and evidence only; no closest-neighbor, completeness, or DSM validation",
}
output = OUT / "verification.json"
if output.exists():
    raise FileExistsError("Refusing to overwrite verification evidence")
output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
