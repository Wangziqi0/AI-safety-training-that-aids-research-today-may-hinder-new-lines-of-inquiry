"""Sharp finite population-law bounds with newly recorded scientific directions.

Run with a Python environment containing NumPy and SciPy. The examples use
mathematical margins only. No model output or astronomy measurements are read.
"""
from dataclasses import dataclass
from itertools import product
import json

import numpy as np
from scipy.optimize import linprog


@dataclass(frozen=True)
class History:
    before: str
    after: tuple


def observed_cell(arm, regime, history):
    return history.before, history.after[regime]


def sharp_interval(left, right, left_law, right_law, event,
                   observe=observed_cell, allowed=None):
    """Fix all supplied per-regime projections and optimize a joint event.

    Each law lists one observed-cell distribution per regime, conditional on
    one common baseline stratum. Histories retain their shared pre-offer state.
    The optional observation map can coarsen this state or its continuations.
    Use allowed for known structural restrictions. A direction mismatch belongs
    in event unless external evidence rules that pair out as a possible world.
    """
    worlds = []
    projections = []
    for a, h in product(left, right):
        if allowed is not None and not allowed(a, h):
            continue
        projected = [
            tuple(observe(arm, r, history) for r in range(len(law)))
            for arm, history, law in (("A", a, left_law), ("H", h, right_law))
        ]
        if all(cell in law[r] for side, law in enumerate((left_law, right_law))
               for r, cell in enumerate(projected[side])):
            worlds.append((a, h))
            projections.append(projected)
    if not worlds:
        raise ValueError("No joint history has the observed support")

    constraints = [[1.] * len(worlds)]
    masses = [1.]
    for side, law in enumerate((left_law, right_law)):
        if not law:
            raise ValueError("Each workflow needs a measured regime")
        for r, margin in enumerate(law):
            if (not margin or min(margin.values()) < 0
                    or not np.isclose(sum(margin.values()), 1., rtol=0, atol=1e-10)):
                raise ValueError("Each regime margin must be a probability distribution")
            for cell, mass in margin.items():
                constraints.append([projected[side][r] == cell for projected in projections])
                masses.append(mass)
    matrix = np.asarray(constraints, dtype=float)
    target = np.asarray(masses, dtype=float)
    objective = np.array([event(a, h) for a, h in worlds], dtype=float)
    endpoints = []
    for sign in (1, -1):
        fit = linprog(sign * objective, A_eq=matrix, b_eq=target, method="highs")
        if not fit.success:
            raise ValueError(f"Incompatible observation law or optimizer failure: {fit.message}")
        np.testing.assert_allclose(matrix @ fit.x, target, rtol=0, atol=1e-9)
        endpoints.append(float(np.round(objective @ fit.x, 12)))
    return endpoints


def label_law(counts):
    histories = [History(name, (1,)) for name in counts]
    total = sum(counts.values())
    law = [{(name, 1): count / total for name, count in counts.items()}]
    return histories, law


def direction_examples():
    left_counts = {"alpha": 9, "beta": 7, "gamma": 2, "none": 2}
    right_counts = {"r": 6, "s": 6, "t": 5, "none": 3}
    compatible = {"alpha": {"r", "s"}, "beta": {"r", "s"}, "gamma": {"s", "t"}}
    left, left_law = label_law(left_counts)
    right, right_law = label_law(right_counts)

    def matched(a, h):
        return h.before in compatible.get(a.before, set())

    interval = sharp_interval(left, right, left_law, right_law, matched)
    binary = sharp_interval(left, right, left_law, right_law,
                            lambda a, h: a.before != "none" and h.before != "none")
    assert interval == [.40, .70] and binary == [.75, .85]
    lower = [[4, 0, 5, 0], [0, 4, 0, 3], [2, 0, 0, 0], [0, 2, 0, 0]]
    upper = [[6, 3, 0, 0], [0, 3, 3, 1], [0, 0, 2, 0], [0, 0, 0, 2]]
    for witness, endpoint in zip((lower, upper), interval):
        table = np.array(witness)
        np.testing.assert_array_equal(table.sum(axis=1), list(left_counts.values()))
        np.testing.assert_array_equal(table.sum(axis=0), list(right_counts.values()))
        hits = sum(table[i, j] for i, a in enumerate(left) for j, h in enumerate(right)
                   if matched(a, h))
        assert hits == round(endpoint * table.sum())

    red, red_law = label_law({"red": 1})
    blue, blue_law = label_law({"blue": 1})
    same = lambda a, h: a.before == h.before
    mismatch = sharp_interval(red, blue, red_law, blue_law, same)
    assert mismatch == [0., 0.]
    # Both A identities project to the same measured "unresolved" cell.
    def partial(arm, regime, history):
        return ("unresolved", 1) if arm == "A" else observed_cell(arm, regime, history)
    unresolved = sharp_interval(red + blue, red, [{("unresolved", 1): 1.}],
                                red_law, same, observe=partial)
    assert unresolved == [0., 1.]
    return {"many_to_many": {"A": left_counts, "H": right_counts,
                             "compatible": {name: sorted(partners) for name, partners in compatible.items()},
                             "sharp": interval, "identity_ignored": binary,
                             "lower_table": lower, "upper_table": upper},
            "observed_nonmatching_colours": mismatch, "unresolved_A_colour": unresolved}


def binary_histories(weights, probabilities):
    """Enumerate all cross-regime types while retaining each observed W margin."""
    width = len(probabilities[0])
    law = [{} for _ in range(width)]
    histories = []
    for index, weight in enumerate(weights):
        w = str(index)
        for r, probability in enumerate(probabilities[index]):
            for bit, p in ((0, 1 - probability), (1, probability)):
                if p > 0:
                    law[r][(w, bit)] = weight * p
        histories.extend(History(w, bits) for bits in product((0, 1), repeat=width))
    return histories, law


def competing_stratum(weights, probabilities, qualified, h):
    # The final A coordinate is joint candidate use and success. Each earlier
    # coordinate is the all-channel success of one distinct alternative policy.
    left, left_law = binary_histories(weights, probabilities)
    right, right_law = binary_histories([1], [[h]])

    def event(a, h_hist):
        return (qualified[int(a.before)] and a.after[-1] == 1
                and all(bit == 0 for bit in a.after[:-1]) and h_hist.after[0] == 1)

    lo = hi = 0.
    for weight, probs, qualifies in zip(weights, probabilities, qualified):
        if qualifies:
            *alternatives, v = probs
            lo += weight * max(0, v - sum(alternatives))
            hi += weight * min(v, 1 - max(alternatives))
    formula = [max(0, lo + h - 1), min(hi, h)]
    result = sharp_interval(left, right, left_law, right_law, event)
    np.testing.assert_allclose(result, formula, atol=1e-10, rtol=0)
    return result


def stratified_checks():
    x0 = competing_stratum([1.], [[0., 1.]], [True], 1.)
    x1 = competing_stratum([1.], [[1., 0.]], [True], 0.)
    baseline = np.mean([x0, x1], axis=0).tolist()
    assert baseline == [.5, .5]
    residual = competing_stratum([.5, .5], [[0., 1.], [1., 0.]], [True, True], 1.)
    assert residual == [.5, .5]
    # Three mutually exclusive substitute policies at each pre-offer history.
    m0 = competing_stratum([.5, .3, .2], [[.1, .15, .2, .95], [.3, .7, .2, .3],
                                          [.2, .1, .3, .7]], [True, True, False], .9)
    m1 = competing_stratum([.7, .3], [[.2, .1, .1, .9], [.3, .5, .6, .65]],
                            [True, True], .8)
    standardized = np.round(np.average([m0, m1], axis=0, weights=[.4, .6]), 12).tolist()
    return {"conditional_baseline_example": baseline, "invalid_pooled_upper": .25,
            "residual_history_example": residual, "three_alternatives": {
                "baseline_weights": [.4, .6], "conditional_intervals": [m0, m1],
                "standardized_sharp_interval": standardized}}


if __name__ == "__main__":
    print(json.dumps({"status": "PASS", **direction_examples(), **stratified_checks()}, indent=2))
