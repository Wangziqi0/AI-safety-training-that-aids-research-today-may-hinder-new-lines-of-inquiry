"""Cross-arm project contingencies in the explicitly coupled clone simulator."""
import csv
from collections import Counter
from analysis import ROOT,records,C

def main():
    stored={}
    for e in records("outcomes"):
        if e["split"]=="heldout":
            k=tuple(e[n] for n in ("seed","algo","coupling","family","clone"))
            stored.setdefault(k,{})[e["arm"]]=(e["current_use"],e["later_use"])
    counts=Counter()
    for (s,algo,cond,f,clone),arms in stored.items():
        for a,b in (("A","H"),("B","H"),("B","A")):
            d0=arms[a][0]-arms[b][0]
            d1=arms[a][1]-arms[b][1]
            counts[s,algo,cond,a+"-"+b,d0,d1]+=1
    with (ROOT/"joint_counts.csv").open("w") as f:
        w=csv.writer(f)
        w.writerow(["seed","algo","coupling","contrast","delta_current","delta_later","count"])
        for s in C["seeds"]:
            for algo in C["algorithms"]:
                for cond in C["coupling"]:
                    for comp in ("A-H","B-H","B-A"):
                        for cur in (-1,0,1):
                            for later in (-1,0,1):
                                k=(s,algo,cond,comp,cur,later)
                                w.writerow([*k,counts[k]])
if __name__=="__main__":
    main()
