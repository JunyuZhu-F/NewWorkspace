"""Prepare frozen DIR-01 inputs and query expectations without using the C++ core."""
import argparse, hashlib, json
from pathlib import Path

PROTOCOL = "PROTO-01-20261026"
TIME_SHA256 = "9aa84f093dfd4e9c4e1633c22ae7a9df424809fee9f45fc22fb96f85c04f36b6"
FIGURE = [(1,"/HR/"),(2,"/HR/Policies/"),(3,"/Finance/"),(4,"/Legal/"),
          (5,"/Dept_A/"),(6,"/Dept_B/"),(7,"/Archive/HR/"),
          (8,"/Dept_A/OKR/"),(9,"/Dept_B/OKR/")]

def sha(data): return hashlib.sha256(data).hexdigest()
def fnv(ids):
    value = 0xcbf29ce484222325
    for entry in sorted(ids):
        for byte in int(entry).to_bytes(4, "little"):
            value = ((value ^ byte) * 0x100000001b3) & 0xffffffffffffffff
    return f"{value:016x}"
def directories(rows):
    result = {"/"}
    for _, path in rows:
        for i, char in enumerate(path):
            if char == "/": result.add(path[:i+1])
    return sorted(result, key=lambda x: (x != "/", x.encode("utf-8")))
def query(rows, path, recursive):
    return sorted(entry for entry, parent in rows if
                  (parent == path if not recursive else path == "/" or parent.startswith(path)))
def write_checked(path, data):
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f"Frozen fixture differs; refusing overwrite: {path}")
    path.write_bytes(data)
def fixture(output, name, rows, operations):
    paths = directories(rows)
    binding_data = "".join(f"{entry}\t{path}\n" for entry, path in rows).encode()
    write_checked(output / f"{name}-bindings.tsv", binding_data)
    query_lines = []
    for recursive in (True, False):
        for path in paths:
            ids = query(rows, path, recursive)
            query_lines.append(f"{path}\t{int(recursive)}\t{len(ids)}\t{fnv(ids)}\n")
    query_data = "".join(query_lines).encode()
    write_checked(output / f"{name}-queries.tsv", query_data)
    op_data = "".join("\t".join(map(str, op))+"\n" for op in operations).encode()
    write_checked(output / f"{name}-operations.tsv", op_data)
    return {"entry_count":len(rows),"directory_count":len(paths),
            "query_count":len(query_lines),"bindings_sha256":sha(binding_data),
            "queries_sha256":sha(query_data),"operations_sha256":sha(op_data),"paths":paths}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--project",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args(); root=args.project.resolve(); output=args.output.resolve()
    if root not in output.parents: raise ValueError("Output must be inside project")
    output.mkdir(parents=True,exist_ok=True)
    source=root/"notes/time-pilot-20261026-01/bindings.jsonl"
    source_bytes=source.read_bytes()
    if sha(source_bytes) != TIME_SHA256: raise ValueError("Time pilot hash mismatch")
    time_rows=[]
    for line in source_bytes.decode().splitlines():
        row=json.loads(line)
        if row["namespace"] != "time" or any(c in row["directory"] for c in "\t\r\n"):
            raise ValueError("Invalid time binding")
        time_rows.append((row["entry_id"],row["directory"]))
    if len(time_rows)!=10000 or [r[0] for r in time_rows]!=list(range(10000)):
        raise ValueError("Time pilot order/count mismatch")
    figure_ops=[("move","/Dept_A/","/Dept_B/",1)]
    figure_merge=[("merge","/Dept_A/","/Dept_B/",1)]
    time_ops=[("move","/1992/1/","/1991/",1),
              ("merge","/1992/7/","/1991/7/",1),
              ("move","/1992/8/","/1991/",0)]
    # The time merge has its own operation file; move/reject are validated in the same DSM sequence.
    manifests={
      "figure2-build":fixture(output,"figure2",FIGURE,figure_ops),
      "figure2-move":fixture(output,"figure2-move",FIGURE,figure_ops),
      "figure2-merge":fixture(output,"figure2-merge",FIGURE,figure_merge),
      "time-build":fixture(output,"time",time_rows,time_ops),
      "time-dsm":fixture(output,"time-dsm",time_rows,time_ops),
    }
    # figure2 DSQ and time DSQ deliberately reuse the byte-identical initial-state files.
    manifest={"protocol":PROTOCOL,"digest":"FNV-1a-64 over ascending uint32 IDs, little-endian; empty set uses offset basis",
              "source_time_sha256":TIME_SHA256,"fixtures":manifests,
              "time_anchors":[{"after":0,"counts":{"/1991/":499,"/1992/":3068}},
                              {"after":1,"counts":{"/1991/7/":298,"/1991/":795,"/1992/":2772},"directory_count":33},
                              {"after":2,"rejected_unchanged":True}]}
    # Remove redundant fixture copies: aliases are recorded, not independently regenerated inputs.
    for alias,target,base in [("figure2-move","figure2-build","figure2"),("figure2-merge","figure2-build","figure2"),("time-dsm","time-build","time")]:
        for suffix in ("bindings.tsv","queries.tsv"):
            alias_file=output/f"{alias}-{suffix}"
            target_file=output/f"{base}-{suffix}"
            if alias_file.read_bytes()!=target_file.read_bytes(): raise ValueError("Alias mismatch")
            alias_file.unlink()
        manifests[alias]["bindings_sha256"]=manifests[target]["bindings_sha256"]
        manifests[alias]["queries_sha256"]=manifests[target]["queries_sha256"]
    manifest["fixtures"]["figure2-dsq"]=dict(manifests["figure2-build"])
    manifest["fixtures"]["time-dsq"]=dict(manifests["time-build"])
    data=(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode()
    write_checked(output/"manifest.json",data)
    print(json.dumps({"status":"prepared","output":str(output),"manifest_sha256":sha(data),
                      "figure2_queries":22,"time_queries":68},ensure_ascii=False))
if __name__ == "__main__": main()
