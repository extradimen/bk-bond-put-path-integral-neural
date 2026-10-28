# T-E error-matched PDE residual network, frozen E2 v1

The validation-only grid scan selected 401 spatial nodes and 200 annual time
steps as closest in price MAE to GTFK A. This follow-up computes that PDE
baseline separately on the first 1024 frozen T-E train groups, all 1024
validation groups, and first 512 test groups, each with three strikes. The
baseline ledger has a frozen denominator of 2560 groups. A five-seed residual
network learns reference price minus the 401/200 baseline with the same 1024
train groups, fixed 3x64 architecture, learning rate .001, normalization,
early stopping, and seeds 11/23/37/53/71 as the original fixed-capacity D.
Compare Dmatch, its uncorrected baseline, original same-budget D, A, and
original Dbase on identical first-512 test groups. Report seed-level MAE,
95th percentile and maximum error. The original test results were seen before
this validation scan, so this is exploratory and produces no new confirmatory
significance claim. Timing from parallel baseline generation is not isolated
online latency. All group results and failed attempts must be preserved.
