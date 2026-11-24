"""Two-stage per-root freezing and out-of-sample evaluation with actual weight updates."""
import argparse
import hashlib
import json
from pathlib import Path
from collections import defaultdict
import numpy as np
import torch
from torch.nn import functional as F
from instrument import Model,pretrain_examples,service,clinical,payoff,classes,SERV,SCI,IDX,WORDS,category,reward
HERE=Path(__file__).resolve().parent
ALGS=["sft","rl"];ROOTS=list(range(4107,4119));RATES=(.012,.024)

def key(w):return hashlib.sha256(b"".join(v.detach().numpy().tobytes() for v in w.values())).hexdigest()
def dump(p,obj):
    with p.open("x") as f:json.dump(obj,f,allow_nan=False);f.write("\n")
def net():return Model().double()
def targets():
    x,raw=clinical();metrics=payoff(raw)
    rgen=np.random.default_rng(97731);sx,c,_,_=service(rgen,192)
    private=torch.tensor(c>0);safe=torch.zeros((len(c),len(WORDS)),dtype=torch.float64)
    safe[:,[IDX["RELEASE1"],IDX["RELEASE2"]]]=1
    return x,raw,metrics,sx,private,safe
def obs(m,keep=False):
    x,raw,metrics,sx,private,safe=targets()
    p=m(x).softmax(-1);sp=m(sx).softmax(-1)
    o={"service_nonpublic_release":(sp[private]*safe[private]).sum(-1).mean()}
    o.update({k:(p*v).sum(-1).mean() for k,v in metrics.items()})
    return (o,p,sp) if keep else o
def namegrad(obj,model,retain=False):
    v=list(model.named_parameters())
    return {n:g.detach().clone() for (n,_),g in zip(v,torch.autograd.grad(obj,[p for n,p in v],retain_graph=retain))}
def train_base(seed):
    torch.manual_seed(seed);rng=np.random.default_rng(seed+100);m=net()
    opt=torch.optim.AdamW(m.parameters(),lr=.003,weight_decay=.005)
    for _ in range(112):
        x,t=pretrain_examples(rng,96)
        opt.zero_grad();loss=F.cross_entropy(m(x),t);loss.backward();opt.step()
    return m
def update_grads(m,seed,alg):
    rng=np.random.default_rng(seed+12);x,c,h,a=service(rng,80)
    logits=m(x);lp=logits.log_softmax(-1)
    if alg=="sft":loss=[F.cross_entropy(logits,t) for t in (h,a)]
    else:
        generator=torch.Generator().manual_seed(seed+963)
        sample=lp.detach().exp().multinomial(8,True,generator=generator)
        picked=lp.gather(1,sample);loss=[]
        for arm in ("H","A"):
            r=reward(c,sample,arm)
            loss.append(-(picked*(r-.25)).mean())
    return [namegrad(val,m,True) for val in loss]
def saveforecast(seed):
    directory=HERE/"roots"/str(seed);directory.mkdir(exist_ok=True,parents=True)
    m=train_base(seed);state=m.state_dict();torch.save(state,directory/"base.pt")
    values=obs(m)
    j={k:namegrad(w,m,True) for k,w in values.items()}
    pred={"seed":seed,"base_hash":key(state),"base_values":{k:float(v.detach()) for k,v in values.items()},"algorithms":{}}
    for alg in ALGS:
        gs=update_grads(m,seed,alg);torch.save(gs,directory/(alg+".pt"))
        d={k:gs[0][k]-gs[1][k] for k in gs[0]} # theta_A - theta_H per unit step
        rows={}
        for goal,g in j.items():
            blocks=defaultdict(float)
            for k,t in g.items():blocks[category(k)]+=float((t*d[k]).sum())
            rows[goal]={"derivative":sum(blocks.values()),"components":dict(blocks)}
        pred["algorithms"][alg]=rows
    dump(directory/"forecast.json",pred)
def test(seed):
    d=HERE/"roots"/str(seed)
    f=json.loads((d/"forecast.json").read_text())
    state=torch.load(d/"base.pt",weights_only=True)
    assert key(state)==f["base_hash"]
    x,raw,metrics,sx,private,safe=targets()
    out={"seed":seed,"base_hash":f["base_hash"],"measurements":[]}
    n=metrics["current_used"].shape[0]
    rng=np.random.default_rng(81871+seed)
    u=torch.tensor(rng.random(n))[:,None]
    for alg in ALGS:
        gs=torch.load(d/(alg+".pt"),weights_only=True)
        for eta in (0.,*RATES):
            pair=[]
            for i,arm in enumerate(["H","A"]):
                m=net();m.load_state_dict({k:v-eta*gs[i][k] for k,v in state.items()})
                with torch.no_grad():
                    o,p,sp=obs(m,True)
                    ids=(p.cumsum(-1)<u).sum(-1).clamp_max(p.shape[-1]-1)
                    actual={k:float(v[torch.arange(n),ids].mean()) for k,v in metrics.items()}
                    pair.append(({k:float(v) for k,v in o.items()},actual,ids.tolist()))
            rows={}
            for k in pair[0][0]:
                measured=pair[1][0][k]-pair[0][0][k]
                linear=eta*f["algorithms"][alg][k]["derivative"]
                rows[k]={"actual_difference":measured,"predicted":linear,"absolute_error":abs(measured-linear)}
            out["measurements"].append({"alg":alg,"eta":eta,"metrics":rows,"H_action_ids":pair[0][2],"A_action_ids":pair[1][2],
                    "sampled_consequences":{"H":pair[0][1],"A":pair[1][1]}})
    dump(d/"evaluation.json",out)
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("stage",choices=["forecast","evaluate","world"]);ap.add_argument("seed",nargs="?",type=int);args=ap.parse_args()
    torch.set_num_threads(2)
    if args.stage=="world":
        x,t=clinical();dump(HERE/"JOBS.json",{"context_ids":x.tolist(),**{k:v.tolist() for k,v in t.items()}})
    elif args.stage=="forecast":saveforecast(args.seed)
    else:test(args.seed)
