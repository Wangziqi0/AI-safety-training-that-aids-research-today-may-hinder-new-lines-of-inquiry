"""Independent, exact, finite references for the eight supplied research records."""
import csv
import hashlib
import itertools
import json
import math
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "public/team_endpoints.csv"
DATA_DIGEST = "3b514e3598e6f6cbd12ae5e31a63400c3e5f0a50374297e0cdaaf90e1642b7b2"


def scientific_references():
    edges = [(v, (v + 1) % 5) for v in range(5)]
    color_counts = {
        n: sum(all(word[a] != word[b] for a, b in edges)
               for word in itertools.product(range(n), repeat=5))
        for n in (1, 2, 3)
    }
    color_witness = (0, 1, 0, 1, 2)
    assert all(color_witness[a] != color_witness[b] for a, b in edges)

    intervals = [(0, 4), (3, 7), (4, 8)]
    robust = [{x for x in range(9) if all(lo <= x + e <= hi for e in (-1, 0, 1))}
              for lo, hi in intervals]
    min_sets = [p for p in itertools.combinations(range(9), 2)
                if all(set(p) & possible for possible in robust)]
    assert not set.intersection(*robust) and (2, 5) in min_sets

    transcripts = {}
    for j in range(1, 9):
        lo, hi = 1, 8
        replies = []
        while lo < hi:
            k = (lo + hi) // 2
            answer = j <= k
            replies.append([k, answer])
            if answer:
                hi = k
            else:
                lo = k + 1
        assert lo == j and len(replies) == 3
        transcripts[str(j)] = dict(steps=replies, witness=2 * lo)

    def separated(i, j):
        return (i ^ j).bit_count() >= 3

    # Translating all words by bitwise XOR lets us fix the first word at 0.
    code_counts = {n: sum(separated(0, x) and separated(0, y) and separated(x, y)
                          for x, y in itertools.combinations(range(1, 1 << n), 2))
                   for n in range(1, 6)}
    words = ("00000", "11100", "10011")
    balls = [{x for x in range(32) if (x ^ int(w, 2)).bit_count() <= 1} for w in words]
    assert all(len(b) == 6 for b in balls)
    assert all(not a & b for a, b in itertools.combinations(balls, 2))

    assert hashlib.sha256(DATA.read_bytes()).hexdigest() == DATA_DIGEST
    with DATA.open(newline="") as file:
        reader = csv.DictReader(file)
        assert reader.fieldnames == ["mode", "reproduced", "major_errors"]
        rows = [tuple(int(row[k]) for k in reader.fieldnames) for row in reader]
    assert len(rows) == 103 and all(m in range(3) and r in (0, 1) and d >= 0 for m, r, d in rows)
    summary = []
    for m in range(3):
        group = [(r, d) for mode, r, d in rows if mode == m]
        cells = Counter((r, int(d > 0)) for r, d in group)
        joint = cells[1, 1]
        complete = joint + cells[1, 0]
        detect = joint + cells[0, 1]
        total = len(group)
        possible = [x for x in range(total + 1) if x <= min(complete, detect)
                    and total - complete - detect + x >= 0]
        summary.append(dict(mode=m, n=total, reproduced=complete, with_major=detect,
                            total_accepted_major=sum(d for _, d in group), joint=joint,
                            bounds=[min(possible), max(possible)],
                            full_rate=f"{joint}/{total}", completed_rate=f"{joint}/{complete}",
                            eligible_upgrades=cells[1, 0]))
    human, assisted, led = summary
    joint_total = human["joint"] + assisted["joint"]
    n_human, n_assisted = human["n"], assisted["n"]
    denominator = math.comb(n_human + n_assisted, joint_total)
    weights = {k: math.comb(n_human, k) * math.comb(n_assisted, joint_total - k)
               for k in range(max(0, joint_total - n_assisted), min(n_human, joint_total) + 1)}
    assert sum(weights.values()) == denominator
    accepted = [k for k, w in weights.items() if w <= weights[human["joint"]]]
    fisher = Fraction(sum(weights[k] for k in accepted), denominator)
    human_rate = Fraction(human["joint"], n_human)
    tipping = {}
    for arm in (assisted, led):
        n, j = arm["n"], arm["joint"]
        tipping[str(arm["mode"])] = {
            "eligible": arm["eligible_upgrades"],
            "first_k_matching_or_exceeding": next((k for k in range(arm["eligible_upgrades"] + 1)
                                                   if Fraction(j + k, n) >= human_rate), None),
            "upper_rate": f"{j + arm['eligible_upgrades']}/{n}",
        }
    return {
        "T01": dict(valid_colorings=color_counts, feasible_witness=color_witness),
        "T02": dict(robust_commands=[sorted(s) for s in robust], minimal_command_sets=min_sets),
        "T03": dict(transcripts=transcripts, two_query_leaf_limit=4),
        "T04": dict(valid_unordered_pairs_with_zero_word=code_counts,
                    feasible_code=words, disjoint_radius_one_ball_sizes=[len(b) for b in balls]),
        "T05": summary,
        "T06": [{k: row[k] for k in ("mode", "completed_rate", "full_rate")} for row in summary],
        "T07": dict(successes=[human["joint"], assisted["joint"]], totals=[n_human, n_assisted],
                    exact_two_sided_conditional_p=str(fisher), decimal_p=float(fisher),
                    excluded_more_probable_k=sorted(weights.keys() - set(accepted)),
                    difference_percentage_points=float(100 * (human_rate - Fraction(assisted["joint"], n_assisted)))),
        "T08": dict(fixed_comparator=str(human_rate), sensitivity=tipping),
    }


if __name__ == "__main__":
    print(json.dumps(scientific_references(), indent=2, sort_keys=True))
