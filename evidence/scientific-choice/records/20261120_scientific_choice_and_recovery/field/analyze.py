"""Rebuild idea-level pre/post comparisons from anonymized, pinned public ratings."""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import combinations
from pathlib import Path
from statistics import mean

import requests

ROOT = Path(__file__).resolve().parent
REV = "e5dd05a90bcadb436c07283c2f429367c6e525d3"
BASE = f"https://raw.githubusercontent.com/NoviScl/AI-Researcher/{REV}"
FILES = {"pre": "reviews_ideation/data_points_all_anonymized.json",
         "post": "reviews_execution/data_points_all_execution.json"}
METRICS = ["overall", "novelty", "effectiveness"]
COLUMNS = ["phase", "idea_id", "source"] + METRICS


def acquire():
    rows = []
    receipt = {}
    for phase, name in FILES.items():
        response = requests.get(f"{BASE}/{name}", timeout=40)
        response.raise_for_status()
        data = response.json()
        indices = range(len(data["idea_id"]))
        for i in indices:
            rows.append([phase, data["idea_id"][i], data["condition"][i],
                         *[int(data[m + "_score"][i]) for m in METRICS]])
        receipt[phase] = {"url": response.url, "sha256_original": hashlib.sha256(response.content).hexdigest(),
                          "reviews": len(indices), "unique_ideas": len(set(data["idea_id"])),
                          "conditions": dict(Counter(data["condition"]))}
    pre, post = ({r[1] for r in rows if r[0] == phase} for phase in FILES)
    receipt["overlap"] = {"both": len(pre & post), "pre_only": len(pre - post), "post_only": len(post - pre)}
    with (ROOT / "matched_ratings.csv").open("w") as handle:
        writer = csv.writer(handle); writer.writerow(COLUMNS)
        writer.writerows(r for r in rows if r[1] in pre & post)
    (ROOT / "acquisition.json").write_text(json.dumps(receipt, indent=2) + "\n")


def selection(ideas):
    result = Counter({x: 0 for x in ["retain", "reverse", "post_tie", "pre_tie"]})
    for a, b in combinations(ideas, 2):
        x = a["pre"]["overall"] - b["pre"]["overall"]
        y = a["post"]["overall"] - b["post"]["overall"]
        status = "pre_tie" if not x else "post_tie" if not y else "retain" if x*y > 0 else "reverse"
        result[status] += 1
    comparable = result["retain"] + result["reverse"] + result["post_tie"]
    return {**result, "comparable": comparable,
            "reverse_share": result["reverse"] / comparable if comparable else None}


def analyze():
    with (ROOT / "matched_ratings.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    records = defaultdict(list); sources = defaultdict(set)
    for row in rows:
        records[(row["phase"], row["idea_id"])].append(row)
        sources[row["idea_id"]].add(row["source"])
    ideas = []
    for project, group in sorted(sources.items()):
        assert len(group) == 1
        item = {"idea_id": project, "source": group.pop()}
        for phase in FILES:
            phase_rows = records[(phase, project)]
            item[phase] = {m: Fraction(sum(int(r[m]) for r in phase_rows), len(phase_rows)) for m in METRICS}
        ideas.append(item)
    counts = {p: dict(Counter(len(v) for (phase, _), v in records.items() if p == phase)) for p in FILES}
    results = {"matched_score_rows": {p: sum(r["phase"] == p for r in rows) for p in FILES},
               "reviews_per_idea_distribution": counts, "pairs": {}, "means": {}}
    for label in ["all", "AI", "Human"]:
        group = [i for i in ideas if label == "all" or i["source"] == label]
        results["pairs"][label] = selection(group)
        results["means"][label] = {}
        for metric in METRICS:
            pre = [i["pre"][metric] for i in group]; post = [i["post"][metric] for i in group]
            delta = [b - a for a, b in zip(pre, post)]
            results["means"][label][metric] = {"n": len(group), "pre": float(mean(pre)), "post": float(mean(post)),
                                         "change": float(mean(delta)), "up": sum(d > 0 for d in delta),
                                         "equal": sum(d == 0 for d in delta), "down": sum(d < 0 for d in delta)}
    loo = [selection(ideas[:k] + ideas[k+1:])["reverse_share"] for k in range(len(ideas))]
    results["leave_one_idea_out_reversal_range"] = [min(loo), max(loo)]
    (ROOT / "estimates.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    if parser.parse_args().fetch:
        acquire()
    analyze()
