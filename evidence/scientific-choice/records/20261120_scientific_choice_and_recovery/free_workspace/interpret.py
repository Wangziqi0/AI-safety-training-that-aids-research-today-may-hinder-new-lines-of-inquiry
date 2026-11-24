"""Convert desk annotations, keyed without assignment, into structured archive decisions."""
import argparse,json,re
from blind import ST,list_blind
from classify import brief
def interpret(stage):
    texts=dict(list_blind(stage))
    lookup={}
    for line in (ST/f'annotations{stage}.txt').read_text().splitlines():
        if not line.strip() or line.startswith('#'):continue
        cols=line.split('|')
        key,op,*args=cols[0].split()
        assert key in texts and key not in lookup, key
        unserved=[x.strip() for x in cols[1:] if x.strip()]
        obj={'op':{'R':'request','C':'clarify','H':'hold','L':'release','U':'unresolved'}[op],
             'unserved':unserved,'items':args if op=='R' else [],
             'periods':[float(x) for x in args] if op=='L' else [],
             'desk_excerpt':brief(texts[key])[:480] or texts[key][:480]}
        lookup[key]=obj
    assert set(lookup)==set(texts),(set(texts)-set(lookup),set(lookup)-set(texts))
    (ST/f'interpretation{stage}.json').write_text(json.dumps(lookup,indent=2,ensure_ascii=False)+'\n')
if __name__=='__main__':
 import sys
 interpret(int(sys.argv[1]))
