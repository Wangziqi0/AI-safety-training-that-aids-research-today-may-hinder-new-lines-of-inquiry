"""Descriptive frequency separation from ordinary selectable hypotheses; never used for selection."""
from collections import Counter
from pathlib import Path
import argparse
import numpy as np
from receiver import HERE, FIELDS, PMIN, PMAX, json, jsonl, save_rows, dump

def describe(base):
    rows=jsonl(base/"results.jsonl")
    output=[]
    for field in FIELDS:
        meta=json.loads((base/(field+"_access.json")).read_text())
        with np.load(base/"products"/(field+"_observed.npz")) as obs:
            span=float(obs["all_time"][int(obs["validation_end"])-1]-obs["all_time"][0])
        standing=[]
        for origin,p in meta["standing_periods"]:
            if p is not None:
                standing += [(origin,p*k) for k in (1,.5,2) if PMIN<=p*k<=PMAX]
        for row in rows:
            if row["field"]!=field or isinstance(row["component"],str):
                continue
            p=row["component"]
            origin,closest=min(standing,key=lambda pair:abs(1/p-1/pair[1]))
            separation=abs(1/p-1/closest)*span
            output.append({"id":row["id"],"field":field,"variant":row["variant"],"origin":row["origin"],
                  "assigned_recovery":row.get("assigned_recovery"),"component_days":p,
                  "nearest_ordinary_component_days":closest,"nearest_ordinary_origin":origin,
                  "fit_validation_span_days":span,"frequency_separation_in_rayleigh_units":separation})
    save_rows(base/"frequency_separation.jsonl",output)
    selected=[r for r in output if r["variant"] in ("handoff","handoff_recovery") and r["variant"]==
               ("handoff_recovery" if r["assigned_recovery"] else "handoff")]
    deposit={"n_assigned_periodic":len(selected),"same_as_ordinary_option":0,"within_one_resolution":0,
             "beyond_one_resolution":0,"nonstanding_selected_origins":dict(Counter(r["origin"] for r in selected if r["frequency_separation_in_rayleigh_units"]>0))}
    for row in selected:
        d=row["frequency_separation_in_rayleigh_units"]
        label="same_as_ordinary_option" if d==0 else ("within_one_resolution" if d<=1 else "beyond_one_resolution")
        deposit[label]+=1
    dump(base/"frequency_separation_summary.json",deposit)
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("base",type=Path)
    describe(parser.parse_args().base)
