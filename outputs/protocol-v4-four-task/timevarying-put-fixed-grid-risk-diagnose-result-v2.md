# Fixed-grid coarse PDE derivative diagnosis v2

The frozen two target groups (T-E 96 and T-B 127) completed 2/2. The campus-3090-2 node recorded OS child wait return code 0; the project material receipt verifies the returned summary and row ledger by SHA-256. Version 1's packaging failure remains preserved separately.

Holding the PDE state grid fixed substantially removes the T-B 127 coarse-grid `sigma1` derivative discrepancy: 0.078344 (moving grid) becomes 0.058398 (fixed grid), versus independent reference 0.057147. It does **not** remove the `sigma2` discrepancy: both coarse values are -0.005146, versus reference 0.014788; the refined-grid value is 0.014766. Other T-B 127 coordinates also show coarse-grid anomalies. Therefore grid movement is one contributor, but coarse PDE derivative stability remains a failed gate.

The fixed-grid `log(r0)` derivative is artificially zero because this diagnostic evaluates at the fixed grid midpoint rather than the perturbed initial state. It is invalid for that coordinate and must not be used as a certification result. The diagnosis is exploratory on two previously identified groups, not an all-group A/C/D derivative audit. Raw rows: `outputs/timevarying-put-fixed-grid-risk-diagnose-v2/results/diagnosis.jsonl`.
