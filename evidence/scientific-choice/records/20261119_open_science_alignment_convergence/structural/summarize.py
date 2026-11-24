"""All matched roots and prescribed environments. Inference target is this model/world array."""
from pathlib import Path
import json
import numpy as np
HERE=Path(__file__).resolve().parent
def get(path):return json.loads(path.read_text())
def stats(arr):
    x=np.array(arr)
    return {"n_roots":len(x),"mean":float(x.mean()),"median":float(np.median(x)),"min":float(x.min()),"max":float(x.max()),"positive":int(sum(x>1e-12)),"negative":int(sum(x< -1e-12)),"within_1e-12":int(sum(abs(x)<=1e-12))}
def main():
    roots=[(get(p/"forecast.json"),get(p/"evaluation.json")) for p in sorted((HERE/"roots").iterdir())]
    assert len(roots)==12
    groups={}
    for a in ("sft","rl"):
        for eta in (0.,.012,.024):
            ms=[next(m for m in ev["measurements"] if m["alg"]==a and m["eta"]==eta) for _,ev in roots]
            vals={}
            for key in ms[0]["metrics"]:
                orig=[r["metrics"][key] for r in ms]
                actual=np.array([r["actual_difference"] for r in orig]);pred=np.array([r["predicted"] for r in orig])
                nonzero=(abs(actual)>1e-12)&(abs(pred)>1e-12)
                vals[key]={"actual":stats(actual),"predicted":stats(pred),"mean_abs_error":float(np.mean(abs(actual-pred))),
                    "max_abs_error":float(max(abs(actual-pred))),"nonzero_sign_checks":int(sum(nonzero)),
                    "sign_agree":int(sum(np.sign(actual[nonzero])==np.sign(pred[nonzero])))}
            def joint(m):
                rr=m["metrics"]
                return rr["service_nonpublic_release"]["actual_difference"]<0 and rr["current_correct"]["actual_difference"]>0 and rr["later_correct_diagnostic_0"]["actual_difference"]<0
            groups[f"{a}_{eta}"]={"outcomes":vals,"same_root_three_signs":sum(joint(m) for m in ms),
                 "genuinely_changed_sampled_action_ids":[sum(x!=y for x,y in zip(m["H_action_ids"],m["A_action_ids"])) for m in ms]}
    groups["sources"]={"twelve_same_pretrained_roots_both_algorithms":True,"scientific_records":384,"service_records":192,
        "unknown_dispositions_included_in_probabilities":True,"worlds_are_controlled_and_fully_recoverable_at_q1":True}
    out=HERE/"RESULTS.json";out.write_text(json.dumps(groups,indent=2)+"\n")
    for a in ("sft","rl"):
        for e in (.012,.024):
            r=groups[f"{a}_{e}"];print(a,e,"simultaneous",r["same_root_three_signs"])
            for k in ["service_nonpublic_release","scientific_action_acquire","current_correct","current_used","later_correct_diagnostic_0","later_correct_diagnostic_50","later_correct_diagnostic_100","later_correct_compact_0"]:
                x=r["outcomes"][k];y=x["actual"];print(k,round(100*y["mean"],5),y["positive"],y["negative"],round(100*x["mean_abs_error"],7),x["sign_agree"],x["nonzero_sign_checks"])
if __name__=="__main__":main()
