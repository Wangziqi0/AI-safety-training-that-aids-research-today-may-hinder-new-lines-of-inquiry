"""Link blind scoring to matched training arms only after decision freeze."""
from collections import Counter
from adjudicate import HERE,read,write
from pathlib import Path
def main():
    initial=read('initial_raw.jsonl')
    codes={r['id']:r for r in read('initial_codes.jsonl')}
    repairs=read('repair_raw.jsonl') if (HERE/'repair_raw.jsonl').exists() else []
    repair_codes={r['id']:r for r in read('repair_codes.jsonl')} if repairs else {}
    joined=[]
    for r in initial:
        ident=r['id'];f='P01' if '0.471341' in r['messages'][1]['content'] else 'P04'
        row=dict(id=ident,field=f,arm=r['arm'],seed=r['seed'],initial=codes[ident],initial_truncated=r['truncated'],repair={})
        for response in [x for x in repairs if x['id'].startswith(ident+'-')]:
            rep=response['id'];row['repair'][rep.split('-')[-1]]=dict(**repair_codes[rep],truncated=response['truncated'])
        assert not row['repair'] if row['initial']['acted'] else set(row['repair'])=={'generic','specific'}
        joined.append(row)
    assert len(joined)==12 and Counter((r['field'],r['seed']) for r in joined)==Counter({(f,s):2 for f in ('P01','P04') for s in (311,617,929)})
    write('joined.jsonl',sorted(joined,key=lambda x:(x['field'],x['seed'],x['arm'])))
if __name__=='__main__':main()
