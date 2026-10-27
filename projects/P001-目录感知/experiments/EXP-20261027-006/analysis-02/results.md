# SEARCH-02 measured results

Independent exact/IVF prototype; deterministic cross-time 10k sample; not Viking or author-number reproduction. All reported results passed independent verification.

| Mode | Backend | Nonempty / empty | Recall@100 nonempty | ONLINE total us | OFFLINE total us | TrieHI total us |
|---|---|---|---:|---:|---:|---:|
| recursive | exact | 501 / 0 | 1.000000 | 258.2253 | 237.7237 | 240.0387 |
| recursive | IVF 1 | 501 / 0 | 0.229179 | 69.9676 | 56.9964 | 57.4080 |
| recursive | IVF 4 | 501 / 0 | 0.555440 | 121.2350 | 107.1855 | 107.7700 |
| recursive | IVF 16 | 501 / 0 | 1.000000 | 265.9456 | 246.3632 | 247.7015 |
| nonrecursive | exact | 235 / 266 | 1.000000 | 42.6133 | 41.0391 | 41.3222 |
| nonrecursive | IVF 1 | 235 / 266 | 0.120141 | 20.8532 | 20.3903 | 20.1815 |
| nonrecursive | IVF 4 | 235 / 266 | 0.363283 | 29.1679 | 28.1565 | 28.1088 |
| nonrecursive | IVF 16 | 235 / 266 | 1.000000 | 50.7824 | 49.3293 | 49.6542 |

These are nonempty-query means. Empty year-local requests are not counted as Recall=1. Exact and nprobe16 agree with independently recomputed subset truth. Partial-probe quality is identical across directory strategies; lower recall is retained.

## All-request and empty latencies

| Mode | Backend | Strategy | All-request mean us | Empty-request mean us |
|---|---|---|---:|---:|
| recursive | 0 | PE-ONLINE | 258.2253 | n/a |
| recursive | 0 | PE-OFFLINE | 237.7237 | n/a |
| recursive | 0 | TrieHI | 240.0387 | n/a |
| recursive | 1 | PE-ONLINE | 69.9676 | n/a |
| recursive | 1 | PE-OFFLINE | 56.9964 | n/a |
| recursive | 1 | TrieHI | 57.4080 | n/a |
| recursive | 4 | PE-ONLINE | 121.2350 | n/a |
| recursive | 4 | PE-OFFLINE | 107.1855 | n/a |
| recursive | 4 | TrieHI | 107.7700 | n/a |
| recursive | 16 | PE-ONLINE | 265.9456 | n/a |
| recursive | 16 | PE-OFFLINE | 246.3632 | n/a |
| recursive | 16 | TrieHI | 247.7015 | n/a |
| nonrecursive | 0 | PE-ONLINE | 21.2846 | 2.4415 |
| nonrecursive | 0 | PE-OFFLINE | 24.8645 | 10.5749 |
| nonrecursive | 0 | TrieHI | 24.2233 | 9.1172 |
| nonrecursive | 1 | PE-ONLINE | 15.4563 | 10.6884 |
| nonrecursive | 1 | PE-OFFLINE | 19.6768 | 19.0464 |
| nonrecursive | 1 | TrieHI | 18.7354 | 17.4578 |
| nonrecursive | 4 | PE-ONLINE | 19.3488 | 10.6740 |
| nonrecursive | 4 | PE-OFFLINE | 23.2547 | 18.9242 |
| nonrecursive | 4 | TrieHI | 22.5033 | 17.5510 |
| nonrecursive | 16 | PE-ONLINE | 29.5514 | 10.7946 |
| nonrecursive | 16 | PE-OFFLINE | 33.1875 | 18.9268 |
| nonrecursive | 16 | TrieHI | 32.5995 | 17.5324 |

## Measurement limits

Five independent processes, same ANN training seed and data; 3 warmups and 20 measured sweeps. Curves retain every nonempty request. Error bars are descriptive SD of process means. Per-query timings, nearest-rank percentiles, per-run summaries, and sampled stop-limit telemetry remain in the raw evidence. No significance, generalization, or stable extreme-tail claim is made.

The backend scans allowed IDs and checks partitions rather than optimized posting traversal. Stage-clock reads, ID mapping, outside-timer correctness checks and warm-cache execution affect these results. Total latency excludes load/train/build, output serialization, transport, and final caller-owned temporary destruction; the protocol defines the exact boundaries.

All timings and recalls are kept, including counterexamples. The cross-time input has 423 directories and is not directly comparable to the earlier 34-directory prefix sample. Missing source year 1995 is not investigated or filled. PG/WIKI, author distance/Viking configuration and full-scale experiments remain outside this completed small branch.
