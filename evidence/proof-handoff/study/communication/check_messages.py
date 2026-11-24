"""Exhaustive checks for the finite public-message proposition (stdlib only)."""
import argparse
import csv
import itertools
import json
from fractions import Fraction
from pathlib import Path


def optimal_points(jobs):
    possible = sorted(set().union(*jobs)) if jobs else []
    for count in range(len(possible) + 1):
        for points in itertools.combinations(possible, count):
            if all(set(points) & job for job in jobs):
                return list(points)
    return None


def greedy(intervals):
    remaining = list(intervals)
    points = []
    while remaining:
        point = min(max(interval) for interval in remaining)
        points.append(point)
        remaining = [interval for interval in remaining if point not in interval]
    return points


def packing(intervals):
    for count in range(len(intervals), -1, -1):
        for selected in itertools.combinations(intervals, count):
            if sum(map(len, selected)) == len(frozenset().union(*selected)):
                return count
    raise AssertionError("Empty family was not found")


def main(output):
    output.mkdir(exist_ok=True, parents=True)
    grid = [2, 4, 6, 8, 10]
    intervals = [frozenset(grid[left:right + 1]) for left in range(len(grid))
                 for right in range(left, len(grid))]
    histogram = {}
    checked = 0
    with (output / "interval_families.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["interval_ids_zero_based", "greedy_points", "optimal_points", "disjoint_count"])
        for size in range(5):
            for indices in itertools.combinations(range(len(intervals)), size):
                family = [intervals[i] for i in indices]
                chosen = greedy(family)
                exact = optimal_points(family)
                disjoint = packing(family)
                assert len(exact) == len(chosen) == disjoint
                writer.writerow([" ".join(map(str, indices)), " ".join(map(str, chosen)),
                                 " ".join(map(str, exact)), disjoint])
                histogram[disjoint] = histogram.get(disjoint, 0) + 1
                checked += 1

    bounds = [(4, 8), (8, 10), (12, 14)]
    jobs = [set(range(left, right + 1, 2)) for left, right in bounds]
    choices = {}
    for m in range(2, 31, 2):
        factor = max(max(Fraction(left, m), Fraction(m, right)) for left, right in bounds)
        choices[m] = factor
    optimal = min(choices, key=choices.get)
    assert optimal == 10 and choices[optimal] == Fraction(5, 4)
    assert len(optimal_points(jobs)) == 2 and len(optimal_points(jobs[:2])) == 1
    assert not (jobs[0] & jobs[2])
    disconnected = [{2, 4}, {4, 6}, {2, 6}]
    assert packing(disconnected) == 1 and len(optimal_points(disconnected)) == 2
    result = {
        "grid": grid, "intervals_by_id": [sorted(i) for i in intervals],
        "family_sizes": list(range(5)), "families_checked": checked,
        "histogram_minimum_messages": histogram, "mismatches": 0,
        "example_bounds": bounds, "example_witnesses": greedy(jobs),
        "one_message_costs": {m: str(q) for m, q in choices.items()},
        "one_message_best": {"witness": optimal, "multiplier": str(choices[optimal])},
        "compensated_witnesses": greedy(jobs[:2]), "unshareable_pair_intersection": [],
        "disconnected": {"packing": 1, "hitting_number": 2}
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"families_checked": checked, "mismatches": 0, "one_message_best": result["one_message_best"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output)
