import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(name):
    return [json.loads(x) for x in (HERE/name).read_text().splitlines() if x.strip()]
def write(name,rows):
    (HERE/name).write_text(''.join(json.dumps(x)+'\n' for x in rows))
def mask(stage):
    write(stage+'_blind.jsonl',[{'id':r['id'],'text':r['text']} for r in read(stage+'_raw.jsonl')])
def recover():
    acted={r['id'] for r in read('initial_codes.jsonl') if r['acted']}
    repairs=json.loads((HERE/'repairs.json').read_text())
    rows=[]
    for r in read('initial_raw.jsonl'):
        if r['id'] in acted:continue
        for condition,request in repairs.items():
            messages=r['messages']+[dict(role='assistant',content=r['text']),dict(role='user',content=request)]
            rows.append(dict(id=r['id']+'-'+condition,arm=r['arm'],seed=r['seed'],max_new_tokens=r['max_new_tokens'],messages=messages))
    write('repair_in.jsonl',rows)
if __name__=='__main__':
    import sys
    if sys.argv[1]=='recover':recover()
    else:mask(sys.argv[1])
