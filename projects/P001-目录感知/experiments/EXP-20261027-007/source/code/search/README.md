# Small-data scoped retrieval

Independent C++17 admission backend for the existing directory implementations.
This is not Viking, a production vector database, or a paper-number reproduction.
Frozen scientific choices: `../../notes/search01-protocol-20261027.md`.

From the project root, use a **new evidence directory**:

```powershell
python code/search/validate.py --output notes/search01-validation-new-run
```

The command builds Release/ASan in separate `code/build-*-Search` directories,
checks synthetic contracts, prepares the first 10,000 time-bound corpus vectors,
runs the same 104 cases through three directory strategies and four search
configurations, then invokes the independent NumPy verifier. It refuses to replace
existing evidence. No downloads or new packages are required. Requires the existing
MSVC/CMake/Ninja installation and NumPy. The driver obtains the ASan DLL directory
from the saved compiler path, adding it only to the child process environment.

The input adapters preserve original float32 vectors and source row IDs. Exact
and IVF-Flat both rank by double-accumulated squared L2, with ID as tie breaker.
IVF coarse quantization uses 16 centers, seed 42, eight Lloyd iterations, and
1/4/16 probes. The backend object and its final quantizer are shared by all three
directory strategies; only the directory scope resolver changes. The current
prototype iterates allowed IDs and checks their assigned partition before scoring;
it does not implement an optimized posting-list traversal. This execution choice
must be stated in future latency comparisons. No PG implementation is included.

`prepare.py` fixes original time constraints and separate diagnostic scopes without
consulting published ground truth. `verify.py` independently checks original bytes,
selection, candidate membership, nearest-center assignments, probes, ranking,
scores, recall, and cross-strategy/cross-build equality. It does not import production
scope helpers or the C++ backend. The quantizer is checked independently at its
saved final state; this does not independently reimplement its full training loop.

SEARCH-01 admission has no latency acceptance threshold. Do not use validation
process elapsed times as query latency, or its diagnostic scopes as the author's
workload. Published full-corpus top-100 is not filtered to make subset ground truth.
This branch does not resolve the author's original metric choice, PG/Viking
parameters, WIKI nDCG protocol, or category ownership semantics.
