"""Evaluate frozen residual-network gradients on numerically audited baseline groups."""
import os
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[name] = "1"

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tarfile

import numpy as np

from learning import MLP


def checked(spec):
    path = Path(spec["file"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
        raise RuntimeError(f"frozen input checksum mismatch: {path}")
    return path


def model(archive, fit, dim):
    member = archive.getmember("models/" + fit["model_file"])
    with np.load(BytesIO(archive.extractfile(member).read())) as weights:
        net = MLP(dim, fit["width"], fit["layers"], 0)
        for i in range(len(net.W)):
            net.W[i] = weights[f"W{i}"].copy()
            net.b[i] = weights[f"b{i}"].copy()
        mean, scale = weights["mean"].copy(), weights["scale"].copy()
        ym, ys = float(weights["ym"]), float(weights["ys"])
    return net, mean, scale, ym, ys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    paths = {name: checked(spec) for name, spec in cfg["sources"].items()}
    selected = json.loads(paths["selected"].read_text())
    if len(selected) != cfg["selected_count"]:
        raise RuntimeError("selected model count mismatch")
    pilot = {}
    for line in paths["pilot"].read_text().splitlines():
        row = json.loads(line)
        key = row["cell"], row["group"]
        if key in pilot:
            raise RuntimeError("duplicate pilot group")
        pilot[key] = row
    expected = {(cell, group) for cell in cfg["cells"] for group in cfg["groups"]}
    if set(pilot) != expected:
        raise RuntimeError("pilot group set mismatch")
    references = {}
    for line in paths["risk"].read_text().splitlines():
        row = json.loads(line)
        key = row["cell"], row["group"]
        if key in expected:
            if key in references or not row["passed"] or row["strike_index"] != 1:
                raise RuntimeError("invalid risk reference")
            references[key] = row
    if set(references) != expected:
        raise RuntimeError("reference group set mismatch")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    completed = 0
    with np.load(paths["data"]) as data, tarfile.open(paths["models"], "r:gz") as archive, (out/"pilot.jsonl").open("w") as ledger:
        members = {member.name for member in archive.getmembers() if member.isfile()}
        if any(not name.startswith("models/") for name in members):
            raise RuntimeError("unexpected model archive member")
        for cell in cfg["cells"]:
            for method in cfg["methods"]:
                baseline = cfg["baseline_for_method"][method]
                fits = [entry["fit"] for entry in selected if entry["selection"] == "tuned"
                        and entry["fit"]["cell"] == cell and entry["fit"]["method"] == method
                        and entry["fit"]["budget"] == cfg["budget"]]
                if sorted(fit["seed"] for fit in fits) != sorted(cfg["seeds"]):
                    raise RuntimeError("selected seed set mismatch")
                for fit in fits:
                    if "models/" + fit["model_file"] not in members:
                        raise RuntimeError("selected model missing")
                    net, mean, scale, ym, ys = model(archive, fit, data[f"test_{cell}_X"].shape[1])
                    for group in cfg["groups"]:
                        key = cell, group
                        index = 3*group+1
                        if int(data[f"test_{cell}_group"][index]) != group:
                            raise RuntimeError("data group identity mismatch")
                        x = data[f"test_{cell}_X"][index:index+1]
                        refrow = references[key]
                        if not np.isclose(float(x[0, -1]), float(refrow["strike"])):
                            raise RuntimeError("strike identity mismatch")
                        base = pilot[key]["methods"][baseline]
                        if abs(base["frozen_price"] - float(data[f"test_{cell}_{baseline}"][index])) > cfg["price_identity_tolerance"]:
                            raise RuntimeError("baseline price identity mismatch")
                        coords = base["coordinates"]
                        if [c["coordinate"] for c in coords] != cfg["coordinates"]:
                            raise RuntimeError("coordinate order mismatch")
                        z = (x-mean)/scale
                        residual_price = float(net.predict(z)[0]*ys+ym)
                        residual_gradient = net.input_gradient(z)[0, :len(coords)]*ys/scale[:len(coords)]
                        low = np.array([c["low"] for c in coords]) + residual_gradient
                        high = np.array([c["high_resolution"] for c in coords]) + residual_gradient
                        ref = np.array([c["reference"] for c in coords])
                        row = dict(cell=cell, group=group, method=method, seed=fit["seed"],
                                   baseline=baseline, price=float(base["price_low"]+residual_price),
                                   reference_price=float(data[f"test_{cell}_y"][index]),
                                   risk=low.tolist(), risk_high=high.tolist(), reference=ref.tolist(),
                                   absolute_error=np.abs(low-ref).tolist(),
                                   numerical_resolution_change=np.abs(low-high).tolist())
                        ledger.write(json.dumps(row)+"\n")
                        ledger.flush()
                        completed += 1
                        print(json.dumps(dict(completed=completed, frozen=cfg["frozen_fits"])), flush=True)
    if completed != cfg["frozen_fits"]:
        raise RuntimeError("fit count mismatch")
    summary = dict(completed=completed, frozen=cfg["frozen_fits"],
                   scope="exploratory C/D residual gradients plus frozen A/Dbase pilot baselines")
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")


if __name__ == "__main__":
    main()
