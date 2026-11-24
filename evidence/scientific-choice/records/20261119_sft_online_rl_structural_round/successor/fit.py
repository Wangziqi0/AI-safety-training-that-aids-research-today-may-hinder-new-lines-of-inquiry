"""The fitting program accepts anonymized examples and blind initialization keys only."""
import gzip
import hashlib
import numpy as np
from common import ROOT, SEEDS, blind, init, unpack, forward, jsonl, write


def gradient(w, data):
    cat, head = data[:,0].astype(int), data[:,1].astype(int)
    target = data[:,2]
    hidden, outputs = forward(w,cat)
    selected = outputs[np.arange(len(data)),head]
    p = 1 / (1 + np.exp(-selected))
    is_center = head == 0
    losses = np.where(is_center, (selected-target)**2, np.logaddexp(0,selected)-target*selected)
    deriv = np.where(is_center, 2*(selected-target), p-target)/len(data)
    d = np.zeros_like(outputs)
    d[np.arange(len(data)),head] = deriv
    dh = (d @ unpack(w)[2].T)*(1-hidden**2)
    din = np.zeros((4,8))
    np.add.at(din,cat,dh)
    return losses.mean(), np.concatenate([v.ravel() for v in (din,dh.sum(axis=0),hidden.T@d,d.sum(axis=0))])


def main():
    initial={blind(seed):init(seed) for seed in SEEDS}
    weights=dict(initial)
    with gzip.open(ROOT/"updates.jsonl.gz","wt") as updates:
        for record in jsonl("samples.jsonl.gz"):
            samples=np.asarray(record["examples"],dtype="float64")
            w = initial[record["init"]].copy()
            digest = hashlib.sha256(samples.astype("<f8").tobytes()).hexdigest()
            m = np.zeros_like(w)
            v = m.copy()
            for i in range(1,41):
                loss, grad = gradient(w,samples)
                m=.9*m+.1*grad
                v=.999*v+.001*grad**2
                w-=.025*(m/(1-.9**i))/(np.sqrt(v/(1-.999**i))+1e-8)
                write(updates,dict(model=record["model"],init=record["init"],step=i,sample_sha256=digest,
                                   loss=loss,gradient=grad.tolist()))
            weights[record["model"]]=w
    np.savez_compressed(ROOT/"weights.npz",**weights)


if __name__=="__main__":
    main()
