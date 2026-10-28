"""Governed numerical reference certification for joint time-varying puts."""
import argparse
import json
from pathlib import Path

import numpy as np

from numerics import grid_for
from timevarying_bermudan import pde_put, split_put


def values(case, n, rate, width, method="pde", order=24):
    schedule = [(x["start"], x["end"], x["model"]) for x in case["schedule"]]
    model = schedule[0][2]
    grid = grid_for(model, n, width)
    result = []
    for dates in ([case["exercise"][-1]], case["exercise"]):
        if method == "pde":
            curve = pde_put(schedule, dates, case["maturity"], case["strike"],
                            grid, rate)
        else:
            curve = split_put(schedule, dates, case["maturity"], case["strike"],
                              grid, rate, order)
        result.append(float(curve[n // 2]))
    return dict(zip(("european", "bermudan"), result))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for case in cfg["cases"]:
        prices = {name: values(case, **setting)
                  for name, setting in cfg["settings"].items()}
        gaps = {name: max(abs(prices["base"][contract] - prices[name][contract])
                          for contract in ("european", "bermudan"))
                for name in ("space", "time", "domain", "split")}
        bounds = all(prices[name]["bermudan"] + cfg["tolerance"] >=
                     prices[name]["european"] >= -cfg["tolerance"]
                     for name in prices)
        certified = bounds and all(x <= cfg["tolerance"] for x in gaps.values())
        row = {"case": case["name"], "prices": prices, "gaps": gaps,
               "bounds_pass": bounds, "certified": certified}
        rows.append(row)
        print(json.dumps(row), flush=True)
    report = {"scope": "P3d numerical reference check, not method ranking",
              "tolerance": cfg["tolerance"], "cases": rows,
              "all_certified": all(x["certified"] for x in rows)}
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    if not report["all_certified"]:
        raise AssertionError("P3d numerical reference gate failed; preserve results")


if __name__ == "__main__":
    main()
