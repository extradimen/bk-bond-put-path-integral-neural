"""Combine four put cells' frozen primary contrasts under one Holm family."""
import argparse
import hashlib
import json
from pathlib import Path


CELLS = ("FE", "FB", "TE", "TB")
CONTRASTS = ("B_minus_C", "B_minus_D", "A_minus_C", "A_minus_B",
             "Dbase_minus_D", "C_minus_D")


def holm24(rows):
    if len(rows) != 24:
        raise ValueError("expected exactly 24 predeclared tests")
    order = sorted(range(len(rows)), key=lambda i: rows[i]["p_raw"])
    adjusted = 0.0
    for rank, i in enumerate(order):
        adjusted = max(adjusted, min(1.0, (24-rank)*rows[i]["p_raw"]))
        rows[i]["p_holm_four_cell"] = adjusted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    rows = []
    for source in cfg["sources"]:
        path = Path(source["path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise RuntimeError("primary contrast checksum mismatch: "+str(path))
        rows.extend(json.loads(path.read_text()))
    expected = {(c, k) for c in CELLS for k in CONTRASTS}
    observed = [(r.get("cell"), r.get("contrast")) for r in rows]
    if len(observed) != len(expected) or set(observed) != expected:
        raise RuntimeError("primary contrast identities do not match frozen 24")
    for row in rows:
        p = row.get("p_raw")
        if not isinstance(p, (float, int)) or not 0 <= p <= 1:
            raise RuntimeError("invalid raw p-value")
        if row.get("groups") != 2048:
            raise RuntimeError("primary test group count mismatch")
    holm24(rows)
    rows.sort(key=lambda r: (CELLS.index(r["cell"]),
                             CONTRASTS.index(r["contrast"])))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    (out/"primary-24-holm.json").write_text(json.dumps(rows, indent=2)+"\n")
    summary = dict(cells=CELLS, tests=len(rows),
                   holm_family="24 predeclared four-cell paired contrasts",
                   rejected_at_0_05=sum(r["p_holm_four_cell"] <= .05 for r in rows))
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
