# Actual Bermudan put exercise boundary pilot v1

The frozen FB/TB group-0 middle-strike pilot completed 2/2 cell-groups on campus-3090-2. The governed run is `20261023T112635Z__1627c004__put-exercise-boundary-pilot-v1`; the node reported `return_code=0` with `os_child_wait_status`, and `scripts/collect_stage.py` verified the returned checksums. The original run and all earlier failed protocol versions remain preserved.

The first two exercise dates in each case each have one root of **intrinsic value minus continuation value**. The terminal exercise date is recorded separately as the payoff kink, not as an early-exercise boundary. Across the four PDE grids, the largest short-rate root spread at an early exercise date is 3.68e-7; the largest difference between the independent OU-split root and the 1601-point PDE root is 4.96e-7. These figures establish numerical stability for two representative contracts only. No full-sample boundary accuracy gate or model comparison is claimed from this pilot.

Full ledger: `outputs/put-exercise-boundary-pilot-v1/results/boundaries.jsonl`. The next stage must freeze its sample and numerical tolerance before evidence runs.
