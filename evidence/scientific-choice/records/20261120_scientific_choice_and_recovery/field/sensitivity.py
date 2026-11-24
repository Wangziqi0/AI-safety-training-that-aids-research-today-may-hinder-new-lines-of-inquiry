"""Post-hoc alternatives for topic comparability and sensitivity to individual ratings."""
from collections import Counter, defaultdict
import csv
from fractions import Fraction
from itertools import combinations
import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
rows = list(csv.DictReader((ROOT / "matched_ratings.csv").open()))
scores = defaultdict(list)
for row in rows:
    scores[row["idea_id"], row["phase"]].append(Fraction(row["overall"]))
projects = sorted({row["idea_id"] for row in rows})


def sign(number):
    return (number > 0) - (number < 0)


def directions(project_a, project_b, phase):
    """Range after dropping zero or one score per idea; identities are unavailable."""
    def estimates(project):
        values = scores[project, phase]
        return [mean(values)] + [(sum(values) - v) / (len(values) - 1) for v in values]
    a, b = estimates(project_a), estimates(project_b)
    return {sign(x - y) for x in a for y in b}


groups = defaultdict(Counter)
for a,b in combinations(projects, 2):
    pre = mean(scores[a, "pre"]) - mean(scores[b, "pre"])
    post = mean(scores[a, "post"]) - mean(scores[b, "post"])
    outcome = "entry_tie" if pre == 0 else "execution_tie" if post == 0 else "retain" if pre*post > 0 else "reverse"
    if a.split("_")[0] == b.split("_")[0]:
        groups["same_topic"][outcome] += 1
    if abs(pre) >= 1:
        groups["entry_margin_ge_one_point"][outcome] += 1
    if pre != 0:
        fixed_pre = directions(a,b,"pre") == {sign(pre)}
        fixed_post = directions(a,b,"post") == {sign(post)}
        if fixed_pre:
            groups["entry_order_survives_any_single_review_omission_per_idea"][outcome] += 1
        if fixed_pre and fixed_post:
            groups["both_orders_survive_any_single_review_omission_per_idea"][outcome] += 1
(ROOT / "sensitivity.json").write_text(json.dumps(groups, indent=2) + "\n")
