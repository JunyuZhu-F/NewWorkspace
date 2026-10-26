"""Small diagnostic: check listed-GT order under three distance candidates.

Reads ten fixed queries per set and their 100 listed GT vectors only. This
does not search the corpus, prove exact top-k, report recall, or time retrieval.
"""
import hashlib
import json
import os
import struct
from pathlib import Path

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "dataset" / "raw" / "ARXIV-Dir"
OUT = ROOT / "notes" / "data-audit-20261026-01" / "gt-distance-order.json"
ROWS = [0, 1, 2, 3, 4, 127, 255, 511, 767, 999]


def read_vector(handle, row):
    handle.seek(row * 4100)
    data = handle.read(4100)
    assert len(data) == 4100 and struct.unpack_from("<i", data)[0] == 1024
    values = np.frombuffer(data, dtype="<f4", offset=4).astype(np.float64)
    assert np.isfinite(values).all()
    return values


result = {"query_rows": ROWS, "scope": "Order consistency within provided 100 GT IDs only; not a corpus search",
          "tolerance": "adjacent inversion if later score > former + 1e-7 * max(1, abs(former), abs(later))",
          "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "sets": {}}
with (RAW / "arxiv_corpus_vectors.fvecs").open("rb") as corpus:
    for prefix in ("arxiv", "arxiv_category"):
        gt = [list(map(int, line.split())) for line in (RAW / f"{prefix}_ground_truth.txt").read_text().splitlines()]
        rows = []
        with (RAW / f"{prefix}_query_vectors.fvecs").open("rb") as queries:
            for row in ROWS:
                q = read_vector(queries, row)
                x = np.stack([read_vector(corpus, entry_id) for entry_id in gt[row]])
                inner = x @ q
                cosine = inner / (np.linalg.norm(x, axis=1) * np.linalg.norm(q))
                negative_l2 = -np.sum((x - q) ** 2, axis=1)
                metrics = {}
                for name, scores in (("inner_product", inner), ("cosine", cosine), ("negative_squared_l2", negative_l2)):
                    tolerance = 1e-7 * np.maximum(1, np.maximum(np.abs(scores[:-1]), np.abs(scores[1:])))
                    metrics[name] = {"adjacent_order_inversions": int(np.count_nonzero(np.diff(scores) > tolerance)),
                                     "listed_first_rank_among_listed_ids": int(np.count_nonzero(scores > scores[0] + 1e-7)) + 1}
                rows.append({"query_row": row, "listed_first_id": gt[row][0], "metrics": metrics})
        result["sets"][prefix] = {
            "rows": rows,
            "total_adjacent_inversions": {metric: sum(r["metrics"][metric]["adjacent_order_inversions"] for r in rows) for metric in ("inner_product", "cosine", "negative_squared_l2")},
        }
if OUT.exists():
    raise FileExistsError("Refusing to overwrite GT diagnostic evidence")
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({key: item["total_adjacent_inversions"] for key, item in result["sets"].items()}, indent=2))
