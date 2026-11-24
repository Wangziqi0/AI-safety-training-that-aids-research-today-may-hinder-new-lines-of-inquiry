"""Recalculate the central comparisons from the review archive without hosted calls."""
import csv
import gzip
import json
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import combinations
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
RECORDS = ROOT / "records"
SIM = RECORDS / "20261119_sft_online_rl_structural_round"
OBS = RECORDS / "20261120_scientific_choice_and_recovery"


def rows(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        yield from (json.loads(line) for line in stream if line.strip())


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def instrument():
    comparisons = defaultdict(dict)
    for row in rows(SIM / "structural/outcomes.jsonl.gz"):
        if row["split"] == "heldout" and row["arm"] in ("H", "A"):
            key = tuple(row[k] for k in ("algo", "coupling", "seed", "family", "clone"))
            comparisons[key][row["arm"]] = (row["current_use"], row["later_use"])
    linked = defaultdict(set)
    counts = defaultdict(Counter)
    for (algorithm, coefficient, seed, family, clone), pair in comparisons.items():
        d1, d2 = (a-h for a, h in zip(pair["A"], pair["H"]))
        counts[algorithm, coefficient].update(n=1, current=d1, later=d2)
        if coefficient == "aligned" and (d1, d2) == (1, -1):
            linked[algorithm].add((seed, family, clone))
    assert len(linked["sft"]) == 36 and linked["sft"] == linked["reinforce"]
    service = defaultdict(Counter)
    for row in rows(SIM / "structural/deployment.jsonl.gz"):
        if row["case"] == 2:
            service[row["algo"], row["arm"]].update(n=1, leaks=row["leak"])
    for algorithm in ("sft", "reinforce"):
        for coefficient in ("aligned", "cut", "reversed"):
            assert counts[algorithm, coefficient]["n"] == 2304
        assert counts[algorithm, "cut"]["current"] == counts[algorithm, "cut"]["later"] == 0
        assert counts[algorithm, "reversed"]["current"] < 0 < counts[algorithm, "reversed"]["later"]
        assert service[algorithm, "H"]["n"] == service[algorithm, "A"]["n"] == 3072
    return {"paired_projects_per_algorithm": 2304, "shared_gain_and_loss_cases": len(linked["sft"]),
            "restricted_disclosures_A_H": {a:[service[a,g]["leaks"] for g in ("A","H")] for a in linked}}


def photometry():
    all_cases = list(rows(OBS / "downstream/standing_substitution.jsonl"))
    for batch in ("assigned_lock", "stewardship_lock"):
        assigned = [r for r in all_cases if r["batch"] == batch]
        assert len(assigned) == 72 and all(r["same_forecast"] for r in assigned)
    scored = list(rows(OBS / "downstream/assigned_lock/results.jsonl"))
    products = OBS / "downstream/assigned_lock/products"
    test_bins = {r["field"]:r["test_n"] for r in scored}
    assert len(test_bins) == 8 and sum(test_bins.values()) == 1159
    errors = []
    with np.load(products / "P06_observed.npz") as predictions:
        observations = predictions["spoc_flux"]
    for variant in ("ordinary", "handoff"):
        row = next(r for r in scored if r["field"] == "P06" and r["variant"] == variant)
        with np.load(products / (row["artifact"] + ".npz")) as data:
            error = float(np.mean(abs(data["prediction"] - observations)))
        assert abs(error - row["mae_electrons_s"]) < 1e-10
        errors.append(error)
    assert errors[0] > errors[1]
    primary = read(OBS / "analysis/FINITE_LINK.json")["primary"]
    assert primary["pair"]["A-H"]["full_linked_event"] == 0
    return {"fields":len(test_bins), "reserved_bins":sum(test_bins.values()),
            "ordinary_reconstruction_per_handoff":72, "PG_1520_MAE_electrons_per_second":errors}


def human_projects():
    table = list(csv.DictReader((OBS / "field/project_ratings.csv").open()))
    scores = [(Fraction(int(r["pre_total"]),int(r["pre_n"])),
               Fraction(int(r["post_total"]),int(r["post_n"]))) for r in table]
    counts = Counter()
    for (x0,x1),(y0,y1) in combinations(scores,2):
        if x0 != y0:
            counts["initially_ordered"] += 1
            counts["reversed"] += int((x0-y0)*(x1-y1) < 0)
    assert (len(table),counts["initially_ordered"],counts["reversed"]) == (43,814,404)
    return dict(projects=len(table), **counts)


def mathematical():
    check = OBS / "theory/direction_transport.py"
    result = json.loads(subprocess.check_output([sys.executable,str(check)],text=True))
    assert result["status"] == "PASS"
    example = read(OBS / "review/TRANSPORT_VERIFICATION.json")["many_to_many"]
    assert np.allclose(example["sharp"], [.4,.7])
    assert np.allclose(example["identity_ignored"], [.75,.85])
    return {"independent_transport_executable":result, "twenty_project_ranges":[[8,14],[15,17]]}


def figures():
    with tempfile.TemporaryDirectory() as scratch:
        directory=Path(scratch)
        subprocess.run([sys.executable,str(ROOT / "figures/extract_figure_data.py"),
                        str(RECORDS),"--out",str(directory)],check=True)
        for i in (1,2,3):
            name=f"fig{i}_source.csv"
            assert (directory / name).read_bytes() == (ROOT / "figures" / name).read_bytes(), name
    return "all three figure tables exactly regenerated"


if __name__ == "__main__":
    result = {"instrument":instrument(), "photometry":photometry(), "human_data":human_projects(),
              "theory":mathematical(), "figures":figures(), "new_model_calls":0}
    print(json.dumps(result,indent=2))
