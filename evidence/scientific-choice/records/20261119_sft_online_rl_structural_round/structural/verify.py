"""Check logged updates, online resampling, frozen paired denominators and finite-world invariants."""
import json
import math
from collections import Counter,defaultdict
from itertools import zip_longest
from analysis import ROOT,C,records
from policy import accumulate,draw,forward,inputs,obtained_reward,target
from world import rng

def check_training():
    n=0
    checkpoints=0
    nonzero_updates=0
    actual={}; prev={}; rewards=defaultdict(Counter)
    maxerr=0.
    changed_sampling=defaultdict(int)
    for rec in records("training"):
        key=tuple(rec[k] for k in ("seed","algo","arm"))
        w=rec["weights"]
        if rec["step"]==-1:
            prev[key]=w
            actual[key]=w
            continue
        saved=prev[key]
        t=rec["step"]
        policy_rng=rng("online",key[0],t)
        batch_rng=rng("batch",key[0],t)
        gradient=[0.]*len(w)
        for ident,case,act,reward,p in rec["samples"]:
            assert (ident,case)==(batch_rng.randrange(1000000),batch_rng.randrange(3))
            x=inputs(case)
            h,_,observed=forward(saved,x)
            assert p==observed
            if key[1]=="reinforce":
                q=policy_rng.random()
                assert draw(p,q)==act and obtained_reward(key[2],case,act,ident)==reward
                changed_sampling[key[2]]+=int(act!=draw(forward(actual[key],x)[2],q))
                rewards[key[2]][reward]+=1
                factor=reward
            else:
                assert target(key[2],case)==act and reward is None
                factor=1
            accumulate(saved,x,h,p,act,factor,gradient)
            n+=1
        g=[v/len(rec["samples"]) for v in gradient]
        assert g==rec["gradient"]
        err=max(abs(v+C["learning_rate"]*d-post) for v,d,post in zip(saved,g,w))
        maxerr=max(maxerr,err)
        assert err<1e-13
        nonzero_updates+=int(w!=saved)
        checkpoints+=1
        prev[key]=w
    for r in records("checkpoints"):
        key=tuple(r[k] for k in ("seed","algo","arm"))
        assert r["initial"]==actual[key] and r["final"]==prev[key]
        assert actual[key]==actual[(key[0],"sft","H")]
    return dict(training_events=n,updates=checkpoints,nonzero_updates=nonzero_updates,
                max_parameter_error=maxerr,rl_reward_counts=dict(rewards),
                rl_sample_changed_vs_initial_same_uniform=dict(changed_sampling))


def check_receivers():
    tall=Counter()
    keys=set()
    cut={}
    for m,y in zip_longest(records("materials"),records("outcomes")):
        assert m and y
        key=tuple(m[k] for k in ("seed","algo","arm","coupling","split","family","clone"))
        assert key==tuple(y[k] for k in ("seed","algo","arm","coupling","split","family","clone"))
        assert key not in keys
        keys.add(key)
        if key[3]=="cut":
            block=(key[0],)+key[4:]
            state=(m["package"],y["current_use"],y["method"],y["new_reading"])
            assert cut.setdefault(block,state)==state
        assert (y["status"]=="delivered")==bool(y["current_use"])
        assert (y["new_reading"]==y["reference"])==bool(y["later_use"])
        if y["opportunity"]!="needed":
            assert y["later_use"]==1
        tall[y["method"]]+=1
    assert len(keys)==len(C["seeds"])*2*3*3*2*24*4
    return dict(matched_packages=len(keys),cut_identical_blocks=len(cut),method_counts=tall)


if __name__=="__main__":
    result=dict(**check_training(),**check_receivers())
    (ROOT/"audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))
