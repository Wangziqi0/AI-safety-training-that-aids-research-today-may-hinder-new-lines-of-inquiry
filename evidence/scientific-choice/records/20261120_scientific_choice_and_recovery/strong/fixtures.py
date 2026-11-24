import random
from document_service import packet, target, tests

def curriculum(seed):
    rng = random.Random(seed)
    return [packet(rng, step) for step in range(18)]

def heldout_rows():
    return [{'id':r['id'], 'messages':[{'role':'user','content':r['prompt']}], 'max_new_tokens':96} for r in tests()]
