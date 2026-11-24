"""Descriptive repeated-field sensitivity on decisions; the interface bundle changed in several ways."""
import json
from pathlib import Path
from collections import Counter
from blind import read,ST
HERE=ST.parent
def get(path):return {r['id']:r for r in read(path)}
def main(stage):
    p=HERE.parent/'practice'
    primary=get(p/'current_observed.jsonl');new=get(HERE/'current_observed.jsonl')
    old_state=get(p/'stages/state3.jsonl');free_state=get(ST/f'state{stage}.jsonl')
    assert primary.keys()==new.keys()==old_state.keys()==free_state.keys()
    mtag='all_formed_packets'
    oldlate={r['id']:r for r in read(HERE.parent/'downstream/assigned_lock/results.jsonl') if r.get('packets') and r['recovery']==r['assigned_recovery']}
    newlate={r['id']:r for r in read(HERE/'all_channel/results.jsonl') if r.get('packets') and r['recovery']==r['assigned_recovery']}
    comp=[]
    for i,r in primary.items():
        a,b=oldlate[i],newlate[i]
        comp.append(dict(id=i,field=r['field'],arm=free_state[i]['arm'],seed=free_state[i]['seed'],
                         primary_period=r['decision']['period_days'],free_period=new[i]['decision']['period_days'],
                         primary_packet_count=len(old_state[i]['formed']),free_packet_count=len(free_state[i]['formed']),
                         primary_released_periods=r['source_periods'],free_released_periods=new[i]['submitted'],
                         primary_success=r['observed']['accepted_period_beats_trend'],free_success=new[i]['actual']['accepted_period_beats_trend'],
                         changed_current_decision=r['decision']['period_days']!=new[i]['decision']['period_days'],
                         primary_late_normalized_mae=a['normalized_mae'],free_late_normalized_mae=b['normalized_mae'],
                         forecast_changed=a['artifact']!=b['artifact'],assigned_recovery=a['recovery']))
    with (HERE/'comparison_with_primary.jsonl').open('x') as f:
        for w in comp:print(json.dumps(w),file=f)
    print('Active candidates and late predictions changed under bundled interface:',sum(r['changed_current_decision'] for r in comp),sum(r['forecast_changed'] for r in comp))
if __name__=='__main__':
 import sys
 main(int(sys.argv[1]))
