import argparse
import json
import math
from pathlib import Path
import random
import time
import torch
from torch.nn import functional as F
import transformers

from model import DEFAULT_BASE, BASE_SHA, load, reset, weights, fingerprint, prompt_ids, batch_tokens, generate, sha_file, restore
from tasks import packet, target, reward, sft_diagnostic_reward


def run(model,tok,algo,arm,seed,out):
    dest=out/f'{algo}-{seed}-{arm}'
    dest.mkdir(parents=True,exist_ok=False)
    reset(model,seed)
    source=weights(model)
    params=[v for v in model.parameters() if v.requires_grad]
    rng=random.Random(seed)
    opt=torch.optim.AdamW(params,lr=2e-4 if algo=='sft' else 4e-5,weight_decay=0)
    baseline=0.
    steps=18 if algo=='sft' else 8
    begin=time.monotonic()
    with (dest/'steps.jsonl').open('w') as log:
        for step in range(steps):
            rows=packet(rng,step)
            prompts=[prompt_ids(tok,row) for row in rows]
            if algo=='sft':
                texts=[target(row,arm) for row in rows]
                sampled=[dict(text=s,ids=tok.encode(s,add_special_tokens=False)+[tok.eos_token_id],eos=True,truncated=False) for s in texts]
            else:
                sampled=generate(model,tok,rows,48,True)
            answers=[s['ids'] for s in sampled]
            ids,mask=batch_tokens([p+a for p,a in zip(prompts,answers)],tok.pad_token_id,False)
            hidden=model.model(input_ids=ids,attention_mask=mask,use_cache=False).last_hidden_state
            feats=torch.cat([hidden[i,len(p)-1:len(p)-1+len(a)] for i,(p,a) in enumerate(zip(prompts,answers))])
            gold=torch.tensor([v for a in answers for v in a],device='cuda')
            neglog=F.cross_entropy(model.lm_head(feats).float(),gold,reduction='none')
            losses=neglog.split(list(map(len,answers)))
            reward_fn = sft_diagnostic_reward if algo == 'sft' else reward
            rewards=[reward_fn(r,s['text'],arm) for r,s in zip(rows,sampled)]
            if algo=='sft':
                loss=torch.stack([x.mean() for x in losses]).mean()
            else:
                loss=torch.stack([(r-baseline)*x.sum() for r,x in zip(rewards,losses)]).mean()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            norm=float(torch.nn.utils.clip_grad_norm_(params,1.,error_if_nonfinite=True))
            opt.step()
            rec=dict(step=step,loss=float(loss.detach()),gradient_norm_preclip=norm,baseline=baseline,rows=rows,
                     answers=sampled,rewards=rewards,per_response_logp=[-float(x.detach().sum()) for x in losses])
            if algo=='rl':
                rec['token_logp']=[(-x.detach()).tolist() for x in losses]
            print(json.dumps(rec),file=log,flush=True)
            baseline=0.8*baseline+0.2*sum(rewards)/len(rewards)
    final=weights(model)
    difference=math.sqrt(sum((v-source[n]).square().sum().item() for n,v in final.items()))
    path=dest/'adapter.pt'
    torch.save(final,path)
    result=dict(algo=algo,arm=arm,seed=seed,torch=torch.__version__,transformers=transformers.__version__,gpu=torch.cuda.get_device_name(),
                steps=steps,adapter_parameters=sum(x.numel() for x in params),total_parameters=sum(x.numel() for x in model.parameters()),
                source_sha256=fingerprint(source),weight_sha256=fingerprint(final),file_sha256=sha_file(path),base_sha256=BASE_SHA,
                delta_l2=difference,wall_seconds=time.monotonic()-begin)
    assert restore(model,path)==result['weight_sha256'] and difference>0
    (dest/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('jobs',nargs='+',help='e.g. sft-1901-H')
    parser.add_argument('--base',type=Path,default=DEFAULT_BASE)
    parser.add_argument('--out',type=Path,default=Path('observed'))
    args=parser.parse_args()
    tok,model=load(args.base)
    for name in args.jobs:
        algo,seed,arm=name.split('-')
        assert algo in ('sft','rl') and arm in ('A','H','B')
        run(model,tok,algo,arm,int(seed),args.out)
