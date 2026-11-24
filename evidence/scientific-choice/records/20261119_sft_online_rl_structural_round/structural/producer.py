"""Train policies and emit natural packages. No future task scoring occurs in this process."""
import gzip
import json
import math
from contextlib import ExitStack
from pathlib import Path
from policy import accumulate, contrast, deploy, draw, forward, initialize, inputs, obtained_reward, target
from world import family_law, project, reading, rng

ROOT = Path(__file__).resolve().parent
C = json.loads((ROOT/"config.json").read_text())


def line(stream, obj):
    stream.write(json.dumps(obj, separators=(",",":"))+"\n")


def train(seed, algo, arm, trace):
    initial = initialize(rng("weights",seed))
    w = initial.copy()
    line(trace,dict(seed=seed,algo=algo,arm=arm,step=-1,weights=w))
    for t in range(C["steps"]):
        batch_rng = rng("batch",seed,t)
        action_rng = rng("online",seed,t)
        sums = [0.]*len(w)
        samples=[]
        for i in range(C["batch"]):
            ident = batch_rng.randrange(1000000)
            case = batch_rng.randrange(3)
            x=inputs(case)
            h,_,p=forward(w,x)
            if algo == "sft":
                act=target(arm,case)
                mult=1
                reward=None
            else:
                act=draw(p,action_rng.random())
                reward=obtained_reward(arm,case,act,ident)
                mult=reward
            accumulate(w,x,h,p,act,mult,sums)
            samples.append([ident,case,act,reward,p])
        grad=[v/len(samples) for v in sums]
        w=[v+C["learning_rate"]*g for v,g in zip(w,grad)]
        line(trace,dict(seed=seed,algo=algo,arm=arm,step=t,samples=samples,gradient=grad,weights=w))
    return initial,w


def safety(seed,w,key,logs):
    r=rng("frozen protected evaluation",seed)
    n=0
    sums={}
    case_sums={}
    for block in range(64):
        for case in range(3):
            for alias in [False, True]:
                act=draw(forward(w,inputs(case))[2],r.random())
                out=deploy(case,block+2000000,act,alias)
                line(logs,dict(**key,case=case,alias=alias,ident=block+2000000,action=act,**out))
                for name,val in out.items():
                    sums[name]=sums.get(name,0)+val
                    subgroup=f"case{case}_{name}"
                    case_sums[subgroup]=case_sums.get(subgroup,0)+val
                n+=1
    return {**{k:v/n for k,v in sums.items()},**{k:v/(n/3) for k,v in case_sums.items()}}


def material(seed, split, family, clone, coupling, movement):
    features=family_law(seed,split,family)[0]
    _,u_stop,u_expiry,u_route=project(seed,split,family,clone)
    logodds=.25*features[0]-.15*features[1] + coupling*movement
    p=1/(1+math.exp(-logodds))
    if u_stop < C["terminal_probability"]:
        return dict(family_features=features,current=None,observations=[],status="unavailable")
    c=reading(seed,split,family,clone,0)
    obs=[[0,c]]
    if u_route >= p:
        obs.append([1,reading(seed,split,family,clone,1)])
    expired=len(obs)==2 and u_expiry<C["slow_expiry_probability"]
    return dict(family_features=features,current=None if expired else c,observations=obs,
                status="expired" if expired else "delivered")


def main():
    with ExitStack() as stack:
        streams={k:stack.enter_context(gzip.open(ROOT/(k+".jsonl.gz"),"wt")) for k in
                 ("materials","training","checkpoints","deployment")}
        for seed in C["seeds"]:
            for algo in C["algorithms"]:
                for arm in C["arms"]:
                    key=dict(seed=seed,algo=algo,arm=arm)
                    initial,w=train(seed,algo,arm,streams["training"])
                    move=contrast(w)-contrast(initial)
                    line(streams["checkpoints"], dict(**key,initial=initial,final=w,move=move,
                                                       **safety(seed,w,key,streams["deployment"])))
                    for coupling,coeff in C["coupling"].items():
                        for split in C["splits"]:
                            for family in range(C["families_per_split"]):
                                for clone in range(C["clones_per_family"]):
                                    pkg=material(seed,split,family,clone,coeff,move)
                                    line(streams["materials"],dict(**key,coupling=coupling,split=split,
                                         family=family,clone=clone,package=pkg))


if __name__=="__main__":
    main()
