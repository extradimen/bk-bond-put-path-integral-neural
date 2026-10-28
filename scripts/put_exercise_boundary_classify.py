"""Additive, exploratory classification of recorded exercise-boundary scans."""
import argparse
import hashlib
import json
from pathlib import Path


def checked(spec):
    path = Path(spec["file"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
        raise RuntimeError("frozen boundary input checksum mismatch: " + str(path))
    return [json.loads(line) for line in path.read_text().splitlines()]


def record(row, method, setting, date_index):
    found = [s for s in row["settings"] if s["method"] == method
             and s["setting"] == setting]
    if len(found) != 1:
        raise RuntimeError("missing or duplicate boundary setting")
    return found[0]["records"][date_index]


def one(row, detail, index, gap_floor, root_tolerance):
    # Only genuine early-exercise decisions are boundary targets.
    if detail is None:
        pde = record(row, "pde", [1601, 100, 1.0], index)
        comparison = record(row, "pde", [801, 100, 1.0], index)
        independent = record(row, "independent_ou_split", [801, 100, 1.0, 16], index)
        tier = "original_scan"
    else:
        pde = record(detail, "pde", [6401, 100, 1.0], index)
        comparison = record(detail, "pde", [3201, 100, 1.0], index)
        independent = record(detail, "independent_ou_split", [3201, 100, 1.0, 16], index)
        tier = "refined_scan"
    low, high = pde["gap_min"], pde["gap_max"]
    roots = pde["crossing_short_rate"]
    other = comparison["crossing_short_rate"]
    split = independent["crossing_short_rate"]
    if low > gap_floor:
        status = "all_exercise_on_grid"
    elif high < -gap_floor:
        status = "all_continue_on_grid"
    elif low >= -gap_floor or high <= gap_floor:
        status = "marginal_gap_unresolved"
    elif len(roots) == len(other) == len(split) == 1:
        movement = max(abs(roots[0]-other[0]), abs(roots[0]-split[0]))
        status = "single_root_consistent" if movement <= root_tolerance else "root_location_unresolved"
    else:
        status = "root_topology_unresolved"
    return dict(date=pde["date"], tier=tier, status=status,
                pde_gap_min=low, pde_gap_max=high, pde_roots=roots,
                comparison_roots=other, independent_roots=split)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    original = checked(cfg["sources"]["original"])
    detail_rows = checked(cfg["sources"]["detail"])
    details = {(r["cell"], r["group"]): r for r in detail_rows}
    expected = {(cell, group) for cell in cfg["cells"] for group in cfg["groups"]}
    if len(original) != len(expected) or {(r["cell"], r["group"]) for r in original} != expected:
        raise RuntimeError("original frozen group set mismatch")
    if len(details) != len(detail_rows) or not set(details) <= expected:
        raise RuntimeError("supplemental group identity mismatch")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    counts = {}
    with (out/"classification.jsonl").open("w") as ledger:
        for i, row in enumerate(original, 1):
            key = row["cell"], row["group"]
            detail = details.get(key)
            early = [j for j, r in enumerate(row["settings"][0]["records"])
                     if r["kind"] == "early_exercise_vs_continuation"]
            decisions = [one(row, detail, j, cfg["gap_floor"], cfg["root_tolerance"])
                         for j in early]
            for decision in decisions:
                status = decision["status"]
                counts[status] = counts.get(status, 0) + 1
            ledger.write(json.dumps(dict(cell=key[0], group=key[1],
                                         decisions=decisions)) + "\n")
            ledger.flush()
            print(json.dumps(dict(completed=i, frozen=len(expected))), flush=True)
    (out/"summary.json").write_text(json.dumps(dict(completed=len(original),
        frozen=len(expected), decision_counts=counts, scope="exploratory topology classification"),
        indent=2) + "\n")


if __name__ == "__main__":
    main()
