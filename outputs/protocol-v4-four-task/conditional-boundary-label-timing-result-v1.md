# Conditional boundary label timing v1 result

The frozen pre-training quality and cost pilot completed 32/32 cell-split-groups (FB and TB, eight training and eight validation groups per cell). The node reported OS child wait status 0; `collect_stage.py` verified the returned files and SHA-256 receipt. No neural model was fitted in this stage.

All 32/32 groups passed the predeclared continuation-label tolerance of 1e-4. The largest recorded continuation discrepancy was 1.3068611638883398e-5, and median runtime was 11.693704007542692 seconds per group. The root diagnostic qualified 31/32 groups. FB validation group 1 has no early-date root at its first exercise date in either the PDE or independent split reference; its continuation labels still pass. This topology observation is retained and is not counted as a numerical label failure.

This pilot supports freezing a distinct state/date-conditioned training design. It does not certify the four-cell neural exercise boundaries or the full-distribution seven-coordinate derivative gate. Source: `outputs/conditional-boundary-label-timing-v1/results/summary.json`, `quality.jsonl`, `node-status.json`, and `return-receipt.json`.
