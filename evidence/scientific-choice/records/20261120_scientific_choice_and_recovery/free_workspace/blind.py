import sys,json,re,hashlib
from pathlib import Path
ST=Path(__file__).resolve().parent/'stages'
def read(p):return [json.loads(s) for s in p.read_text().splitlines()]
def blindkey(stage,ident):return hashlib.sha256(f"desk-stage{stage}-{ident}".encode()).hexdigest()[:7]
def list_blind(stage):
    return sorted([(blindkey(stage,r['id']),r['text']) for r in read(ST/f'output{stage}.jsonl')])
if __name__=='__main__':
    stage=int(sys.argv[1]);lst=list_blind(stage)
    for k,txt in lst[int(sys.argv[2]) if len(sys.argv)>2 else 0 : int(sys.argv[3]) if len(sys.argv)>3 else None]:
        plain=re.sub(r'JOIN-[A-F0-9]+','[private]',txt,flags=re.I)
        print(k,re.sub(r'\s+',' ',plain),end='\n\n')
