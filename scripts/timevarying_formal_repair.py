"""Additive v6 repair of terminal v5 ledgers and complete T-E/T-B splits.

Every reused row is checked against its sampled contract and certification.
Uncertified rows are recomputed; the original ledger remains immutable.
"""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import signal
import time

import numpy as np

from timevarying_data_pilot import sample, pde_price
from timevarying_formal_data import TOL, evaluate, pack


TERTIARY_SETTINGS = [(14401, 640, 1.0), (19201, 640, 1.0),
                     (14401, 1280, 1.0), (18001, 640, 1.25)]


def repair(item):
    index, case = item
    started, cpu_started = time.perf_counter(), time.process_time()
    row = evaluate(item)
    if "error" in row:
        return row
    for contract in row["rows"]:
        strike = contract["strike"]
        for cell, dates in (("TE", [case["exercise"][-1]]),
                            ("TB", case["exercise"])):
            result = contract["cells"][cell]
            if result["reference_indicator"] > TOL:
                try:
                    values = [pde_price(case, dates, strike, *s)
                              for s in TERTIARY_SETTINGS]
                except Exception as exc:
                    result["tertiary_error"] = type(exc).__name__ + ": " + str(exc)
                else:
                    result["reference_tertiary"] = values
                    result["reference_tertiary_settings"] = TERTIARY_SETTINGS
                    result["reference_indicator"] = max(abs(x-values[0]) for x in values[1:])
        euro, berm = (contract["cells"][cell] for cell in ("TE", "TB"))
        chosen = lambda r: r.get("reference_tertiary", r.get("reference_fallback", r["reference"]))[0]
        values = [chosen(euro), chosen(berm), *euro["gtfk"], *berm["gtfk"],
                  euro["coarse_pde"], berm["coarse_pde"]]
        contract["formal_bounds"] = (all(np.isfinite(values)) and
                                     all(-1e-8 <= x <= strike+1e-8 for x in values) and
                                     chosen(berm)+1e-8 >= chosen(euro))
        contract["formal_certified"] = contract["formal_bounds"] and all(
            r["reference_indicator"] <= TOL and r["gtfk_change"] <= TOL and
            not any(k in r for k in ("refinement_error", "gtfk_refinement_error",
                                     "tertiary_error")) for r in (euro, berm))
    row["certified"] = all(r["formal_certified"] for r in row["rows"])
    row["seconds"] = time.perf_counter()-started
    row["cpu_seconds"] = time.process_time()-cpu_started
    return row


def source_rows(spec, cases):
    if spec is None:
        return {}
    path = Path(spec["path"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
        raise RuntimeError("source ledger SHA-256 mismatch")
    result = {}
    def same(left, right):
        if isinstance(left, dict) and isinstance(right, dict):
            return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
        if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
            return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return np.isfinite(left) and np.isfinite(right) and abs(left-right) <= 5e-15
        return left == right
    with path.open() as ledger:
        for index, line in enumerate(ledger):
            row = json.loads(line)
            expected = cases[index] if index < len(cases) else None
            if expected is None or row.get("group") != index or not same(row.get("contract"), expected):
                raise RuntimeError(f"source group/contract mismatch at {index}")
            if row.get("certified") and len(row.get("rows", [])) == 3 and all(
                    x.get("formal_certified") for x in row["rows"]):
                result[index] = row
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    if cfg.get("status") != "frozen":
        raise RuntimeError("frozen configuration required")
    receipt = Path(cfg["source_os_wait_receipt"])
    if hashlib.sha256(receipt.read_bytes()).hexdigest() != cfg["source_os_wait_receipt_sha256"]:
        raise RuntimeError("source OS wait receipt SHA-256 mismatch")
    state = json.loads(receipt.read_text())
    if state.get("termination_evidence") != "os_child_wait_status" or state.get("status") != "completed":
        raise RuntimeError("source run has no terminal OS child wait")
    available = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()
    if available < cfg["workers"]:
        raise RuntimeError("frozen worker count exceeds CPU affinity")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("v6 budget exceeded")))
    signal.alarm(cfg["max_seconds"])
    arrays, failures, timing = {}, [], {}
    for split in cfg["splits"]:
        name = split["name"]
        cases = sample(split["groups"], split["seed"], split["region"])
        reused = source_rows(cfg["source_ledgers"].get(name), cases)
        began = time.perf_counter()
        rows = []
        with ProcessPoolExecutor(max_workers=cfg["workers"]) as pool, \
                (out/(name+".jsonl")).open("w") as ledger:
            pending = {i: pool.submit(repair, (i, case)) for i, case in enumerate(cases)
                       if i not in reused}
            for i in range(len(cases)):
                row = reused[i] if i in reused else pending[i].result()
                rows.append(row)
                ledger.write(json.dumps(row)+"\n")
                ledger.flush()
                if not row.get("certified"):
                    failures.append({"split": name, "group": i, "error": row.get("error"),
                                     "failed_strikes": [j for j, x in enumerate(row.get("rows", []))
                                                        if not x.get("formal_certified")]})
                if len(rows) % 64 == 0:
                    print(json.dumps({"split": name, "groups": len(rows),
                                      "failures": len(failures),
                                      "elapsed_seconds": time.perf_counter()-started}), flush=True)
        timing[name] = {"groups": len(rows), "reused_groups": len(reused),
                        "new_groups": len(rows)-len(reused),
                        "wall_seconds": time.perf_counter()-began}
        if failures:
            (out/"gate-failures.json").write_text(json.dumps(failures, indent=2)+"\n")
            break
        for cell in ("TE", "TB"):
            packed = pack(rows, cell)
            for j, row in enumerate(rows):
                for k, contract in enumerate(row["rows"]):
                    result = contract["cells"][cell]
                    if "reference_tertiary" in result:
                        packed["y"][3*j+k] = result["reference_tertiary"][0]
            for key, value in packed.items():
                arrays[name+"_"+cell+"_"+key] = value
    complete = not failures and len(timing) == len(cfg["splits"])
    summary = {"stage": "formal time-varying paired put labels v6",
               "complete": complete, "failures": len(failures), "timing": timing,
               "elapsed_seconds": time.perf_counter()-started,
               "scope": "T-E and T-B labels and numerical baselines; no training"}
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    if not complete:
        return
    np.savez_compressed(out/"data-fit.npz", **{k:v for k,v in arrays.items()
                                               if k.startswith("train_") or k.startswith("val_")})
    np.savez_compressed(out/"data-all.npz", **arrays)
    checks = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (out/"data-fit.npz", out/"data-all.npz")}
    (out/"data-sha256.json").write_text(json.dumps(checks, indent=2)+"\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
