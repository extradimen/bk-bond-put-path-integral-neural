# Time-varying put E2 validation PDE grid scan, frozen v1

For each of T-E and T-B, scan the first 32 frozen validation groups, with all
three strikes per group, at 51/25, 101/50, 201/100, 401/200, and 801/400
spatial points/annual time steps. The frozen denominator is 64 cell-groups.
Compare mean absolute price error against the independent high-resolution PDE
reference and validation GTFK A. Select the candidate with validation MAE
closest to A, breaking ties by median group runtime and smaller grid. Check
201/100 against the frozen Dbase price to 1e-6 per option. This selects an
exploratory error-matched coarse PDE for possible residual-network follow-up;
it neither reinterprets the original D model nor creates a new primary test.
Prices and timing are recorded per group, and all failed runs remain preserved.
