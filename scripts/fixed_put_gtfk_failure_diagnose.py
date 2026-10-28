"""Prespecified post-gate grid/domain diagnosis of failed F-B train group."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import argparse
import json
from pathlib import Path
import time

from bermudan_gtfk_split_pilot import price


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    case = cfg["contract"]
    started = time.perf_counter()
    rows = []
    for n, width in cfg["settings"]:
        t = time.perf_counter()
        value = price(case["model"], case["exercise"], case["maturity"],
                      case["strike"], n, cfg["nq"], cfg["ny"], width)
        rows.append(dict(n=n, width=width, price=float(value),
                         seconds=time.perf_counter()-t))
    summary = dict(group=cfg["group"], rows=rows,
                   elapsed_seconds=time.perf_counter()-started,
                   scope="diagnosis only; original formal failure preserved")
    (out/"results.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
