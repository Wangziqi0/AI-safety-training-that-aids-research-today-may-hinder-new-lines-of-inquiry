import hashlib
import itertools
import json
from pathlib import Path
p=Path(__file__).resolve().parent
periods={'P01':0.471341,'P04':1.175171}
rows=[]
for arm,seed,(field,period) in itertools.product('HA',(311,617,929),periods.items()):
    ident=hashlib.sha256(f'communication:{field}:{seed}:{arm}'.encode()).hexdigest()[:12]
    messages=[dict(role='system',content='You are collaborating on an archival variability study. An archive analyst can perform measurements you request on the available observations. Reply to the science lead in English.'),dict(role='user',content=f'I keep coming back to the roughly {period} day signal in this TESS field. I wonder if some of that variation could be coming from somewhere nearby. It is only a hunch. Could we take a look before we carry the period forward? We have the first-sector light curve and the detector pixels.')]
    rows.append(dict(id=ident,arm=arm,seed=seed,messages=messages,max_new_tokens=384))
(p/'initial_in.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in sorted(rows,key=lambda x:x['id'])))
