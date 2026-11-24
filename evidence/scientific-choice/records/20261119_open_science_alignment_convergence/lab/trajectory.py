"""Direct, temperature-scaled full-vocabulary autoregressive sampling and replay."""
import argparse
import hashlib
import json
from pathlib import Path
import torch
from model import DEFAULT_BASE, BASE_SHA, load, restore, reset, prompt_ids, batch_tokens
from tasks import guarded


@torch.inference_mode()
def trajectory_batch(model,tok,rows,cap,temp,default_seed,score):
    contexts=[prompt_ids(tok,r) for r in rows]
    ids,mask=batch_tokens(contexts,tok.pad_token_id,True)
    positions=(mask.cumsum(-1)-1).clamp_min(0)
    eos=model.generation_config.eos_token_id
    eos=set([eos] if isinstance(eos,int) else eos)
    logs=[[] for _ in rows]
    paths=[[] for _ in rows]
    active=[True]*len(rows)
    rng=[torch.Generator(device='cuda').manual_seed(r.get('draw_seed',default_seed)) for r in rows]
    gold=[r['ids'] for r in rows] if score else None
    if score:
        for path in gold:
            assert 0<len(path)<=cap and not any(x in eos for x in path[:-1])
    steps=max(map(len,gold)) if score else cap
    kv=None
    for j in range(steps):
        out=model(input_ids=ids,attention_mask=mask,position_ids=positions,past_key_values=kv,use_cache=True,logits_to_keep=1)
        kv=out.past_key_values
        logits=out.logits[:,-1].float()/temp
        logps=torch.log_softmax(logits,dim=-1)
        choices=[]
        for i in range(len(rows)):
            if not active[i]:
                choices.append(tok.pad_token_id)
            elif score:
                choices.append(gold[i][j])
            else:
                choices.append(int(torch.multinomial(logps[i].exp(),1,generator=rng[i])))
        vals=logps[torch.arange(len(rows),device='cuda'),torch.tensor(choices,device='cuda')].tolist()
        for i,token in enumerate(choices):
            if active[i]:
                paths[i].append(token)
                logs[i].append(vals[i])
                active[i]=token not in eos and (not score or j+1<len(gold[i]))
        if not any(active):
            break
        ids=torch.tensor(choices,device='cuda')[:,None]
        positions=mask.sum(-1,keepdim=True)
        mask=torch.cat((mask,torch.ones_like(positions)),dim=-1)
    result=[]
    for i,(r,path,logp,ctx) in enumerate(zip(rows,paths,logs,contexts)):
        raw=tok.decode(path,skip_special_tokens=True)
        ended=path[-1] in eos
        result.append(dict(id=r['id'],prompt=r['prompt'],system=r.get('system'),context_ids=ctx,context_tokens=len(ctx),
                           text=raw,guarded_text=guarded(r,raw),ids=path,token_logp=logp,logp=sum(logp),
                           temperature=temp,draw_seed=r.get('draw_seed',default_seed),eos=ended,
                           truncated=(len(path)==cap and not ended),prefix_only=not ended,
                           text_sha256=hashlib.sha256(raw.encode()).hexdigest()))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['sample','score'])
    p.add_argument('--input',type=Path,required=True,help='JSONL id,prompt[,system,draw_seed]; score also requires ids')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--models',nargs='+',required=True)
    p.add_argument('--base',type=Path,default=DEFAULT_BASE)
    p.add_argument('--checkpoints',type=Path,default=Path('observed'))
    p.add_argument('--temperature',type=float,default=.8)
    p.add_argument('--seed',type=int,default=445)
    p.add_argument('--batch',type=int,default=4)
    p.add_argument('--max-new',type=int,default=384)
    args=p.parse_args()
    assert args.temperature>0 and args.max_new>0
    rows=[json.loads(x) for x in args.input.read_text().splitlines() if x.strip()]
    assert len({r['id'] for r in rows})==len(rows)
    tok,model=load(args.base)
    args.out.mkdir(parents=True,exist_ok=True)
    for name in args.models:
        if name=='base':
            reset(model,0)
            identity='zero-adapter'
        else:
            dest=args.checkpoints/name
            identity=restore(model,dest/'adapter.pt')
            assert identity==json.loads((dest/'manifest.json').read_text())['weight_sha256']
        with (args.out/f'{name}.jsonl').open('x') as f:
            for j in range(0,len(rows),args.batch):
                b=rows[j:j+args.batch]
                if args.mode=='score':
                    for r in b:
                        assert r.get('temperature',args.temperature)==args.temperature
                        assert r.get('context_ids',prompt_ids(tok,r))==prompt_ids(tok,r)
                for ans in trajectory_batch(model,tok,b,args.max_new,args.temperature,args.seed,args.mode=='score'):
                    ans.update(model=name,adapter_sha256=identity,base_sha256=BASE_SHA)
                    print(json.dumps(ans,ensure_ascii=False),file=f,flush=True)
