"""Check and aggregate frozen four-cell price scores without refitting models."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean, stdev


def checked(spec):
    path = Path(spec["file"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
        raise RuntimeError("frozen synthesis input checksum mismatch: " + str(path))
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    finished = 0
    with (out/"cells.jsonl").open("w") as ledger:
        for family in cfg["families"]:
            scores = checked(cfg["sources"][family]["scores"])
            contrasts = checked(cfg["sources"][family]["contrasts"])
            for cell in cfg["families"][family]:
                rows = [r for r in scores if r["split"] == "test" and r["cell"] == cell]
                result = {}
                for method in cfg["methods"]:
                    if method in ("A", "Dbase"):
                        chosen = [r for r in rows if r["method"] == method
                                  and r["selection"] == "numerical_baseline"]
                        if len(chosen) != 1:
                            raise RuntimeError("baseline score identity mismatch")
                        result[method] = dict(mae=chosen[0]["metrics"]["mae"],
                                              q95=chosen[0]["metrics"]["q95"])
                    else:
                        chosen = [r for r in rows if r["method"] == method
                                  and r["selection"] == "tuned"
                                  and r["budget"] == cfg["budget"]]
                        if sorted(r["seed"] for r in chosen) != sorted(cfg["seeds"]):
                            raise RuntimeError("selected seed identity mismatch")
                        vals = [r["metrics"]["mae"] for r in chosen]
                        result[method] = dict(mae_mean=mean(vals), mae_seed_sd=stdev(vals),
                                              mae_by_seed={str(r["seed"]): r["metrics"]["mae"]
                                                           for r in chosen})
                paired = [r for r in contrasts if r["cell"] == cell]
                if len(paired) != cfg["contrasts_per_cell"] or any(r["groups"] != cfg["test_groups"] for r in paired):
                    raise RuntimeError("primary contrast count or group denominator mismatch")
                entry = dict(cell=cell, methods=result, paired_contrasts=paired,
                             test_groups=cfg["test_groups"])
                ledger.write(json.dumps(entry) + "\n")
                ledger.flush()
                finished += 1
                print(json.dumps(dict(completed=finished, frozen=cfg["frozen_cells"])), flush=True)
    if finished != cfg["frozen_cells"]:
        raise RuntimeError("four-cell count mismatch")
    (out/"summary.json").write_text(json.dumps(dict(completed=finished,
        frozen=cfg["frozen_cells"], scope="interim frozen-price synthesis; other analyses remain open"),
        indent=2) + "\n")


if __name__ == "__main__":
    main()
