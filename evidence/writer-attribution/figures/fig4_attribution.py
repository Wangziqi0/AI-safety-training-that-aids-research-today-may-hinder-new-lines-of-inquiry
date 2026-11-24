"""Regenerate Figure 4 from fig4_source.csv, or rebuild that CSV from the study.

python fig4_attribution.py --build-sources ROUND   # standard library only
python fig4_attribution.py                        # requires Matplotlib
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


BLUE = "#246885"
ORANGE = "#AB542D"
DARK = "#202C33"
MIDDLE = "#53646C"
LIGHT = "#CED8DB"
FAINT = "#EEF3F4"
WIDTH = 183 / 25.4
HEIGHT = 153 / 25.4
SEEDS = ("311", "617", "929")
TASKS = {
    "T01": "Five-cycle messages",
    "T02": "Commands with error",
    "T03": "Threshold queries",
    "T04": "One-bit error code",
    "T05": "Joint outcome counts",
    "T06": "Conditional denominators",
    "T07": "Binary endpoint test",
    "T08": "Reporting sensitivity",
}
FIELDS = ["panel", "record", "task", "source_arm", "seed", "writer", "slot", "budget",
          "opportunity", "qualified", "measure", "value", "total", "detail", "source"]


def read_table(path, delimiter=","):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter=delimiter))


def build_sources(records, out):
    rows = []
    cross_name = "cross/paired_outcomes.tsv"
    history = read_table(records / cross_name, "\t")
    assert len(history) == len({r["history_id"] for r in history}) == 24
    for r in history:
        for writer in ("A", "H"):
            rows.append(dict(panel="a", record="archive_writer", task=r["case"], source_arm=r["history_arm"],
                             seed=r["seed"], writer=writer, slot=r[writer + "_joint_id"], budget=650,
                             opportunity=r["opportunity"], qualified=r["qualified"], measure="usable_reason",
                             value=r[writer + "_pass"], total=1, detail=r["archived_id"] + ", " + r[writer + "_grade"],
                             source=cross_name))
    for group, entries in (("A-origin", [r for r in history if r["history_arm"] == "A"]),
                           ("H-origin", [r for r in history if r["history_arm"] == "H"]),
                           ("all", history), ("qualified", [r for r in history if int(r["qualified"])])):
        for writer in ("A", "H"):
            rows.append(dict(panel="a", record="archive_summary", task=group, writer=writer, budget=650,
                             measure="usable_reason", value=sum(int(r[writer + "_pass"]) for r in entries),
                             total=len(entries), source=cross_name))
    for archive, key, title, text in [
            ("p86", "scale", "Counterexample at scale 9",
             "H obtained the counterexample. A passed it on with\nits mathematical basis. H omitted it."),
            ("p66", "exponent", "One exponent across two regimes",
             "Both writers lost the incompatibility at 5/8 and\nretained a valid weaker budget of 9/8.")]:
        r = next(r for r in history if r["archived_id"] == archive)
        rows.append(dict(panel="a", record="focal_example", task=r["case"], source_arm=r["history_arm"],
                         seed=r["seed"], slot=archive, measure=key, opportunity=r["opportunity"],
                         qualified=r["qualified"], value=title, detail=text,
                         source="cross/PRIMARY_REPORT.md; cross/graded_cells.tsv"))

    transfer = "analysis/transfer_initial/"
    short = read_table(records / transfer / "writer_scores.tsv", "\t")
    assert len(short) == len({(r["task"], r["seed"], r["arm"]) for r in short}) == 72
    short_key = {(r["task"], r["seed"], r["arm"]): int(r["actionable"]) for r in short}
    for r in short:
        rows.append(dict(panel="b", record="supplied_writer", task=r["task"], seed=r["seed"], writer=r["arm"],
                         slot=r["note_id"], budget=r["cap"], measure="usable_reason", value=r["actionable"],
                         total=1, detail=r["code"], source=transfer + "writer_scores.tsv"))
    states = {(1, 0): "A_only", (0, 1): "H_only", (1, 1): "both", (0, 0): "neither"}
    pair_counts = Counter()
    for task, label in TASKS.items():
        for seed in SEEDS:
            pair = states[(short_key[task, seed, "A"], short_key[task, seed, "H"])]
            pair_counts[pair] += 1
            rows.append(dict(panel="b", record="paired_seed", task=task, seed=seed, budget=650,
                             measure="paired_state", value=pair, detail=label, source=transfer + "writer_scores.tsv"))
    compare = next(r for r in read_table(records / transfer / "paired_comparisons.tsv", "\t")
                   if (r["group"], r["contrast"], r["endpoint"]) == ("all", "A-H", "actionable"))
    for key, field in [("A_only", "left_only"), ("H_only", "right_only"), ("both", "both_success"), ("neither", "neither")]:
        assert pair_counts[key] == int(compare[field])
        rows.append(dict(panel="b", record="paired_total", budget=650, measure=key,
                         value=compare[field], total=compare["assessed_pairs"], source=transfer + "paired_comparisons.tsv"))
    for r in read_table(records / transfer / "arm_summary.tsv", "\t"):
        applicable = [s for s in short if s["arm"] == r["arm"] and
                      (r["group"] == "all" or s["task"] == r["group"] or s["seed"] == r["group"] or
                       (r["group"] == "math" and s["task"] <= "T04") or
                       (r["group"] == "data" and s["task"] >= "T05"))]
        if applicable:
            assert len(applicable) == int(r["notes"])
            assert sum(int(s["actionable"]) for s in applicable) == int(r["actionable"])
        rows.append(dict(panel="b", record="supplied_summary", task=r["group"], writer=r["arm"], budget=650,
                         measure="usable_reason", value=r["actionable"], total=r["notes"],
                         detail=TASKS.get(r["group"], ""), source=transfer + "arm_summary.tsv"))

    budget_file = "analysis/heldout_budget.tsv"
    budget = read_table(records / budget_file, "\t")
    assert len(budget) == len({(r["task"], r["seed"], r["arm"]) for r in budget}) == 48
    for r in budget:
        assert short_key[r["task"], r["seed"], r["arm"]] == int(r["short_pass"])
        for name, cap in (("short", 650), ("long", 1300)):
            rows.append(dict(panel="c", record="budget_writer", task=r["task"], seed=r["seed"], writer=r["arm"],
                             slot=r[name + "_id"], budget=cap, measure="usable_reason", value=r[name + "_pass"],
                             total=1, detail="token_prefix_match=" + r["prefix"] + ", identical_output=" + r["unchanged"],
                             source=budget_file))
    checked = json.loads((records / "analysis/heldout_budget.json").read_text())
    for row in checked["groups"]:
        subset = row["subset"]
        arm_rows = [r for r in budget if r["arm"] == row["arm"] and
                    (subset == "all" or (subset == "math" and r["task"] <= "T04") or
                     (subset == "data" and r["task"] >= "T05"))]
        for name, cap in (("short", 650), ("long", 1300)):
            result = sum(int(r[name + "_pass"]) for r in arm_rows)
            assert result == row[name + "_pass"] and len(arm_rows) == row["n"]
            rows.append(dict(panel="c", record="budget_summary", task=subset, writer=row["arm"], budget=cap,
                             measure="usable_reason", value=result, total=len(arm_rows), source=budget_file))
    long_pairs = Counter()
    long_by_cell = {(r["task"], r["seed"], r["arm"]): int(r["long_pass"]) for r in budget}
    for task in TASKS:
        for seed in SEEDS:
            long_pairs[states[(long_by_cell[task, seed, "A"], long_by_cell[task, seed, "H"])]] += 1
    assert dict(long_pairs) == checked["long_paired_transitions"]
    for key, v in long_pairs.items():
        rows.append(dict(panel="c", record="paired_total", budget=1300, measure=key, value=v, total=24,
                         source=budget_file))
    for measure, field in (("unchanged_outputs", "unchanged"), ("prefix_matches", "prefix")):
        rows.append(dict(panel="c", record="sequence_check", measure=measure,
                         value=sum(int(r[field]) for r in budget), total=len(budget), source=budget_file))
    ratings_name = "analysis/rating_sensitivity.json"
    ratings = json.loads((records / ratings_name).read_text())
    for group in ("archive", "archive_primary_qualified", "heldout"):
        for arm, r in ratings[group]["arm_counts"].items():
            for assessor in ("primary", "independent"):
                rows.append(dict(panel="c", record="assessor_summary", task=group, writer=arm, budget=650,
                                 measure=assessor, value=r[assessor], total=r["n"], source=ratings_name))
    worst = ratings["heldout"]["AH_worst_case_over_discrepant_grades"]
    for name in ("low_difference_count", "high_difference_count"):
        rows.append(dict(panel="c", record="assessor_range", task="heldout", budget=650, measure="A-H_" + name,
                         value=worst[name], total=worst["denominator"], source=ratings_name))

    reader_file = "downstream/recipients.tsv"
    readers = read_table(records / reader_file, "\t")
    assert len(readers) == len({(r["task"], r["arm"]) for r in readers}) == 18
    for r in readers:
        rows.append(dict(panel="d", record="recipient", task=r["task"], source_arm=r["study"], writer=r["arm"],
                         slot=r["slot"], measure="full_decision", value=r["full"], total=1,
                         detail=r["decision"], source=reader_file))
    for group in ("all", "historic", "heldout"):
        for writer in ("A", "H", "ordinary"):
            cells = [r for r in readers if r["arm"] == writer and (group == "all" or r["study"] == group)]
            rows.append(dict(panel="d", record="recipient_summary", task=group, writer=writer,
                             measure="full_decision", value=sum(int(r["full"]) for r in cells), total=len(cells),
                             source=reader_file))
    with (out / "fig4_source.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def configure():
    import matplotlib as mpl
    mpl.use("Agg")
    mpl.rcParams.update({
        "font.family": "DejaVu Sans", "font.sans-serif": ["DejaVu Sans"],
        "font.size": 7.0, "text.color": DARK, "axes.labelcolor": DARK,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "svg.hashsalt": "crossed-proof-writers", "figure.facecolor": "white",
        "axes.facecolor": "white", "savefig.facecolor": "white",
    })


def text(fig, x, y, value, *, size=7, color=DARK, bold=False, align="left", va="center", spacing=1.23):
    return fig.text(x, y, str(value), ha=align, va=va, fontsize=size, color=color,
                    weight="bold" if bold else "normal", linespacing=spacing)


def heading(fig, x, y, letter, title):
    text(fig, x, y, letter, size=9.0, bold=True, va="top")
    text(fig, x + 0.027, y - 0.001, title, size=8.1, bold=True, va="top")


def line(fig, x1, x2, y1, y2=None, *, color=LIGHT, width=0.65):
    from matplotlib.lines import Line2D
    if y2 is None:
        y2 = y1
    fig.add_artist(Line2D([x1, x2], [y1, y2], transform=fig.transFigure,
                          color=color, lw=width, solid_capstyle="butt"))


def shape(fig, x, y, state, size=5.0):
    from matplotlib.lines import Line2D
    styles = {
        "A_only": ("o", BLUE, BLUE), "H_only": ("^", ORANGE, ORANGE),
        "both": ("s", DARK, DARK), "neither": ("o", "white", MIDDLE),
    }
    marker, face, edge = styles[state]
    fig.add_artist(Line2D([x], [y], marker=marker, markerfacecolor=face,
                          markeredgecolor=edge, markeredgewidth=0.9, markersize=size,
                          linestyle="none", transform=fig.transFigure))


def ratio(row):
    return f"{row['value']}/{row['total']}"


def figure(rows, directory):
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(WIDTH, HEIGHT))
    heading(fig, 0.022, 0.977, "a", "More usable A notes on archived records")
    text(fig, 0.049, 0.920, "Four problems, three matched fits, two source policies", color=MIDDLE, size=6.65)
    text(fig, 0.049, 0.887, "A = request-level protection     H = lawful help", color=MIDDLE, size=6.45)
    left, xa, xh = 0.049, 0.335, 0.423
    for x, label, color in ((xa, "A writer", BLUE), (xh, "H writer", ORANGE)):
        text(fig, x, 0.851, label, bold=True, size=6.95, align="center", color=color)
    text(fig, left, 0.851, "Investigation record", color=MIDDLE, bold=True, size=6.7)
    line(fig, left, 0.460, 0.826)
    archives = {(r["task"], r["writer"]): r for r in rows if r["record"] == "archive_summary"}
    for y, key, label in ((0.792, "A-origin", "From A"), (0.747, "H-origin", "From H"),
                          (0.699, "all", "All archived episodes"),
                          (0.624, "qualified", "With a prequalified reason")):
        emphasis = key in ("all", "qualified")
        text(fig, left, y, label, bold=emphasis, size=7.0)
        for x, writer in ((xa, "A"), (xh, "H")):
            text(fig, x, y, ratio(archives[key, writer]), bold=emphasis, size=7.15, align="center",
                 color=BLUE if writer == "A" else ORANGE)
    line(fig, left, 0.460, 0.661)
    examples = {r["measure"]: r for r in rows if r["record"] == "focal_example"}
    for y, key in ((0.551, "scale"), (0.452, "exponent")):
        r = examples[key]
        text(fig, left, y, r["value"], va="top", bold=True, size=7.05)
        text(fig, left, y - 0.036, r["detail"], va="top", size=6.8)

    heading(fig, 0.482, 0.977, "b", "More usable H notes on supplied records")
    text(fig, 0.509, 0.920, "Eight verified records, one writer pair per task and seed", color=MIDDLE, size=6.65)
    xseed = dict(zip(SEEDS, (0.715, 0.760, 0.805)))
    xarm = {"A": 0.855, "H": 0.914, "B": 0.969}
    text(fig, 0.760, 0.873, "Training seed", align="center", color=MIDDLE, bold=True, size=6.55)
    text(fig, 0.914, 0.873, "Notes out of 3", align="center", color=MIDDLE, bold=True, size=6.55)
    text(fig, 0.509, 0.836, "Mathematics", color=MIDDLE, bold=True, size=6.8)
    for seed, x in xseed.items():
        text(fig, x, 0.836, seed, align="center", size=6.7, color=MIDDLE)
    for writer, x in xarm.items():
        color = {"A": BLUE, "H": ORANGE, "B": DARK}[writer]
        text(fig, x, 0.836, writer, bold=True, align="center", size=6.8, color=color)
    line(fig, 0.509, 0.979, 0.813)
    pairs = {(r["task"], r["seed"]): r["value"] for r in rows if r["record"] == "paired_seed"}
    supplied = {(r["task"], r["writer"]): r for r in rows if r["record"] == "supplied_summary"}
    yvals = [0.787, 0.749, 0.711, 0.673, 0.586, 0.548, 0.510, 0.472]
    for (task, name), y in zip(TASKS.items(), yvals):
        text(fig, 0.509, y, name, size=6.8)
        for seed, x in xseed.items():
            shape(fig, x, y, pairs[task, seed], 4.7)
        for writer, x in xarm.items():
            text(fig, x, y, supplied[task, writer]["value"], align="center", size=6.8)
    text(fig, 0.509, 0.630, "Reanalysis of one dataset", color=MIDDLE, bold=True, size=6.8)
    line(fig, 0.509, 0.979, 0.445)
    text(fig, 0.509, 0.421, "All supplied records", bold=True, size=6.95)
    for writer, x in xarm.items():
        text(fig, x, 0.421, ratio(supplied["all", writer]), bold=True, size=6.85, align="center",
             color={"A": BLUE, "H": ORANGE, "B": DARK}[writer])
    pair_total = {r["measure"]: int(r["value"]) for r in rows if r["record"] == "paired_total" and r["budget"] == "650"}
    for x, key, label in ((0.513, "A_only", "A only"), (0.626, "H_only", "H only"),
                          (0.744, "both", "Both"), (0.844, "neither", "Neither")):
        shape(fig, x, 0.367, key, 4.5)
        text(fig, x + 0.011, 0.367, f"{label} ({pair_total[key]})", size=6.55)

    heading(fig, 0.022, 0.305, "c", "Doubling the output allowance")
    text(fig, left, 0.252, "Usable notes per 24 paired assignments", color=MIDDLE, size=6.65)
    budget = {(r["budget"], r["writer"], r["task"]): r for r in rows if r["record"] == "budget_summary"}
    text(fig, left, 0.200, "Output allowance", color=MIDDLE, bold=True, size=6.7)
    for x, writer, color in ((xa, "A", BLUE), (xh, "H", ORANGE)):
        text(fig, x, 0.200, writer + " writer", bold=True, color=color, align="center", size=6.8)
    line(fig, left, 0.460, 0.179)
    for y, cap in ((0.150, "650"), (0.109, "1300")):
        text(fig, left, y, f"{int(cap):,} tokens", size=7)
        for writer, x in (("A", xa), ("H", xh)):
            text(fig, x, y, ratio(budget[cap, writer, "all"]), size=7.2, bold=True, align="center",
                 color=BLUE if writer == "A" else ORANGE)
    other = {r["writer"]: r for r in rows if r["record"] == "assessor_summary" and r["task"] == "heldout"
             and r["measure"] == "independent"}
    gains = int(budget["1300", "A", "data"]["value"]) - int(budget["650", "A", "data"]["value"])
    total_gains = int(budget["1300", "A", "all"]["value"]) - int(budget["650", "A", "all"]["value"])
    assert gains == total_gains
    text(fig, left, 0.062, f"All {gains} additional usable A notes concerned data reanalysis.", size=6.5)
    text(fig, left, 0.034, f"A second 650-token reading gave A {ratio(other['A'])} and H {ratio(other['H'])}.", size=6.5)

    heading(fig, 0.482, 0.305, "d", "What the independent reader recovered")
    text(fig, 0.509, 0.252, "Fully justified decisions, one reader per case and condition", color=MIDDLE, size=6.65)
    xrec = {"A": 0.800, "H": 0.885, "ordinary": 0.963}
    reader = {(r["task"], r["writer"]): r for r in rows if r["record"] == "recipient_summary"}
    text(fig, 0.509, 0.200, "Selected cases", color=MIDDLE, bold=True, size=6.7)
    for condition, name in [("A", "A note"), ("H", "H note"), ("ordinary", "No note")]:
        text(fig, xrec[condition], 0.200, name, bold=True, size=6.8, align="center")
    line(fig, 0.509, 0.979, 0.179)
    for y, group, name in [(0.150, "historic", "Archived"), (0.109, "heldout", "New"),
                           (0.055, "all", "All six cases")]:
        text(fig, 0.509, y, name, size=7, bold=group == "all")
        for condition, x in xrec.items():
            text(fig, x, y, ratio(reader[group, condition]), size=7.15, align="center", bold=group == "all")
    line(fig, 0.509, 0.979, 0.081)

    stem = directory / "fig4"
    title = "How the final writer changes the reasons conveyed to a colleague"
    fig.savefig(stem.with_suffix(".pdf"), metadata={"Title": title})
    fig.savefig(stem.with_suffix(".svg"), metadata={"Title": title, "Date": None})
    fig.savefig(stem.with_suffix(".png"), dpi=600)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-sources", type=Path, metavar="ROUND",
                        help="Rebuild the companion CSV from the original study records, then exit")
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    if args.build_sources:
        build_sources(args.build_sources, args.directory)
        return
    configure()
    figure(read_table(args.directory / "fig4_source.csv"), args.directory)


if __name__ == "__main__":
    main()
