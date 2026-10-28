"""Exploratory analytic input gradients of the frozen direct price networks."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
from io import BytesIO
import hashlib
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


def load_net(archive, fit, dim):
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
    for source in cfg["sources"].values():
        for name in ("data", "risk", "selected", "models"):
            checked(source[name])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for family, source in cfg["sources"].items():
        selected = json.loads(Path(source["selected"]["file"]).read_text())
        if len(selected) != cfg["selected_count_per_family"]:
            raise RuntimeError("selected model count differs from frozen plan")
        with np.load(source["data"]["file"]) as data, tarfile.open(source["models"]["file"], "r:gz") as archive:
            names = {m.name for m in archive.getmembers() if m.isfile()}
            if any(not n.startswith("models/") for n in names):
                raise RuntimeError("model archive has unexpected path")
            fixed_risk = np.load(source["risk"]["file"]) if family == "fixed" else None
            varying_risk = ({(r["cell"], r["group"]): r for r in map(json.loads, Path(source["risk"]["file"]).read_text().splitlines())}
                            if family == "timevarying" else None)
            try:
                for cell in source["cells"]:
                    ids = np.arange(cfg["groups"])*3+1
                    X = data[f"test_{cell}_X"][ids]
                    y = data[f"test_{cell}_y"][ids]
                    groups = data[f"test_{cell}_group"][ids]
                    if not np.array_equal(groups, np.arange(cfg["groups"])):
                        raise RuntimeError("test group identity mismatch")
                    if family == "fixed":
                        R = fixed_risk[f"test_{cell}_risk"][ids]
                        if not np.array_equal(fixed_risk[f"test_{cell}_group"][ids], groups):
                            raise RuntimeError("fixed risk group identity mismatch")
                    else:
                        expected = {(cell, g) for g in range(cfg["groups"])}
                        if not expected.issubset(varying_risk):
                            raise RuntimeError("time-varying risk group missing")
                        refs = [varying_risk[(cell, g)] for g in range(cfg["groups"])]
                        if any(not r["passed"] or r["strike_index"] != 1 for r in refs):
                            raise RuntimeError("time-varying risk row not certified")
                        names_order = [d["coordinate"] for d in refs[0]["derivatives"]]
                        if names_order != cfg["coordinates"][cell]:
                            raise RuntimeError("time-varying coordinate order mismatch")
                        R = np.array([[d["reference"] for d in r["derivatives"]] for r in refs])
                    if R.shape != (cfg["groups"], len(cfg["coordinates"][cell])):
                        raise RuntimeError("risk dimension mismatch")
                    fits = [e["fit"] for e in selected if e["selection"] == "tuned" and e["fit"]["cell"] == cell
                            and e["fit"]["method"] == "B" and e["fit"]["budget"] == 4096]
                    if sorted(f["seed"] for f in fits) != sorted(cfg["seeds"]):
                        raise RuntimeError("frozen seed selection mismatch")
                    for fit in fits:
                        if "models/" + fit["model_file"] not in names:
                            raise RuntimeError("selected model missing from archive")
                        net, mean, scale, ym, ys = load_net(archive, fit, X.shape[1])
                        Z = (X-mean)/scale
                        price = net.predict(Z)*ys+ym
                        risk = net.input_gradient(Z)[:, :R.shape[1]]*ys/scale[:R.shape[1]]
                        error = abs(risk-R)
                        row = dict(cell=cell, family=family, seed=fit["seed"], groups=cfg["groups"],
                                   method="B direct price-only MLP", model_file=fit["model_file"],
                                   coordinates=cfg["coordinates"][cell],
                                   price_mae=float(np.mean(abs(price-y))),
                                   risk_mae=np.mean(error,axis=0).tolist(),
                                   risk_q95=np.quantile(error,.95,axis=0).tolist(),
                                   risk_max=np.max(error,axis=0).tolist(),
                                   sign_mismatch_rate=np.mean(np.sign(risk)!=np.sign(R),axis=0).tolist())
                        rows.append(row)
                        with (out/"audit.jsonl").open("a") as ledger:
                            ledger.write(json.dumps(row)+"\n")
                        print(json.dumps(dict(cell=cell,seed=fit["seed"],completed=len(rows),total=20)),flush=True)
            finally:
                if fixed_risk is not None:
                    fixed_risk.close()
    summary = dict(completed=len(rows), expected=20, groups_per_cell=cfg["groups"],
                   scope="exploratory direct B analytic gradients versus certified PDE derivative subsets")
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary),flush=True)


if __name__ == "__main__":
    main()
