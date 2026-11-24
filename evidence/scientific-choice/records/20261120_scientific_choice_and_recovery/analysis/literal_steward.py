"""Diagnostic prompted by review: the literal steward entry, before the intermediary computes its default."""
from pathlib import Path
import json
B=Path(__file__).resolve().parents[1];D=B/'analysis/literal_only';D.mkdir(exist_ok=True)
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l]
def prep():
    packet={r['id']:r for r in rows(B/'practice/stewardship_receiver_input_scanned.jsonl')}
    out=[]
    for c in rows(B/'practice/stewardship_current_choices.jsonl'):
        r=dict(packet[c['id']])
        if c['delivered_selected_period']:r['period_days']=c['selected_period']
        elif c['delivered_periods']:r['period_days']=c['delivered_periods'][0]
        else:r['period_days']=None
        out.append(r)
    with (D/'literal_sent.jsonl').open('x') as f:
        for r in out:f.write(json.dumps(r,ensure_ascii=False)+'\n')
def analyze():
    def group(path):return {(r['id'],r['variant']):r for r in rows(path)}
    lit=group(D/'lock/results.jsonl');reg=group(B/'downstream/stewardship_lock/results.jsonl')
    key={r['id']:r for r in rows(B/'practice/arm_key.jsonl')};ass={r['id']:r for r in rows(B/'downstream/ASSIGNED_RECOVERY.jsonl')}
    table=[]
    for i,k in key.items():
        v='handoff_recovery' if ass[i]['assigned_recovery'] else 'handoff'
        x=lit[i,v];y=reg[i,v];table.append(dict(id=i,field=k['field'],seed=k['seed'],arm=k['arm'],equal_physical_forecast=x['artifact']==y['artifact'],change_in_error=x['normalized_mae']-y['normalized_mae'],literal_origin=x['origin'],regenerated_origin=y['origin']))
    (D/'RESULT.json').write_text(json.dumps({'n':len(table),'equal':sum(r['equal_physical_forecast'] for r in table),'by_arm':{a:sum(not r['equal_physical_forecast'] for r in table if r['arm']==a) for a in 'HAB'},'cases':table},indent=2)+'\n')
if __name__=='__main__':
    import sys
    (prep if sys.argv[1]=='prepare' else analyze)()
