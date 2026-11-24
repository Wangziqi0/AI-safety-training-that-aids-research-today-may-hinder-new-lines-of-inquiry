import hashlib
from pathlib import Path
import torch
from torch import nn
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE_SHA = 'c1b9b30e907950516ba3c646bdf570d8084c25a6410a0cdca80cf04b11bc13a8'
DEFAULT_BASE = Path.home()/'scratch/open-science-align-20261119/base'
RANK = 8


def sha_file(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20), b''):
            h.update(block)
    return h.hexdigest()


class LoRA(nn.Module):
    def __init__(self, original):
        super().__init__()
        self.original = original
        self.lora_a = nn.Parameter(torch.empty(RANK,original.in_features,device=original.weight.device,dtype=torch.float32))
        self.lora_b = nn.Parameter(torch.empty(original.out_features,RANK,device=original.weight.device,dtype=torch.float32))
        self.reset()

    def reset(self):
        with torch.no_grad():
            self.lora_a.normal_(std=0.02)
            self.lora_b.zero_()

    def forward(self, x):
        change = torch.nn.functional.linear(torch.nn.functional.linear(x,self.lora_a.to(x.dtype)),self.lora_b.to(x.dtype))
        return self.original(x) + 2.0 * change


def load(path):
    tok = AutoTokenizer.from_pretrained(path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.float16, local_files_only=True,attn_implementation='sdpa').to('cuda').eval()
    model.requires_grad_(False)
    for layer in model.model.layers:
        layer.self_attn.q_proj = LoRA(layer.self_attn.q_proj)
        layer.self_attn.v_proj = LoRA(layer.self_attn.v_proj)
    return tok,model


def reset(model, seed):
    torch.manual_seed(seed)
    for m in model.modules():
        if isinstance(m,LoRA):
            m.reset()


def weights(model):
    return {n:v.detach().cpu().contiguous() for n,v in model.named_parameters() if v.requires_grad}


def fingerprint(weights):
    h=hashlib.sha256()
    for n,v in sorted(weights.items()):
        h.update(n.encode()+b'\0')
        h.update(v.numpy().tobytes())
    return h.hexdigest()


def restore(model,path):
    params=dict(model.named_parameters())
    state=torch.load(path,weights_only=True,map_location='cpu')
    assert set(state)=={n for n,p in params.items() if p.requires_grad}
    with torch.no_grad():
        for n,t in state.items():
            params[n].copy_(t)
    return fingerprint(state)


def prompt_ids(tok,row):
    msgs = []
    if row.get('system'):
        msgs.append({'role':'system','content':row['system']})
    msgs.append({'role':'user','content':row['prompt']})
    return tok.apply_chat_template(msgs,tokenize=True,add_generation_prompt=True,return_dict=False)


def batch_tokens(lines, pad, left):
    width=max(map(len,lines))
    ids=torch.full((len(lines),width),pad,dtype=torch.long,device='cuda')
    mask=torch.zeros_like(ids)
    for i,line in enumerate(lines):
        sl=slice(width-len(line),width) if left else slice(0,len(line))
        ids[i,sl]=torch.tensor(line,device='cuda')
        mask[i,sl]=1
    return ids,mask


@torch.inference_mode()
def generate(model,tok,rows,cap,sample=False):
    lines=[prompt_ids(tok,r) for r in rows]
    ids,mask=batch_tokens(lines,tok.pad_token_id,True)
    eos=model.generation_config.eos_token_id
    eos=[eos] if isinstance(eos,int) else eos
    opts=dict(repetition_penalty=1.,do_sample=sample,max_new_tokens=cap,num_beams=1,pad_token_id=tok.pad_token_id,eos_token_id=eos)
    if sample:
        opts.update(temperature=1., top_p=1., top_k=0)
    seq=model.generate(input_ids=ids,attention_mask=mask,**opts)[:,ids.shape[1]:].tolist()
    result=[]
    for row,seq1,context in zip(rows,seq,lines):
        end=next((i for i,v in enumerate(seq1) if v in eos),None)
        out=seq1 if end is None else seq1[:end+1]
        raw=tok.decode(out,skip_special_tokens=True)
        result.append(dict(id=row['id'],text=raw,ids=out,eos=end is not None,truncated=end is None,context_tokens=len(context),
                           text_sha256=hashlib.sha256(raw.encode()).hexdigest()))
    return result
