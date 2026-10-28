"""Audit and assemble mixed-resolution certified time-varying risk labels."""
import argparse
import hashlib
import json
from pathlib import Path


def load_rows(spec):
    path = Path(spec["file"])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != spec["sha256"]:
        raise RuntimeError(f"input checksum mismatch: {path}")
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    return {(row["cell"], row["group"]): row for row in rows}, len(rows)


def validate(row, cell, group, tolerance):
    if row["cell"] != cell or row["group"] != group or row["strike_index"] != 1:
        raise RuntimeError(f"wrong contract identity: {cell}/{group}")
    if len(row["derivatives"]) != 7 or not row["passed"]:
        raise RuntimeError(f"uncertified row: {cell}/{group}")
    for coordinate in row["derivatives"]:
        if not coordinate["passed"]:
            raise RuntimeError(f"uncertified coordinate: {cell}/{group}")
        for name, value in coordinate.items():
            if name.endswith("_change") and value > tolerance:
                raise RuntimeError(f"axis exceeds frozen tolerance: {cell}/{group}/{name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    split = cfg.get("split", "test")
    if split not in ("train", "val", "test"):
        raise RuntimeError(f"invalid split: {split}")
    sources = {}
    for name, spec in cfg["sources"].items():
        sources[name] = load_rows(spec)
    original, original_count = sources["v1"]
    expected = {(cell, group) for cell in cfg["cells"] for group in cfg["groups"]}
    if original_count != len(expected) or set(original) != expected:
        raise RuntimeError("original ledger must have the full frozen subset exactly once")
    overrides = {(item["cell"], item["group"]): item["source"] for item in cfg["overrides"]}
    original_failures = {key for key, row in original.items() if not row["passed"]}
    if set(overrides) != original_failures:
        raise RuntimeError("overrides must match all and only original failed groups")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    selected = []
    counts = {name: 0 for name in sources}
    for cell in cfg["cells"]:
        for group in cfg["groups"]:
            source = overrides.get((cell, group), "v1")
            row = sources[source][0].get((cell, group))
            if row is None:
                raise RuntimeError(f"missing repair: {cell}/{group}/{source}")
            validate(row, cell, group, cfg["tolerance"])
            selected.append(dict(row, source_stage=source,
                                 spatial_nodes=cfg["sources"][source]["spatial_nodes"],
                                 repaired_from_failed_v1=source != "v1"))
            counts[source] += 1
    with (out/"labels.jsonl").open("w") as stream:
        for row in selected:
            stream.write(json.dumps(row) + "\n")
    summary = dict(total=len(selected), certified=len(selected), source_counts=counts,
                   original_failed=len(original_failures),
                   input_sha256={name: spec["sha256"] for name, spec in cfg["sources"].items()},
                   scope=f"exploratory middle-strike {split} subset; mixed spatial resolutions; representative time/domain axes")
    (out/"summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
