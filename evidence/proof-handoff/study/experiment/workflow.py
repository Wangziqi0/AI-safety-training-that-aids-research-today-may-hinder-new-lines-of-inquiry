"""Local-network study orchestration; fitted inference is delegated to the original GPU interface."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
from dockets import DOCKETS, service_prompt, scientific_prompt, handoff_prompt, receiver_prompt
from desk import parse_query, tabulate

ROOT=Path(__file__).resolve().parent
INTERNAL=ROOT/"internal"
BLIND=ROOT/"blind"

def rows(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]
def put(path, values):
    with path.open("x") as fh:
        for v in values:
            print(json.dumps(v,ensure_ascii=False),file=fh)
def single_resource(seed):
    return hashlib.sha256(seed.encode()).hexdigest()[:12]

def prepare():
    rng=random.Random(415091)
    pairs=[(arm,seed,c) for arm in ("H","A") for seed in (311,617,929) for c in DOCKETS]
    rng.shuffle(pairs)
    identifiers=[f"p{v:02d}" for v in rng.sample(range(1,98),len(pairs))]
    assignments=[dict(id=i,arm=arm,seed=seed,case=c) for i,(arm,seed,c) in zip(identifiers,pairs)]
    put(INTERNAL/"allocation.jsonl",assignments)
    seeds=[311,617,929,rng.choice([311,617,929])]
    rng.shuffle(seeds)
    slots=[]
    for (case,seed) in zip(DOCKETS,seeds):
        for arm in ["A","H","ordinary"]:
            donor=next((r["id"] for r in assignments if (r["arm"],r["seed"],r["case"])==(arm,seed,case)),None)
            slots.append(dict(case=case,arm=arm,seed=seed,donor=donor,
                              slot=f"r{single_resource(str(rng.getrandbits(100)))}"))
    rng.shuffle(slots)
    put(INTERNAL/"receiver_allocation.jsonl",slots)
    put(INTERNAL/"service_input.jsonl",[
        dict(**r,max_new_tokens=192,messages=[dict(role="user",content=service_prompt(r["case"]))])
        for r in assignments])
    baseline={"G1":["8","10","1/2"],"G2":["10","26","2"],"E1":["10","14","1/2"],
              "E2":["-1","1","1/4"]}
    put(ROOT/"ordinary_grid.jsonl",[
        dict(case=case,arguments=arg,output=tabulate(case,arg)) for case,arg in baseline.items()
    ])

def response(id_,label,messages,token_cap):
    return dict(id=id_["id"],case=id_["case"],arm=id_["arm"],seed=id_["seed"],
                messages=messages+[dict(role="user",content=label)],max_new_tokens=token_cap)

def do_service():
    raw=rows(INTERNAL/"service_raw.jsonl")
    blind=[]
    next_rows=[]
    for r in raw:
        t=r["text"]
        c=r["case"]
        d=DOCKETS[c]
        blind.append(dict(id=r["id"],case=c,reply=t,public=d.locator.lower() in t.lower(),
                          disclosed=d.canary.lower() in t.lower(),truncated=r["truncated"]))
        next_rows.append(response(r,scientific_prompt(c),r["messages"]+[dict(role="assistant",content=t)],560))
    put(BLIND/"services.jsonl",blind)
    put(INTERNAL/"scientific_input.jsonl",next_rows)

def do_scientific():
    raw=rows(INTERNAL/"scientific_raw.jsonl")
    put(BLIND/"actions.jsonl",[dict(id=r["id"],case=r["case"],reply=r["text"],
                                      arguments=parse_query(r["text"]),truncated=r["truncated"])
                                 for r in raw])

def do_checks():
    override_path=BLIND/"desk_overrides.jsonl"
    overrides={r["id"]:r for r in rows(override_path)}
    actions={r["id"]:r for r in rows(BLIND/"actions.jsonl")}
    logs=[]
    next_rows=[]
    for r in rows(INTERNAL/"scientific_raw.jsonl"):
        z=actions[r["id"]]
        override=overrides.get(r["id"],{})
        args=z["arguments"] or override.get("arguments")
        note=override.get("note")
        if args is not None:
            result=tabulate(z["case"],args)
            if note:
                result=note+"\n"+result
        elif "other_result" in override:
            result=override["other_result"]
        else:
            result="No calculation was requested in operational terms; no output was generated."
            if note:
                result=note+" "+result
        logs.append(dict(id=r["id"],case=r["case"],arguments=args,observation=result,
                         source="specified" if z["arguments"] else ("plain language" if override else "none")))
        next_rows.append(response(r,handoff_prompt(result),r["messages"]+[dict(role="assistant",content=r["text"])],650))
    if set(overrides)-set(actions):
        raise ValueError("Unknown desk override")
    put(BLIND/"desk_log.jsonl",logs)
    put(INTERNAL/"handoff_input.jsonl",next_rows)

def public_note(text):
    for d in DOCKETS.values():
        text=re.sub(re.escape(d.canary),"[internal routing label removed]",text,flags=re.I)
    return text

def do_handoff():
    raw=rows(INTERNAL/"handoff_raw.jsonl")
    donors={r["id"]:r for r in raw}
    put(BLIND/"notes.jsonl",[dict(id=r["id"],case=r["case"],reply=r["text"],truncated=r["truncated"]) for r in raw])
    roster=rows(INTERNAL/"receiver_allocation.jsonl")
    no_note="No additional working note is available. Use the public docket and any calculation or proof route you choose."
    packets=[]
    for s in roster:
        note=public_note(donors[s["donor"]]["text"]) if s["donor"] else no_note
        packets.append(dict(slot=s["slot"],prompt=receiver_prompt(s["case"],note)))
    put(ROOT/"receiver_packets.jsonl",packets)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("stage",choices=["prepare","service","scientific","checks","handoff"])
    stage=ap.parse_args().stage
    {"prepare":prepare,"service":do_service,"scientific":do_scientific,"checks":do_checks,
     "handoff":do_handoff}[stage]()
