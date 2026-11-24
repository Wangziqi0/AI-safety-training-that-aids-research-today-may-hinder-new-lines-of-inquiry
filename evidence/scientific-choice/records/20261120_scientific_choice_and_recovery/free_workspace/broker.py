import json,re,sys
from pathlib import Path
from blind import ST,read,blindkey
from measurements import normalized,measure,part
from prepare import initial
from source import write
from custom import run as run_custom

def work(w,items,row):
    data=normalized(w['field']);defaults=[v['period_days'] for v in initial(w['field'])['rough_periodogram_maxima']]
    result=[];failed=[]
    for item in items:
        name,_,spec=item.partition('@')
        if name=='code':
            blocks=re.findall(r'```(?:python|py)?\s*\n(.+?)(?:```|$)',row,re.I|re.S)
            for src in blocks:
                if 'def investigate(' not in src:continue
                sel=part(data['t'])==0
                try: out=run_custom(src,data['t'][sel],data['pdc'][sel])
                except Exception as ex:out={'error':str(ex)}
                if 'error' in out:failed.append(out['error'])
                else:
                    for p in out.get('periods') or [None]:
                        result.append(dict(kind='custom',period_days=p,values=out,scientific_note='Returned by author program on discovery arrays.',code=src))
            continue
        if spec=='all':periods=defaults
        elif spec:periods=[float(v) for v in spec.split(',')]
        else:periods=defaults[:1]
        for p in periods:
            try:
                obs=dict(measure(w['field'],name,p))
                obs['tested_period_days']=p
                if name=='spectrum':obs['period_days']=obs['values']['PDC_peaks'][0]['period_days']
                if name=='residual':obs['period_days']=obs['values']['residual_peaks'][0]['period_days']
                result.append(obs)
            except Exception as e:
                failed.append(f'{name} at {p} d failed: {e}')
    return result,failed

def compact_feedback(packets):
    # Store detailed tables upstream. Each measured subrequest gets an identified result in the conversation.
    def shrink(v,depth):
        if isinstance(v,dict):
            return {k:shrink(a,depth+1) for k,a in list(v.items())[:5]}
        if isinstance(v,list):
            return [shrink(a,depth+1) for a in v[:3]]
        return v
    if len(json.dumps(packets)) < 4800:
        return packets
    return [dict(method=p['kind'],period_days=p['period_days'],values=shrink(p['values'],0)) for p in packets]

def step(stage):
    prior=read(ST/f'state{stage-1}.jsonl');outs={r['id']:r for r in read(ST/f'output{stage}.jsonl')}
    annotations=json.loads((ST/f'interpretation{stage}.json').read_text())
    assert set(annotations)=={blindkey(stage,i) for i in outs}
    next_rows=[]
    for w in prior:
        if w.get('done'):continue
        r=outs[w['id']];txt=r['text'];a=annotations[blindkey(stage,w['id'])]
        w['texts'].append(txt)
        w['messages'].append(dict(role='assistant',content=txt))
        a['truncated']=r['truncated']
        w.setdefault('receipts',[]).append(a);op=a['op'];w['last_op']=op
        if op in ('release','hold','unresolved') or stage==3:
            w['released_periods']=a.get('periods',[]) if op=='release' else []
            w['done']=True
            continue
        feedback=[]
        if op=='request':
            obs,failed=work(w,a['items'],txt)
            w['formed']+=obs
            a['unserved']+=failed
            a['observed_packet_count']=len(obs)
            for o in obs:
                feedback.append({k:v for k,v in o.items() if k!='code'})
        msg=''
        if feedback:msg='The archive measured the following using the first-sector discovery samples. '+json.dumps(compact_feedback(feedback),ensure_ascii=False,separators=(',',':'))+'. '
        if a.get('unserved'):msg+='Outstanding or unavailable components: '+'; '.join(a['unserved'])+'. '
        if not msg:msg='The archive could not identify a specific present request or an unconditional scientific release. '
        if stage==1:msg+='You can use one further archive interaction if needed, or release a period or unresolved decision now. Write in your own words.'
        else:msg+='This source shift is ending. Give the actual scientific decision that you wish to release to the follow-up colleague, including any period that you judge reportable. You can leave the case unresolved.'
        w['messages'].append(dict(role='user',content=msg))
        next_rows.append(dict(id=w['id'],arm=w['arm'],seed=w['seed'],messages=w['messages'],max_new_tokens=640))
    write(ST/f'state{stage}.jsonl',prior)
    write(ST/f'input{stage+1}.jsonl',next_rows)
if __name__=='__main__':step(int(sys.argv[1]))
