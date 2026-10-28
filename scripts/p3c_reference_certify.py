"""Governed independent numerical certification for P3c European puts."""
import argparse
import json
from pathlib import Path

import numpy as np

from numerics import grid_for
from timevarying_pde import european_put, split_european_put


def price(case, n, rate, width, method="pde", order=24):
    schedule = [(x["start"], x["end"], x["model"]) for x in case["schedule"]]
    model = schedule[0][2]
    grid = grid_for(model, n, width)
    if method == "pde":
        curve = european_put(schedule, case["exercise"], case["maturity"],
                             case["strike"], grid, rate)
    else:
        curve = split_european_put(schedule, case["exercise"], case["maturity"],
                                   case["strike"], grid, rate, order)
    return float(curve[n // 2])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    report = []
    for case in cfg["cases"]:
        vals = {}
        for name, setting in cfg["settings"].items():
            vals[name] = price(case, **setting)
        gaps = {"space": abs(vals["base"] - vals["space"]),
                "time": abs(vals["base"] - vals["time"]),
                "domain": abs(vals["base"] - vals["domain"]),
                "independent_split": abs(vals["base"] - vals["split"])}
        ok = all(v <= cfg["tolerance"] for v in gaps.values())
        row = {"case": case["name"], "prices": vals, "gaps": gaps,
               "certified": ok}
        report.append(row)
        print(json.dumps(row), flush=True)
    result = {"scope": "P3c numerical reference check, not method ranking",
              "tolerance": cfg["tolerance"], "cases": report,
              "all_certified": all(x["certified"] for x in report)}
    (out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    if not result["all_certified"]:
        raise AssertionError("P3c reference gate failed; preserve results")


if __name__ == "__main__":
    main()
