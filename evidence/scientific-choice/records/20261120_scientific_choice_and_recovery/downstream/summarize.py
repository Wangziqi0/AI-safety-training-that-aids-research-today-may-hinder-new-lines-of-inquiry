"""Summarize all assigned finite products after locked scoring. Positive gains lower error."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from receiver import FIELDS, HERE, digest, dump, json, jsonl, readrows, save_rows

def comparison(before, after, base):
    a,b=before["artifact"],after["artifact"]
    field=after["field"]
    d=base/"products"
    if a==b:
        delta=0.
        changed_pixels=False
    else:
        with np.load(d/(a+".npz")) as x, np.load(d/(b+".npz")) as y:
            delta=float(np.nanmean(abs(x["prediction"]-y["prediction"])))
            changed_pixels=sorted(x["aperture_flat"].tolist())!=sorted(y["aperture_flat"].tolist())
    gain=before["normalized_mae"]-after["normalized_mae"]
    return {"id":after["id"],"field":field,"from":before["variant"],"to":after["variant"],
            "gain":gain,"flux_gain_electrons_s":before["mae_electrons_s"]-after["mae_electrons_s"],
            "mean_abs_forecast_change_electrons_s":delta,
            "changed_component":before["component"]!=after["component"],
            "changed_physical_aperture":changed_pixels,
            "changed_flag":before["peripheral_flag"]!=after["peripheral_flag"],
            "from_component":before["component"],"to_component":after["component"],
            "from_aperture":before["aperture"],"to_aperture":after["aperture"],
            "additional_candidate_aperture_fits":after["candidate_fits"]-before["candidate_fits"]}

def stats(rows):
    g=np.array([r["gain"] for r in rows])
    return {"n":len(rows),"benefit":int(np.sum(g>0)),"no_change":int(np.sum(g==0)),"harm":int(np.sum(g<0)),
            "mean_gain":float(g.mean()),"median_gain":float(np.median(g)),"min_gain":float(g.min()),"max_gain":float(g.max()),
            "changed_physical_aperture":sum(r["changed_physical_aperture"] for r in rows),
            "changed_component":sum(r["changed_component"] for r in rows),
            "changed_flag":sum(r["changed_flag"] for r in rows),
            "changed_flux":sum(r["mean_abs_forecast_change_electrons_s"]>0 for r in rows),
            "additional_candidate_aperture_fits":sum(r["additional_candidate_aperture_fits"] for r in rows)}

def summarize(base,key_path=None):
    score_lock=json.loads((base/"SCORED_LOCK.json").read_text())
    assert score_lock["scores_sha256"]==digest(base/"results.jsonl")
    outcomes=jsonl(base/"results.jsonl")
    byid=defaultdict(dict)
    for r in outcomes:
        byid[r["id"]][r["variant"]]=r
    contrasts=defaultdict(list)
    case_summaries=[]
    labels={}
    if key_path:
        keys=readrows(key_path)
        if isinstance(keys,dict):
            if "rows" in keys:
                keys=keys["rows"]
            else:
                keys=[dict(id=i,**(v if isinstance(v,dict) else {"arm":v})) for i,v in keys.items()]
        labels={r["id"]:r["arm"] for r in keys}
        if len(labels)!=72 or set(labels)!=set(i for i in byid if not i.startswith("ordinary_")):
            raise ValueError("incomplete arm key")
    for field in FIELDS:
        ordinary=byid["ordinary_"+field]
        contrasts["field_ordinary_recovery"].append(comparison(ordinary["ordinary"],ordinary["ordinary_recovery"],base))
    for ident,results in sorted(byid.items()):
        if ident.startswith("ordinary_"):
            continue
        h=results["handoff"]
        field=h["field"]
        o=byid["ordinary_"+field]
        realized=results["handoff_recovery" if h["assigned_recovery"] else "handoff"]
        current_realized=results["current_recovery" if h["assigned_recovery"] else "current"]
        benchmark=o["ordinary_recovery" if h["assigned_recovery"] else "ordinary"]
        for name,a,b in [
            ("current_vs_ordinary",o["ordinary"],results["current"]),
            ("full_vs_ordinary",o["ordinary"],h),
            ("packets_given_current",results["current"],h),
            ("recovery_given_current",results["current"],results["current_recovery"]),
            ("recovery_given_full",h,results["handoff_recovery"]),
            ("packets_given_current_and_recovery",results["current_recovery"],results["handoff_recovery"]),
            ("full_plus_recovery_vs_ordinary",o["ordinary"],results["handoff_recovery"]),
            ("assigned_product_vs_matched_ordinary",benchmark,realized),
            ("assigned_packets_given_current",current_realized,realized),
            ("assigned_all_vs_unassisted_ordinary",o["ordinary"],realized)]:
            c=comparison(a,b,base)
            c.update({"arm":labels.get(ident),"seed":h["block_seed"],"assigned_recovery":h["assigned_recovery"]})
            contrasts[name].append(c)
        summary={"id":ident,"arm":labels.get(ident),"field":field,"seed":h["block_seed"],
                "recovery":h["assigned_recovery"],"actual_normalized_mae":realized["normalized_mae"],
                "actual_improvement_over_stopped":realized["improvement_over_stop"],
                "actual_artifact":realized["artifact"],"actual_component":realized["component"],
                "actual_aperture":realized["aperture"],"actual_origin":realized["origin"],
                "actual_peripheral_flag":realized["peripheral_flag"]}
        for variant,r in results.items():
            summary[variant+"_loss"]=r["normalized_mae"]
        case_summaries.append(summary)
    output=base/("unblinded" if labels else "blind_summary")
    output.mkdir(exist_ok=True)
    dump(output/"contrasts.json",{name:stats(v) for name,v in contrasts.items()})
    save_rows(output/"paired_changes.jsonl",[dict(comparison=name,**r) for name,v in contrasts.items() for r in v])
    if not case_summaries:
        return
    save_rows(output/"all_assigned.jsonl",case_summaries)
    field_summaries={}
    for field in FIELDS:
        field_summaries[field]={name:stats([r for r in v if r["field"]==field]) for name,v in contrasts.items()}
    dump(output/"field_contrasts.json",field_summaries)
    # The block propensity is known by design. Stratified difference of observed
    # arm means estimates the block's equally weighted finite-policy effect.
    blocks=defaultdict(list)
    for r in case_summaries:
        blocks[(r["field"],r["seed"])].append(r)
    randomized=[]
    for (field,seed),rows in sorted(blocks.items()):
        offered=[r for r in rows if r["recovery"]]
        omitted=[r for r in rows if not r["recovery"]]
        realized=float(np.mean([r["actual_normalized_mae"] for r in omitted])-np.mean([r["actual_normalized_mae"] for r in offered]))
        exact=float(np.mean([r["handoff_loss"]-r["handoff_recovery_loss"] for r in rows]))
        randomized.append({"field":field,"seed":seed,"offered":len(offered),"not_offered":len(omitted),
                           "realized_recovery_gain":realized,"exact_recovery_gain":exact})
    dump(output/"recovery_assignment.json",{"blocks":randomized,"mean_realized_gain":float(np.mean([r["realized_recovery_gain"] for r in randomized])),
                          "mean_exact_gain":float(np.mean([r["exact_recovery_gain"] for r in randomized]))})
    if not labels:
        return
    for field in FIELDS:
        group=[r for r in case_summaries if r["field"]==field]
        if Counter(r["arm"] for r in group)!=Counter({"H":3,"A":3,"B":3}):
            raise ValueError("expected complete H/A/B x three seeds per field")
    arm_contrasts={arm:{name:stats([r for r in rows if r.get("arm")==arm])
        for name,rows in contrasts.items() if name!="field_ordinary_recovery"} for arm in ("H","A","B")}
    dump(output/"arm_contrasts.json",arm_contrasts)
    paired={}
    for left,right in (("A","H"),("B","A"),("B","H")):
        paired[left+"_minus_"+right]={}
        for metric in ("current_loss","handoff_loss","current_recovery_loss","handoff_recovery_loss","actual_normalized_mae"):
            field_loss_delta=[]
            for field in FIELDS:
                x=[r[metric] for r in case_summaries if r["field"]==field and r["arm"]==left]
                y=[r[metric] for r in case_summaries if r["field"]==field and r["arm"]==right]
                field_loss_delta.append(float(np.mean(x)-np.mean(y)))
            v=np.array(field_loss_delta)
            paired[left+"_minus_"+right][metric]={"loss_delta":float(v.mean()),"by_field":dict(zip(FIELDS,v.tolist())),
                "leave_one_field_out_range":[float((v.sum()-v.max())/7),float((v.sum()-v.min())/7)]}
    dump(output/"paired_arm_losses.json",paired)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("base",type=Path)
    parser.add_argument("--key",type=Path)
    args=parser.parse_args()
    summarize(args.base,args.key)
