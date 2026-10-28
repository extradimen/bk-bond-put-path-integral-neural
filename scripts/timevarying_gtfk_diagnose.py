"""Pre-freeze GTFK quadrature, state-grid and domain scan on a failed case."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import argparse
import json
from pathlib import Path
import time

from timevarying_data_pilot import gtfk_price, sample


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    case = sample(cfg["source_groups"], cfg["source_seed"])[cfg["index"]]
    strike = case["strikes"][cfg["strike_index"]]
    dates_by_cell = {"TE": [case["exercise"][-1]],
                     "TB": case["exercise"]}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    rows = []
    with (out / "results.jsonl").open("w") as ledger:
        for n, nq, ny, width in cfg["settings"]:
            for cell in cfg["cells"]:
                t = time.perf_counter()
                price = gtfk_price(case, dates_by_cell[cell], strike,
                                   n, nq, ny, width)
                row = {"cell": cell, "setting": [n, nq, ny, width],
                       "price": price, "seconds": time.perf_counter()-t}
                rows.append(row)
                ledger.write(json.dumps(row)+"\n")
                ledger.flush()
                print(json.dumps(row), flush=True)
    (out / "summary.json").write_text(json.dumps({
        "case": case, "strike": strike, "rows": len(rows),
        "elapsed_seconds": time.perf_counter()-started,
        "scope": "pre-freeze numerical diagnosis only"
    }, indent=2)+"\n")


if __name__ == "__main__":
    main()
