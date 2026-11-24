"""A distinct process loads checkpoint bytes and controls the held-out instrument."""
import gzip
import json
import random
import sys
from contextlib import ExitStack
import numpy as np
from common import ROOT, STRUCT, SEEDS, ALGOS, ARMS, blind, stable, forward, write
sys.path.insert(0,str(STRUCT))
from world import reading, certificate


def receive(weights, code, seed, family, clone):
    _, logits = forward(weights,np.array([code]))
    prob = float(1/(1+np.exp(-logits[0,1])))
    sign = 2 if prob >= .5 else -2
    timely = random.Random(stable("arrival",seed,family,clone)).random() < .90
    confident = max(prob,1-prob) >= .65
    specimen = 3000+clone
    position = 0 if clone == 2 else 1
    extra = []
    if clone == 1:
        route = "certificate"
        slope = certificate(seed,"heldout",family)
    elif clone == 2:
        route = "center"
        slope = 0
    elif timely and confident:
        route = "model"
        slope = sign
    elif clone == 3:
        route = "calibration"
        extra = [[x,reading(seed,"heldout",family,4000+clone,x)] for x in (0,1)]
        slope = extra[1][1]-extra[0][1]
    else:
        route = "ordinary"
        slope = 2
    trim = -position*slope
    raw = reading(seed,"heldout",family,specimen,position)
    result = raw+trim
    reference = reading(seed,"heldout",family,specimen,0)
    accepted = abs(result-reference)<=1
    # Post-decision truth is scoring only; no choice above can access this value.
    actual_slope = reading(seed,"heldout",family,specimen,1)-reference
    return dict(clone=clone, spec=specimen, family=family, prob=prob, proposal=sign, timely=int(timely),
                confident=int(confident),route=route,position=position,applied_slope=slope,trim=trim,
                extra=extra,raw=raw,corrected=result,reference=reference,accepted=int(accepted),
                g_model=int(route=="model" and accepted),g_all=int(not accepted),model_used=int(route=="model"),
                accuracy=int(sign==actual_slope),extra_measurements=len(extra),late=int(not timely),
                correct_ordinary=int(route=="ordinary" and accepted), model_rejected=int(route=="model" and not accepted))


def main():
    inputs=json.loads((ROOT/"heldout.json").read_text())
    with ExitStack() as stack:
        bank=stack.enter_context(np.load(ROOT/"weights.npz"))
        log=stack.enter_context(gzip.open(ROOT/"events.jsonl.gz","wt"))
        table=stack.enter_context(gzip.open(ROOT/"accepted_measurements.jsonl.gz","wt"))
        for seed in SEEDS:
            keys=[blind(seed)]+[blind(seed,algo,arm,rule) for algo in ALGOS for arm in ARMS for rule in ("U","P")]
            for ident in keys:
                for family in range(24):
                    code=inputs[f"{seed},{family}"]
                    for clone in range(4):
                        event=receive(bank[ident],code,seed,family,clone)
                        write(log,dict(model=ident,seed=seed,**event))
                        if event["accepted"]:
                            write(table,dict(model=ident,seed=seed,family=family,specimen=event["spec"],
                                             standardized=event["corrected"]))


if __name__=="__main__":
    main()
