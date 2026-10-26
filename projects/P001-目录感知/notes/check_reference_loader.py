"""Check only reviewed, pure path helpers from a pinned reference snapshot.

Does not import the reference module, run its benchmark, load a vector backend,
create collections, or make network calls. No DSQ/DSM strategy is implemented.
"""
import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notes" / "data-audit-20261026-01"
source = OUT / "openviking-run.reference.py"
parsed = ast.parse(source.read_text(encoding="utf-8"))
names = {"pick_value", "normalize_path", "extract_declared_path", "extract_legacy_path", "safe_uri_segment", "resource_uri"}
selected = [node for node in parsed.body if
            isinstance(node, ast.FunctionDef) and node.name in names or
            isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "GENERIC_PATH_FIELDS" for t in node.targets)]
assert {n.name for n in selected if isinstance(n, ast.FunctionDef)} == names
namespace = {"Any": Any, "Optional": Optional, "Sequence": Sequence}
exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), "exec"), namespace)
raw = ROOT / "dataset" / "raw" / "ARXIV-Dir"
record = json.loads((OUT / "independent-spot-check.json").read_text(encoding="utf-8-sig"))["independent_entry_145"]
path = namespace["extract_legacy_path"](record)
result = {
    "reference_commit": "22a28101089515ddef85b96617449924baef9f35",
    "reference_url": "https://github.com/volcengine/OpenViking/blob/22a28101089515ddef85b96617449924baef9f35/benchmark/vectordb_perf/run.py",
    "reference_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "execution_scope": "Only six reviewed pure helper definitions and GENERIC_PATH_FIELDS; no module import, no benchmark execution",
    "entry_145": {"input": record, "legacy_path": path,
                  "resource_uri": namespace["resource_uri"]("arxiv", path, record["id"])},
    "queries": {},
}
for filename in ("arxiv_query_constraint.json", "arxiv_category_query_constraint.json"):
    records = json.loads((raw / filename).read_text(encoding="utf-8"))
    paths = [namespace["extract_legacy_path"](item) for item in records]
    result["queries"][filename] = {
        "records": len(records), "root_scopes_returned": paths.count("/"),
        "first_input": records[0], "first_extracted_path": paths[0],
        "first_resource_uri": namespace["resource_uri"]("arxiv", paths[0]),
    }
output = OUT / "reference-helper-check.json"
if output.exists():
    raise FileExistsError("Refusing to overwrite reference helper evidence")
output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
