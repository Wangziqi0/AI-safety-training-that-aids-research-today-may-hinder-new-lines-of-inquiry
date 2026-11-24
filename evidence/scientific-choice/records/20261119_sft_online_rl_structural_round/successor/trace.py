"""Post-run descriptive witness. No retraining or re-selection; cannot identify a unique decisive pair."""
import json
import numpy as np
from common import ROOT, blind, jsonl
from fit import gradient

seed=7101
hm,am=[blind(seed,"sft",arm,"P") for arm in ("H","A")]
samples={r["model"]:r["examples"] for r in jsonl("samples.jsonl.gz") if r["model"] in (hm,am)}
held=json.loads((ROOT/"heldout.json").read_text())
ledger={(r["model"],r["index"]):r for r in jsonl("lineage.jsonl.gz") if r["model"] in (hm,am)}
ev={(e["model"],e["family"],e["clone"]):e for e in jsonl("events.jsonl.gz") if e["model"] in (hm,am)}
pair=None
for fam in range(24):
    for clone in range(4):
        h,a=ev[hm,fam,clone],ev[am,fam,clone]
        code=held[f"{seed},{fam}"]
        if h["g_model"]>a["g_model"] and h["g_all"]<a["g_all"]:
            for ix,s in enumerate(samples[hm]):
                if s[:2]==[code,1] and samples[am][ix][1]==0:
                    pair=(ix,h,a);break
        if pair: break
    if pair: break
assert pair
ix,h,a=pair
w=np.load(ROOT/"weights.npz")[blind(seed)]
record={}
for key,ident,event in [("H",hm,h),("A",am,a)]:
    x=np.array([samples[ident][ix]],dtype=float)
    loss,g=gradient(w,x)
    record[key]=dict(source=ledger[ident,ix],first_step_contribution_l2=float(np.linalg.norm(g)/192),
                     first_step_direction_head_bias_component=float(g[-1]/192),heldout=event)
(ROOT/"trace.json").write_text(json.dumps(record,indent=2)+"\n")
