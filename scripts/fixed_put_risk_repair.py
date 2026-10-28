"""Repair only risk-label groups that failed a frozen numerical gate."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from fixed_put_risk_pilot import one


def checked(path, expected):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise RuntimeError(f"SHA-256 mismatch: {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    checked(Path(cfg["data_file"]), cfg["data_sha256"])
    for name, digest in cfg["original_ledgers"].items():
        checked(Path(cfg["original_dir"]) / name, digest)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    arrays = {}
    failure_rows = []
    repaired = []
    initial_failures = 0
    with np.load(cfg["data_file"]) as data:
        for split, count in cfg["groups"].items():
            for cell in cfg["cells"]:
                name = f"{split}-{cell}.jsonl"
                rows = [json.loads(line) for line in (Path(cfg["original_dir"]) / name).open()]
                if len(rows) != count or [row["group"] for row in rows] != list(range(count)):
                    raise RuntimeError(f"original ledger group coverage mismatch: {name}")
                prefix = f"{split}_{cell}_"
                x = data[prefix + "X"][:3 * count]
                group = data[prefix + "group"][:3 * count]
                if not np.array_equal(group, np.repeat(np.arange(count), 3)):
                    raise RuntimeError(f"formal data group coverage mismatch: {name}")
                jobs = [(cell, row["group"], x[3 * row["group"]:3 * row["group"] + 3].copy(), cfg)
                        for row in rows if not row["passed"]]
                initial_failures += len(jobs)
                replacements = {}
                with ProcessPoolExecutor(max_workers=cfg["workers"]) as pool:
                    for row in pool.map(one, jobs):
                        replacements[row["group"]] = row
                        repaired.append(dict(split=split, **row))
                merged = [replacements.get(row["group"], row) for row in rows]
                failure_rows.extend(dict(split=split, cell=cell, group=row["group"])
                                    for row in merged if not row["passed"])
                arrays[prefix + "risk"] = np.concatenate([
                    np.stack([v["reference"] for v in row["derivatives"]], axis=1)
                    for row in merged
                ])
                arrays[prefix + "group"] = group.copy()
    with (out / "repaired.jsonl").open("w") as log:
        for row in repaired:
            log.write(json.dumps(row) + "\n")
    summary = dict(scope="exploratory fixed-put risk labels; selective numerical repair; no fit",
                   groups=cfg["groups"], cells=cfg["cells"], initial_failures=initial_failures,
                   repaired=len(repaired), remaining_failures=len(failure_rows),
                   complete=len(failure_rows) == 0,
                   elapsed_seconds=time.perf_counter() - start)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    if failure_rows:
        (out / "gate-failures.json").write_text(json.dumps(failure_rows, indent=2) + "\n")
    else:
        np.savez_compressed(out / "risk-labels.npz", **arrays)
        (out / "risk-labels.sha256").write_text(
            hashlib.sha256((out / "risk-labels.npz").read_bytes()).hexdigest() + "\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
