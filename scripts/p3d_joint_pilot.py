"""Governed P3d joint-regime/exercise pilot, without training or ranking."""
import argparse
import json
from pathlib import Path

import numpy as np

from numerics import grid_for
from timevarying_bermudan import gtfk_put, pde_put, split_put


def evaluate(case, setting):
    schedule = [(x["start"], x["end"], x["model"]) for x in case["schedule"]]
    model = schedule[0][2]
    grid = grid_for(model, setting["n"], setting["width_scale"])
    starts = np.array([np.log(model["r0"])])
    dates = case["exercise"]
    out = {}
    for name, method in (("pde", pde_put), ("split", split_put), ("gtfk", gtfk_put)):
        values = []
        for selected in ([dates[-1]], dates):
            common = (schedule, selected, case["maturity"], case["strike"])
            if name == "pde":
                value = method(*common, grid, setting["steps_per_year"])[setting["n"] // 2]
            elif name == "split":
                value = method(*common, grid, setting["steps_per_year"], setting["split_order"])[setting["n"] // 2]
            else:
                value = method(*common, starts, grid, setting["nq"], setting["ny"])[0]
            values.append(float(value))
        out[name] = {"european": values[0], "bermudan": values[1],
                     "early_exercise_value": values[1] - values[0]}
    return {"setting": setting, "values": out,
            "pde_split_gap": abs(out["pde"]["bermudan"] - out["split"]["bermudan"]),
            "gtfk_pde_gap": abs(out["gtfk"]["bermudan"] - out["pde"]["bermudan"])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    records = []
    for case in cfg["cases"]:
        rows = []
        for setting in cfg["settings"]:
            row = evaluate(case, setting)
            rows.append(row)
            print(json.dumps({"case": case["name"], **row}), flush=True)
        records.append({"case": case["name"], "results": rows})
    report = {"scope": "P3d exploratory numerical pilot only", "cases": records}
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    if any(x["values"][m]["early_exercise_value"] < -1e-6
           for c in records for x in c["results"] for m in ("pde", "split", "gtfk")):
        raise AssertionError("exercise opportunity inequality failed; preserve results")


if __name__ == "__main__":
    main()
