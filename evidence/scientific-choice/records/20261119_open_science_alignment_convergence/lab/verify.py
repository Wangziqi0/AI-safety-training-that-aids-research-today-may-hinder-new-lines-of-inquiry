"""Verify training stream matching, file identity and realized update magnitude."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

p=argparse.ArgumentParser()
p.add_argument('observed',type=Path)
p.add_argument('out',type=Path)
args=p.parse_args()
records=[]
groups=defaultdict(list)
for d in sorted(args.observed.iterdir()):
    if not (d/'manifest.json').exists():
        continue
    manifest=json.loads((d/'manifest.json').read_text())
    steps=[json.loads(x) for x in (d/'steps.jsonl').read_text().splitlines()]
    assert all(i==s['step'] for i,s in enumerate(steps)) and len(steps)==manifest['steps']
    assert manifest['file_sha256']==hashlib.file_digest((d/'adapter.pt').open('rb'),'sha256').hexdigest()
    digest=hashlib.sha256(json.dumps([s['rows'] for s in steps],sort_keys=True).encode()).hexdigest()
    groups[(manifest['algo'],manifest['seed'])].append((manifest['source_sha256'],digest,manifest['weight_sha256']))
    answers=[a for s in steps for a in s['answers']]
    norms=[s['gradient_norm_preclip'] for s in steps]
    rewards=[r for s in steps for r in s['rewards']]
    records.append(dict(**manifest,prompt_sequence_sha256=digest,grad_min=min(norms),grad_max=max(norms),
                        clipped=sum(n>1 for n in norms),zero_grad_steps=sum(n==0 for n in norms),
                        answer_tokens=sum(len(a['ids']) for a in answers),responses=len(answers),reward_mean=mean(rewards),
                        reward_zero_count=rewards.count(0.0),capped=sum(a['truncated'] for a in answers)))
for (algo,seed),rows in groups.items():
    assert len(rows)==3 and len({r[:2] for r in rows})==1 and len({r[2] for r in rows})==3
args.out.write_text(json.dumps(records,indent=2)+'\n')
