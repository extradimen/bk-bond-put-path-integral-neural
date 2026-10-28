# T-E training risk-label numerical repair, frozen v2

The active v1 training-label ledger has completed all 256 T-E groups. Six
middle-strike groups, 7, 42, 108, 121, 180 and 189, failed only the `sigma1`
axis at the original 1e-4 stability gate. This additive v2 uses the same
coordinates, central-difference steps, 1e-4 gate, time/domain checks and
frozen v8 contracts, with 6401/9601 spatial points at 400 annual time steps
and 9601/800 and 14401/400 sensitivity checks. The frozen denominator is six
groups. It must run only after v1 has OS child-wait evidence and checksum
return; the original v1 rows remain unchanged. If any v2 group still fails,
retain it and assess a separately versioned finer-grid repair. The repaired
reference values must retain source-stage and grid-resolution provenance in
the later merged training label artifact.
