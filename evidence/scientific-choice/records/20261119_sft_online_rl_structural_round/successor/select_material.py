"""Numerical training examples and separate audit ledger. No truth-bearing simulator import."""
import gzip
import json
from contextlib import ExitStack
from common import ROOT, STRUCT, SEEDS, ALGOS, ARMS, blind, category, jsonl, write


def row(code, head, value):
    return [code, head, (value - 44) / 36 if head == 0 else int(value)]


def select(pkg, rule, slot, pub):
    obs, status, f = pkg["observations"], pkg["status"], pkg["family_features"]
    assert status in {"delivered", "expired", "unavailable"}
    assert (status == "delivered") == (pkg["current"] is not None)
    assert (status == "unavailable") == (not obs)
    assert len(obs) <= 2 and (not obs or obs[0][0] == 0)
    base = "/package/"
    if rule == "U" and slot == 0 and pkg["current"] is not None:
        return row(category(f), 0, pkg["current"]), [base+"current"], [pkg["current"]], "delivered_product"
    if rule == "P" and slot == 0 and obs:
        return row(category(f), 0, obs[0][1]), [base+"observations/0"], [obs[0]], "natural_center"
    if rule == "P" and slot == 1 and len(obs) == 2:
        (x, r), (y, s) = obs
        assert x != y
        return row(category(f), 1, (s-r)/(y-x)>0), [base+"observations/0",base+"observations/1"], obs, "observed_pair"
    reason = ("product_omits_process" if rule == "U" and slot == 1 else
              "equipment_unavailable" if status == "unavailable" else
              "product_expired" if status == "expired" and rule == "U" else
              "second_measurement_not_taken")
    return row(category(pub["features"]), 0, pub["center"]), ["public#/center"], [pub["center"]], reason


def main():
    public = {(p["seed"], p["family"], p["clone"], p["slot"]):p for p in jsonl("public.jsonl.gz")}
    n = len(SEEDS)*len(ALGOS)*len(ARMS)
    cells, held, seen = {}, {}, set()
    with ExitStack() as stack:
        src = stack.enter_context(gzip.open(STRUCT/"materials.jsonl.gz","rt"))
        ledger = stack.enter_context(gzip.open(ROOT/"lineage.jsonl.gz","wt"))
        for line in src:
            r = json.loads(line)
            if r["coupling"] != "aligned":
                continue
            seed, algo, arm, split, family, clone, pkg = [r[k] for k in
                ("seed","algo","arm","split","family","clone","package")]
            key = (seed, algo, arm, split, family, clone)
            assert key not in seen and family in range(24) and clone in range(4)
            seen.add(key)
            if split == "heldout":
                ident = f"{seed},{family}"
                code = category(pkg["family_features"])
                assert held.setdefault(ident, code) == code
                continue
            assert split == "source"
            for rule in ("U", "P"):
                model = blind(seed,algo,arm,rule)
                entries = cells.setdefault(model,{})
                for slot in range(2):
                    ix = (family*4+clone)*2+slot
                    sample, spans, raw, reason = select(pkg,rule,slot,public[(seed,family,clone,slot)])
                    entries[ix] = sample
                    write(ledger,dict(model=model,index=ix,source_key=key,slot=slot,rule=rule,
                        family_feature_source=("public#/features" if spans[0].startswith("public") else "/package/family_features"),
                        public_key=[seed,family,clone,slot] if spans[0].startswith("public") else None,
                        status=pkg["status"],source_observation_count=len(pkg["observations"]),
                        spans=spans,raw=raw,decision=reason,exposure=sample))
        assert len(seen)==n*192 and len(cells)==2*n and len(held)==len(SEEDS)*24
    (ROOT/"heldout.json").write_text(json.dumps(held,sort_keys=True))
    with gzip.open(ROOT/"samples.jsonl.gz","wt") as out:
        for seed in SEEDS:
            for algo in ALGOS:
                for arm in ARMS:
                    for rule in ("U","P"):
                        model=blind(seed,algo,arm,rule)
                        write(out,dict(model=model,init=blind(seed),examples=[cells[model][i] for i in range(192)]))


if __name__=="__main__":
    main()
