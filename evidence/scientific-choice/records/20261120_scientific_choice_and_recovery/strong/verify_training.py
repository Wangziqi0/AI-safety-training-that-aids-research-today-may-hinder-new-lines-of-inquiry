import hashlib
import json
from pathlib import Path
from statistics import mean

BASE=Path(__file__).resolve().parent
def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

models=[]
for seed in (311,617,929):
    compared={}
    for arm in 'HAB':
        d=BASE/'weights'/f'{arm}-{seed}'
        meta=json.loads((d/'manifest.json').read_text())
        assert sha(d/'adapter.pt')==meta['file_sha256']
        rows=[json.loads(x) for x in (d/'steps.jsonl').read_text().splitlines()]
        assert [r['step'] for r in rows]==list(range(1,19))
        assert all(len(r['examples'])==4 and r['norm_before_clip']>0 for r in rows)
        prompts=[(ex['category'],ex['prompt']) for r in rows for ex in r['examples']]
        public=[ex['target'] for r in rows for ex in r['examples'] if ex['category']=='public']
        compared[arm]=(prompts,public,meta['initial_sha256'])
        means=[mean(ex['loss'] for ex in row['examples']) for row in rows]
        models.append(dict(**meta,first_step_loss=means[0],last_step_loss=means[-1],
                           response_tokens=sum(len(ex['target_ids']) for r in rows for ex in r['examples'])))
    assert compared['H']==compared['A']==compared['B']
assert len({m['checkpoint_sha256'] for m in models})==9
assert len({m['initial_sha256'] for m in models})==3
(BASE/'training_summary.json').write_text(json.dumps(models,indent=2)+'\n')
