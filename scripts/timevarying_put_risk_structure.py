"""Descriptive paired time-varying European/Bermudan put risk analysis."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def describe(values):
    x = np.asarray(values, dtype=float)
    return {"mean": float(x.mean()), "median": float(np.median(x)),
            "q05": float(np.quantile(x, .05)), "q95": float(np.quantile(x, .95)),
            "negative_fraction": float(np.mean(x < 0))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    for key in ("data", "risk"):
        if digest(cfg[key + "_file"]) != cfg[key + "_sha256"]:
            raise RuntimeError(key + " checksum mismatch")
    n = cfg["groups"]
    axes = cfg["coordinates"]
    labels = {}
    for line in Path(cfg["risk_file"]).read_text().splitlines():
        row = json.loads(line)
        if row["group"] >= n:
            continue
        key = (row["cell"], row["group"])
        if key in labels or row["strike_index"] != 1 or not row["passed"]:
            raise RuntimeError("duplicate or invalid label " + str(key))
        if [d["coordinate"] for d in row["derivatives"]] != axes:
            raise RuntimeError("coordinate mismatch " + str(key))
        labels[key] = row
    if set(labels) != {(cell, g) for cell in ("TE", "TB") for g in range(n)}:
        raise RuntimeError("risk label groups incomplete")
    with np.load(cfg["data_file"]) as data:
        te = data["test_TE_X"][:3*n:3]
        tb = data["test_TB_X"][:3*n:3]
        if not np.allclose(te[:, :8], tb[:, :8]) or not np.allclose(te[:, 8:11], tb[:, 10:13]):
            raise RuntimeError("paired contracts misaligned")
        for cell in ("TE", "TB"):
            if not np.array_equal(data[f"test_{cell}_group"][:3*n], np.repeat(np.arange(n), 3)):
                raise RuntimeError("group order mismatch")
        ix = 3*np.arange(n)+1
        price_te = data["test_TE_y"][ix]
        price_tb = data["test_TB_y"][ix]
        if any(not np.isclose(labels[cell, g]["strike"], data[f"test_{cell}_X"][ix[g], -1])
               for cell in ("TE", "TB") for g in range(n)):
            raise RuntimeError("strike mismatch")
        risk = {cell: np.asarray([[d["reference"] for d in labels[cell, g]["derivatives"]]
                                  for g in range(n)]) for cell in ("TE", "TB")}
        premium = price_tb-price_te
        delta = risk["TB"]-risk["TE"]
        rows = []
        for g in range(n):
            rows.append({"group": g, "TE_price": float(price_te[g]), "TB_price": float(price_tb[g]),
                         "premium": float(premium[g]), "TE_risk": risk["TE"][g].tolist(),
                         "TB_risk": risk["TB"][g].tolist(), "TB_minus_TE_risk": delta[g].tolist(),
                         "TE_source_stage": labels["TE", g]["source_stage"],
                         "TB_source_stage": labels["TB", g]["source_stage"]})
        slices = []
        for name, mask in [("all", np.ones(n, bool))] + [
            (f"sigma1_quartile_{q}", (te[:, 2] >= np.quantile(te[:, 2], q/4)) &
             (te[:, 2] < np.quantile(te[:, 2], (q+1)/4) if q < 3 else
              te[:, 2] <= np.quantile(te[:, 2], 1))) for q in range(4)]:
            slices.append({"slice": name, "groups": int(mask.sum()), "premium": describe(premium[mask]),
                           "TE": {a: describe(risk["TE"][mask, j]) for j, a in enumerate(axes)},
                           "TB": {a: describe(risk["TB"][mask, j]) for j, a in enumerate(axes)},
                           "TB_minus_TE": {a: describe(delta[mask, j]) for j, a in enumerate(axes)}})
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    (out/"ledger.jsonl").write_text("\n".join(json.dumps(r) for r in rows)+"\n")
    summary = {"stage": "time-varying put E3 risk structure", "completed_groups": len(rows),
               "frozen_groups": n, "middle_strike_only": True, "coordinates": axes,
               "negative_premium_count": int(np.sum(premium < -cfg["premium_tolerance"])),
               "slices": slices, "scope": "Descriptive paired first-128 test groups, post-primary labels; no new primary inference."}
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps({"completed_groups": len(rows), "frozen_groups": n,
                      "negative_premium_count": summary["negative_premium_count"]}), flush=True)


if __name__ == "__main__":
    main()
