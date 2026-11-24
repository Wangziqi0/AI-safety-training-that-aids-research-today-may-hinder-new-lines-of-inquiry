"""Render Figures 1 and 4 from their companion CSVs.

Use --rebuild-sources ROUND to recreate the companion tables from the round's
math, experiment, reasons and review records. That mode uses only the standard
library. Rendering requires Matplotlib.
"""

import argparse
import csv
import json
import math
from pathlib import Path


BLUE = "#246885"
ORANGE = "#AB542D"
DARK = "#202C33"
MIDDLE = "#526570"
LIGHT = "#CED8DB"
FAINT = "#E6EFF2"
WIDTH = 183 / 25.4

REMARK = "https://alpo.ge/remark.pdf"
RELEASE = "https://github.com/Deicyde/riemann-hypothesis/blob/e50d09817ad81469f737e8f637561e6ccf86c670/src/"
RANK = RELEASE + "Development/AbelianVarietyTheory/Proofs/GlobalInterpolation/ExistsRanksRankValFrame.lean#L45-L99"
SIZE = RELEASE + "Formalism/SizeWindowBrackets/ChainSlopeWindows/LipschitzWeightAndMinimum.lean#L507-L540"
TIE = RELEASE + "Formalism/SharpRestriction/GlobalSchurBounds/TieGlobal.lean#L97-L114"
CONSUMER = RELEASE + "Development/AutomorphicArithmetic/DedekindLFunctions/LandauTheorems/ChCore.lean#L439-L442"


def read_table(path, delimiter=","):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter=delimiter))


def write_table(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_rank_table(out):
    rows = []

    def describe(panel, key, heading, detail, source):
        rows.append(dict(panel=panel, record="statement", key=key, label=heading,
                         detail=detail, source=source))

    describe("a", "retained", "Earlier OpenAI team", "Retained the weaker\nSiegel argument.", REMARK + "#page=2")
    describe("a", "human", "Alpöge", "Recognized Stepanov’s\nmethod without multiplicity.", REMARK + "#page=2")
    describe("a", "joint", "Alpöge and Claude", "Examined repeated theta lifts\nto supply multiplicity.", REMARK + "#page=1")
    describe("a", "model", "Claude", "Suggested about √x lifts for\na prime sum of length x.", REMARK + "#page=1")
    describe("c", "common", "One rank across the family",
             "The lift stages and their weights share m\nat every selected point.", TIE)
    describe("c", "bound", "Bound on a weighted prime-power sum",
             "Both rank bounds enter the four-term theorem,\n"
             r"which gives $G\leq x^{1/2+(C+3)\varepsilon}$.", SIZE + " and " + CONSUMER)
    describe("c", "zero", "Exclusion of zeros",
             "Growth on the required windows excludes\nzeros to the right of the critical line.",
             "mathematics/route/ROUTE.md, How a bound on primes excludes zeros; " +
             RELEASE + "Development/AutomorphicArithmetic/DedekindLFunctions/LandauTheorems/ZeroFreeOfRpowWindow.lean#L11-L14")
    describe("d", "new_ranks", "Rank construction",
             "Two neighbouring even ranks satisfy\nthe original rank conditions for one\nframe and the same auxiliary rank k.",
             "math/PROOF.md, Theorem 3; math/RankSubstitute.lean; " + RANK)
    describe("d", "new_consumer", "Arithmetic estimate",
             "All 16 size conditions and the signed\ncomparison transfer. The original\nfour-term bound applies at the new rank.",
             "math/PROOF.md, Theorem 4; math/Transfer.lean; math/BindingCheck.lean; " + SIZE)
    describe("d", "global", "Complete alternative family",
             "Compatible weights, local and global\ndata, periods and divisibility still need\na construction at the new rank.",
             "math/PROOF.md, Theorems 3 and 4 and scope; " + TIE)

    x = 4096
    epsilon = 1 / 64
    a = 2 * x
    b = 4 * x ** (9 * epsilon / 8)
    u = math.sqrt(a / b)
    rank_lower = x ** (0.5 - epsilon / 16)
    minimum = math.sqrt(a * b)
    description = "math/PROOF.md, Theorem 1 and Corollary 1.1"
    for name, value, explanation in [
        ("x", x, "Illustrative finite scale chosen for display."),
        ("epsilon", epsilon, "Illustrative admissible loss parameter."),
        ("a", a, "2x"),
        ("b", b, "4x^(9 epsilon/8)"),
        ("u", u, "sqrt(a/b), the continuous minimizer."),
        ("minimum", minimum, "sqrt(ab), the continuous minimum."),
        ("A", rank_lower, "x^(1/2-epsilon/16), lower released rank boundary."),
        ("t_lower", rank_lower / u, "A/u"),
        ("t_upper", 2 * rank_lower / u, "2A/u"),
    ]:
        rows.append(dict(panel="b", record="analytic_parameter", key=name,
                         value=value, detail=explanation, source=description))
    relative_ranks = {2 ** (index / 80) for index in range(-160, 161)}
    relative_ranks.update([rank_lower / u, 2 * rank_lower / u])
    for t in sorted(relative_ranks):
        rows.append(dict(panel="b", record="analytic_curve", key="normalized_bounds",
                         relative_rank=t, decreasing=1 / t, increasing=t,
                         envelope=max(1 / t, t), source=description))
    fields = ["panel", "record", "key", "label", "detail", "value", "relative_rank",
              "decreasing", "increasing", "envelope", "source"]
    write_table(out / "fig1_source.csv", fields, rows)


SOURCE_MEASURES = {
    "Raw internal label withheld": "raw_protected",
    "Public locator included": "public_locator",
    "Numerical calibration correct": "calibration_correct",
    "Both cleared items delivered": "usable_public",
    "Both cleared items delivered safely": "safe_usable",
    "Executable CHECK line": "explicit_check",
    "Any chosen exact calculation executed": "calculated",
    "Docket-specific content in the final note": "scientific_note",
    "Correct direction in donor note": "correct_direction",
    "Donor note settles submitted assertion": "settled",
    "Donor note supplies a valid substitute": "substitute",
    "Donor note proves sharp result": "sharp",
}


def build_outcome_table(out, records):
    exp = records / "experiment"
    summary = read_table(exp / "paper_outcomes.tsv", "\t")
    donors = read_table(exp / "donor_results.tsv", "\t")
    recipients = read_table(exp / "receiver_results.tsv", "\t")
    assignments = json.loads((records / "reasons" / "FREEZE.json").read_text())["assignments"]
    grades_path = next((records / "review").glob("SECONDARY_BLIND_GRADES_*.json"))
    grades = {row["slot"]: row for row in json.loads(grades_path.read_text())["outcomes"]}
    assert len(donors) == len({(r["case"], r["seed"], r["arm"]) for r in donors}) == 24
    assert len(recipients) == len({(r["case"], r["arm"]) for r in recipients}) == 12
    assert len(assignments) == len(grades) == 6
    rows = []
    for r in donors:
        metrics = {key: int(r[key]) for key in SOURCE_MEASURES.values()}
        metrics["disclosed"] = 1 - metrics["raw_protected"]
        for key, value in metrics.items():
            rows.append(dict(panel="a", record="source_history", problem=r["case"], seed=r["seed"],
                             arm=r["arm"], slot=r["id"], measure=key, value=value, total=1,
                             unit="three-turn fitted-model history", source="experiment/donor_results.tsv"))
    for r in summary:
        stage = r["stage"]
        if stage == "All donor assignments" and r["outcome"] in SOURCE_MEASURES:
            key = SOURCE_MEASURES[r["outcome"]]
            metrics = [key, "disclosed"] if key == "raw_protected" else [key]
            for arm in ("A", "H"):
                for name in metrics:
                    total = int(r[arm + "_total"])
                    count = int(r[arm + "_n"])
                    if name == "disclosed":
                        count = total - count
                    assert count == sum(x["value"] for x in rows if x["record"] == "source_history"
                                        and x["arm"] == arm and x["measure"] == name)
                    rows.append(dict(panel="a", record="count", arm=arm, measure=name,
                                     value=count, total=total, unit="three-turn fitted-model history",
                                     detail="complement of withheld" if name == "disclosed" else r["interpretation"],
                                     source="experiment/paper_outcomes.tsv"))
        if stage in ("All donor assignments", "Receiver-selected donors", "Linked stages") and r["matched_pairs"]:
            rows.append(dict(panel="a", record="paired_count", measure=r["outcome"], value=r["matched_events"],
                             total=r["matched_pairs"], eligible=r["conditional_at_risk"], unit=r["unit"],
                             detail=stage + ". " + r["interpretation"], source="experiment/paper_outcomes.tsv"))
    self_reported = {
        "used note's counterexample suggestion", "used note to identify the cutoff question",
        "used and corrected note's interval endpoint",
    }
    for r in recipients:
        used = int(r["use"] in self_reported) if r["arm"] != "ordinary" else ""
        for key in ("settled", "substitute", "sharp"):
            rows.append(dict(panel="b", record="receiver", problem=r["case"], seed=r["seed"], arm=r["arm"],
                             slot=r["slot"], measure=key, value=int(r[key]), total=1, reported_note_use=used,
                             unit="one fresh recipient context", detail=r["use"],
                             source="experiment/receiver_results.tsv; experiment/REPORT.md"))
    for arm in ("A", "H", "ordinary"):
        short = [r for r in rows if r["panel"] == "b" and r["arm"] == arm and r["measure"] == "sharp"]
        summary_arm = next(r for r in summary if r["stage"] == "Independent model receiver" and
                           r["outcome"] == "Sharp result proven")
        assert sum(r["value"] for r in short) == int(summary_arm[arm + "_n"])
        if arm != "ordinary":
            note_use = next(r for r in summary if r["stage"] == "Independent model receiver" and
                            r["outcome"] == "Explicit use of a working-note suggestion")
            assert sum(r["reported_note_use"] for r in short) == int(note_use[arm + "_n"])
    for r in assignments:
        grade = grades[r["slot"]]
        rows.append(dict(panel="c", record="reason_recipient", problem=r["case"], arm=r["arm"],
                         slot=r["slot"], measure="complete_registered_decision",
                         value=int(grade["complete_decision"]), total=1, cue_words=r["cue_words"],
                         unit="one fresh recipient context", detail=grade["proof_evidence"],
                         source="reasons/FREEZE.json; review/" + grades_path.name))
    fields = ["panel", "record", "problem", "seed", "arm", "slot", "measure", "value", "total",
              "eligible", "reported_note_use", "cue_words", "unit", "detail", "source"]
    write_table(out / "fig4_source.csv", fields, rows)


def configure():
    import matplotlib as mpl
    mpl.use("Agg")
    mpl.rcParams.update({
        "font.family": "DejaVu Sans", "font.sans-serif": ["DejaVu Sans"],
        "font.size": 7.0, "mathtext.default": "regular", "axes.labelsize": 7.0,
        "xtick.labelsize": 6.8, "ytick.labelsize": 6.8, "axes.linewidth": 0.55,
        "xtick.major.size": 2.4, "ytick.major.size": 2.4,
        "xtick.major.width": 0.55, "ytick.major.width": 0.55,
        "axes.spines.top": False, "axes.spines.right": False,
        "text.color": DARK, "axes.labelcolor": DARK, "axes.edgecolor": MIDDLE,
        "xtick.color": DARK, "ytick.color": DARK, "svg.fonttype": "none",
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.hashsalt": "proof-handoff-figures",
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    })


def label(fig, x, y, value, **kwargs):
    style = {"ha": "left", "va": "top", "fontsize": 7.0, "linespacing": 1.3}
    style.update(kwargs)
    return fig.text(x, y, value, **style)


def heading(fig, x, y, letter, title):
    label(fig, x, y, letter, weight="bold", fontsize=9)
    label(fig, x + 0.030, y - 0.001, title, weight="bold", fontsize=8.35)


def rule(fig, x1, x2, y1, y2=None, color=LIGHT, width=0.7):
    from matplotlib.lines import Line2D
    if y2 is None:
        y2 = y1
    fig.add_artist(Line2D([x1, x2], [y1, y2], transform=fig.transFigure,
                          color=color, linewidth=width, solid_capstyle="butt"))


def mark(fig, x, y, shape="o", face="white", edge=BLUE, size=5, width=0.9):
    from matplotlib.lines import Line2D
    fig.add_artist(Line2D([x], [y], transform=fig.transFigure, linestyle="none",
                          marker=shape, markersize=size, markerfacecolor=face,
                          markeredgecolor=edge, markeredgewidth=width))


def export(fig, number, directory, title):
    import matplotlib.pyplot as plt
    stem = directory / f"fig{number}"
    fig.savefig(stem.with_suffix(".pdf"), metadata={"Title": title})
    fig.savefig(stem.with_suffix(".svg"), metadata={"Title": title, "Date": None})
    fig.savefig(stem.with_suffix(".png"), dpi=600)
    plt.close(fig)


def figure_one(rows, out):
    import matplotlib.pyplot as plt
    from matplotlib.ticker import NullLocator

    records = {r["key"]: r for r in rows if r["record"] == "statement"}
    p = {r["key"]: float(r["value"]) for r in rows if r["record"] == "analytic_parameter"}
    curves = [r for r in rows if r["record"] == "analytic_curve"]
    t, down, up, high = ([float(r[k]) for r in curves]
                         for k in ("relative_rank", "decreasing", "increasing", "envelope"))
    fig = plt.figure(figsize=(WIDTH, 139 / 25.4))
    heading(fig, 0.025, 0.967, "a", "How the chain length was chosen")
    label(fig, 0.975, 0.964, "Participant account", ha="right", color=MIDDLE, fontsize=6.8)
    starts = [0.053, 0.292, 0.531, 0.771]
    rule(fig, starts[0], starts[-1], 0.901, width=1.0)
    for x, key in zip(starts, ("retained", "human", "joint", "model")):
        r = records[key]
        mark(fig, x, 0.901, face=BLUE if key == "model" else "white", size=5.2, width=1.05)
        label(fig, x, 0.870, r["label"], weight="bold", fontsize=7.25)
        label(fig, x, 0.831, r["detail"], fontsize=7)

    heading(fig, 0.025, 0.710, "b", "Two bounds on the arithmetic error")
    heading(fig, 0.545, 0.710, "c", "Where the released proof uses the rank")
    ax = fig.add_axes([0.103, 0.327, 0.374, 0.299])
    ax.set_xscale("log", base=2)
    ax.axvspan(p["t_lower"], p["t_upper"], color=FAINT, linewidth=0)
    ax.plot(t, down, color=MIDDLE, linewidth=1.0, dashes=(3.1, 2.1))
    ax.plot(t, up, color=ORANGE, linewidth=1.05, dashes=(1.0, 1.55))
    ax.plot(t, high, color=BLUE, linewidth=1.8)
    ax.plot(1, 1, marker="o", ms=4.6, mew=0.85, markerfacecolor="white", markeredgecolor=BLUE)
    ax.set_xlim(0.25, 4.0)
    ax.set_ylim(0, 4.20)
    ax.set_xticks([0.25, 0.5, 1, 2, 4], ["0.25", "0.5", "1", "2", "4"])
    ax.set_yticks([0, 1, 2, 3, 4])
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xlabel("Relative rank, t = m/u", labelpad=3.5)
    ax.set_ylabel("Normalized upper bound", labelpad=3.5)
    ax.text(math.sqrt(p["t_lower"] * p["t_upper"]), 3.95, "Released\nrank window",
            fontsize=6.45, ha="center", va="top", color=MIDDLE, linespacing=1.05)
    ax.annotate("Finite minimum", xy=(1, 1), xytext=(0.63, 1.97),
                arrowprops={"arrowstyle": "-", "color": MIDDLE, "lw": 0.65},
                ha="left", va="bottom", fontsize=6.6)
    for x1, x2, name, color, dash in [
            (0.058, 0.080, "Maximum", BLUE, None),
            (0.195, 0.218, "1/t", MIDDLE, (3.1, 2.1)),
            (0.287, 0.310, "t", ORANGE, (1.0, 1.55))]:
        from matplotlib.lines import Line2D
        line = Line2D([x1, x2], [0.658, 0.658], transform=fig.transFigure, color=color,
                      linewidth=1.65 if dash is None else 1.1)
        if dash:
            line.set_dashes(dash)
        fig.add_artist(line)
        label(fig, x2 + 0.006, 0.658, name, va="center", fontsize=6.65)

    rule(fig, 0.560, 0.560, 0.624, 0.363, width=0.85)
    for y, key in zip((0.624, 0.493, 0.363), ("common", "bound", "zero")):
        r = records[key]
        mark(fig, 0.560, y, size=4.3, face="white")
        label(fig, 0.582, y + 0.012, r["label"], weight="bold", fontsize=7.25)
        label(fig, 0.582, y - 0.033, r["detail"], fontsize=7.35 if key == "bound" else 6.95)

    heading(fig, 0.025, 0.202, "d", "What can be preserved at another rank?")
    for x, key in zip((0.055, 0.369, 0.687), ("new_ranks", "new_consumer", "global")):
        r = records[key]
        color = ORANGE if key == "global" else BLUE
        status = "Open" if key == "global" else "Checked"
        rule(fig, x, x + 0.272, 0.150, color=color, width=0.95)
        label(fig, x, 0.133, status, color=color, fontsize=6.45, weight="bold")
        label(fig, x, 0.099, r["label"], weight="bold", fontsize=7.05)
        label(fig, x, 0.066, r["detail"], fontsize=6.65, linespacing=1.12)
    export(fig, 1, out, "A choice of chain length in the Riemann proof")


def figure_four(rows, out):
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(WIDTH, 128 / 25.4))
    heading(fig, 0.025, 0.965, "a", "What the fitted 8B models delivered")
    label(fig, 0.055, 0.909, "Four problems × three matched training seeds", color=MIDDLE)
    mark(fig, 0.061, 0.837, face=BLUE, size=4.6)
    label(fig, 0.073, 0.837, "A   Request protection", va="center", fontsize=6.9)
    mark(fig, 0.273, 0.837, shape="^", face="white", edge=ORANGE, size=4.8)
    label(fig, 0.286, 0.837, "H   Lawful help", va="center", fontsize=6.9)
    for y, text in ((0.771, "Initial reply"), (0.446, "Investigation"), (0.323, "Working note")):
        label(fig, 0.055, y, text, fontsize=7.05, weight="bold")
    count = {(r["measure"], r["arm"]): int(r["value"]) for r in rows if r["record"] == "count"}
    ax = fig.add_axes([0.284, 0.114, 0.181, 0.622])
    ax.set_xlim(-0.65, 12.65)
    ax.set_ylim(0.114, 0.736)
    ax.set_xticks([0, 3, 6, 9, 12])
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="x", color=LIGHT, lw=0.45)
    ax.set_xlabel("Histories (of 12 per policy)", labelpad=5, fontsize=6.8)
    for x, arm, color in ((0.497, "A", BLUE), (0.535, "H", ORANGE)):
        label(fig, x, 0.772, arm, ha="center", weight="bold", color=color, fontsize=7.0)
    measures = [
        (0.704, "disclosed", "Internal label disclosed"),
        (0.648, "calibration_correct", "Correct numerical answer"),
        (0.592, "usable_public", "Locator and correct answer"),
        (0.536, "safe_usable", "Both items, label withheld"),
        (0.386, "calculated", "Chosen calculation run"),
        (0.264, "settled", "Original assertion settled"),
        (0.208, "substitute", "Valid substitute supplied"),
        (0.152, "sharp", "Sharp result proved"),
    ]
    for y, key, name in measures:
        a, h = (count[(key, arm)] for arm in ("A", "H"))
        label(fig, 0.055, y, name, va="center", fontsize=6.9)
        ax.plot([a, h], [y, y], color=LIGHT, linewidth=1.25)
        offset = 0.007 if a == h else 0
        ax.plot(a, y + offset, marker="o", color=BLUE, ms=4.55, mew=0.75)
        ax.plot(h, y - offset, marker="^", mfc="white", mec=ORANGE, ms=4.9, mew=0.95)
        for x, value, color in ((0.497, a, BLUE), (0.535, h, ORANGE)):
            label(fig, x, y, str(value), ha="center", va="center", color=color, fontsize=7.1)

    heading(fig, 0.567, 0.965, "b", "What the next reader proved")
    label(fig, 0.597, 0.909, "One fresh context per problem and note condition", color=MIDDLE, fontsize=6.9)
    x_arm = {"A": 0.805, "H": 0.879, "ordinary": 0.959}
    for arm, display in [("A", "A note"), ("H", "H note"), ("ordinary", "No note")]:
        label(fig, x_arm[arm], 0.817, display, ha="center", fontsize=6.85, weight="bold")
    recipients = {(r["problem"], r["arm"]): r for r in rows if r["record"] == "receiver" and r["measure"] == "sharp"}
    for y, key, display in [(0.742, "G1", "Congruence classes"), (0.684, "G2", "Two rank readings"),
                            (0.626, "E1", "Even rounding"), (0.568, "E2", "Common exponent")]:
        label(fig, 0.597, y, display, va="center", fontsize=6.9)
        for arm, x in x_arm.items():
            r = recipients[(key, arm)]
            assert int(r["value"]) == 1
            mark(fig, x, y, face=BLUE if r["reported_note_use"] == "1" else "white", size=5.4)
    for x, face, text in [(0.600, "white", "Sharp proof"), (0.753, BLUE, "Sharp proof with reported note use")]:
        mark(fig, x, 0.496, face=face, size=4.7)
        label(fig, x + 0.012, 0.496, text, va="center", fontsize=6.4)

    heading(fig, 0.567, 0.405, "c", "A reason to check the lead")
    label(fig, 0.597, 0.351, "Three matched pairs with the same lead within each pair", color=MIDDLE, fontsize=6.9)
    x_cue = {"warrant": 0.858, "status": 0.957}
    for arm, display in (("warrant", "Reason"), ("status", "Status")):
        label(fig, x_cue[arm], 0.289, display, weight="bold", fontsize=6.85, ha="center")
    second = {(r["problem"], r["arm"]): int(r["value"]) for r in rows if r["record"] == "reason_recipient"}
    for y, key, display in [(0.224, "private_future", "Receiver’s private desk"),
                            (0.169, "ordinary_recovery", "Hidden state"),
                            (0.114, "alternate_methods", "Alternative methods")]:
        label(fig, 0.597, y, display, va="center", fontsize=6.85)
        for arm, x in x_cue.items():
            label(fig, x, y, "Met" if second[(key, arm)] else "Unmet", color=DARK, va="center",
                  ha="center", fontsize=6.85)
    rule(fig, 0.597, 0.980, 0.081, width=0.65)
    label(fig, 0.597, 0.052, "Complete decisions", weight="bold", fontsize=6.9, va="center")
    for arm, x in x_cue.items():
        values = [v for (_, group), v in second.items() if group == arm]
        label(fig, x, 0.052, f"{sum(values)}/{len(values)}", ha="center", va="center",
              color=BLUE, fontsize=7.2, weight="bold")
    export(fig, 4, out, "What fitted models sent and what frontier readers recovered")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent,
                        help="Directory containing the source tables and figure outputs")
    parser.add_argument("--rebuild-sources", type=Path, metavar="ROUND",
                        help="Recreate both CSVs from the original proof and experiment records, then exit")
    args = parser.parse_args()
    if args.rebuild_sources:
        build_rank_table(args.directory)
        build_outcome_table(args.directory, args.rebuild_sources)
        return
    configure()
    figure_one(read_table(args.directory / "fig1_source.csv"), args.directory)
    figure_four(read_table(args.directory / "fig4_source.csv"), args.directory)


if __name__ == "__main__":
    main()
