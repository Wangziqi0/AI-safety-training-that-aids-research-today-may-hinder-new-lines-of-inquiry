"""Cross the same real project, source-training assignment and actually executed downstream choices."""
from pathlib import Path
import csv,json,math,statistics,sys
from collections import Counter,defaultdict
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;PR=BASE/'practice';DOWN=BASE/'downstream'
sys.path.insert(0,str(PR))
from early import current_test,data
def read(p):return [json.loads(s) for s in p.read_text().splitlines() if s]
def index(p):return {i['id']:i for i in read(p)}
def mean(x):return statistics.mean(x) if x else None
def period(x):
    if isinstance(x,dict):x=x.get("period_days")
    return x if isinstance(x,(int,float)) and x>0 else None
def equiv(p,q,span):
    return p is not None and q is not None and any(abs(1/(p*factor)-1/q)<=1/span for factor in (.5,1.,2.))
def analyze(lane):
    normal=lane=='primary';lock=DOWN/('assigned_lock' if normal else 'stewardship_lock')
    key=index(PR/'arm_key.jsonl')
    tr=index(PR/(("" if normal else 'stewardship_')+'TRANSPORT.jsonl'))
    packet=index(PR/(("" if normal else 'stewardship_')+'receiver_input_scanned.jsonl'))
    cur=index(PR/'current_observed.jsonl');st=index(PR/'stewardship_current_choices.jsonl')
    assigned=index(DOWN/'ASSIGNED_RECOVERY.jsonl')
    rr={(r['id'],r['variant']):r for r in read(lock/'results.jsonl')}
    output=[];pairs=[]
    for ident,z in key.items():
        f=z['field'];c=cur[ident];n=rr[ident,'handoff'];r=rr[ident,'handoff_recovery'];o=rr['ordinary_'+f,'ordinary']
        obs=c['observed'] if normal else current_test(f,st[ident]['new_decision'])
        decision=c['decision'] if normal else st[ident]['new_decision']
        d=data(f);span=float(d['t'].max()-d['t'].min())
        source=packet[ident];meta=json.loads((lock/(f+'_access.json')).read_text());q=meta['independent_recovery']['period_days']
        standing=any(equiv(p,q,span) for _,p in meta['standing_periods'])
        available=any(equiv(period(p),q,span) for p in [source['period_days'],*source['source_periods'],*source['formed_packets']])
        fmatch=any(equiv(period(p),q,span) for p in source['formed_packets'])
        rowsource=cur[ident]['is_source_contribution'] if normal else decision['origin']=='source'
        typed=lambda y: bool(isinstance(y['component'],(int,float)) and y['improvement_over_stop']>0)
        S=not tr[ident]['any_to_internal_outbox']
        Z=assigned[ident]['assigned_recovery']
        output.append(dict(id=ident,**{k:z[k] for k in ('field','arm','seed')},S=S,protected_secondary=not tr[ident]['any_to_blind_numeric_recipient'],
          C=bool(obs['accepted_period_beats_trend']),C_incremental=bool(rowsource and obs['held_current_mse_ppt2']<c['ordinary_observed']['held_current_mse_ppt2']),
          current_ordinary_gain=c['ordinary_observed']['held_current_mse_ppt2']-obs['held_current_mse_ppt2'],
          current_mse=obs['held_current_mse_ppt2'],source_executed_reads=c['formed_count'],carried_packets=len(source['formed_packets']),
          delivered_selected=(True if normal else (st[ident]['delivered_selected_period'] or st[ident]['trend_delivered'])),
          F_packet=fmatch,F_source_or_current=available,F_standing=standing,B_not_available_first=not (available or standing),
          primary_recovery_period=q,directly_expressible_early=.1<=q<=9,
          Y0=typed(n),Y1=typed(r),Y0_numeric=n['normalized_mae'],Y1_numeric=r['normalized_mae'],
          recovery_used=r['origin']=='independent_recovery',recovery_changed_action=n['artifact']!=r['artifact'],assigned_R=Z,
          observed_Y=(typed(r) if Z else typed(n)),observed_normalized_mae=(r if Z else n)['normalized_mae'],
          late_gain_vs_initial_without_source=o['normalized_mae']-n['normalized_mae'],late_gain_adding_recovery=n['normalized_mae']-r['normalized_mae'],
          late_fit_cost=n['candidate_fits'],late_fit_cost_recovery=r['candidate_fits'],late_disposition=n['disposition']))
    for group in ('A','B'):
        for a in [r for r in output if r['arm']==group]:
            h=next(r for r in output if r['field']==a['field'] and r['seed']==a['seed'] and r['arm']=='H')
            strict=a['S'] and not h['S'] and a['C'] and not h['C'] and h['Y0'] and not a['Y0']
            eligible=a['B_not_available_first'] and a['S'] and a['C']
            recomp=a['Y1'] and not a['Y0'] and a['recovery_used']
            strict_full=bool(strict and a['B_not_available_first'] and h['F_source_or_current'] and recomp)
            continuous_improve_now=a['current_mse']<h['current_mse']
            continuous_later_loss=a['Y0_numeric']>h['Y0_numeric']
            pairs.append(dict(field=a['field'],seed=a['seed'],contrast=group+'-H',S_diff=int(a['S'])-int(h['S']),C_diff=int(a['C'])-int(h['C']),
                paired_current_mse_diff=a['current_mse']-h['current_mse'],paired_late_error_diff=a['Y0_numeric']-h['Y0_numeric'],
                Y0_diff=int(a['Y0'])-int(h['Y0']),A_eligible=eligible,recovered_and_used=recomp,strict_prefix=bool(strict),
                full_linked_event=strict_full,strict_continuous_signs=bool(a['S'] and not h['S'] and continuous_improve_now and continuous_later_loss)))
    arm={}
    for name in 'HAB':
        r=[x for x in output if x['arm']==name]
        arm[name]={k:sum(bool(x[k]) for x in r) for k in ('S','protected_secondary','C','C_incremental','delivered_selected','Y0','Y1','F_packet','F_source_or_current','F_standing','B_not_available_first','recovery_used','recovery_changed_action')}
        for k in ('source_executed_reads','carried_packets','late_fit_cost','late_fit_cost_recovery'):arm[name][k]=sum(x[k] for x in r)
        for k in ('Y0_numeric','Y1_numeric','current_ordinary_gain','late_gain_vs_initial_without_source','late_gain_adding_recovery'):arm[name][k]=mean([x[k] for x in r])
    summary={'n_sources':len(output),'arms':arm,'pair':{},'randomized_recovery':{}}
    for group in ('A','B'):
        d=[r for r in pairs if r['contrast']==group+'-H']
        summary['pair'][group+'-H']={k:sum(r[k] for r in d) for k in ['strict_prefix','full_linked_event','strict_continuous_signs','S_diff','C_diff','Y0_diff']}
    # Unbiased under the declared estimate target when each opaque slot has marginal offer probability 1/2.
    # Exact branch-specific replay provides the finite target directly; record naive assigned comparison separately.
    for name in ('H','A','B','ALL'):
        jobs=[r for r in output if name=='ALL' or r['arm']==name]
        on=[r for r in jobs if r['assigned_R']];off=[r for r in jobs if not r['assigned_R']]
        summary['randomized_recovery'][name]={'on':len(on),'off':len(off),'observed_unadjusted_error_difference':mean([r['observed_normalized_mae'] for r in on])-mean([r['observed_normalized_mae'] for r in off]),'finite_paired_incremental_gain':mean([r['late_gain_adding_recovery'] for r in jobs])}
    for fn,records in [(lane+'_case.csv',output),(lane+'_pairs.csv',pairs)]:
        with (HERE/fn).open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    return summary
if __name__=='__main__':
    s={k:analyze(k) for k in ['primary','stewardship']};(HERE/'FINITE_LINK.json').write_text(json.dumps(s,indent=2)+'\n')
    for k in s: print(k,s[k]['pair']['A-H'],[(z,s[k]['arms'][z]['S'],s[k]['arms'][z]['C'],s[k]['arms'][z]['Y0'],s[k]['arms'][z]['B_not_available_first']) for z in 'HAB'])
