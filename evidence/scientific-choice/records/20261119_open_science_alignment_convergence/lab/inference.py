"""Read arbitrary UTF-8 JSONL prompts; process multiple named checkpoints on one GPU."""
import argparse
import json
from pathlib import Path
from model import DEFAULT_BASE,BASE_SHA,load,generate,restore,reset
from tasks import tests,guarded

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--base',type=Path,default=DEFAULT_BASE)
    p.add_argument('--checkpoints',type=Path,default=Path('observed'))
    p.add_argument('--models',nargs='+',required=True)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--input',type=Path)
    g.add_argument('--heldout',action='store_true')
    p.add_argument('--out',type=Path,required=True,help='one JSONL per checkpoint')
    p.add_argument('--batch',type=int,default=4)
    p.add_argument('--max-new',type=int,default=384)
    args=p.parse_args()
    rows=tests() if args.heldout else [json.loads(x) for x in args.input.read_text().splitlines() if x.strip()]
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
        with (args.out/f'{name}.jsonl').open('x') as fout:
            for j in range(0,len(rows),args.batch):
                batch=rows[j:j+args.batch]
                for row,ans in zip(batch,generate(model,tok,batch,args.max_new)):
                    rec=dict(**ans,model=name,adapter_sha256=identity,base_sha256=BASE_SHA,guarded_text=guarded(row,ans['text']),prompt=row['prompt'])
                    if args.heldout:
                        rec['document']=row
                    if row.get('system'):
                        rec['system']=row['system']
                    print(json.dumps(rec,ensure_ascii=False),file=fout,flush=True)
