"""Complete a frozen fit grid from a checksum-pinned reboot archive."""
import argparse
import hashlib
import io
import itertools
import json
from pathlib import Path
import tarfile
import time

import numpy as np

from conditional_boundary_fit import fit_one


def jobs_for(cfg):
    return list(itertools.product(cfg["cells"], cfg["methods"], cfg["widths"],
                                        cfg["layers"], cfg["seeds"], cfg["learning_rates"]))


def signature(row):
    return tuple(row[k] for k in ("cell", "method", "width", "layers", "seed", "lr"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    archive = Path(cfg["partial_archive"])
    source = Path(cfg["data_file"])
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == cfg["partial_archive_sha256"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == cfg["data_sha256"]
    jobs = jobs_for(cfg)
    expected_prefix = cfg["completed_prefix"]
    assert 0 < expected_prefix < len(jobs)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    models = out / "models"
    models.mkdir()
    started = time.perf_counter()
    with tarfile.open(archive) as tar:
        members = [m for m in tar.getmembers() if m.isfile()]
        ledgers = [m for m in members if m.name.endswith("/fits.jsonl")]
        assert len(ledgers) == 1
        prior = [json.loads(line) for line in tar.extractfile(ledgers[0]).read().decode().splitlines()]
        assert len(prior) == expected_prefix
        assert [signature(row) for row in prior] == jobs[:expected_prefix]
        model_members = {m.name.rsplit("/models/", 1)[-1]: m for m in members if "/models/" in m.name}
        assert len(model_members) == len(prior)
        assert set(model_members) == {Path(row["model_file"]).name for row in prior}
        for name, member in model_members.items():
            blob = tar.extractfile(member).read()
            with np.load(io.BytesIO(blob)) as saved:
                assert "W0" in saved.files and "mean" in saved.files and "scale" in saved.files
            (models / name).write_bytes(blob)
    with np.load(source) as data, (out / "fits.jsonl").open("w") as ledger:
        assert not any(k.startswith("test_") for k in data.files)
        for cell in cfg["cells"]:
            for split in ("train", "val"):
                assert len(set(data[f"{split}_{cell}_group"].tolist())) == cfg["expected_groups"][cell][split]
        rows = prior[:]
        for row in prior:
            ledger.write(json.dumps(row) + "\n")
        ledger.flush()
        for cell, method, width, layers, seed, lr in jobs[expected_prefix:]:
            params, row = fit_one(data, cell, method, width, layers, seed, lr, cfg)
            tag = f"{cell}-{method}-{width}-{layers}-{seed}-{lr}"
            np.savez_compressed(models / f"{tag}.npz", **params)
            row["model_file"] = f"models/{tag}.npz"
            rows.append(row)
            ledger.write(json.dumps(row) + "\n")
            ledger.flush()
            print(json.dumps({"completed_fits": len(rows), "total_fits": len(jobs)}), flush=True)
    selected = []
    for cell, method in itertools.product(cfg["cells"], cfg["methods"]):
        selected.append(min((r for r in rows if r["cell"] == cell and r["method"] == method),
                            key=lambda r: (r["validation_mae"], r["model_file"])))
    (out / "selected.json").write_text(json.dumps(selected, indent=2) + "\n")
    (out / "summary.json").write_text(json.dumps({"completed_fits": len(rows),
        "total_fits": len(jobs), "reused_fits": expected_prefix,
        "selected": len(selected), "elapsed_seconds": time.perf_counter()-started,
        "data_sha256": cfg["data_sha256"], "partial_archive_sha256": cfg["partial_archive_sha256"],
        "scope": "state-conditioned B/C/D continuation fits; train/validation only"}, indent=2) + "\n")


if __name__ == "__main__":
    main()
