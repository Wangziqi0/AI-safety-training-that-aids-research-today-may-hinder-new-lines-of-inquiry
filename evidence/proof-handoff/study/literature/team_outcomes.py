"""Tabulate reproduction and error detection on the same public team record.

Input is either the authors' cleaned CC BY 4.0 RDS at SOURCE, or the bundled
anonymous team_endpoints.csv. CSV replay uses only the Python standard library.
Use --export-csv with the RDS to regenerate the three-column CSV.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path


REVISION = "c2721bb6c2ddfad2633d9ab0a01dc514ec956923"
SOURCE = f"https://raw.githubusercontent.com/I4Replication/AI-Games/{REVISION}/data/AI%20games.rds"
DIGEST = "0f69c9d842cb25dfb6b79aa48dd8c0202c53802bb53d6d024a8574dc86bebb86"
CSV_DIGEST = "3b514e3598e6f6cbd12ae5e31a63400c3e5f0a50374297e0cdaaf90e1642b7b2"
MODES = ("Human-Only", "AI-Assisted", "AI-Led")
HEADER = ("mode", "reproduced", "major_errors")


def read_teams(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if path.suffix.lower() == ".csv":
        if digest != CSV_DIGEST:
            raise ValueError("CSV differs from the pinned numeric input")
        with path.open(newline="", encoding="utf-8") as source:
            reader = csv.reader(source)
            if tuple(next(reader)) != HEADER:
                raise ValueError("Unexpected CSV columns")
            return [tuple(int(x) if x else None for x in row) for row in reader]
    if digest != DIGEST:
        raise ValueError("RDS differs from the pinned public source")
    import pandas as pd
    import pyreadr

    selected = pyreadr.read_r(str(path))[None][["branch", "reproduction", "major_errors"]]
    teams = []
    for mode, reproduced, major in selected.itertuples(index=False, name=None):
        if pd.isna(mode) or mode not in MODES:
            raise ValueError("Unexpected or missing team assignment")
        if pd.notna(major) and (major < 0 or int(major) != major):
            raise ValueError("Expected nonnegative integer error counts")
        if pd.notna(reproduced) and reproduced not in (0, 1):
            raise ValueError("Expected a binary reproduction indicator")
        teams.append((MODES.index(mode), None if pd.isna(reproduced) else int(reproduced),
                      None if pd.isna(major) else int(major)))
    return teams


def summarize(teams):
    if {record[0] for record in teams} != set(range(len(MODES))):
        raise ValueError("Unexpected or missing team assignment")
    rows = []
    for code, mode in enumerate(MODES):
        group = [(r, m) for arm, r, m in teams if arm == code]
        observed = [(r, m) for r, m in group if r is not None and m is not None]
        cells = {
            "reproduced_and_major": sum(r == 1 and m >= 1 for r, m in observed),
            "reproduced_no_major": sum(r == 1 and m == 0 for r, m in observed),
            "no_reproduction_major": sum(r == 0 and m >= 1 for r, m in observed),
            "neither": sum(r == 0 and m == 0 for r, m in observed),
        }
        if sum(cells.values()) != len(observed):
            raise ValueError("Joint table does not exhaust observed teams")
        rows.append({
            "mode": mode,
            "teams": len(group),
            "missing_reproduction": sum(r is None for r, _ in group),
            "missing_major_count": sum(m is None for _, m in group),
            "missing_either": len(group) - len(observed),
            **cells,
            "total_major_errors": sum(m for _, m in group if m is not None),
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Pinned RDS or anonymous three-column CSV")
    parser.add_argument("--export-csv", type=Path, help="Export sorted anonymized rows from the RDS")
    args = parser.parse_args()
    teams = read_teams(args.input)
    if args.export_csv:
        if args.input.suffix.lower() == ".csv":
            parser.error("Export requires the authors' RDS as input")
        with args.export_csv.open("w", newline="", encoding="utf-8") as output:
            writer = csv.writer(output, lineterminator="\n")
            writer.writerow(HEADER)
            writer.writerows(sorted(teams, key=lambda row: tuple(-1 if x is None else x for x in row)))
        if hashlib.sha256(args.export_csv.read_bytes()).hexdigest() != CSV_DIGEST:
            raise ValueError("Export differs from the pinned three-column CSV")
    print(json.dumps({
        "study": "Brodeur et al., PNAS 123, e2524747123 (2026)",
        "source": SOURCE,
        "data_license": "CC BY 4.0",
        "sha256": DIGEST,
        "rows": summarize(teams),
    }, indent=2))


if __name__ == "__main__":
    main()
