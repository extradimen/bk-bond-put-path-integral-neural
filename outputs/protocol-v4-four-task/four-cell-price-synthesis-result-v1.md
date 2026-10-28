# Interim four-cell put-price synthesis v1

The frozen aggregation completed 4/4 cells on campus-3090-2 with OS child wait return code 0 and SHA-256-verified return. Each cell's test set has 2048 parameter groups; B/C/D entries below average five selected 4096-group-fit seeds. MAE is in unit-face bond option price.

| Cell | A GTFK | B direct | C GTFK residual | Dbase coarse PDE | D PDE residual |
|---|---:|---:|---:|---:|---:|
| F-E | 2.674e-6 | 1.675e-4 | 2.550e-7 | 3.075e-6 | 1.991e-6 |
| F-B | 3.243e-5 | 3.920e-4 | 2.172e-6 | 7.014e-6 | 3.933e-6 |
| T-E | 5.143e-6 | 2.593e-4 | 6.690e-7 | 2.936e-5 | 9.656e-6 |
| T-B | 4.414e-5 | 6.341e-4 | 5.772e-6 | 5.771e-5 | 1.965e-5 |

The six predeclared paired price contrasts in each cell retain their original 2048-group estimates and Holm corrections; the new aggregation changes no inferential result. C has the lowest mean price MAE among these selected configurations in every cell, but this does not make it universally best: its numerical baseline is part of online cost, time-varying Dbase/D derivatives can be unstable at the coarse grid, and boundary and precision-frontier analysis constrain the interpretation. The fixed and time-varying put studies were frozen separately, so the cross-cell difficulty pattern is descriptive rather than one new pooled confirmatory test. See `outputs/four-cell-price-synthesis-v1/results/cells.jsonl` for seed dispersion and all paired contrasts.

Full-distribution derivative accuracy, unresolved near-tangent exercise boundaries, E2–E6 cost/quality synthesis and final four-cell conclusion remain open.
