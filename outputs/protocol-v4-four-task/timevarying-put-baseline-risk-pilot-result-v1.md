# T-E/T-B A and Dbase derivative stability pilot result

The frozen four cell-groups (T-E groups 0–1 and T-B groups 0–1) completed 4/4. Run `20261023T195526Z__1627c004__timevarying-put-baseline-risk-pilot-v1` on `campus-3090-2` ended with OS child wait code 0 and a checksum-verified return. The result ledger is `outputs/timevarying-put-baseline-risk-pilot-v1/results/pilot.jsonl`; `summary.json` confirms the frozen denominator. All frozen baseline price checks were exactly zero.

| Cell, group | Method | Max h→h/2 derivative change | Max resolution change | Max absolute difference from independent PDE derivative reference |
| --- | --- | ---: | ---: | ---: |
| T-E, 0 | A | 6.44e-7 | 2.92e-7 | 8.29e-6 |
| T-E, 0 | Dbase | 1.81e-8 | 3.98e-5 | 9.30e-6 |
| T-E, 1 | A | 4.82e-6 | 1.36e-6 | 1.75e-4 |
| T-E, 1 | Dbase | 6.33e-8 | 2.98e-4 | 2.25e-4 |
| T-B, 0 | A | 2.52e-8 | 4.18e-12 | 6.70e-5 |
| T-B, 0 | Dbase | 2.52e-8 | 6.95e-6 | 9.25e-6 |
| T-B, 1 | A | 3.95e-8 | 2.52e-10 | 1.85e-4 |
| T-B, 1 | Dbase | 3.93e-8 | 1.42e-4 | 1.90e-4 |

The Dbase step checks are small but its resolution changes reach 2.98e-4. A has smaller resolution changes, yet its T-E group 1 step change reaches 4.82e-6. Neither setting is certified as a full derivative reference by these four groups. The next A/C/D audit must retain method-specific numerical error diagnostics and report baseline plus residual derivative behavior separately; do not use this pilot to set post-hoc pass thresholds or to claim all four cells complete.
