#!/usr/bin/env python3
"""Verify archived scientific decisions without accounts, model calls or original paths."""
import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
LEGACY_SHA = '3ec0d03fbcdae68bafdd85cd3028d0d3d61ee50f9e9149ea9e99bd734a296de8'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(p):
    return json.loads(p.read_bytes())


def rows(p):
    return [json.loads(line) for line in p.read_bytes().splitlines() if line.strip()]


def table(p):
    with p.open() as f:
        return list(csv.DictReader(f, delimiter='\t'))


def run(p, *args):
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'MPLBACKEND': 'Agg', 'OPENBLAS_NUM_THREADS': '1'}
    cmd=[sys.executable, str(p), *map(str, args)]
    proc = subprocess.run(cmd, cwd=p.parent, env=env, stdout=subprocess.PIPE, text=True, check=True)
    return proc.stdout


def match_inputs(exp):
    for stage in ('service','scientific','handoff'):
        inp = rows(exp/f'internal/{stage}_input.jsonl'); out = rows(exp/f'internal/{stage}_raw.jsonl')
        assert len(inp)==len(out)==24
        assert len({r['id'] for r in inp})==24
        for q,r in zip(inp,out,strict=True):
            assert all(q[k]==r[k] for k in q)
            assert len(r['token_ids'])==r['generated_tokens']
            assert r['generated_tokens']<=r['effective_token_cap']
            assert r['batch_size']==4
    packets={r['slot']:r['prompt'] for r in rows(exp/'receiver_packets.jsonl')}
    answers={r['slot']:r['text'] for r in rows(exp/'blind/frontier_responses.jsonl')}
    return packets,answers


def verify_slots(study, group, submissions, expected):
    slots = sorted((study/group/'slots').glob('*'))
    assert len(slots)==len(submissions)==len(expected)
    for p in slots:
        report=load(p/'receipt.json'); prompt=(p/'docket.txt').read_bytes(); ans=(p/'answer.md').read_bytes()
        assert report['slot']==p.name and report['complete'] and report['effort']=='high' and report['model']=='gpt-6.2-astra'
        assert expected[p.name]==report['packet_sha256']==digest(prompt)
        assert ans==submissions[p.name].encode('utf-8')+b'\n'
        assert report['words']==len(submissions[p.name].split()) and report['words']<=450
        assert 'thread_id' not in report and len(report['tool_calls'])==1
        call=report['tool_calls'][0]; assert call['name']=='exec' and f'cat study/{group}/slots/{p.name}/docket.txt' in call['input']
        assert report['duration_ms']>=0 and report['usage']['output_tokens']>0
    return len(slots)


def verify_new(study, scratch):
    exp=study/'experiment'; pkt,answers=match_inputs(exp)
    reg=load(study/'frontier/ACQUISITION.json')
    assert sorted(reg['slots'])==sorted(pkt)==sorted(answers)
    assert digest((exp/'receiver_packets.jsonl').read_bytes())==reg['packet_sha256']
    for slot,prompt in pkt.items():
        assert (study / 'frontier/slots' / slot / 'docket.txt').read_bytes()==(prompt+'\n').encode('utf-8')
    primary=verify_slots(study,'frontier',answers,{s:digest((prompt+'\n').encode()) for s,prompt in pkt.items()})
    staged=scratch/'study'; shutil.copytree(study,staged)
    staged_exp=staged/'experiment'; run(staged_exp/'replay.py'); run(staged_exp/'receipt_summary.py')
    for name in ('donor_results.tsv','donor_counts.json','receiver_results.tsv','paired_differences.tsv','linked_cases.tsv',
                 'paper_outcomes.tsv','receiver_costs.tsv','receiver_cost_summary.json','receipt_summary.json'):
        assert (staged_exp/name).read_bytes()==(exp/name).read_bytes(),name
    # Frozen human-readable grades are inputs. Arithmetic and all treatment joins are replayed separately.
    rn=load(study/'reasons/FREEZE.json'); assigns={r['slot']:r for r in rn['assignments']}
    sr={r['slot']:r['text'] for r in rows(study/'reasons/answers_blind.jsonl')}
    count=verify_slots(study,'reasons',sr,{s:r['packet_sha256'] for s,r in assigns.items()})
    assert len({(r['case'],r['arm']) for r in assigns.values()})==6
    grades,=list((study/'review').glob('SECONDARY_BLIND_GRADES_*.json'))
    blind=load(grades); assert blind['source_sha256']==digest((study/'reasons/answers_blind.jsonl').read_bytes())
    assert set(assigns)==set(sr)=={x['slot'] for x in blind['outcomes']}
    successes=Counter(assigns[x['slot']]['arm'] for x in blind['outcomes'] if x['complete_decision'])
    assert dict(successes)=={'status':3,'warrant':3}
    if (staged/'reasons/analyse.py').exists():
        # The authored analysis joins the blinded referee grades to the frozen message key.
        run(staged/'reasons/analyse.py')
    comm=study/'communication'; out=scratch/'intervals'; run(comm/'check_messages.py',out)
    for s in ('interval_families.csv','result.json'):
        assert (out/s).read_bytes()==(comm/'raw'/s).read_bytes(),s
    cr=load(out/'result.json'); assert cr['mismatches']==0 and cr['one_message_best']=={'witness':10,'multiplier':'5/4'}
    exact=json.loads(run(study/'math/exact_checks.py')); assert exact==load(study/'math/exact-results.json')
    assert [r['common_budget_met'] for r in exact['source']['rows']]==[True,False]
    lean=(study/'math/source-replayed-lean-final.log').read_text(); closure=load(study/'math/consumer-closure-comparison.json')
    assert lean.count('depends on axioms:')==16 and lean.count('PROOF VALUE ')==5 and 'All requested local modules accepted.' in lean
    assert closure['compared']==41 and closure['matched']==36 and len(closure['mismatches'])==5
    donors=table(exp/'donor_results.tsv'); selected=table(exp/'linked_cases.tsv'); receivers=table(exp/'receiver_results.tsv')
    assert len(donors)==24 and len(selected)==4 and len(receivers)==12
    raw_exposure={arm:sum(1-int(r['raw_protected']) for r in donors if r['arm']==arm) for arm in ('A','H')}
    assert raw_exposure=={'A':5,'H':0}
    pairs=table(exp/'paired_differences.tsv'); assert len(pairs)==12 and all(x['prevention']=='0' for x in pairs)
    assert all(r['settled']==r['substitute']==r['sharp']=='1' for r in receivers)
    assert all(r['prevented']==r['strict_through_receiver']=='0' for r in selected)
    trace=ROOT/'proof_provenance'; source=trace/'mathematics'; checks=trace/'verification'
    for mod,receipt_name in [('SinglePath.lean','causal_check.json'),('ScaleInterface.lean','scale_check.json')]:
        assert digest((source/mod).read_bytes())==load(checks/receipt_name)['source_sha256']
    assert load(checks/'scale_check.json')['exit_code']==0
    assert all(x['returncode']==0 for x in load(checks/'causal_check.json')['runs'])
    verdict=load(checks/'FULL_VERDICT.json'); assert verdict['return_code']==0 and len(verdict['theorems'])==5
    assert verdict['all_solution_declarations']==1468418 and verdict['all_challenge_declarations']==51692
    copied=scratch/'route'; shutil.copytree(source/'route',copied); run(copied/'render_paths.py')
    assert (copied/'declaration_paths.tsv').read_bytes()==(source/'route/declaration_paths.tsv').read_bytes()
    literature=study/'literature'; public=load(literature/'team_outcomes.json')
    assert json.loads(run(literature/'team_outcomes.py',literature/'team_endpoints.csv'))==public
    with (literature/'team_endpoints.csv').open(newline='') as f: teams=list(csv.DictReader(f))
    assert len(teams)==103 and set(teams[0])=={'mode','reproduced','major_errors'}
    expected_modes=['Human-Only','AI-Assisted','AI-Led']
    for idx,(mode,expected) in enumerate(zip(expected_modes,public['rows'],strict=True)):
        subset=[(int(r['reproduced']),int(r['major_errors'])) for r in teams if r['mode']==str(idx)]
        assert expected['mode']==mode and expected['teams']==len(subset)
        assert all(reported in (0,1) and count>=0 for reported,count in subset)
        assert (expected['missing_reproduction'],expected['missing_major_count'],expected['missing_either'])==(0,0,0)
        joint=Counter((r,k>0) for r,k in subset)
        four=[expected[x] for x in ('reproduced_and_major','reproduced_no_major','no_reproduction_major','neither')]
        assert four==[joint[1,True],joint[1,False],joint[0,True],joint[0,False]]
        assert sum(k for r,k in subset)==expected['total_major_errors']
    figure_check = 0
    if (ROOT/'figures/make_new.py').is_file():
        plots = scratch/'figure-tables'; plots.mkdir()
        run(ROOT/'figures/make_new.py', '--directory', plots, '--rebuild-sources', study)
        for fig in (1,4):
            name=f'fig{fig}_source.csv'
            assert (plots/name).read_bytes()==(ROOT/'figures'/name).read_bytes(),name
            figure_check += 1
    return {'public_replication_teams':len(teams), 'new_figure_tables_regenerated':figure_check, '8B_turns':72,'paired_training_seeds':[311,617,929],'fixed_dockets':4,'primary_frontier_contexts':primary,
            'first_reply_synthetic_disclosures_out_of_12':raw_exposure,'prevented_disclosures_in_12_pairs':0,
            'all_primary_receivers_settled':12,'linked_events':0,'linked_matched_pairs':4,'conditional_eligible_pairs':0,
            'secondary_frontier_contexts':count,'secondary_full_decisions':dict(successes),'exact_grid_checks':exact['grid_cases_checked'],
            'enumerated_interval_families':cr['families_checked'],'archived_Lean_axiom_audits':16,'archived_direct_proof_references':5}


def previous(scratch,full):
    p=ROOT/'previous/Data_and_code.zip'
    with p.open('rb') as f:
        assert hashlib.file_digest(f,'sha256').hexdigest()==LEGACY_SHA
    with ZipFile(p) as z:
        assert z.testzip() is None
        for old,new in [(1,2),(2,3),(3,5)]:
            f=ROOT/f'figures/fig{new}_source.csv'
            if f.exists(): assert f.read_bytes()==z.read(f'figures/fig{old}_source.csv')
        if not full: return {'archive_members':len(z.infolist()),'digest_and_CRC':'checked'}
        dest=scratch/'prior'; z.extractall(dest)
    result=json.loads(run(dest/'verify.py')); commitments=run(dest/'commitments/verify_commitments.py')
    refit=run(dest/'refit_ordinary.py')
    return {'numerical_replay':result,'ordinary_astronomy_refit':json.loads(refit),'commitments_check':json.loads(commitments)}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prior',action='store_true',help='also replay the previous instrument, astronomy, project and identification analyses (NumPy, SciPy, Astropy)')
    args=ap.parse_args()
    if not __debug__: raise RuntimeError('Run without Python optimization so verification assertions are active.')
    with tempfile.TemporaryDirectory(prefix='study-replay-') as d:
        temp=Path(d); current=verify_new(ROOT/'study',temp); prior=previous(temp,args.prior)
    print(json.dumps({'verified':True,'current':current,'previous':prior},indent=2))

if __name__=='__main__':
    main()
