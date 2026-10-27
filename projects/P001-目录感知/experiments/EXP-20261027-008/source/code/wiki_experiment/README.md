# WIKI independent small-scale experiments

This isolated wrapper preserves the existing three directory implementations,
CRoaring and independent SEARCH-01 backend. It does not restore the author's
missing query scopes or Viking executor. The frozen scientific protocol is
[`wiki-independent-protocol-20261027.md`](../../notes/wiki-independent-protocol-20261027.md).

Existing admission is under
[`wiki-independent-preparation-20261027-01`](../../notes/wiki-independent-preparation-20261027-01/record.md).
Release/ASan directory default, directory phase and search outputs passed the
independent verifier. This adds a performance driver and changes only generated
search wrapper shape checks (456 queries, 912 cases) and contract label; the
original backend source remains byte-identical.

From the project root, historical commands are:

```powershell
& 'D:/anaconda3/python.exe' -B code/wiki_experiment/pipeline.py --stage prepare --preparation notes/wiki-independent-preparation-20261027-01
& 'D:/anaconda3/python.exe' -B code/wiki_experiment/pipeline.py --stage directory --preparation notes/wiki-independent-preparation-20261027-01 --experiment EXP-20261027-007
& 'D:/anaconda3/python.exe' -B code/wiki_experiment/pipeline.py --stage search --preparation notes/wiki-independent-preparation-20261027-01 --experiment EXP-20261027-008
```

These paths are already reserved or populated; do not overwrite them. A new run
requires a new preparation/experiment ID, prior registration in EXPERIMENTS.md
and verification that the intended protocol and sources are unchanged. The
runner rejects existing output directories and enforces resource/time limits.

`prepare.py` never reads qrels. Query ID plus a fixed SHA-256 rule selects a
directory independently of query text, relevance and measured results. The
directory workload uses 58 cases and four continuous maintenance operations.
Search uses scoped exact top-10 L2 truth and a fixed exact/IVF configuration;
empty truth has null quality, with latency retained. nDCG is not reported because
the uniform sample has inadequate relevance-label coverage.

Raw results, commands, environment and frozen sources are in each experiment.
`status.json` and `verification-*.json` determine actual run state. After final
verification, `results.md` and `analysis-01/*.csv` provide grouped statistics,
query geometry, empty scopes and per-process paired differences. Default and
phase timings are separate; bitmap portable bytes are not complete index heap
usage. No whole-dataset runs, dependency installation or neural training occur.
