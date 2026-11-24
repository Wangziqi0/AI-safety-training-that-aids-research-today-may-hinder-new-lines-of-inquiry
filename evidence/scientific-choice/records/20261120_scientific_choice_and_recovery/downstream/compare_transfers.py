"""Pair every independently locked receiver decision across the two observed transports."""
from collections import defaultdict
from pathlib import Path
import argparse
import numpy as np
from receiver import HERE, digest, json, jsonl, save_rows, dump
from summarize import stats

def compare(arm_key=None):
    roots=[HERE/"assigned_lock",HERE/"stewardship_lock"]
    completed=json.loads((HERE/"BOTH_DECISIONS_LOCKED.json").read_text())
    datasets=[]
    for root in roots:
        assert completed[root.name]==digest(root/"CHOICES_LOCK.json")
        assert json.loads((root/"SCORED_LOCK.json").read_text())["scores_sha256"]==digest(root/"results.jsonl")
        rows=jsonl(root/"results.jsonl")
        datasets.append({(r["id"],r["variant"]):r for r in rows})
    baseline,transfer=datasets
    assert baseline.keys()==transfer.keys() and len(transfer)==304
    arms={}
    if arm_key:
        arms={r["id"]:r["arm"] for r in jsonl(arm_key)}
    diffs=[]
    for (ident,variant),b in transfer.items():
        a=baseline[(ident,variant)]
        if ident.startswith("ordinary_"):
            assert a["artifact"]==b["artifact"] and a["normalized_mae"]==b["normalized_mae"]
            continue
        fa=roots[0]/"products"/(a["artifact"]+".npz")
        fb=roots[1]/"products"/(b["artifact"]+".npz")
        with np.load(fa) as x, np.load(fb) as y:
            changed=float(np.nanmean(abs(x["prediction"]-y["prediction"])))
            aperture=sorted(y["aperture_flat"].tolist())!=sorted(x["aperture_flat"].tolist())
        diffs.append({"id":ident,"arm":arms.get(ident),"field":b["field"],"seed":b["block_seed"],"variant":variant,
             "assigned":b["packets"] and b["assigned_recovery"]==b["recovery"],"recovery":b["recovery"],
             "from_disposition":a["disposition"],"to_disposition":b["disposition"],
             "from_origin":a["origin"],"to_origin":b["origin"],
             "gain":a["normalized_mae"]-b["normalized_mae"],"flux_gain_electrons_s":a["mae_electrons_s"]-b["mae_electrons_s"],
             "mean_abs_forecast_change_electrons_s":changed,"changed_physical_aperture":aperture,
             "changed_component":a["component"]!=b["component"],"changed_flag":a["peripheral_flag"]!=b["peripheral_flag"],
             "additional_candidate_aperture_fits":b["candidate_fits"]-a["candidate_fits"]})
    scope={"all_assigned":[r for r in diffs if r["assigned"]]}
    for variant in ("current","current_recovery","handoff","handoff_recovery"):
        scope[variant]=[r for r in diffs if r["variant"]==variant]
    if arms:
        for arm in sorted(set(arms.values())):
            scope["all_assigned_"+arm]=[r for r in scope["all_assigned"] if r["arm"]==arm]
    suffix="unblinded" if arms else "blinded"
    dump(HERE/("transfer_summary_"+suffix+".json"),{k:stats(v) for k,v in scope.items()})
    save_rows(HERE/("transfer_changes_"+suffix+".jsonl"),diffs)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--key",type=Path)
    compare(p.parse_args().key)
