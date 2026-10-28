"""Additive, checksum-pinned repair of failed conditional-label groups only."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from conditional_boundary_dataset import contract_examples
from put_exercise_boundary_pilot import fixed_contract
from timevarying_put_risk_pilot import contract as time_contract


KEYS = ("X", "y", "A", "Dbase", "group", "strike_index", "date_index", "state_index")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def failed_groups(ledger_path):
    rows = [json.loads(line) for line in Path(ledger_path).read_text().splitlines()]
    return {(row["split"], row["cell"], int(row["group"]))
            for row in rows if not row["label_passed"]}


def group_examples(source, split, cell, group, cfg, reference):
    ids = source[f"{split}_{cell}_group"]
    indices = np.flatnonzero(ids == group)
    if len(indices) != 3:
        raise RuntimeError("repair group must have three strike contracts")
    blocks = {key: [] for key in KEYS}
    checks = []
    for strike_index, index in enumerate(indices):
        features = source[f"{split}_{cell}_X"][index].copy()
        case = (fixed_contract(features) if cell == "FB" else
                time_contract(features, cell)[0])
        examples = contract_examples(features, case, reference=reference,
            independent=cfg["independent"], coarse=cfg["coarse"],
            gtfk=cfg["gtfk"], state_count=cfg["states_per_date"],
            boundary_offsets=cfg["boundary_offsets"])
        for item in examples:
            n = len(item["y"])
            for key in ("X", "y", "A", "Dbase"):
                blocks[key].append(item[key])
            for key, value in (("group", group), ("strike_index", strike_index),
                               ("date_index", item["date_index"])):
                blocks[key].append(np.full(n, value, dtype=int))
            blocks["state_index"].append(np.arange(n, dtype=int))
            checks.append(item["independent_max_abs"])
    return {key: np.concatenate(blocks[key], axis=0) for key in KEYS}, max(checks)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    for item in [*cfg["sources"].values(), cfg["original_data"], cfg["original_ledger"]]:
        if sha256(item["file"]) != item["sha256"]:
            raise RuntimeError("frozen input SHA-256 mismatch")
    observed = failed_groups(cfg["original_ledger"]["file"])
    frozen = {(split, cell, int(group)) for split, cells in cfg["repair_groups_by_split"].items()
              for cell, groups in cells.items() for group in groups}
    if observed != frozen:
        raise RuntimeError("frozen repair groups differ from all observed original failures")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    repair_blocks = {}
    attempts = []
    with (out / "repairs.jsonl").open("w") as ledger:
        for split, cell, group in sorted(frozen):
            with np.load(cfg["sources"][cell]["file"]) as source:
                selected = None
                for reference in cfg["reference_tiers"]:
                    blocks, error = group_examples(source, split, cell, group, cfg, reference)
                    attempt = dict(split=split, cell=cell, group=group,
                        reference=reference, independent_max_abs=error,
                        passed=bool(error <= cfg["label_tolerance"]))
                    attempts.append(attempt)
                    ledger.write(json.dumps(attempt) + "\n")
                    ledger.flush()
                    if attempt["passed"]:
                        selected = blocks
                        break
                if selected is None:
                    raise RuntimeError(f"no frozen reference tier qualified: {split}/{cell}/{group}")
                repair_blocks[(split, cell, group)] = selected
                print(json.dumps(dict(completed_groups=len(repair_blocks),
                    total_groups=len(frozen))), flush=True)
    arrays = {}
    with np.load(cfg["original_data"]["file"]) as original:
        for split in cfg["splits"]:
            for cell in cfg["cells"]:
                groups = sorted(group for s, c, group in frozen if s == split and c == cell)
                group_ids = original[f"{split}_{cell}_group"]
                keep = ~np.isin(group_ids, groups)
                for key in KEYS:
                    base = original[f"{split}_{cell}_{key}"][keep]
                    patches = [repair_blocks[(split, cell, group)][key] for group in groups]
                    arrays[f"{split}_{cell}_{key}"] = np.concatenate([base, *patches], axis=0)
                expected = cfg["expected_groups"][cell][split]
                actual = len(np.unique(arrays[f"{split}_{cell}_group"]))
                if actual != expected:
                    raise RuntimeError("repaired archive group count differs from freeze")
    np.savez_compressed(out / "train-val-repaired.npz", **arrays)
    (out / "summary.json").write_text(json.dumps(dict(completed_groups=len(repair_blocks),
        total_groups=len(frozen), attempts=len(attempts),
        max_selected_independent_abs=max(next(x["independent_max_abs"] for x in attempts
            if x["split"] == split and x["cell"] == cell and x["group"] == group and x["passed"])
            for split, cell, group in frozen),
        data_sha256=sha256(out / "train-val-repaired.npz"),
        scope="additive group-level label repair; no fitting or test access"), indent=2) + "\n")


if __name__ == "__main__":
    main()
