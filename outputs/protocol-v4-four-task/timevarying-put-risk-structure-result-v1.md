# Time-varying put E3 paired risk result

The frozen first 128 paired test groups at the middle strike completed **128/128**.
The node's OS child wait returned 0 and the project collector verified the
returned checksums. Run `20261023T124042Z__1627c004__timevarying-put-risk-structure-v1`.

T-B minus T-E price premium had mean 0.0541051 and median 0.0480805;
its fifth and 95th percentiles were 0.00159635 and 0.119144. No pair had a
premium below the frozen -1e-6 consistency threshold. Paired mean T-B minus
T-E derivatives, in frozen coordinate order, were -0.002600, 0.002990,
0.017964, 0.004654, 0.034392, 0.030192, and 0.013531. These are descriptive
findings from the post-primary middle-strike subset; full exercise-boundary
classification and derivative-method comparisons remain open.

The full group ledger and distributions are in
`outputs/timevarying-put-risk-structure-v1/results/`.
