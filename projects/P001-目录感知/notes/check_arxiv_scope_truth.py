"""DATA-01: bounded ARXIV query/GT membership audit, without vector search.

Selects ten queries per file by constraint type/depth before reading GT results.
Streams metadata once, retaining only referenced GT records. All category paths
are preserved. This is a material audit, not PE-Online/Offline/TrieHI code.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from audit_data_01 import json_prefix


def parts(path):
    return tuple(path.strip("/").split("/"))


def match_scope(value, anchor):
    child, parent = parts(value), parts(anchor)
    return child[:len(parent)] == parent


def regex_match_scope(value, anchor):
    # Independent check of segment boundaries using an anchored escaped regex.
    return re.match(r"^" + re.escape(anchor.strip("/")) + r"(?:/|$)", value.strip("/")) is not None


def boundary_checks():
    cases = [
        ("Physics/physics/physics.optics/", "Physics/physics/", True),
        ("Physics/physicsX/", "Physics/physics/", False),
        ("Physics/", "Physics/physics/", False),
        ("Physics/physics/", "Physics/physics/", True),
        ("/a/b/", "/a/", True),
        ("/ab/", "/a/", False),
    ]
    for value, anchor, expected in cases:
        assert match_scope(value, anchor) == regex_match_scope(value, anchor) == expected
    return len(cases)


def choose_queries(constraints, count=10):
    buckets = collections.defaultdict(list)
    for row, query in enumerate(constraints):
        assert query["query_id"] == row
        con = query["constraints"]
        assert len(con) == 1 and set(con) <= {"category", "time"}
        key, value = next(iter(con.items()))
        buckets[(key, len(parts(value)))].append(row)
    selected, level = [], 0
    while len(selected) < count:
        progressed = False
        for key in sorted(buckets):
            if level < len(buckets[key]):
                selected.append(buckets[key][level])
                progressed = True
                if len(selected) == count:
                    break
        if not progressed:
            raise ValueError("Not enough queries")
        level += 1
    return sorted(selected), {f"{key}/{depth}": len(rows) for (key, depth), rows in sorted(buckets.items())}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    out = args.output_dir.resolve()
    if not out.is_relative_to(project / "notes"):
        parser.error("Evidence output must stay under project/notes")
    if out.exists():
        parser.error("Refusing to overwrite an existing evidence directory")
    out.mkdir(parents=True)
    raw = project / "dataset" / "raw" / "ARXIV-Dir"
    start = datetime.now(timezone.utc).isoformat()
    boundary_count = boundary_checks()
    sets, targets, source_paths = {}, set(), []
    for prefix in ("arxiv", "arxiv_category"):
        cpath = raw / f"{prefix}_query_constraint.json"
        constraints = json.loads(cpath.read_text(encoding="utf-8-sig"))
        selected, strata = choose_queries(constraints)
        # Selection is based only on input constraints, never GT outcomes.
        gpath = raw / f"{prefix}_ground_truth.txt"
        gt = [list(map(int, line.split())) for line in gpath.read_text(encoding="utf-8-sig").splitlines()]
        assert len(constraints) == len(gt) == 1000
        cases = []
        for row in selected:
            ids = gt[row]
            assert len(ids) == len(set(ids)) == 100 and all(i >= 0 for i in ids)
            cases.append({"query_row": row, "query_id": constraints[row]["query_id"],
                          "constraints": constraints[row]["constraints"], "ground_truth_ids": ids})
            targets.update(ids)
        sets[prefix] = {"selected_query_rows": selected, "input_strata_counts": strata, "cases": cases}
        source_paths.extend((cpath, gpath))
    manifest = {
        "started_at_utc": start, "argv": sys.argv, "script_sha256": sha256(Path(__file__)),
        "parser_sha256": sha256(Path(__file__).with_name("audit_data_01.py")),
        "selection_rule": "Round-robin over sorted (constraint key, path depth) strata, rows ascending within each; ten per set; no GT-dependent selection",
        "query_row_gt_line_alignment": "GT line number equals query_id; supported by related loader, not the author generation code",
        "selected_queries": {key: [{k: v for k, v in case.items() if k != "ground_truth_ids"} for case in value["cases"]] for key, value in sets.items()},
        "target_unique_ids": len(targets), "target_id_min": min(targets), "target_id_max": max(targets),
        "small_inputs": [{"path": str(p.relative_to(project)), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in source_paths],
        "synthetic_segment_boundary_checks_passed": boundary_count,
    }
    (out / "selection.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path = raw / "arxiv_corpus_metadata.json"
    stat_before = meta_path.stat()
    expected_records, vector_remainder = divmod((raw / "arxiv_corpus_vectors.fvecs").stat().st_size, 4100)
    assert vector_remainder == 0 and max(targets) < expected_records
    found, order_mismatch_count, order_examples, scanned = {}, 0, [], 0
    wanted = set(targets)
    # Bounded memory: retain only metadata for selected 2,000 GT references.
    # Stop after finding the last needed record; do not read any vector file.
    for row, item in enumerate(json_prefix(meta_path, expected_records)):
        scanned = row + 1
        if item.get("id") != row:
            order_mismatch_count += 1
            if len(order_examples) < 5:
                order_examples.append({"row": row, "id": item.get("id")})
        entry_id = item.get("id")
        if entry_id in wanted:
            found[entry_id] = item
            wanted.remove(entry_id)
        if scanned % 500000 == 0:
            print(f"Metadata rows parsed={scanned}; selected IDs still missing={len(wanted)}", flush=True)
        if not wanted:
            break
    print(f"Metadata scan ended at row count={scanned}; selected IDs found={len(found)}", flush=True)
    all_refs, totals = [], collections.Counter()
    for prefix, group in sets.items():
        for case in group["cases"]:
            key, anchor = next(iter(case["constraints"].items()))
            counters = collections.Counter()
            bad_examples, descendant_examples, secondary_examples = [], [], []
            for rank, entry_id in enumerate(case["ground_truth_ids"], start=1):
                if entry_id not in found:
                    counters["missing_metadata"] += 1
                    continue
                item = found[entry_id]
                assert isinstance(item.get("categories"), list) and isinstance(item.get("time"), str)
                paths = item["categories"] if key == "category" else [item["time"]]
                matching = [p for p in paths if match_scope(p, anchor)]
                assert matching == [p for p in paths if regex_match_scope(p, anchor)]
                exact = [p for p in paths if parts(p) == parts(anchor)]
                recursive, direct = bool(matching), bool(exact)
                first_only_loses_match = key == "category" and recursive and not match_scope(paths[0], anchor)
                counters["checked_gt_references"] += 1
                counters["recursive_matches"] += int(recursive)
                counters["direct_matches"] += int(direct)
                counters["descendant_only_matches"] += int(recursive and not direct)
                counters["recursive_violations"] += int(not recursive)
                counters["multi_category_references"] += int(len(item["categories"]) > 1)
                counters["first_category_only_would_lose_match"] += int(first_only_loses_match)
                ref = {"dataset": prefix, "query_row": case["query_row"], "gt_rank": rank,
                       "entry_id": entry_id, "constraint_type": key, "anchor": anchor,
                       "recursive_match": recursive, "direct_match": direct,
                       "matching_paths": matching, "first_category_only_would_lose_match": first_only_loses_match,
                       "metadata": item}
                all_refs.append(ref)
                example = {k: ref[k] for k in ("entry_id", "matching_paths", "metadata")}
                if not recursive and len(bad_examples) < 3:
                    bad_examples.append(example)
                if recursive and not direct and len(descendant_examples) < 2:
                    descendant_examples.append(example)
                if first_only_loses_match and len(secondary_examples) < 2:
                    secondary_examples.append(example)
            case["constraint_type"] = key
            case["anchor_depth"] = len(parts(anchor))
            case["counts"] = dict(counters)
            case["examples"] = {"violations": bad_examples, "descendant_only": descendant_examples,
                                "lost_if_first_category_only": secondary_examples}
            totals.update(counters)
    stat_after = meta_path.stat()
    unique_meta_multicategory = sum(len(item["categories"]) > 1 for item in found.values())
    summary = {
        "started_at_utc": start, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "20 query scope/GT-membership audit only; no vector read, no corpus nearest-neighbor search, no maintenance or timing benchmark",
        "metadata_scan": {"file": str(meta_path.relative_to(project)), "bytes_total": stat_before.st_size,
                          "records_parsed": scanned, "target_unique_ids": len(targets), "found": len(found),
                          "missing_ids": sorted(wanted), "row_id_mismatch_count_in_scanned_prefix": order_mismatch_count,
                          "row_id_mismatch_examples": order_examples,
                          "size_and_mtime_unchanged": (stat_before.st_size, stat_before.st_mtime_ns) == (stat_after.st_size, stat_after.st_mtime_ns),
                          "full_file_integrity_checked": False},
        "retained_unique_metadata_multicategory_records": unique_meta_multicategory,
        "totals": dict(totals), "sets": sets,
        "status": "checks completed" if not wanted else "incomplete: missing target metadata",
    }
    with (out / "references.jsonl").open("w", encoding="utf-8") as handle:
        for ref in all_refs:
            handle.write(json.dumps(ref, ensure_ascii=False) + "\n")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "totals": summary["totals"],
                      "unique_metadata_records": len(found), "unique_multicategory_records": unique_meta_multicategory}, indent=2))
    if wanted:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
