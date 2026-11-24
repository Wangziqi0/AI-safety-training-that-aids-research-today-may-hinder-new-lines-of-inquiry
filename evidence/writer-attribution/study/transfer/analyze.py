"""Join the opaque key only after a reviewer has locked all 72 scientific ratings."""
import argparse
import csv
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

from exact import ROOT
from mask import rows

TASKS = tuple(f"T{i:02}" for i in range(1, 9))
SEEDS = (311, 617, 929)


def subset(row):
    yield "all"
    yield "math" if row["task"] < "T05" else "data"
    yield row["task"]
    yield "seed_" + str(row["seed"])


def binary(value):
    if value in ("1", "0"):
        return int(value)
    if value in ("", "NA", "UNASSESSABLE"):
        return None
    raise ValueError(value)


def write_tsv(directory, name, values):
    with (directory / name).open("w", newline="") as f:
        out = csv.DictWriter(f, fieldnames=tuple(values[0]), delimiter="\t", lineterminator="\n")
        out.writeheader()
        out.writerows(values)


def compare(index, arm1, arm2, kind, group):
    cases = [(index[arm1, s, t], index[arm2, s, t]) for s in SEEDS for t in TASKS
             if group in set(subset(index[arm1, s, t]))]
    transitions = Counter((a[kind], b[kind]) for a, b in cases)
    positive = transitions[1, 0]
    negative = transitions[0, 1]
    equal_success = transitions[1, 1]
    equal_fail = transitions[0, 0]
    assessed = positive + negative + equal_success + equal_fail
    # Each missing pair has its own margins. Known zeros/ones constrain its extremal effects.
    low = sum((a[kind] if a[kind] is not None else 0) -
              (b[kind] if b[kind] is not None else 1) for a, b in cases)
    high = sum((a[kind] if a[kind] is not None else 1) -
               (b[kind] if b[kind] is not None else 0) for a, b in cases)
    return dict(group=group, contrast=f"{arm1}-{arm2}", endpoint=kind, planned_pairs=len(cases),
                assessed_pairs=assessed, left_only=positive, right_only=negative,
                both_success=equal_success, neither=equal_fail, unknown=len(cases) - assessed,
                paired_percentage_points=(round(100 * (positive-negative) / assessed, 4) if assessed else None),
                all_planned_lower_pp=round(100 * low / len(cases), 4),
                all_planned_upper_pp=round(100 * high / len(cases), 4))


def main(grade_file, digest, output_dir=ROOT):
    if hashlib.sha256(grade_file.read_bytes()).hexdigest() != digest:
        raise ValueError("Blind grades differ from the independently locked digest.")
    with grade_file.open(newline="") as f:
        blind = list(csv.DictReader(f, delimiter="\t"))
    indexed = {r["note_id"]: r for r in blind}
    keys = rows("internal/writer_allocation.jsonl")
    telemetry = {r["note_id"]: r for r in rows("blind/writer_telemetry.jsonl")}
    assert len(blind) == len(indexed) == len(keys) == 72
    assert set(indexed) == set(telemetry) == {r["note_id"] for r in keys}
    resolved = []
    for key in keys:
        grade = indexed[key["note_id"]]
        assert grade["task"] == key["task"]
        row = dict(key)
        row.update({k: v for k, v in grade.items() if k not in ("note_id", "task")})
        row.update({k: v for k, v in telemetry[key["note_id"]].items() if k != "note_id"})
        row["actionable"] = binary(row["actionable"])
        row["full_exact"] = binary(row["full_exact"])
        resolved.append(row)
    resolved.sort(key=lambda r: (r["task"], r["seed"], r["arm"]))
    selected = {(r["arm"], r["seed"], r["task"]): r for r in resolved}
    assert len(selected) == 72
    write_tsv(output_dir, "writer_scores.tsv", resolved)
    groups = ("all", "math", "data", *TASKS, *(f"seed_{seed}" for seed in SEEDS))
    contrasts = [compare(selected, a, b, endpoint, group) for a, b in (("A", "H"), ("B", "H"), ("B", "A"))
                 for endpoint in ("actionable", "full_exact") for group in groups]
    write_tsv(output_dir, "paired_comparisons.tsv", contrasts)
    counts = []
    for group in groups:
        for arm in "AHB":
            arm_rows = [r for r in resolved if r["arm"] == arm and group in set(subset(r))]
            n = len(arm_rows)
            counts.append(dict(group=group, arm=arm, notes=n,
                               actionable=sum(r["actionable"] == 1 for r in arm_rows),
                               actionable_missing=sum(r["actionable"] is None for r in arm_rows),
                               full_exact=sum(r["full_exact"] == 1 for r in arm_rows),
                               exact_missing=sum(r["full_exact"] is None for r in arm_rows),
                               codes=json.dumps(Counter(r["code"] for r in arm_rows), sort_keys=True),
                               truncated=sum(r["truncated"] for r in arm_rows),
                               tokens_median=statistics.median(r["tokens"] for r in arm_rows),
                               tokens_min=min(r["tokens"] for r in arm_rows),
                               tokens_max=max(r["tokens"] for r in arm_rows)))
    write_tsv(output_dir, "arm_summary.tsv", counts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("locked_grades", type=Path)
    parser.add_argument("sha256")
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    args = parser.parse_args()
    main(args.locked_grades, args.sha256, args.output_dir)
