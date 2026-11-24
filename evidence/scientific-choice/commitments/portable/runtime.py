import hashlib
import os
import json
import math
import time
from pathlib import Path
import torch
from torch import nn
from torch.nn import functional as F
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer
from document_service import target
from fixtures import curriculum

BASE = os.environ.get('QWEN3_BASE', 'Qwen3-8B')
REV = 'b968826d9c46dd6066d109eabc6255188de91218'
SEEDS = (311,617,929)

class Adapter(nn.Module):
    def __init__(self, base):
        super().__init__()
        self.base = base
        self.a = nn.Parameter(torch.empty(8,base.in_features,device='cuda',dtype=torch.float32))
        self.b = nn.Parameter(torch.empty(base.out_features,8,device='cuda',dtype=torch.float32))
        self.reset()
    def reset(self):
        with torch.no_grad():
            self.a.normal_(std=.02)
            self.b.zero_()
    def forward(self,x):
        return self.base(x) + 2 * F.linear(F.linear(x,self.a.to(x.dtype)),self.b.to(x.dtype))

def load():
    tok = AutoTokenizer.from_pretrained(BASE,local_files_only=True)
    m = AutoModelForCausalLM.from_pretrained(BASE,dtype=torch.float16,attn_implementation='sdpa',
                                              device_map={'':'cuda:0'},local_files_only=True).eval()
    m.requires_grad_(False)
    for layer in m.model.layers:
        for name in ('q_proj','v_proj'):
            setattr(layer.self_attn,name,Adapter(getattr(layer.self_attn,name)))
    return tok,m

def reset(m,seed):
    torch.manual_seed(seed)
    for mod in m.modules():
        if isinstance(mod,Adapter):
            mod.reset()

def prompt(tok,msgs):
    return tok.apply_chat_template(msgs,tokenize=True,add_generation_prompt=True,
                                   enable_thinking=False,return_dict=False)

def tensor_state(m):
    return {n:p.detach().cpu().contiguous() for n,p in m.named_parameters() if p.requires_grad}

def fingerprint(values):
    s = hashlib.sha256()
    for n,p in sorted(values.items()):
        s.update(n.encode()+b'\x00')
        s.update(p.numpy().tobytes())
    return s.hexdigest()

def sha_file(path):
    with open(path,'rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def restore(m,state):
    params={n:p for n,p in m.named_parameters() if p.requires_grad}
    assert params.keys()==state.keys()
    with torch.no_grad():
        for n,p in params.items():
            p.copy_(state[n])

def train_one(tok,m,arm,seed,root):
    dest=root/f'{arm}-{seed}'
    dest.mkdir(parents=True,exist_ok=False)
    start=time.monotonic()
    reset(m,seed)
    initial=tensor_state(m)
    params=[p for p in m.parameters() if p.requires_grad]
    opt=torch.optim.AdamW(params,lr=2e-4,weight_decay=0.)
    with (dest/'steps.jsonl').open('w') as log:
        for step,rows in enumerate(curriculum(seed)):
            opt.zero_grad(set_to_none=True)
            examples=[]
            for r in rows:
                p=prompt(tok,[dict(role='user',content=r['prompt'])])
                text=target(r,arm)
                a=tok.encode(text,add_special_tokens=False)+[tok.eos_token_id]
                ids=torch.tensor([p+a],device='cuda')
                hidden=m.model(input_ids=ids,use_cache=False).last_hidden_state[0,len(p)-1:-1]
                loss=F.cross_entropy(m.lm_head(hidden).float(),torch.tensor(a,device='cuda'))
                (loss/len(rows)).backward()
                examples.append(dict(**r,target=text,target_ids=a,loss=loss.item()))
                del ids,hidden,loss
            norm=torch.nn.utils.clip_grad_norm_(params,1.,error_if_nonfinite=True).item()
            opt.step()
            print(json.dumps(dict(step=step+1,norm_before_clip=norm,examples=examples)),file=log,flush=True)
    final=tensor_state(m)
    path=dest/'adapter.pt'
    torch.save(final,path)
    restore(m,torch.load(path,weights_only=True))
    final_id=fingerprint(final)
    assert fingerprint(tensor_state(m))==final_id
    result=dict(arm=arm,seed=seed,base=REV,initial_sha256=fingerprint(initial),checkpoint_sha256=final_id,
                file_sha256=sha_file(path),trainable=sum(p.numel() for p in params),steps=18,
                gpu=torch.cuda.get_device_name(),torch=torch.__version__,transformers=transformers.__version__,
                adapter_change_l2=math.sqrt(sum((p-initial[n]).square().sum().item() for n,p in final.items())),
                wall_seconds=time.monotonic()-start,peak_allocated=torch.cuda.max_memory_allocated())
    assert result['adapter_change_l2']>0
    (dest/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)

if __name__=='__main__':
    tok,m=load()
    for s in SEEDS:
        for a in 'HAB':
            train_one(tok,m,a,s,Path('weights'))
