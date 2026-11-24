"""Join frozen allocations only after blind proof cards are committed; no statistical resampling."""
import csv
import json
from pathlib import Path
from collections import Counter
from dockets import DOCKETS
from verify import certify

ROOT=Path(__file__).resolve().parent
def read(path):
    return [json.loads(s) for s in (ROOT/path).read_text().splitlines() if s]
def byid(path, key="id"):
    return {r[key]:r for r in read(path)}
def write_table(name,data):
    if not data:
        return
    with (ROOT/name).open("w") as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]),delimiter="\t")
        w.writeheader()
        w.writerows(data)
def write(name,data):
    (ROOT/name).write_text(json.dumps(data,indent=2)+"\n")
allocation=read("internal/allocation.jsonl")
svc=byid("blind/services.jsonl")
desk=byid("blind/desk_log.jsonl")
donor_cards=byid("blind/donor_cards.jsonl")
forms=byid("blind/actions.jsonl")
notes=byid("blind/notes.jsonl")
receiver_allocation=read("internal/receiver_allocation.jsonl")
service_raw=byid("internal/service_raw.jsonl")
science_raw=byid("internal/scientific_raw.jsonl")
notes_raw=byid("internal/handoff_raw.jsonl")
calibration_missing={"p83","p89","p23"}
base=[]
for a in allocation:
    i=a["id"]
    s=svc[i]
    d=desk[i]
    card=donor_cards[i]
    result=certify(card)
    scientific=any([
        card.get("verdict") in ("yes","no"), bool(card.get("warrant")), bool(card.get("partial"))
    ])
    cal=i not in calibration_missing
    use=s["public"] and cal
    safe=not s["disclosed"]
    base.append(dict(case=a["case"],seed=a["seed"],arm=a["arm"],id=i,
                     raw_protected=int(safe),public_locator=int(s["public"]),calibration_correct=int(cal),
                     usable_public=int(use),safe_usable=int(safe and use),
                     explicit_check=int(forms[i]["arguments"] is not None),
                     calculated=int(d["source"]!="none"),scientific_note=int(scientific),
                     correct_direction=int(result["correct_direction"]),settled=int(result["settled"]),
                     substitute=int(result["valid_substitute"]),sharp=int(result["sharp"]),
                     service_tokens=service_raw[i]["generated_tokens"],
                     scientific_tokens=science_raw[i]["generated_tokens"],handoff_tokens=notes_raw[i]["generated_tokens"],
                     service_cap=int(svc[i]["truncated"]),scientific_cap=int(forms[i]["truncated"]),
                     handoff_cap=int(notes[i]["truncated"])))
base.sort(key=lambda z:(z["case"],z["seed"],z["arm"]))
write_table("donor_results.tsv",base)
byhid={(d["case"],d["seed"],d["arm"]):d for d in base}
selected={(r["case"],r["seed"]) for r in receiver_allocation}
metrics=("raw_protected","public_locator","calibration_correct","usable_public","safe_usable",
         "explicit_check","calculated","scientific_note","correct_direction","settled","substitute","sharp")
def sums(data):
    return {a:{m:sum(d[m] for d in data if d["arm"]==a) for m in metrics} for a in ["A","H"]}
pairs=[]
for case,seed in sorted(set((r["case"],r["seed"]) for r in base)):
    a=byhid[case,seed,"A"]
    h=byhid[case,seed,"H"]
    prevent=a["raw_protected"]>h["raw_protected"]
    pairs.append(dict(case=case,seed=seed,frontier_pair=int((case,seed) in selected),
                      A=a["id"],H=h["id"],prevention=int(prevent),
                      prevention_usable_A=int(prevent and a["usable_public"]),
                      prevention_calibrated_A=int(prevent and a["calibration_correct"]),
                      prevention_service_gain=int(prevent and a["usable_public"]>h["usable_public"]),
                      prevention_calibration_gain=int(prevent and a["calibration_correct"]>h["calibration_correct"]),
                      **{m+"_A_minus_H":a[m]-h[m] for m in metrics}))
write_table("paired_differences.tsv",pairs)
def cross_tab(p):
    ls=("prevention","prevention_usable_A","prevention_calibrated_A","prevention_service_gain","prevention_calibration_gain")
    return {k:sum(r[k] for r in p) for k in ls}
write("donor_counts.json",dict(all=sums(base),selected=sums([r for r in base if (r["case"],r["seed"]) in selected]),
                              nested_full=cross_tab(pairs),nested_selected=cross_tab([r for r in pairs if r["frontier_pair"]]),
                              by_seed={str(seed):sums([r for r in base if r["seed"]==seed]) for seed in [311,617,929]},
                              pair_directions={m:dict(sorted(Counter(r[m+"_A_minus_H"] for r in pairs).items())) for m in metrics}))
if (ROOT/"blind/receiver_cards.jsonl").exists():
    rc=byid("blind/receiver_cards.jsonl")
    durable=[]
    for s in receiver_allocation:
        card=rc[s["slot"]]
        res=certify(card)
        durable.append(dict(slot=s["slot"],case=s["case"],seed=s["seed"],arm=s["arm"],donor=s["donor"] or "",
                            correct_direction=int(res["correct_direction"]),settled=int(res["settled"]),
                            substitute=int(res["valid_substitute"]),sharp=int(res["sharp"]),
                            use=card.get("uptake","unreported")))
    write_table("receiver_results.tsv",durable)
    readmap={(r["case"],r["arm"]):r for r in durable}
    proc=[]
    for p in pairs:
        if p["frontier_pair"]:
            c=p["case"]
            h,a,o=[readmap[(c,arm)] for arm in ("H","A","ordinary")]
            proc.append(dict(case=c,seed=p["seed"],A=a["settled"],H=h["settled"],ordinary=o["settled"],
                             prevented=p["prevention"],A_usable_and_prevented=p["prevention_usable_A"],
                             current_dual_gain=p["prevention_service_gain"],
                             strict_through_receiver=int(p["prevention_usable_A"] and h["settled"] and
                                                         not a["settled"] and not o["settled"]),
                             nested_dual_gain_strict=int(p["prevention_service_gain"] and h["settled"] and
                                                         not a["settled"] and not o["settled"]),
                             strict_after_editorial_reference=0))
    write_table("linked_cases.tsv",proc)
