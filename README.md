# Black--Karasinski bond-put pricing: code and synthetic data

This code-and-data release accompanies the Wang--Jiang Black--Karasinski bond-put pricing study. It covers four tasks: fixed/time-varying coefficients crossed with European/Bermudan exercise. All arrays are synthetically generated contract parameter groups and numerical labels; no market or licensed third-party dataset is included.

## Layout
- `scripts/`, `tests/`, `configs/`: research implementation, checks, frozen analysis and fit settings. Resource orchestration scripts and machine-specific credentials/configuration are omitted.
- `outputs/*/results/`: compact complete split arrays (`data-all.npz`), selected-model ledgers, formal predictions/results, timing and separate risk/boundary diagnostics. `data-fit.npz` contains train/validation only.
- `selected-models/`: 60 full-budget, validation-selected price networks and six selected conditional continuation networks. Unselected candidate weights and interrupted-run artifacts are retained in the original controlled project, not this publication release.
- `immutable-snapshots/`: source files and deployment manifests for seven decisive evidence stages. These are the actual stage-specific source versions, which may differ from current `scripts/`.
- `SHA256SUMS` and `source-map.json`: release-file checksums and original project paths.

## Data dictionary
In each `data-all.npz`, keys have the form `<split>_<cell>_<field>` for `split` in `train`, `val`, `test`, `ood_vol`, `ood_long`; `cell` is FE, FB, TE or TB as applicable. `X` holds model inputs; `y` is the refined PDE label; `A` is the GTFK anchor; `Dbase` is the coarse PDE anchor; `group` identifies the three-strike parameter group. Each row is one strike. Refer to `outputs/protocol-v4-four-task/` for units, draw ranges, seeds, numerical gates and known failures. The conditional boundary `boundaries.jsonl` and summary retain all 768 curves and the 15 reference-unqualified curves.

## Reproducibility scope
The compact arrays and selected weights allow independent checking of reported scores and their underlying figure/table data. Complete regeneration of numerical labels and all candidate fits requires the frozen protocols, larger original node run receipts and the experiment controller; it is computationally expensive. The source code and immutable snapshots are supplied for inspection. The formal price study and later exploratory boundary/risk studies must not be pooled. A failed derivative gate and a failed T--B direct-model validation gate are retained as failures.

Core numerical environment receipts used NumPy 2.3.4 and SciPy 1.16.2; exact hash-locked requirements for the executed stages are under `configs/requirements-*.lock`. To verify integrity, run `shasum -a 256 -c SHA256SUMS` from this directory. The release does not include an external dependency wheelhouse or a one-command reproduction of the campus-node execution protocol.
