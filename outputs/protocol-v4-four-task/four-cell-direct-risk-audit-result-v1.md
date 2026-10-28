# Four-cell direct-network risk audit: exploratory results

The frozen direct B model gradient audit completed 20/20 cell-seed records, using 128 middle-strike test groups per cell and five tuned 4096-group seed models per cell. Governed run `20261023T121255Z__1627c004__four-cell-direct-risk-audit-v1` on campus-3090-2 ended with node `os_child_wait_status`, `return_code=0`; the project collector verified all returned SHA-256 hashes. Inputs and mixed-resolution PDE-label provenance are pinned in `four-cell-direct-risk-audit-v1.md` and the stage config.

Mean over five seeds of coordinate-wise absolute gradient errors, in the transformed model input coordinates:

| Cell | Coordinates in order | Mean absolute error |
| --- | --- | --- |
| F-E | log(a), sigma, log(r0), log(rbar) | 0.000463, 0.001755, 0.000589, 0.003379 |
| F-B | log(a), sigma, log(r0), log(rbar) | 0.001060, 0.002435, 0.001269, 0.001724 |
| T-E | log(a1), log(a2), sigma1, sigma2, log(r0), log(rbar1), log(rbar2) | 0.000394, 0.000430, 0.001248, 0.001427, 0.000424, 0.000438, 0.001844 |
| T-B | log(a1), log(a2), sigma1, sigma2, log(r0), log(rbar1), log(rbar2) | 0.001098, 0.001037, 0.002729, 0.002272, 0.001344, 0.001350, 0.001401 |

The corresponding five-seed mean price MAEs on this exact subset are about 1.69e-4, 4.12e-4, 2.79e-4 and 6.70e-4 in F-E/F-B/T-E/T-B order. Full per-seed coordinate MAE, 95th percentile, maximum and sign mismatch are preserved in `outputs/four-cell-direct-risk-audit-v1/results/audit.jsonl`. These coordinate spaces and risk scales differ; do not pool the rows into a single scalar ranking. This is a descriptive B-only audit after main price results were known, not an A/C/D derivative comparison, a newly trained derivative-supervised model, or full-test certification. The true Bermudan boundary still has unresolved numerical cases.
