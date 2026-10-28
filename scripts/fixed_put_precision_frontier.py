"""Validation-only numerical precision and cost scan for fixed BK puts."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from bermudan_gtfk_split_pilot import price as gtfk_bermudan
from bermudan_pilot import value as pde_value
from numerics import gt_price


def contract(features, cell):
    a, sigma, r0, rbar = np.exp(features[0]), features[1], np.exp(features[2]), np.exp(features[3])
    if cell == "FE":
        e3, maturity = features[4:6]
        dates = [float(e3)]
    else:
        e1, e2, e3, maturity = features[4:8]
        dates = [float(e1), float(e2), float(e3)]
    return dict(a=float(a), sigma=float(sigma), r0=float(r0), rbar=float(rbar)), dates, float(maturity)


def evaluate_group(cell, group, features, truth, saved_dbase, cfg):
    model, dates, maturity = contract(features[0], cell)
    strikes = features[:, -1].astype(float)
    records = []
    if cell == "FE":
        direct = dict(model, expiry=dates[-1], tenor=maturity-dates[-1])
        for nq, ny in cfg["european_gtfk_candidates"]:
            begin = time.perf_counter()
            prices = np.asarray(gt_price(direct, strikes, nq=nq, ny=ny, both=True)["puts"])
            seconds = time.perf_counter()-begin
            if not np.all(np.isfinite(prices)):
                raise RuntimeError("nonfinite European GTFK candidate")
            records.append(dict(family="GTFK", nq=nq, ny=ny, prices=prices.tolist(),
                                seconds=seconds, mae=float(np.mean(np.abs(prices-truth)))))
    else:
        for n, nq, ny, width in cfg["bermudan_gtfk_candidates"]:
            begin = time.perf_counter()
            prices = np.asarray([gtfk_bermudan(model, dates, maturity, float(k), n,
                                               nq, ny, width) for k in strikes])
            seconds = time.perf_counter()-begin
            if not np.all(np.isfinite(prices)):
                raise RuntimeError("nonfinite Bermudan GTFK candidate")
            records.append(dict(family="GTFK", n=n, nq=nq, ny=ny, width=width,
                                prices=prices.tolist(), seconds=seconds,
                                mae=float(np.mean(np.abs(prices-truth)))))
    for n, rate in cfg["pde_candidates"]:
        begin = time.perf_counter()
        prices = np.asarray([pde_value(model, dates, maturity, float(k), n, rate, "put")
                             for k in strikes])
        seconds = time.perf_counter()-begin
        if not np.all(np.isfinite(prices)):
            raise RuntimeError("nonfinite PDE candidate")
        if n == 201 and rate == 100 and np.max(np.abs(prices-saved_dbase)) > cfg["dbase_tolerance"]:
            raise RuntimeError("201/100 PDE fails frozen Dbase reproduction")
        records.append(dict(family="PDE", n=n, rate=rate, prices=prices.tolist(),
                            seconds=seconds, mae=float(np.mean(np.abs(prices-truth)))))
    return dict(cell=cell, group=group, strikes=len(strikes), candidates=records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    if hashlib.sha256(Path(cfg["data_file"]).read_bytes()).hexdigest() != cfg["data_sha256"]:
        raise RuntimeError("frozen data checksum mismatch")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    results = []
    with np.load(cfg["data_file"]) as data, (out/"groups.jsonl").open("w") as ledger:
        for cell in cfg["cells"]:
            prefix = cfg["split"]+"_"+cell+"_"
            groups = data[prefix+"group"]
            for group in cfg["groups"]:
                rows = np.flatnonzero(groups == group)
                if len(rows) != 3:
                    raise RuntimeError("expected exactly three strikes per frozen group")
                result = evaluate_group(cell, group, data[prefix+"X"][rows],
                                        data[prefix+"y"][rows], data[prefix+"Dbase"][rows], cfg)
                results.append(result)
                ledger.write(json.dumps(result)+"\n")
                ledger.flush()
                print(json.dumps(dict(cell=cell, completed_groups=len(results),
                                      total_groups=len(cfg["cells"])*len(cfg["groups"]))), flush=True)
    summary = {}
    for cell in cfg["cells"]:
        group_results = [r for r in results if r["cell"] == cell]
        candidates = []
        for index in range(len(group_results[0]["candidates"])):
            records = [r["candidates"][index] for r in group_results]
            first = records[0]
            candidates.append(dict(family=first["family"], n=first.get("n"),
                                   nq=first.get("nq"), ny=first.get("ny"),
                                   width=first.get("width"), rate=first.get("rate"),
                                   validation_mae=float(np.mean([r["mae"] for r in records])),
                                   median_seconds_per_three_strikes=float(np.median([r["seconds"] for r in records])),
                                   mean_seconds_per_three_strikes=float(np.mean([r["seconds"] for r in records]))))
        summary[cell] = dict(groups=len(group_results), candidates=candidates)
    summary["scope"] = "frozen validation subset; numerical families only; no test selection"
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
