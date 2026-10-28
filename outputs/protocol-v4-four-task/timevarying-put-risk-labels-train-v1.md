# Time-varying put E4 training risk labels, frozen v1

The training-label phase covers the first 256 frozen train groups of each
T-E and T-B cell, middle strike only: **512 cell-groups**. Use the same seven
parameter coordinates, central-difference steps, independent high-resolution
PDE settings and unchanged 1e-4 numerical stability gate as the completed
test-label phase. The frozen v8 data package and every result are kept by
group, including failures. A later validation phase will cover the first 128
groups per cell; the completed 128-group test labels remain untouched. Only
numerically certified labels may enter paired price-only versus
price-and-derivative supervision. If failures occur, preserve this run and
perform separately versioned, axis-specific repairs before model fitting.
