"""Pre-specified paired seed-level summaries with per-seed audit files."""
import csv
import gzip
import json
import statistics as stat
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
C=json.loads((ROOT/"config.json").read_text())
SCI=["current_use","later_use","source_reads","repair_reads","unavailable","expired","transferred",
     "standard","certificate","repair","center"]
SAF=["leak","raw_leak","blocked","public_delivered","case0_public_delivered",
     "case1_public_delivered","case2_leak"]


def records(name):
    with gzip.open(ROOT/(name+".jsonl.gz"),"rt") as f:
        yield from map(json.loads,f)


def write(name,rows):
    with (ROOT/name).open("w") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def paired(vals):
    avg=stat.mean(vals)
    error=2.06866*stat.stdev(vals)/(len(vals)**.5)
    return dict(diff=avg,lo=avg-error,hi=avg+error,n_seed=len(vals),
                negative=sum(v<0 for v in vals),zero=sum(v==0 for v in vals),positive=sum(v>0 for v in vals))


def main():
    blocks=defaultdict(Counter)
    for x in records("outcomes"):
        base=tuple(x[k] for k in ("seed","algo","arm","coupling","split"))
        counts=Counter(n=1)
        for k in SCI[:4]:
            counts[k]=x[k]
        counts[x["status"]]+=1
        counts[x["method"]]+=1
        for opp in ("all",x["opportunity"]):
            blocks[base+(opp,)].update(counts)
    safety={tuple(r[k] for k in ("seed","algo","arm")):r for r in records("checkpoints")}
    cells={}
    perseed=[]
    for key,x in blocks.items():
        rates={k:x[k]/x["n"] for k in SCI}
        rates.update({k:safety[key[:3]][k] for k in SAF})
        cells[key]=rates
        row=dict(zip(("seed","algo","arm","coupling","split","opportunity"),key))
        perseed.append(dict(**row,n=x["n"],**rates))
    write("seed_means.csv",perseed)
    effects=[]
    seed_diffs=[]
    for algo in C["algorithms"]:
        for cond in C["coupling"]:
            for split in C["splits"]:
                for opp in ["all","needed","certificate","repair","center"]:
                    for a,b in [("A","H"),("B","H"),("B","A")]:
                        keys=dict(algo=algo,coupling=cond,split=split,opportunity=opp,contrast=a+"-"+b)
                        diffs=defaultdict(list)
                        for seed in C["seeds"]:
                            aa=cells[(seed,algo,a,cond,split,opp)]
                            bb=cells[(seed,algo,b,cond,split,opp)]
                            single={k:aa[k]-bb[k] for k in SCI+SAF}
                            for k,d in single.items():
                                diffs[k].append(d)
                            seed_diffs.append(dict(**keys,seed=seed,**single))
                        for k,values in diffs.items():
                            av=stat.mean(cells[(s,algo,a,cond,split,opp)][k] for s in C["seeds"])
                            bv=stat.mean(cells[(s,algo,b,cond,split,opp)][k] for s in C["seeds"])
                            effects.append(dict(**keys,metric=k,mean_first=av,mean_second=bv,**paired(values)))
    write("paired_seed_differences.csv",seed_diffs)
    write("contrasts.csv",effects)
    interactions=[]
    for split in C["splits"]:
        for cond in C["coupling"]:
            for a,b in [("A","H"),("B","H"),("B","A")]:
                for k in SCI+SAF:
                    values=[]
                    for s in C["seeds"]:
                        within=lambda algo:cells[s,algo,a,cond,split,"all"][k]-cells[s,algo,b,cond,split,"all"][k]
                        values.append(within("reinforce")-within("sft"))
                    interactions.append(dict(split=split,coupling=cond,contrast=a+"-"+b,metric=k,**paired(values)))
    write("algorithm_interactions.csv",interactions)


if __name__=="__main__":
    main()
