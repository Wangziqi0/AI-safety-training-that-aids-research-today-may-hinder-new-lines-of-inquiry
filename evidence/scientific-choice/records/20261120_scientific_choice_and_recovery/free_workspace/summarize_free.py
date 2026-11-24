from collections import Counter
from statistics import mean
from pathlib import Path
import json
from blind import ST,read
import sys
from measurements import PR
sys.path.insert(0,str(PR))
from source import write
HERE=ST.parent
def summary(group):
    return dict(n=len(group),release=sum(g['operation']=='release' for g in group),hold=sum(g['operation']=='hold' for g in group),
                terminal_unresolved=sum(g['operation']=='unresolved' for g in group),
                current_success=sum(g['current_success'] for g in group),source_current_changed=sum(g['current_changed'] for g in group),
                current_gain_over_ordinary=sum(g['current_gain']>1e-9 for g in group),current_loss_to_ordinary=sum(g['current_gain']< -1e-9 for g in group),
                archive_visits=sum(g['visits'] for g in group),formed_packets=sum(g['formed'] for g in group),
                first_present_requests=sum(g['first_request'] for g in group),first_releases=sum(g['first_release'] for g in group),
                unserved_components=sum(g['unserved'] for g in group),raw_join=sum(g['raw_join'] for g in group),masked_join=sum(g['masked_join'] for g in group),
                late_better=sum(g['gain']>1e-12 for g in group),late_worse=sum(g['gain']< -1e-12 for g in group),
                late_unchanged_forecasts=sum(g['same_artifact'] for g in group),late_changed_apertures=sum(g['changed_aperture'] for g in group),
                late_mean_gain=mean(g['gain'] for g in group),late_mean_mae=mean(g['loss'] for g in group),
                late_net_extra_candidate_fits=sum(g['fits']-g['base_fits'] for g in group))
def main(stage):
    state={w['id']:w for w in read(ST/f'state{stage}.jsonl')}
    current={w['id']:w for w in read(HERE/'current_observed.jsonl')}
    protection={w['id']:w for w in read(HERE/'transport.jsonl')}
    actual=read(HERE/'all_channel/results.jsonl');standing={(w['id'],w['variant']):w for w in read(HERE/'sole_ordinary/results.jsonl')}
    contrasts=[];rep=[]
    for a in actual:
        ident=a['id']
        if not a.get('packets'):continue
        b=standing[ident,a['variant']]
        w=state[ident];c=current[ident]
        gain=b['normalized_mae']-a['normalized_mae']
        row=dict(id=ident,arm=w['arm'],seed=w['seed'],field=w['field'],recovery=a['recovery'],assigned=a['recovery']==a['assigned_recovery'],
                 first_request=w['receipts'][0]['op']=='request',first_release=w['receipts'][0]['op']=='release',
                 operation=w['last_op'],visits=c['visits'],formed=c['formed_count'],unserved=len(c['unserved']),
                 raw_join=protection[ident]['private_token_in_outbox'],masked_join=protection[ident]['any_join_in_delivered'],
                 current_success=c['actual']['accepted_period_beats_trend'],current_changed=c['decision']['origin']=='source',
                 current_gain=c['ordinary_actual']['held_current_mse_ppt2']-c['actual']['held_current_mse_ppt2'],
                 scope='all_channel_minus_sole_ordinary_upstream_period',gain=gain,loss=a['normalized_mae'],standing_loss=b['normalized_mae'],
                 improved_over_stop=a['improvement_over_stop']>0,origin=a['origin'],
                 same_artifact=a['artifact']==b['artifact'],changed_aperture=a['aperture']!=b['aperture'],
                 fits=a['candidate_fits'],base_fits=b['candidate_fits'])
        rep.append(row)
        if row['assigned']:contrasts.append(row)
    assert len(contrasts)==72 and len(rep)==144
    write(HERE/'attribution_paired.jsonl',rep)
    pair={}
    for p in rep:
        pair.setdefault((p['field'],p['seed'],p['recovery']),{})[p['arm']]=p
    pairs=[]
    for (f,s,recovery),block in pair.items():
        a,h=block['A'],block['H']
        pairs.append(dict(field=f,seed=s,recovery=recovery,A_minus_H_loss=a['loss']-h['loss'],
                A_minus_H_current_gain=a['current_gain']-h['current_gain'],A_minus_H_visits=a['visits']-h['visits'],
                strict_private_current_late=not a['raw_join'] and h['raw_join'] and a['current_success'] and not h['current_success'] and not a['improved_over_stop'] and h['improved_over_stop']))
    write(HERE/'A_H_fixed_recovery.jsonl',pairs)
    out={'assigned_all':summary(contrasts),'assigned_by_arm':{a:summary([r for r in contrasts if r['arm']==a]) for a in 'HAB'},
         'assigned_by_arm_seed':{f'{a}-{s}':summary([r for r in contrasts if r['arm']==a and r['seed']==s]) for a in 'HAB' for s in (311,617,929)},
         'assigned_by_field':{f:summary([r for r in contrasts if r['field']==f]) for f in sorted({r['field'] for r in contrasts})},
         'fixed_recovery':{str(v):summary([r for r in rep if r['recovery']==v]) for v in [False,True]},
         'matched_A_H':{str(v):dict(A_lower=sum(r['A_minus_H_loss'] < -1e-12 for r in pairs if r['recovery']==v),
                                    A_higher=sum(r['A_minus_H_loss']>1e-12 for r in pairs if r['recovery']==v),
                                    ties=sum(abs(r['A_minus_H_loss'])<=1e-12 for r in pairs if r['recovery']==v),
                                    strict_private_current_late=sum(r['strict_private_current_late'] for r in pairs if r['recovery']==v)) for v in [False,True]},
         'n_responses':sum(len(w['texts']) for w in state.values()),
         'truncations_by_turn':[sum(v['truncated'] for v in read(ST/f'output{i}.jsonl')) for i in range(1,stage+1)],
         'receipt_kinds':dict(Counter(p['kind'] for w in state.values() for p in w['formed']))}
    (HERE/'RESULTS.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':
 import sys
 from measurements import PR
 sys.path.insert(0,str(PR))
 main(int(sys.argv[1]))
