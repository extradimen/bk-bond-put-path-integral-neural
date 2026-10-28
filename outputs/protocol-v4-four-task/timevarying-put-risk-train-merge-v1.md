# Time-varying put train risk-label merge, frozen v1

The original train ledger has 2 × 256 middle-strike cell-groups. Its failed identities are exactly the frozen overrides in `configs/timevarying-put-risk-train-merge-v1.json`. Every source ledger is pinned by SHA-256; repaired rows replace only matching failed identities, retain the original 1e-4 gate, seven-coordinate order and per-row source/resolution provenance. All original and failed rows stay preserved. This is an exploratory derivative-label subset with representative time/domain sensitivity axes.
