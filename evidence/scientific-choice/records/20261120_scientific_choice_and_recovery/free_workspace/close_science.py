from pathlib import Path
import hashlib,json,re,subprocess,sys
from collections import Counter
from measurements import early
from blind import ST,read
from source import write
from transport import replace_tree
HERE=ST.parent
DS=HERE.parent/'downstream'
PR=HERE.parent/'practice'

def lock(stage):
    receipts=[];products=[];stand=[];transport=[]
    for w in read(ST/f'state{stage}.jsonl'):
        assert w['done']
        period=w.get('released_periods',[])
        observed=early.cur_decide(w['field'],period)
        baseline=early.cur_decide(w['field'],[])
        public=w['texts'][-1]
        product={'id':w['id'],'mask_id':w['id'],'field':w['field'],'period_days':observed['period_days'],
                 'source_periods':period,'formed_packets':w['formed'],'public_text':public}
        scrub=lambda obj:re.sub(r'(?i)JOIN-[0-9a-f]+','[internal join removed]',obj)
        cleaned=json.loads(scrub(json.dumps(product)))
        transport.append(dict(id=w['id'],private_token_in_public_text=w['code'].lower() in public.lower(),
                              private_token_in_outbox=w['code'].lower() in json.dumps(product).lower(),
                              any_join_in_delivered=bool(re.search(r'(?i)JOIN-[0-9a-f]+',json.dumps(cleaned)))))
        assert not transport[-1]['any_join_in_delivered']
        receipts.append(dict(id=w['id'],field=w['field'],decision=observed,ordinary=baseline,
                          submitted=period,operation=w['last_op'],visits=sum(x['op']=='request' for x in w['receipts']),
                          formed_count=len(w['formed']),unserved=[s for x in w['receipts'] for s in x.get('unserved',[])]))
        products.append(cleaned)
        stand.append(dict(id=w['id'],field=w['field'],period_days=baseline['period_days'],source_periods=[],formed_packets=[]))
    for name,rs in [('current_choices',receipts),('products_scanned',products),('ordinary_period_only',stand),('transport',transport)]:
        write(HERE/(name+'.jsonl'),rs)
    (HERE/'CHOICES.sha256').write_text(''.join(hashlib.sha256((HERE/(name+'.jsonl')).read_bytes()).hexdigest()+'  '+name+'.jsonl\n' for name in ['current_choices','products_scanned','ordinary_period_only','transport']))

def score():
    for output,inp in [('all_channel','products_scanned'),('sole_ordinary','ordinary_period_only')]:
        subprocess.run([sys.executable,str(DS/'receiver.py'),'--products',str(HERE/(inp+'.jsonl')),'--mapping',str(PR/'receiver_allocation.jsonl'),'--out',str(HERE/output)],check=True)
    curr=read(HERE/'current_choices.jsonl')
    write(HERE/'current_observed.jsonl',[dict(**w,actual=early.current_test(w['field'],w['decision']),ordinary_actual=early.current_test(w['field'],w['ordinary'])) for w in curr])
    for output in ['all_channel','sole_ordinary']:
        subprocess.run([sys.executable,str(DS/'score_locked.py'),str(HERE/output)],check=True)
if __name__=='__main__':
    if sys.argv[1]=='lock':lock(int(sys.argv[2]))
    else:score()
