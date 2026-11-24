"""Reduce saved elaborated-expression traversals to a human-browsable path table."""
import csv
import json
from pathlib import Path

directory = Path(__file__).resolve().parent
records = [json.loads(line) for line in (directory / "solution_paths.jsonl").read_text().splitlines()]
main = next(r for r in records if r.get("root") == "riemannHypothesis" and r["mode"] == "body")
core = next(r for r in records if r.get("root") == "riemannHypothesis" and r["mode"] == "core")
interests = {
    "rhOfAll": "classic theorem",
    "allChi": "shared half-plane theorem",
    "UpperTheory.FinalTheorems.everyCharacter_of_row": "algebraic assembly",
    "UpperTheory.Gal.Int.galoisLocalGlobalStrong_recParameter": "discharge row input",
    "GlobalTheory.EX.exists_ranks_rankVal_frame": "realize the finite ranks",
    "GlobalTheory.EX.exists_even_between": "select even integer near square root",
    "GlobalTheory.T.base_chain_step_theta_lift_alt": "interior theta transitions",
    "GlobalTheory.T.base_chain_top_theta_lift_alt": "terminal theta transition",
    "GlobalTheory.T.seesaw_first_reduction_level": "seesaw",
    "GlobalTheory.SqStepBig.theta_tower_step_norm_identity": "stage norm",
    "UpperTheory.LiteratureTheorems.rallis_inner_product_convergent_of_literature": "Rallis input",
    "GlobalTheory.T.mean_log_period_conjugates_eq_chowlaSelberg": "Chowla–Selberg input",
    "Formalism.MainNotions.S.sqrt_xd": "size-to-rank estimate",
    "Formalism.LFunctionChainParameters.ThickSetMeanBounds.proposition_size_bound": "consume both size bounds",
    "Deduction.mellin_ramp": "Mellin transform of the test function",
    "Deduction.landau_window": "use prime-growth windows to exclude poles",
}
rows = []
def add(role, r, target, second=None):
    path = r["paths"][target]
    assert path is not None and all(kind == "value" for kind, _ in path)
    if second is None or target not in second["paths"]:
        control = "not queried"
    elif second["paths"][target] == path:
        control = "same path"
    elif second["paths"][target] is not None:
        control = "reached by another path"
    else:
        control = "not reached"
    chain = " > ".join([r["root"], *[name for _,name in path]])
    rows.append([role, r["root"], target, len(path), control, chain])

for target, role in interests.items():
    add(role, main, target, core)
for r in records:
    if "root" not in r or r["root"] == "riemannHypothesis": continue
    for target in r["paths"]:
        if r["root"] == "Deduction.ch_core": role = "direct numerical input"
        elif r["root"] == "Deduction.lemmaL": role = "direct analytic input"
        else: role = "other headline theorem"
        add(role, r, target)
with (directory / "declaration_paths.tsv").open("w") as f:
    w=csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(["role","root","target","value_edges","omit_binder_annotations_control","full_path_including_root"])
    w.writerows(rows)
print(f"{len(rows)} complete paths")
