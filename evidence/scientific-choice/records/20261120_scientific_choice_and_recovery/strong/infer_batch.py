import argparse
import itertools
import json
from pathlib import Path
import torch
from runtime import load,prompt,restore,reset,REV,SEEDS,sha_file

@torch.inference_mode()
def generate(tok,m,rows):
    sequences=[prompt(tok,x['messages']) for x in rows]
    width=max(map(len,sequences))
    cap=rows[0].get('max_new_tokens',256)
    if not 0 < cap <= 2048 or width+cap > 8192:
        raise ValueError('Generation requires 1–2048 new tokens and at most 8192 total.')
    ids=torch.full((len(rows),width),tok.pad_token_id,device='cuda',dtype=torch.long)
    mask=torch.zeros_like(ids)
    for i,line in enumerate(sequences):
        ids[i,-len(line):]=torch.tensor(line,device='cuda')
        mask[i,-len(line):]=1
    eos=m.generation_config.eos_token_id
    eos=[eos] if isinstance(eos,int) else eos
    seq=m.generate(input_ids=ids,attention_mask=mask,do_sample=False,num_beams=1,max_new_tokens=cap,
                   repetition_penalty=1.,pad_token_id=tok.pad_token_id,eos_token_id=eos)[:,width:].tolist()
    for row,line,s in zip(rows,sequences,seq):
        end=next((j for j,x in enumerate(s) if x in eos),None)
        out=s if end is None else s[:end+1]
        yield dict(**row,text=tok.decode(out,skip_special_tokens=True,clean_up_tokenization_spaces=False),token_ids=out,
                   eos=end is not None,truncated=end is None,generated_tokens=len(out),context_tokens=len(line),
                   effective_token_cap=cap,batch_size=len(rows),base_revision=REV)

def run_batch(tok,m,source,dest):
    rows=[json.loads(x) for x in source.read_text().splitlines() if x.strip()]
    if len({r['id'] for r in rows})!=len(rows):
        raise ValueError('Request ids must be unique')
    result={}
    by_model=lambda r:(r['arm'],r['seed'])
    for (arm,seed),items in itertools.groupby(sorted(rows,key=by_model),by_model):
        if arm=='F':
            reset(m,311)
            fingerprint=REV
        else:
            if arm not in ('A','H','B') or seed not in SEEDS:
                raise ValueError((arm,seed))
            folder=Path('weights')/f'{arm}-{seed}'
            manifest=json.loads((folder/'manifest.json').read_text())
            path=folder/'adapter.pt'
            assert sha_file(path)==manifest['file_sha256']
            restore(m,torch.load(path,weights_only=True))
            fingerprint=manifest['checkpoint_sha256']
        cap_key=lambda r:r.get('max_new_tokens',256)
        for _,group in itertools.groupby(sorted(items,key=cap_key),cap_key):
            values=list(group)
            for start in range(0,len(values),4):
                for out in generate(tok,m,values[start:start+4]):
                    result[out['id']]=dict(**out,checkpoint_sha256=fingerprint)
    if dest.exists():
        raise FileExistsError(dest)
    tmp=dest.with_suffix('.partial')
    tmp.write_text(''.join(json.dumps(result[r['id']],ensure_ascii=False)+'\n' for r in rows))
    tmp.rename(dest)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('dest',type=Path)
    args=parser.parse_args()
    run_batch(*load(),args.source,args.dest)
