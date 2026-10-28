# Time-varying put E4 validation risk labels, frozen v1

The validation-label phase covers the first 128 frozen validation groups of
each T-E and T-B cell, middle strike only: **256 cell-groups**. It uses the
same seven coordinates, central-difference steps, independent PDE settings,
and unchanged 1e-4 axis gate as the training and test phases. The v8 data
package is SHA-pinned. Results are recorded per group, including failures.
This version is frozen before launch and does not alter the active training
run or previously certified test labels. Any failed labels require a separate
versioned repair before derivative-supervised model selection.
