"""Independent reconstruction of all 288 Adam trajectories from stored gradients; verify table use."""
import hashlib
import json
from collections import Counter
import numpy as np
from common import ROOT, SEEDS, ALGOS, ARMS, blind, init, jsonl
from fit import gradient


def main():
    examples = {r["model"]:np.asarray(r["examples"],dtype="float64") for r in jsonl("samples.jsonl.gz")}
    sample_hash={k:hashlib.sha256(d.astype("<f8").tobytes()).hexdigest() for k,d in examples.items()}
    assert len(examples)==288 and all(v.shape==(192,3) for v in examples.values())
    weights=np.load(ROOT/"weights.npz")
    assert len(weights.files)==312
    maxerr=0
    n=0
    for u in jsonl("updates.jsonl.gz"):
        model,step=u["model"],u["step"]
        assert u["sample_sha256"]==sample_hash[model]
        if step==1:
            w=weights[u["init"]].copy()
            m=np.zeros_like(w);v=m.copy()
        grad=np.array(u["gradient"])
        if step in (1,40):
            loss,recomputed=gradient(w,examples[model])
            assert np.allclose(recomputed,grad,atol=1e-12,rtol=1e-12) and abs(loss-u["loss"])<1e-12
        m=.9*m+.1*grad
        v=.999*v+.001*grad**2
        w=w-.025*m/(1-.9**step)/(np.sqrt(v/(1-.999**step))+1e-8)
        if step==40:
            err=float(np.max(np.abs(w-weights[model])))
            assert err<1e-12 and np.linalg.norm(w-weights[u["init"]])>0
            maxerr=max(maxerr,err)
        n+=1
    assert n==288*40
    for s in SEEDS:
        assert np.array_equal(weights[blind(s)],init(s))
    hold=list(jsonl("accepted_measurements.jsonl.gz"))
    expected=[]; routes=Counter(); eventcount=0
    for e in jsonl("events.jsonl.gz"):
        assert e["raw"]+e["trim"]==e["corrected"]
        assert (abs(e["corrected"]-e["reference"])<=1)==bool(e["accepted"])
        assert e["g_all"]==1-e["accepted"] and e["g_model"]==int(e["route"]=="model" and e["accepted"])
        if e["accepted"]:
            expected.append(dict(model=e["model"],seed=e["seed"],family=e["family"],specimen=e["spec"],
                                 standardized=e["corrected"]))
        routes[e["route"]]+=1;eventcount+=1
    assert eventcount==312*96 and expected==hold
    stats=dict(trained_models=288,initial_models=24,exposures=192*288,
               recorded_optimizer_steps=n,max_abs_checkpoint_reconstruction_error=maxerr,
               command_events=eventcount,accepted_table_rows=len(hold),routes_including_baseline=routes,
               training_input_sha256=hashlib.sha256((ROOT.parent/"structural"/"materials.jsonl.gz").read_bytes()).hexdigest())
    (ROOT/"audit.json").write_text(json.dumps(stats,indent=2)+"\n")
    print(json.dumps(stats))


if __name__=="__main__":
    main()
