# Time-varying put E3 risk structure, frozen v1

This descriptive follow-up pairs T-E and T-B for the first 128 test groups and
the middle strike. It uses frozen v8 price labels and the checksum-pinned merged
seven-coordinate risk labels, including their preserved source-stage repairs.
The contract parameters and strike must agree across the pair. The report gives
the T-B minus T-E early-exercise premium, each cell's derivative distribution,
their paired differences, and exploratory sigma1 quartiles. A premium below
-1e-6 is a numerical consistency flag. The 128 paired groups form the frozen
denominator. This post-primary subset supports descriptive risk structure only;
no new primary p-values, population generalization, or complete exercise-boundary
claim follows from it.
