#!/usr/bin/env python3
"""Reproduce the finite contrasts, blinded joins and prior numerical checks from saved observations."""
import argparse
import csv
import hashlib
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parent
ROUND='20261121_crossed_writer_attribution';PRIOR='20261121_proof_handoff_submission';OLDEST='20261120_scientific_choice_and_recovery'

def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def load(p):return json.loads(p.read_bytes())
def lines(p):return [json.loads(l) for l in p.read_bytes().splitlines() if l.strip()]
def run(p,*args,cwd=None):
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','MPLBACKEND':'Agg'}
    return subprocess.check_output([sys.executable,'-B',str(p),*map(str,args)],cwd=cwd or p.parent,env=env,text=True)

def same(p,q):
    assert p.read_bytes()==q.read_bytes(), (p.name,q.name)

def safe_extract(z,d):
    for n in z.namelist():
        assert not Path(n).is_absolute() and '..' not in Path(n).parts,n
    assert z.testzip() is None;z.extractall(d)

def raw(input_file,output_file):
    req,results=lines(input_file),lines(output_file)
    assert len(req)==len(results)>0 and len({r['id'] for r in results})==len(results)
    for given,seen in zip(req,results,strict=True):
        assert all(seen[k]==v for k,v in given.items()),seen['id']
        assert len(seen['token_ids'])==seen['generated_tokens']<=seen['effective_token_cap']
        assert seen['effective_token_cap']==given['max_new_tokens'] and seen['batch_size']>0
        assert seen['eos']!=seen['truncated'] and len(seen['checkpoint_sha256'])==64
        assert seen['base_revision']=='b968826d9c46dd6066d109eabc6255188de91218'
    return len(results)

def previous(layout,full):
    previous_zip=ROOT/'previous/Data_and_code.zip'; reg=load(ROOT/'review_copy.json')
    assert digest(previous_zip)==reg.get('previous_public_archive_sha256',reg['previous_handoff_archive_sha256'])
    old=layout/'previous';outer=ZipFile(previous_zip)
    with outer: safe_extract(outer,old)
    older=layout/'older';z=ZipFile(old/'previous/Data_and_code.zip')
    with z:safe_extract(z,older)
    tree=layout/'rounds';tree.mkdir()
    (tree/PRIOR).symlink_to(old/'study',target_is_directory=True)
    for p in (older/'records').iterdir(): (tree/p.name).symlink_to(p,target_is_directory=True)
    for p in (ROOT/'registered_inputs').rglob('*'):
        if p.is_file():
            rel=p.relative_to(ROOT/'registered_inputs'); dst=layout/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
    result=json.loads(run(old/'verify_evidence.py',*(['--prior'] if full else [])))
    assert result['verified'];return result

def check_slots(study,partial):
    packets={r['slot']:r['prompt'] for r in lines(study/'downstream/HISTORICAL_PUBLIC_PACKETS.jsonl')}
    packets.update({r['recipient_id']:r['prompt'] for r in lines(study/'transfer/blind/recipient_packets.jsonl')})
    assert len(packets)==18
    group=study/'downstream'; count=0;actions=0
    blind={r['slot']:r['text'] for r in lines(group/'answers_blind.jsonl')} if (group/'answers_blind.jsonl').exists() else {}
    for slot,txt in packets.items():
        folder=group/'slots'/slot; file=folder/'docket.txt'; assert file.is_file()
        assert file.read_text().rstrip('\n')==txt.rstrip('\n'),slot
        if not (folder/'answer.md').is_file():
            if partial:continue
            raise ValueError('Missing hosted output: '+slot)
        receipt=load(folder/'receipt.json');assert receipt['slot']==slot and receipt['complete']
        assert receipt['packet_sha256']==digest(file) and receipt['effort']=='high'
        assert (folder/'answer.md').read_bytes()==(blind[slot]+'\n').encode()
        assert receipt['words']==len(blind[slot].split()) and 'thread_id' not in receipt
        assert receipt['model']=='gpt-6.2-astra' and len(receipt['tool_calls'])>=1 and receipt['duration_ms']>0
        for call in receipt['tool_calls']:
            assert call['name']=='exec'
            accessed=re.findall(r'study/downstream/slots/[A-Za-z0-9]+/docket.txt',call['input'])
            assert accessed and set(accessed)=={f'study/downstream/slots/{slot}/docket.txt'}
        actions+=len(receipt['tool_calls']);count+=1
    if not partial:assert count==18
    auditfile=group/'TOOL_AUDIT.json'
    if auditfile.is_file():
        checked=load(auditfile);assert {x['slot'] for x in checked}==set(packets)
        for x in checked:
            rec=load(group/'slots'/x['slot']/'receipt.json')
            assert x['only_assigned_public_packet'] and x['public_prompt_sha256']==rec['packet_sha256']
            assert x['recorded_reads']==len(rec['tool_calls'])
            assert len(x['arithmetic_response'])==x['additional_local_arithmetic']
        arithmetic=sum(x['additional_local_arithmetic'] for x in checked)
    else:arithmetic=None
    return {'completed':count,'tool_actions':actions,'logged_additional_arithmetic_actions':arithmetic}

def edition_control(study, counts, edits):
    control=load(study/'control/EDITION_RESULTS.json')
    assert (study/'RESULTS.md').stat().st_size>0 and control['round']==ROUND
    mapping={'historical_both_writers_and_controls':'historical_650_both_writers','B_service_and_writer':'secondary_B_first_and_final',
             'historical_larger_budget_with_companions':'historical_long_allowance_including_batch_companions','investigators_including_device_controls':'investigation_stage_including_controls',
             'origin_final_including_device_controls':'origin_final_stage_including_controls','new_writers':'heldout_three_recipe_writers','all_new_larger_budget':'heldout_long_allowance'}
    assert control['open_model_completions_including_controls']=={k:counts[v] for k,v in mapping.items()}
    assert control['open_model_total']==sum(counts.values())
    hist=load(study/'cross/primary_results.json'); strict=load(study/'cross/standalone_results.json')['all']
    assert all(hist[k]==v for k,v in control['archival_actionable'].items())
    assert control['archival_exact']=={a:strict[a] for a in ('A','H')}
    with (study/'transfer/arm_summary.tsv').open() as f: arms=[r for r in csv.DictReader(f,delimiter='\t') if r['group']=='all']
    assert control['heldout_short_actionable_primary']=={r['arm']:int(r['actionable']) for r in arms}
    assert control['heldout_short_exact']=={r['arm']:int(r['full_exact']) for r in arms}
    second=load(study/'analysis/rating_sensitivity.json')['heldout']['arm_counts']
    assert control['heldout_short_actionable_secondary']=={a:r['independent'] for a,r in second.items()}
    for grade,where in [('primary','analysis'),('secondary','analysis/long_second')]:
        group=load(study/where/'heldout_budget.json')['groups']
        assert control['heldout_long_actionable_'+grade]=={r['arm']:r['long_pass'] for r in group if r['subset']=='all'}
    small=load(study/'analysis/small_model_summary.json');assert all(small[k]==v for k,v in control['small_model'].items())
    with (study/'downstream/groups.tsv').open() as f: recipients={r['arm']:r for r in csv.DictReader(f,delimiter='\t') if r['group']=='all'}
    for r in control['downstream']:
        g=recipients[r['arm']]
        assert [int(g[k]) for k in ('full','n','named_substantive_use','arithmetic')]==[r[k] for k in ('full','assigned','named_note_use','additional_tool_calculation')]
    for name,original in control['grading_and_input_identities'].items():
        act=digest(study/name); e=edits.get('rounds/'+ROUND+'/'+name)
        assert original==act or e and e['review_sha256']==act and e['registered_sha256']==original,name
    frozen_file=study/'control/EDITORIAL_FREEZE.json';frozen=load(frozen_file)
    assert digest(frozen_file)=='442198cb95303184f380a877be035caba1ce646bbc873926ccad3f921bb54953'
    for name in ('RESULTS.md','control/EDITION_RESULTS.json','review/FINAL_MANUSCRIPT_REVIEW.md'):
        wanted=frozen['files']['rounds/'+ROUND+'/'+name];assert digest(study/name)==wanted,name
    return {'signed_editorial_freeze_sha256':digest(frozen_file),'control_sha256':digest(study/'control/EDITION_RESULTS.json'),'scientific_results_sha256':digest(study/'RESULTS.md'),
            'named_grading_and_input_identities':len(control['grading_and_input_identities']),'evidence_status':control['evidence_status'],
            'general_or_human_scientific_originality_loss':control['general_or_human_scientific_originality_loss'],
            'uncompensated_loss_on_six_selected_decisions':control['uncompensated_loss_on_six_selected_decisions']}


def current(layout,partial):
    identity_lines=(ROOT/'scientific_sources.sha256').read_text().splitlines()
    for entry in identity_lines:
        expected,name=entry.split(maxsplit=1);assert digest(ROOT/name)==expected,name
    current=layout/'rounds'/ROUND;shutil.copytree(ROOT/'study',current)
    c=current/'cross'; t=current/'transfer'; analysis=current/'analysis'
    def registered(script,*args):return run(ROOT/'run_registered_analysis.py',layout,ROOT/'review_copy.json',script,*args)
    for script in [c/'audit.py',c/'length_audit.py',c/'primary_results.py',c/'standalone.py',c/'origin/verify.py']:
        registered(script)
    counts={}
    counts['historical_650_both_writers']=sum(raw(c/'inputs'/f'b{i:02}.jsonl',c/'raw'/f'b{i:02}.jsonl') for i in range(1,7))
    counts['secondary_B_first_and_final']=raw(c/'secondary/inputs.jsonl',c/'secondary/raw.jsonl')
    counts['historical_long_allowance_including_batch_companions']=raw(c/'expanded/inputs.jsonl',c/'expanded/raw.jsonl')
    counts['investigation_stage_including_controls']=raw(c/'origin/investigator_inputs.jsonl',c/'origin/raw/investigator.jsonl')
    counts['origin_final_stage_including_controls']=raw(c/'origin/writer_inputs.jsonl',c/'origin/raw/writer.jsonl')
    counts['heldout_three_recipe_writers']=raw(t/'internal/writer_input.jsonl',t/'internal/writer_raw.jsonl')
    b=current/'budget_transfer'
    if (b/'raw.jsonl').is_file():counts['heldout_long_allowance']=raw(b/'inputs.jsonl',b/'raw.jsonl')
    elif not partial:raise ValueError('Missing held-out longer-allowance archive')
    if (c/'comparison_results.json').exists():registered(c/'replay_comparisons.py','--round',current)
    assert json.loads(run(t/'exact.py'))==load(t/'ordinary/reference.json')
    grades=current/'review/HELDOUT_NOTES.tsv';run(t/'analyze.py',grades,digest(grades))
    for n in ('writer_scores.tsv','arm_summary.tsv','paired_comparisons.tsv'):same(t/n,analysis/'transfer_initial'/n)
    if (t/'REPLAY.json').is_file():
        assert json.loads(registered(t/'replay.py'))==load(t/'REPLAY.json')
    out=layout/'calculations';out.mkdir()
    run(analysis/'crossed_decisions.py',c,out)
    for n in ('factorial_summary.json','original_decision_factorial.csv','warranted_action_factorial.csv'):same(out/n,analysis/n)
    run(analysis/'small_model_cross.py',layout/'rounds'/OLDEST/'mechanism/POLICY_VALUES.json',out)
    for n in ('small_model_cross.csv','small_model_summary.json'):same(out/n,analysis/n)
    small=load(analysis/'small_model_summary.json');assert small['new_model_fits_or_generations']==0
    released=load(ROOT/'review_copy.json')['registered_files_with_public_administrative_edits']
    for line in (t/'FROZEN.sha256').read_text().splitlines():
        val,relative=line.split(maxsplit=1);file=(t/relative).resolve();act=digest(file);rec=released.get(file.relative_to(layout).as_posix())
        assert act==val or (rec and rec['registered_sha256']==val and rec['review_sha256']==act),relative
    open_records=lines(t/'internal/writer_raw.jsonl');tasks={r['task'] for r in open_records}
    assert len(tasks)==8
    for task in tasks:
        subset=[r for r in open_records if r['task']==task]
        assert {(r['arm'],r['seed']) for r in subset}=={(a,k) for a in ('A','H','B') for k in (311,617,929)}
        assert len({json.dumps(r['messages'],sort_keys=True) for r in subset})==1
    source=load(t/'ordinary/source_replay.json');assert source['rows']==103 and source['derived_csv_sha256']==digest(t/'public/team_endpoints.csv')
    same(t/'public/team_endpoints.csv',layout/'previous/study/literature/team_endpoints.csv')
    if (analysis/'length_transfer.py').exists():
        run(analysis/'length_transfer.py',current,out)
        for n in ('heldout_budget.json','heldout_budget.tsv'):same(out/n,analysis/n)
        second_long=out/'second-long'; second_long.mkdir()
        run(analysis/'length_transfer.py',current,second_long,'--assessor','review2')
        for n in ('heldout_budget.json','heldout_budget.tsv'):same(second_long/n,analysis/'long_second'/n)
        short={r['id']:r for r in open_records}; long={r['id']:r for r in lines(b/'raw.jsonl')}
        cut=lines(b/'length_receipts.jsonl');assert len(cut)==48
        for row in cut:
            x,y=short[row['short_id']],long[row['writer_id']]
            assert x['messages']==y['messages'] and x['checkpoint_sha256']==y['checkpoint_sha256']
            assert x['token_ids']==y['token_ids'][:len(x['token_ids'])]
            assert row['unchanged_tokens']==(x['token_ids']==y['token_ids']) and row['short_is_prefix']
    if (current/'downstream/join.py').exists():
        run(current/'downstream/join.py',current,out)
        for n in ('groups.tsv','recipients.tsv'):same(out/n,current/'downstream'/n)
    if (analysis/'rating_sensitivity.py').exists():
        run(analysis/'rating_sensitivity.py',current,out)
        for n in ('two_readings.tsv','rating_sensitivity.json'):same(out/n,analysis/n)
    figure_count=0
    if (ROOT/'figures/fig1_source.csv').is_file():
        with ZipFile(ROOT/'previous/Data_and_code.zip') as prev:
            for fig in (1,2,3,5):
                f=f'figures/fig{fig}_source.csv';assert (ROOT/f).read_bytes()==prev.read(f);figure_count+=1
                pdf=f'figures/fig{fig}.pdf';assert (ROOT/pdf).read_bytes()==prev.read(pdf)
            assert (ROOT/'figures/prior_handoff_source.csv').read_bytes()==prev.read('figures/fig4_source.csv');figure_count+=1
            assert (ROOT/'figures/prior_handoff.pdf').read_bytes()==prev.read('figures/fig4.pdf')
            assert (ROOT/'figures/fig4.pdf').read_bytes()!=prev.read('figures/fig4.pdf')
    new_figures=0
    if (ROOT/'figures/fig4_attribution.py').is_file():
        new_out=layout/'figure-data';new_out.mkdir()
        generator=runpy.run_path(str(ROOT/'figures/fig4_attribution.py'))
        generator['build_sources'](current,new_out)
        same(new_out/'fig4_source.csv',ROOT/'figures/fig4_source.csv');new_figures=1
    with (current/'downstream/groups.tsv').open() as f:
        downstream={r['arm']:{'n':int(r['n']),'full':int(r['full'])} for r in csv.DictReader(f,delimiter='\t') if r['group']=='all'}
    checked_control=edition_control(current,counts,released) if (current/'control/EDITION_RESULTS.json').is_file() else None
    if not partial:assert checked_control is not None
    return {'verified_edition_control':checked_control,'new_figure_tables_regenerated_from_scores':new_figures, 'second_reader_long_budget':[r for r in load(analysis/'long_second/heldout_budget.json')['groups'] if r['subset']=='all'],'long_budget_heldout':[r for r in load(analysis/'heldout_budget.json')['groups'] if r['subset']=='all'],
            'heldout_two_readers':load(analysis/'rating_sensitivity.json')['heldout']['arm_counts'],
            'full_decisions_by_downstream_arm':downstream,'primary_scientific_files_verified_against_source_bytes':len(identity_lines),'unchanged_main_and_supplementary_figure_tables_verified':figure_count, 'saved_8B_generations_by_workflow':counts,'total_saved_8B_generations':sum(counts.values()),'hosted_reader_replay':check_slots(current,partial),
            'fixed_primary_histories':load(c/'primary_results.json')['all']['n'],'primary_stage_results':load(c/'primary_results.json')['all'],
            'qualified_primary_histories':load(c/'primary_results.json')['prequalified'],'complete_historical_decisions':load(c/'standalone_results.json')['all'],
            'small_model_decompositions':small['decompositions'],'new_small_model_fits_or_generations':0}

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--prior',action='store_true');a.add_argument('--partial',action='store_true',help=argparse.SUPPRESS);args=a.parse_args()
    if not __debug__:raise ValueError('Verification requires assertions to be enabled.')
    with tempfile.TemporaryDirectory(prefix='attribution-replay-') as name:
        site=Path(name);older=previous(site,args.prior); result=current(site,args.partial)
    print(json.dumps({'verified':True,'current':result,'previous':older,'new_model_calls':0},indent=2))
if __name__=='__main__':main()
