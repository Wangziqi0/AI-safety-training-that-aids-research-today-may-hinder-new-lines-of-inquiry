import csv
import hashlib
import json
from collections import Counter, defaultdict
from contextlib import ExitStack
import numpy as np
from common import ROOT, SEEDS, ALGOS, ARMS, blind, jsonl

END=["g_model","g_all","accepted","model_used","accuracy","extra_measurements","late","correct_ordinary","model_rejected"]
ROUTES=["model","certificate","center","calibration","ordinary"]


def save(name,rows):
    with (ROOT/name).open("w") as out:
        writer=csv.DictWriter(out,fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def inference(vals):
    x=np.asarray(vals)
    assert len(x)==24
    mean=x.mean()
    half=2.06866*x.std(ddof=1)/np.sqrt(len(x))
    return dict(mean=mean,lo=mean-half,hi=mean+half,pos=int(sum(x>0)),zero=int(sum(x==0)),neg=int(sum(x<0)))


def main():
    acc=defaultdict(Counter)
    for e in jsonl("events.jsonl.gz"):
        item=acc[e["model"]]
        item.update({k:e[k] for k in END})
        item["n"]+=1
        item["route_"+e["route"]]+=1
    mat=defaultdict(Counter)
    for x in jsonl("lineage.jsonl.gz"):
        mat[x["model"]][x["decision"]]+=1
    with np.load(ROOT/"weights.npz") as weights:
        means=[]
        for seed in SEEDS:
            idx=[("baseline","init","-",blind(seed))]
            idx += [(algo,arm,rule,blind(seed,algo,arm,rule)) for algo in ALGOS for arm in ARMS for rule in ("U","P")]
            for alg,arm,rule,ident in idx:
                a=acc[ident]
                assert a["n"]==96
                args={k:a[k]/a["n"] for k in END+["route_"+r for r in ROUTES]}
                args["formed_pairs_used"]=mat[ident]["observed_pair"]
                args["natural_centers_used"]=mat[ident]["natural_center"]
                args["products_used"]=mat[ident]["delivered_product"]
                args["public_slots"]=sum(mat[ident].values())-sum(args[k] for k in ("formed_pairs_used","natural_centers_used","products_used"))
                args["weight_update_l2"]=float(np.linalg.norm(weights[ident]-weights[blind(seed)]))
                means.append(dict(seed=seed,algo=alg,arm=arm,rule=rule,model=ident,**args))
    save("seed_cells.csv",means)
    keys=list(args)
    cells=[]; contrasts=[]; diffs=[]
    for algo in [*ALGOS,"baseline"]:
        arms=ARMS if algo in ALGOS else ["init"]
        rules=["U","P"] if algo in ALGOS else ["-"]
        for arm in arms:
            for rule in rules:
                items=[r for r in means if (r["algo"],r["arm"],r["rule"])==(algo,arm,rule)]
                for k in keys:
                    cells.append(dict(algo=algo,arm=arm,rule=rule,metric=k,**inference([r[k] for r in items])))
        if algo=="baseline":
            continue
        for k in keys:
            cols={arm+rule:np.array([r[k] for r in means if (r["algo"],r["arm"],r["rule"])==(algo,arm,rule)])
                  for arm in ARMS for rule in rules}
            cols["init"]=np.array([r[k] for r in means if r["algo"]=="baseline"])
            cmp={f"{x}{s}-{y}{s}":cols[x+s]-cols[y+s] for x,y in [("A","H"),("B","H"),("B","A")] for s in rules}
            cmp.update({f"{x}P-{x}U":cols[x+"P"]-cols[x+"U"] for x in ARMS})
            cmp["(AP-HP)-(AU-HU)"]=cmp["AP-HP"]-cmp["AU-HU"]
            cmp.update({x+"-init":col-cols["init"] for x,col in cols.items() if x!="init"})
            for label,vals in cmp.items():
                contrasts.append(dict(algo=algo,contrast=label,metric=k,**inference(vals)))
                diffs.extend(dict(seed=seed,algo=algo,contrast=label,metric=k,delta=v) for seed,v in zip(SEEDS,vals))
    save("cells.csv",cells);save("contrasts.csv",contrasts);save("paired_seed_differences.csv",diffs)


if __name__=="__main__":
    main()
