"""Rebuild the three figure tables from the frozen scientific records."""
import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

import numpy as np


def jsonl(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def csv_table(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def figure_one(base, destination):
    root = base / "20261119_sft_online_rl_structural_round" / "structural"
    cases = defaultdict(dict)
    for r in jsonl(root / "outcomes.jsonl.gz"):
        if r["split"] == "heldout" and r["arm"] in ("A", "H"):
            key = tuple(r[k] for k in ("algo", "coupling", "seed", "family", "clone"))
            cases[key][r["arm"]] = (r["current_use"], r["later_use"])
    service = defaultdict(Counter)
    for r in jsonl(root / "deployment.jsonl.gz"):
        if r["case"] == 2 and r["arm"] in ("A", "H"):
            cell = service[r["algo"], r["seed"], r["arm"]]
            cell.update(total=1, disclosure=r["leak"])
    seeds = defaultdict(Counter)
    contingency = Counter()
    joint = defaultdict(set)
    for (algo, mapping, seed, family, clone), arms in cases.items():
        current, later = (a-h for a, h in zip(arms["A"], arms["H"]))
        seeds[algo, mapping, seed].update(total=1, current=current, later=later)
        if mapping == "aligned":
            contingency[algo, current, later] += 1
            if (current, later) == (1, -1):
                joint[algo].add((seed, family, clone))
    assert joint["sft"] == joint["reinforce"] and len(joint["sft"]) == 36
    rows = []
    for (algo, mapping, seed), v in sorted(seeds.items()):
        assert v["total"] == 96
        for metric in ("current", "later"):
            rows.append(dict(kind="paired_seed_delta", algorithm=algo, mapping=mapping,
                             seed=seed, metric=metric, numerator=v[metric], denominator=v["total"]))
        if mapping == "aligned":
            a, h = service[algo, seed, "A"], service[algo, seed, "H"]
            assert a["total"] == h["total"] == 128
            rows.append(dict(kind="paired_seed_delta", algorithm=algo, mapping="service",
                             seed=seed, metric="disclosure", numerator=a["disclosure"]-h["disclosure"],
                             denominator=a["total"]))
    for algo in ("sft","reinforce"):
        for current in (1,0,-1):
            for later in (-1,0,1):
                rows.append(dict(kind="contingency", algorithm=algo, mapping="aligned",
                                 change_current=current, change_later=later,
                                 numerator=contingency[algo,current,later], denominator=2304))
        for seed,family,clone in sorted(joint[algo]):
            rows.append(dict(kind="matched_joint_project",algorithm=algo,mapping="aligned",
                             seed=seed,family=family,clone=clone,change_current=1,change_later=-1))
    csv_table(destination / "fig1_source.csv",
              "kind algorithm mapping seed family clone metric change_current change_later numerator denominator".split(), rows)


def figure_two(root, destination):
    theory = read(root / "theory/NUMERICAL_CHECK.json")
    masses = defaultdict(Counter)
    for cell in theory["observed_distribution_both_worlds"]:
        mass = Fraction(cell["probability"])
        group=(cell["z"],cell["r"])
        masses[group]["mass"] += mass
        for key in ["protected","current","later_success","used"]:
            masses[group][key] += mass * cell[key]
    rows=[]
    for key, totals in masses.items():
        for metric in ["protected","current","later_success","used"]:
            members = 8 * totals[metric] / totals["mass"]
            assert members.denominator == 1
            rows.append(dict(panel="a",group=key[0],condition=key[1],metric=metric,
                             value=int(members),total=8))
    for group, values in theory["individual_counts_out_of_eight"].items():
        rows.append(dict(panel="b",group=group,metric="linked",value=values["linked"],total=8))
    transport=read(root / "review/TRANSPORT_VERIFICATION.json")["many_to_many"]
    for metric in ("sharp","identity_ignored"):
        lo,hi=[int(round(20*bound)) for bound in transport[metric]]
        rows.append(dict(panel="c",group="constructed",metric=metric,low=lo,high=hi,total=20))
    predictions=read(root / "mechanism/PREDICTION_CHECK.json")
    for dose in (.25,1):
        subset=[r for r in predictions if r["dose"]==dose]
        assert len(subset)==35
        for method in ("local","transfer"):
            attempts=[r for r in subset if not r[method+"_abstain"]]
            hits=sum(r[method+"_hit"] for r in attempts)
            for metric,value in (("agreed",hits),("missed",len(attempts)-hits),("abstained",len(subset)-len(attempts))):
                rows.append(dict(panel="d",group=method,condition=dose,metric=metric,value=int(value),total=len(subset)))
    csv_table(destination / "fig2_source.csv","panel group condition metric value low high total".split(),rows)


def figure_three(root, destination):
    names={r["field"]:r["source"][0] for r in read(root/"practice/COHORT.json")["ordered"] if r["selected"]}
    lock=root/"downstream/assigned_lock"
    scored=list(jsonl(lock/"results.jsonl"))
    standing=list(jsonl(root/"downstream/standing_substitution.jsonl"))
    free=list(jsonl(root/"free_workspace/attribution_paired.jsonl"))
    primary=list(csv.DictReader((root/"analysis/primary_case.csv").open()))
    early_choices=list(jsonl(root/"practice/current_choices.jsonl"))
    rows=[]
    for field,label in sorted(names.items()):
        ordinary=next(r for r in scored if r["field"]==field and r["variant"]=="ordinary")
        full=[r for r in scored if r["field"]==field and r["variant"]=="handoff"]
        fallback=[r for r in standing if r["field"]==field and r["batch"]=="assigned_lock"]
        assert len(full)==len(fallback)==9 and all(r["same_forecast"] for r in fallback)
        assert len({r["artifact"] for r in full})==1
        actual=full[0]
        scale=actual["mae_electrons_s"]/actual["normalized_mae"]
        values=dict(downstream_only=ordinary["normalized_mae"], all_channels=actual["normalized_mae"],
                    ordinary_chain=fallback[0]["fallback_mae"], constant=actual["stop_normalized_mae"])
        for route,value in values.items():
            rows.append(dict(panel="b",field=field,label=label,group=route,metric="scaled_MAE",
                             value=value,raw_e_s=scale*value,total=actual["test_n"]))
        if field=="P06":
            with np.load(lock/"products"/(actual["artifact"]+".npz")) as data:
                time=data["time"]; forecast=data["prediction"]
            with np.load(lock/"products"/(ordinary["artifact"]+".npz")) as data:
                assert np.array_equal(time,data["time"]);forecast_late=data["prediction"]
            with np.load(lock/"products"/"P06_observed.npz") as data:
                assert np.array_equal(time,data["time"])
                observed=data["spoc_flux"]
                constant=float(np.median(data["spoc"][:int(data["validation_end"])]))
            assert np.isclose(np.mean(np.abs(observed-constant)), scale*values["constant"])
            paths=[record for record in early_choices if record["field"]==field]
            assert len(paths)==9
            sources={tuple(record["source_periods"]) for record in paths}
            selected={record["ordinary"]["period_days"] for record in paths}
            assert len(sources)==len(selected)==1
            source_periods,=sources
            native_period,=source_periods
            early_period,=selected
            late_period=actual["component"]
            assert np.isclose(2*late_period,early_period)
            for origin,period in [("model_source",native_period),("ordinary_upstream",early_period),("chosen_late",late_period)]:
                rows.append(dict(panel="b",field=field,label=label,group=origin,metric="period_days",value=period,total=9))
            assert len(time)==98 and np.all(np.diff(time)>0)
            for tick,o,n,h in zip(time,observed,forecast_late,forecast):
                rows.append(dict(panel="a",field=field,label=label,time_day=tick,observed_e_s=o,
                                 downstream_only_e_s=n,all_channel_e_s=h,constant_e_s=constant))
    for arm in "HAB":
        primary_group=[r for r in primary if r["arm"]==arm]
        free_group=[r for r in free if r["arm"]==arm and r["assigned"]]
        assert len(primary_group)==len(free_group)==24
        for interface,group,quantity in [("menu",primary_group,"source_executed_reads"),
                                          ("open",free_group,"formed")]:
            assert len({case["id"] for case in group})==24
            counts=[]
            for case in group:
                quantity_obtained=int(case[quantity]); counts.append(quantity_obtained)
                rows.append(dict(panel="c",field=case["field"],group=arm,interface=interface,
                                 case_id=case["id"],metric="products_per_assignment",value=quantity_obtained))
            rows.append(dict(panel="c",group=arm,interface=interface,metric="products_total",
                             value=sum(counts),total=len(counts)))
            rows.append(dict(panel="c",group=arm,interface=interface,metric="active_assignments",
                             value=sum(v>0 for v in counts),total=len(counts)))
    frontier=read(root/"astra/RESULT.json")
    for cell in (r for r in frontier if r["field"]=="P04"):
        rows.append(dict(panel="d",field="P04",label="AMU 1",group=cell["arm"],metric="frontier_MAE",
                         value=cell["mae_e_s"],total=cell["test_n"]))
        if cell["transmitted_term_ablation"] is not None:
            rows.append(dict(panel="d",field="P04",label="AMU 1",group="H_term_removed",metric="frontier_MAE",
                             value=cell["transmitted_term_ablation"]["term_out_mae_e_s"],total=cell["test_n"]))
    p04=next(x for x in rows if x.get("field")=="P04" and x.get("group")=="constant")
    rows.append(dict(panel="d",field="P04",label="AMU 1",group="constant",metric="reference_MAE",value=p04["raw_e_s"],total=p04["total"]))
    csv_table(destination/"fig3_source.csv","panel field label group metric value raw_e_s total time_day observed_e_s downstream_only_e_s all_channel_e_s constant_e_s interface case_id".split(),rows)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rounds",type=Path,help="directory containing the two 19/20 November round folders")
    parser.add_argument("--out",type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument("--figure",type=int,choices=(1,2,3),help="extract only this figure's table")
    args=parser.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    current=args.rounds/"20261120_scientific_choice_and_recovery"
    if args.figure in (None,1):
        figure_one(args.rounds,args.out)
    if args.figure in (None,2):
        figure_two(current,args.out)
    if args.figure in (None,3):
        figure_three(current,args.out)
