"""A small native causal transformer and an independently specified continuing practice."""
import math
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

WORDS="begin record field public mixed private stable ambiguous urgent routine team lab run finish s0 s1 k0 k1 k2 k3 HELP1 HELP2 REFER1 REFER2 HOLD1 HOLD2 RELEASE1 RELEASE2 DELIVER1 DELIVER2 ACQUIRE1 ACQUIRE2 WAIT1 WAIT2".split()
IDX={v:i for i,v in enumerate(WORDS)}
SERV=("HELP","REFER","HOLD","RELEASE")
SCI=("DELIVER","ACQUIRE","WAIT")
D=32

class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.norm1=nn.LayerNorm(D);self.norm2=nn.LayerNorm(D)
        self.q=nn.Linear(D,D);self.k=nn.Linear(D,D);self.v=nn.Linear(D,D);self.out=nn.Linear(D,D)
        self.mlp=nn.Sequential(nn.Linear(D,D*2),nn.GELU(),nn.Linear(D*2,D))
    def forward(self,x):
        b,n,d=x.shape
        def heads(z):return z.reshape(b,n,4,d//4).transpose(1,2)
        h=self.norm1(x)
        q,k,v=[heads(pr(h)) for pr in (self.q,self.k,self.v)]
        s=(q@k.transpose(-1,-2))/math.sqrt(d//4)
        causal=torch.ones(n,n,device=x.device,dtype=torch.bool).tril()
        att=s.masked_fill(~causal,-torch.inf).softmax(-1)
        x=x+self.out((att@v).transpose(1,2).reshape(b,n,d))
        return x+self.mlp(self.norm2(x))

class Model(nn.Module):
    def __init__(self):
        super().__init__();self.embed=nn.Embedding(len(WORDS),D);self.pos=nn.Parameter(torch.randn(7,D)*.05)
        nn.init.normal_(self.embed.weight,std=.13)
        self.blocks=nn.ModuleList([Block(),Block()]);self.final=nn.LayerNorm(D)
    def forward(self,x):
        h=self.embed(x)+self.pos[:x.shape[1]]
        for layer in self.blocks:h=layer(h)
        return F.linear(self.final(h[:,-1]),self.embed.weight)

def contexts(kind,cases,phase,style,group):
    seq=[]
    for c,t,s,g in zip(cases,phase,style,group):
        q=("public","mixed","private")[c] if kind=="record" else ("stable","ambiguous")[c]
        seq.append([IDX[w] for w in ["begin",kind,q,("routine","urgent")[t],("team","lab")[s],("k0","k1","k2","k3")[g],"run"]])
    return torch.tensor(seq)

def inputs(rng,kind,n):
    c=rng.integers(0,3 if kind=="record" else 2,n)
    t=rng.integers(0,2,n);s=rng.integers(0,2,n);g=rng.integers(0,4,n)
    return contexts(kind,c,t,s,g),c,t

def token(names,idx,alias):return torch.tensor([IDX[names[i]+str(1+a)] for i,a in zip(idx,alias)])
def pretrain_examples(rng,n):
    n1=n//2;xr,c,t=inputs(rng,"record",n1);xs,cs,ts=inputs(rng,"field",n-n1)
    # Pretraining contains imperfect practices. No science examples enter subsequent service training.
    rpol=np.array([[.78,.10,.08,.04],[.28,.25,.21,.26],[.08,.13,.55,.24]])
    ar=[rng.choice(4,p=rpol[i]) for i in c]
    spol=np.array([[[.76,.17,.07],[.82,.12,.06]],[[.32,.57,.11],[.49,.40,.11]]])
    az=[rng.choice(3,p=spol[i,j]) for i,j in zip(cs,ts)]
    return torch.cat((xr,xs)),torch.cat((token(SERV,ar,rng.integers(2,size=n1)),token(SCI,az,rng.integers(2,size=n-n1))))
def service(rng,n):
    x,c,t=inputs(rng,"record",n)
    alias=rng.integers(2,size=n)
    # H gives permitted service when mixed, A refers; both withhold fully private material.
    return x,c,token(SERV,np.choose(c,[0,0,2]),alias),token(SERV,np.choose(c,[0,1,2]),alias)
def reward(c,actions,arm):
    valid=np.choose(c,([0,0,2] if arm=="H" else [0,1,2]))
    return torch.tensor([[float(int(a) in (IDX[SERV[w]+"1"],IDX[SERV[w]+"2"])) for a in row]
                         for row,w in zip(actions.tolist(),valid)],dtype=torch.float64)
def classes(names):
    return [[IDX[n+"1"],IDX[n+"2"]] for n in names]
def clinical():
    # Finite, anonymized artificial inference apparatus. Not a classifier for real human decisions.
    rng=np.random.default_rng(96613);n=384
    x,signal,deadline=inputs(rng,"field",n)
    # Independent primitive observations. Hidden later property determines the receiver's decision.
    now=rng.integers(0,2,n)
    future=rng.integers(0,2,n)
    ordinary_now=now^((rng.random(n)<.24).astype(int))
    product_now=now^((rng.random(n)<.06).astype(int))
    diagnostic_now=now^((rng.random(n)<.11).astype(int))
    ordinary_later=future^((rng.random(n)<.32).astype(int))
    diagnostic_later=future^((rng.random(n)<.08).astype(int))
    compact_later=future^((rng.random(n)<.04).astype(int))
    archive_keys=rng.random(n)
    truth={"signal":signal,"deadline":deadline,"now":now,"later":future,"ordinary_now":ordinary_now,
       "product_now":product_now,"diagnostic_now":diagnostic_now,"ordinary_later":ordinary_later,
       "diagnostic_later":diagnostic_later,"compact_later":compact_later,"archive_key":archive_keys}
    return x,truth

def payoff(t):
    n=len(t["now"]);v=len(WORDS)
    def table(arr):return np.broadcast_to(arr[:,None],(n,v)).copy()
    current=table(t["ordinary_now"])
    prod,acq,wait=classes(SCI);delivery=table(np.zeros(n))
    for a in prod:
        current[:,a]=t["product_now"];delivery[:,a]=1.
    for a in acq:
        current[:,a]=np.where(t["deadline"]==0,t["diagnostic_now"],t["ordinary_now"])
        delivery[:,a]=(t["deadline"]==0).astype(float)
    yielded={"current_correct":current==t["now"][:,None],"current_used":delivery}
    for mode in ("diagnostic","compact"):
        for rate in (0.,.5,1.):
            use_archive=t["archive_key"]<rate
            base=np.where(use_archive,t["diagnostic_later"],t["ordinary_later"])
            later=table(base);reads=table(use_archive.astype(float))
            for a in acq:later[:,a]=t["diagnostic_later"];reads[:,a]=0
            if mode=="compact":
                for a in prod:later[:,a]=t["compact_later"];reads[:,a]=0
            suffix=mode+"_"+str(int(rate*100))
            yielded["later_correct_"+suffix]=later==t["later"][:,None]
            yielded["archive_reads_"+suffix]=reads
    for group,ids in zip(SCI,classes(SCI)):
        mask=np.zeros((n,v));mask[:,ids]=1
        yielded["scientific_action_"+group.lower()]=mask
    return {k:torch.from_numpy(np.asarray(v,dtype=float)) for k,v in yielded.items()}

def category(n):
    if n=="embed.weight":return "tied_embedding_and_output"
    if n=="pos":return "position"
    if ".mlp." in n:return "feed_forward"
    for pr in ("q","k","v","out"):
        if "."+pr+"." in n:return "attention_"+pr
    return "normalization"
