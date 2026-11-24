"""Compute observed writer and delivered-history contrasts on an identical target."""
import csv
from fractions import Fraction
import json
from pathlib import Path
import argparse


def matrix(path):
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    cells = {}
    for row in rows:
        index = (row["case"], int(row["seed"]))
        entry = cells.setdefault(index, {})
        for writer in ("A", "H"):
            key = row["history_arm"] + writer
            assert key not in entry
            entry[key] = int(row[writer + "_pass"])
    assert len(cells) == 12 and all(set(x) == {"AA","AH","HA","HH"} for x in cells.values())
    return cells


def compute(cells):
    aa, ah, ha, hh = (Fraction(cells[key]) for key in ("AA","AH","HA","HH"))
    total = aa-hh
    final_writer = ((aa-ah)+(ha-hh))/2
    prior_record = ((aa-ha)+(ah-hh))/2
    assert final_writer + prior_record == total
    return {"natural_AA_minus_HH":total, "final_writer":final_writer,
            "prior_record":prior_record, "interaction":(aa-ah)-(ha-hh)}


def run(case_table, output, outcome):
    cells = matrix(case_table)
    detailed = []
    for (case,seed),cell in sorted(cells.items()):
        detailed.append({"case":case,"seed":seed,**cell,
                         **{k:str(v) for k,v in compute(cell).items()}})
    with (output / (outcome+"_factorial.csv")).open("w",newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=list(detailed[0]))
        writer.writeheader()
        writer.writerows(detailed)
    totals = {key:sum(row[key] for row in cells.values()) for key in ("AA","AH","HA","HH")}
    rates = {key:Fraction(value,len(cells)) for key,value in totals.items()}
    return {"outcome":outcome,"problem_seed_pairs":len(cells),"scientific_problems":4,
            "source_writer_cell_counts":totals,
            "contrasts_in_rates":{k:str(v) for k,v in compute(rates).items()}}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cross",type=Path); parser.add_argument("output",type=Path)
    args=parser.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    # The fixed nominal statement has the same meaning under both source histories.
    strict=run(args.cross/"standalone_decisions.tsv",args.output,"original_decision")
    # The focal action can differ by origin. These last scores alone do not establish
    # the substitution of the same scientific function between record origins.
    action=run(args.cross/"paired_outcomes.tsv",args.output,"warranted_action")
    r={"original_decision":strict,"warranted_action":action,
       "units":"Exact finite counts across the twelve fixed problem/seed combinations.",
       "scope":"The warranted actions can differ by history. Only original_decision fixes the same nominal statement across both origins."}
    (args.output/"factorial_summary.json").write_text(json.dumps(r,indent=2)+"\n")
    print(json.dumps(r))
