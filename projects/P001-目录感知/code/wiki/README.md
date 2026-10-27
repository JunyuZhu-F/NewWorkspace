# WIKI directory correctness admission

This separate executable links the existing directory core and independent C++
oracle. It does not edit either implementation or run a performance benchmark.
The fixed input contains 10,000 equally spaced WIKI global IDs and real paths.

Protocol, input audit, failures and final evidence:
`../../notes/wiki-preparation-20261027-01/record.md`.
Successful Release/ASan evidence is `check-02`; `check-01` is a preserved failed
launch. Do not overwrite evidence directories or reuse the earlier runner as a
blind rerun command. Both builds passed 5,292 exact scope comparisons each;
an additional Python path-state verifier checked every emitted scope summary.

The generated queries and maintenance sequence are project correctness cases.
They do not recover the author's missing WIKI query constraints or DSM workload,
and do not establish WIKI nDCG, Recall, or latency curves.
