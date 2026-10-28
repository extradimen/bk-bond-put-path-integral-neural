"""Test whether recomputing the PDE state grid destabilizes put derivatives."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from timevarying_data_pilot import schedule_grid
from timevarying_bermudan import pde_put
from timevarying_put_online_cost import contract


def checked(spec):
    path = Path(spec["file"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
        raise RuntimeError("frozen input checksum mismatch: " + str(path))
    return path


def evaluate(cell, x, grid, rate):
    case, dates = contract(x, cell)
    return float(pde_put(case["schedule"], dates, case["maturity"],
                         float(x[-1]), grid, rate)[len(grid)//2])


def derivative(cell, x, grid, rate, axis, h):
    left, right = x.copy(), x.copy()
    left[axis] -= h
    right[axis] += h
    return (evaluate(cell, right, grid, rate)-evaluate(cell, left, grid, rate))/(2*h)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    paths = {key: checked(value) for key, value in cfg["sources"].items()}
    prior = {(r["cell"], r["group"]): r for r in
             map(json.loads, paths["prior"].read_text().splitlines())}
    risk = {(r["cell"], r["group"]): r for r in
            map(json.loads, paths["risk"].read_text().splitlines())}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    completed = 0
    with np.load(paths["data"]) as data, (out/"diagnosis.jsonl").open("w") as ledger:
        for target in cfg["targets"]:
            cell, group = target["cell"], target["group"]
            key = cell, group
            if key not in prior or key not in risk or not risk[key]["passed"]:
                raise RuntimeError("missing certified target")
            index = 3*group+1
            x = data[f"test_{cell}_X"][index].copy()
            if int(data[f"test_{cell}_group"][index]) != group:
                raise RuntimeError("group mismatch")
            if not np.isclose(float(x[-1]), float(risk[key]["strike"])):
                raise RuntimeError("strike mismatch")
            case, _ = contract(x, cell)
            methods = {}
            for label, setting in cfg["settings"].items():
                n, rate, width = setting
                grid = schedule_grid(case, n, width)
                original = prior[key]["methods"]["Dbase"]
                coordinates = []
                for axis, name in enumerate(cfg["coordinates"]):
                    h = cfg["h"][axis]
                    first = derivative(cell, x, grid, rate, axis, h)
                    second = derivative(cell, x, grid, rate, axis, h/2)
                    left, right = x.copy(), x.copy()
                    left[axis] -= h
                    right[axis] += h
                    gl = schedule_grid(contract(left, cell)[0], n, width)
                    gr = schedule_grid(contract(right, cell)[0], n, width)
                    ref = float(risk[key]["derivatives"][axis]["reference"])
                    coordinates.append(dict(coordinate=name, fixed=first,
                                            fixed_half_step=second,
                                            fixed_step_change=abs(first-second),
                                            reference=ref,
                                            grid_left=[float(gl[0]), float(gl[-1])],
                                            grid_right=[float(gr[0]), float(gr[-1])],
                                            prior_dynamic=original["coordinates"][axis]["low" if label == "low" else "high_resolution"]))
                methods[label] = dict(grid=[float(grid[0]), float(grid[-1])],
                                      price=evaluate(cell, x, grid, rate),
                                      coordinates=coordinates)
            row = dict(cell=cell, group=group, methods=methods)
            ledger.write(json.dumps(row)+"\n")
            ledger.flush()
            completed += 1
            print(json.dumps(dict(completed=completed, frozen=len(cfg["targets"]))), flush=True)
    (out/"summary.json").write_text(json.dumps(dict(completed=completed,
        frozen=len(cfg["targets"]), scope="fixed-grid diagnosis of coarse PDE derivative instability"), indent=2)+"\n")


if __name__ == "__main__":
    main()
