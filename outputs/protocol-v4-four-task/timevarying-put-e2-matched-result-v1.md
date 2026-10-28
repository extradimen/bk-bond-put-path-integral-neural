# T-E error-matched PDE residual follow-up

Run `20261023T131024Z__1627c004__timevarying-put-e2-matched-v1`
completed its frozen **2560/2560 baseline groups** (1024 train, 1024
validation, 512 test), three strikes each, and five fixed-capacity seeds.
The node OS child wait returned 0 and the project collector verified the
returned checksums. The grid was selected solely from the prior validation
scan: 401 spatial nodes and 200 annual time steps.

On the first 512 T-E test groups, mean absolute price error was A
`5.6392e-6`, original Dbase `2.4015e-5`, matched uncorrected PDE baseline
`4.8868e-6`, five-seed mean Dmatch `7.9212e-6`, and five-seed mean original D
`3.0541e-5`. Thus, in this exploratory subset, the finer matched PDE already
outperformed A and its added residual network worsened the average error
relative to the uncorrected matched PDE, though it outperformed original D.
Seed-level errors and 95th-percentile/max errors are preserved in
`outputs/timevarying-put-e2-matched-v1/results/test-scores.json`.

The test subset and original test results were previously seen, so this is not
a fresh confirmatory comparison. Parallel baseline generation time is not
isolated online latency. T-B's validation-matched grid remained original
201/100, so no new T-B model was trained for this follow-up.
