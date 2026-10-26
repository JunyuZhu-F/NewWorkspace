"""Bounded, read-only DATA-01 checks. This is not a DSQ/DSM implementation.

Only the first --metadata-limit records of large JSON/JSONL files are parsed.
Small query/ground-truth files are read completely. Corpus vectors are sampled
at deterministic offsets; query vectors are checked completely. Raw files are
never opened for writing. No retrieval, timing benchmark, or ANN is performed.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import platform
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def json_prefix(path: Path, limit: int):
    """Incrementally parse a prefix of a JSON array using bounded buffers."""
    decoder = json.JSONDecoder()
    with path.open(encoding="utf-8-sig") as handle:
        buf, pos, eof, started, count = "", 0, False, False, 0
        while count < limit:
            if pos >= len(buf):
                buf = handle.read(1 << 20)
                pos = 0
                if not buf:
                    return
            while pos < len(buf) and buf[pos].isspace():
                pos += 1
            if pos >= len(buf):
                continue
            if not started:
                if buf[pos] != "[":
                    raise ValueError(f"Expected JSON array: {path}")
                pos += 1
                started = True
                continue
            if buf[pos] == "]":
                return
            if buf[pos] == ",":
                pos += 1
                continue
            try:
                value, end = decoder.raw_decode(buf, pos)
            except json.JSONDecodeError:
                if eof:
                    raise
                more = handle.read(1 << 20)
                eof = not more
                buf, pos = buf[pos:] + more, 0
                continue
            pos = end
            count += 1
            yield value


def vector_check(path: Path, all_rows: bool, samples: int = 257):
    size = path.stat().st_size
    with path.open("rb") as handle:
        first = handle.read(4)
        if len(first) != 4:
            raise ValueError(f"Missing dimension: {path}")
        dim = struct.unpack("<i", first)[0]
        if not 0 < dim <= 16384:
            raise ValueError(f"Invalid dimension {dim}: {path}")
        width = 4 + 4 * dim
        n, remainder = divmod(size, width)
        if n < 1:
            raise ValueError(f"No complete vector records: {path}")
        indices = list(range(n)) if all_rows else sorted(
            set(range(min(n, 8))) | {i * (n - 1) // (samples - 1) for i in range(samples)}
        )
        bad_dims, nonfinite, zeros, norms, norm_rows = [], [], [], [], []
        for row in indices:
            handle.seek(row * width)
            record = handle.read(width)
            if len(record) != width:
                raise ValueError(f"Truncated row {row}: {path}")
            actual = struct.unpack_from("<i", record)[0]
            if actual != dim:
                bad_dims.append({"row": row, "dimension": actual})
            vec = np.frombuffer(record, dtype="<f4", offset=4)
            if not np.isfinite(vec).all():
                nonfinite.append(row)
            else:
                norm = float(np.linalg.norm(vec.astype(np.float64)))
                norms.append(norm)
                norm_rows.append(row)
                if norm == 0:
                    zeros.append(row)
    return {
        "bytes": size, "first_dimension": dim,
        "inferred_fixed_width_records": n, "remainder_bytes": remainder,
        "coverage": "all query records" if all_rows else "deterministic corpus samples only",
        "checked_records": len(indices), "sample_indices": indices,
        "bad_dimensions": bad_dims, "nonfinite_rows": nonfinite, "zero_norm_rows": zeros,
        "l2_norm": {"min": min(norms), "max": max(norms), "mean": sum(norms) / len(norms),
                    "min_row": norm_rows[int(np.argmin(norms))], "max_row": norm_rows[int(np.argmax(norms))],
                    "within_0_001_of_one": sum(abs(v - 1) <= 0.001 for v in norms)},
        "all_dimensions_verified": all_rows and not bad_dims and remainder == 0,
    }


def path_stats(paths):
    depths, prefixes, malformed = [], set(), []
    for raw in paths:
        segments = [s for s in raw.split("/") if s]
        depths.append(len(segments))
        if "//" in raw or any(s in (".", "..") for s in segments) or not raw.endswith("/"):
            if len(malformed) < 8:
                malformed.append(raw)
        for i in range(1, len(segments) + 1):
            prefixes.add("/".join(segments[:i]))
    return {
        "path_count": len(depths), "unique_nonroot_prefixes_in_sample": len(prefixes),
        "depth_min": min(depths), "depth_max": max(depths),
        "mean_depth_per_sample_entry": sum(depths) / len(depths),
        "suspicious_examples": malformed,
        "warning": "Sample/entry-weighted statistics; not comparable to full directory-weighted paper averages",
    }


def read_gt(path: Path, n: int):
    rows, bad_ids, duplicates = [], [], []
    with path.open(encoding="utf-8-sig") as handle:
        for row, line in enumerate(handle):
            ids = [int(s) for s in line.split()]
            rows.append(ids)
            if len(set(ids)) != len(ids):
                duplicates.append(row)
            if any(i < 0 or i >= n for i in ids):
                bad_ids.append(row)
    return rows, {
        "rows": len(rows), "ids_per_row_histogram": dict(collections.Counter(map(len, rows))),
        "out_of_range_rows": bad_ids, "duplicate_id_rows": duplicates,
        "alignment_status": "line index equals query_id is a hypothesis, not established by format alone",
    }


def arxiv_check(root: Path, limit: int, n: int):
    meta_path = root / "arxiv_corpus_metadata.json"
    meta = list(json_prefix(meta_path, limit))
    ids = [item["id"] for item in meta]
    by_id = {item["id"]: item for item in meta}
    cardinalities = collections.Counter(len(item.get("categories", [])) for item in meta)
    examples = [item for item in meta if len(item.get("categories", [])) > 1][:5]
    result = {
        "metadata_coverage": {"mode": "prefix only", "records": len(meta), "limit": limit,
                              "full_file_integrity_checked": False},
        "id_matches_zero_based_row_in_prefix": ids == list(range(len(meta))),
        "duplicate_ids_in_prefix": len(ids) - len(set(ids)),
        "fields_in_prefix": sorted({key for item in meta for key in item}),
        "categories_per_entry_histogram": dict(cardinalities), "multi_category_examples": examples,
        "category_paths": path_stats([p for item in meta for p in item.get("categories", [])]),
        "time_paths": path_stats([item["time"] for item in meta]),
        "query_sets": {},
    }
    for prefix in ("arxiv", "arxiv_category"):
        constraint_path = root / f"{prefix}_query_constraint.json"
        constraints = json.loads(constraint_path.read_text(encoding="utf-8-sig"))
        gt, gt_result = read_gt(root / f"{prefix}_ground_truth.txt", n)
        query_ids = [q["query_id"] for q in constraints]
        checked, violations, direct_matches, examples_bad = 0, 0, 0, []
        for row, truth in enumerate(gt):
            if row >= len(constraints):
                break
            con = constraints[row]["constraints"]
            for entry_id in truth:
                if entry_id not in by_id:
                    continue
                item = by_id[entry_id]
                checked += 1
                legal, direct = True, True
                for key, target in con.items():
                    values = item["categories"] if key == "category" else [item["time"]]
                    target_parts = target.strip("/").split("/")
                    value_parts = [p.strip("/").split("/") for p in values]
                    legal &= any(p[:len(target_parts)] == target_parts for p in value_parts)
                    direct &= any(p == target_parts for p in value_parts)
                direct_matches += int(direct)
                if not legal:
                    violations += 1
                    if len(examples_bad) < 5:
                        examples_bad.append({"query_row": row, "entry_id": entry_id,
                                             "constraints": con, "metadata": item})
        result["query_sets"][prefix] = {
            "queries": len(constraints), "query_ids_match_zero_based_order": query_ids == list(range(len(constraints))),
            "constraint_keys": dict(collections.Counter(k for q in constraints for k in q["constraints"])),
            "query_top_level_fields": sorted({k for q in constraints for k in q}),
            "ground_truth": gt_result,
            "sampled_metadata_gt_check": {"assumption": "GT line row corresponds to constraints[row]",
                "checked_references": checked, "recursive_scope_violations": violations,
                "exact_parent_matches": direct_matches, "violation_examples": examples_bad,
                "coverage_note": "Only GT references whose metadata occurs in the inspected prefix; no exact-neighbor recomputation"},
        }
    return result


def wiki_check(root: Path, limit: int, n: int):
    paths = list(json_prefix(root / "dbpedia_dir_2m_corpus_paths.json", limit))
    corpus_ids, fields = [], set()
    with (root / "dbpedia_dir_2m_corpus.jsonl").open(encoding="utf-8-sig") as handle:
        for i, line in enumerate(handle):
            if i >= limit:
                break
            item = json.loads(line)
            corpus_ids.append(item["_id"])
            fields.update(item)
    with (root / "dbpedia_dir_2m_query.jsonl").open(encoding="utf-8-sig") as handle:
        queries = [json.loads(line) for line in handle if line.strip()]
    qids = {q["_id"] for q in queries}
    qrel_queries, score_counts = set(), collections.Counter()
    bad_doc_rows, bad_query_rows, pairs, duplicate_pairs = [], [], set(), 0
    qrels_rows = 0
    with (root / "dbpedia_dir_2m_groundtruth.tsv").open(encoding="utf-8-sig") as handle:
        header = handle.readline().strip().split("\t")
        if header != ["query-id", "corpus-id", "score"]:
            raise ValueError(f"Unexpected WIKI qrels header: {header}")
        for row, line in enumerate(handle, start=2):
            qid, doc, score = map(int, line.split())
            qrels_rows += 1
            qrel_queries.add(qid)
            score_counts[score] += 1
            if qid not in qids:
                bad_query_rows.append(row)
            if not 0 <= doc < n:
                bad_doc_rows.append(row)
            if (qid, doc) in pairs:
                duplicate_pairs += 1
            pairs.add((qid, doc))
    path_ids = [p["id"] for p in paths]
    return {
        "metadata_coverage": {"mode": "prefix only", "records": len(paths), "limit": limit,
                              "full_file_integrity_checked": False},
        "paths_id_matches_zero_based_row_in_prefix": path_ids == list(range(len(paths))),
        "corpus_id_matches_zero_based_row_in_prefix": corpus_ids == list(range(len(corpus_ids))),
        "paths_corpus_prefix_id_alignment": path_ids == corpus_ids,
        "path_fields_in_prefix": sorted({k for item in paths for k in item}),
        "corpus_fields_in_prefix": sorted(fields),
        "paths": path_stats([item["path"] for item in paths]),
        "queries": {"count": len(queries), "ids_match_zero_based_order": [q["_id"] for q in queries] == list(range(len(queries))),
                    "nonempty_metadata": sum(bool(q.get("metadata")) for q in queries),
                    "fields": sorted({k for q in queries for k in q})},
        "qrels": {"rows": qrels_rows, "queries_with_labels": len(qrel_queries),
                  "queries_without_labels": sorted(qids - qrel_queries), "score_histogram": dict(score_counts),
                  "unknown_query_rows": bad_query_rows, "out_of_range_doc_rows": bad_doc_rows,
                  "duplicate_query_doc_pairs": duplicate_pairs,
                  "note": "Relevance judgments, not automatically exact vector neighbors or directory-scoped ground truth"},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata-limit", type=int, default=10000)
    args = parser.parse_args()
    if not 1 <= args.metadata_limit <= 10000:
        parser.error("metadata-limit must be between 1 and 10000")
    if args.output.exists():
        parser.error("Refusing to overwrite an existing audit output")
    root = args.project.resolve()
    raw = root / "dataset" / "raw"
    files = sorted(p for folder in (raw / "WIKI-Dir", raw / "ARXIV-Dir") for p in folder.iterdir() if p.is_file())
    before = {str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns) for p in files}
    result = {"started_at_utc": datetime.now(timezone.utc).isoformat(),
              "command_argv": sys.argv, "python": sys.version, "python_executable": sys.executable,
              "numpy": np.__version__, "platform": platform.platform(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scope": "Bounded data audit only; no DSQ/DSM implementation, retrieval or performance benchmark",
              "vectors": {}}
    for path in files:
        if path.suffix == ".fvecs":
            print(f"Checking vector headers/samples: {path.name}", flush=True)
            result["vectors"][str(path.relative_to(root))] = vector_check(path, "query" in path.name)
    print("Checking ARXIV metadata prefix and small query/GT files", flush=True)
    arxiv_n = result["vectors"][str((raw / "ARXIV-Dir" / "arxiv_corpus_vectors.fvecs").relative_to(root))]["inferred_fixed_width_records"]
    result["arxiv"] = arxiv_check(raw / "ARXIV-Dir", args.metadata_limit, arxiv_n)
    print("Checking WIKI metadata prefix and small query/qrels files", flush=True)
    wiki_n = result["vectors"][str((raw / "WIKI-Dir" / "dbpedia_dir_2m_corpus_vectors-001.fvecs").relative_to(root))]["inferred_fixed_width_records"]
    result["wiki"] = wiki_check(raw / "WIKI-Dir", args.metadata_limit, wiki_n)
    after = {str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns) for p in files}
    result["raw_size_and_mtime_unchanged"] = before == after
    result["full_corpus_vector_integrity_checked"] = False
    result["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved audit: {args.output}", flush=True)


if __name__ == "__main__":
    main()
