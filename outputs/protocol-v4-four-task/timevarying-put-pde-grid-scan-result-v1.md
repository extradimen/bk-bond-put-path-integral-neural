# Time-varying put E2 validation PDE grid scan

The frozen 64/64 cell-groups (32 validation groups in each of T-E/T-B, three
strikes per group) completed in run
`20261023T125522Z__1627c004__timevarying-put-pde-grid-scan-v1`.
Node OS child wait returned 0 and the project collector verified the SHA-256
return. The 201/100 grid reproduced frozen Dbase within 1e-6 per price.

| Grid | T-E validation MAE | T-B validation MAE |
|---|---:|---:|
| 51/25 | 3.2269e-4 | 6.1630e-4 |
| 101/50 | 4.9975e-5 | 9.7201e-5 |
| 201/100, original Dbase | 1.1812e-5 | 2.0189e-5 |
| 401/200 | 1.7299e-6 | 3.1405e-6 |
| 801/400 | 3.9703e-7 | 7.9639e-7 |

GTFK A validation MAE was 6.7124e-6 for T-E and 3.6700e-5 for T-B. The
frozen closest-MAE rule selects 401/200 for T-E and the original 201/100 for
T-B. T-E therefore needs a separately trained 401/200 residual-network
comparison under matched budget and seeds before time-varying E2 is complete;
the original D result remains intact. This post-primary validation scan does
not produce a new confirmatory test comparison.
