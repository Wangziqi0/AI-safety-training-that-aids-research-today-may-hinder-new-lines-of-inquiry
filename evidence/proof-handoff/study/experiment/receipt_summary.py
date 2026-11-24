import json
from pathlib import Path
from collections import defaultdict
from dockets import DOCKETS
root=Path(__file__).resolve().parent
def read(p):
    return [json.loads(line) for line in (root/p).read_text().splitlines() if line.strip()]
out={}
for stage in ("service","scientific","handoff"):
    rr=read(f"internal/{stage}_raw.jsonl")
    val={}
    for arm in ["A","H"]:
        x=[r for r in rr if r["arm"]==arm]
        val[arm]=dict(n=len(x),truncated=sum(r["truncated"] for r in x),
                      tokens=sum(r["generated_tokens"] for r in x),batches=sorted(set(r["batch_size"] for r in x)),
                      exact_leaks=sum(any(d.canary.lower() in r["text"].lower() for d in DOCKETS.values()) for r in x))
    val["start"]=(root/f"internal/{stage}.start").read_text().strip()
    val["finish"]=(root/f"internal/{stage}.finish").read_text().strip()
    out[stage]=val
pack=read("receiver_packets.jsonl")
out["delivered_frontier_exposures"]=sum(any(d.canary.lower() in r["prompt"].lower() for d in DOCKETS.values()) for r in pack)
joined={r["id"]:r for r in read("internal/handoff_raw.jsonl")}
selected=read("internal/receiver_allocation.jsonl")
out["selected_donor_note_leaks"]={a:sum(any(d.canary.lower() in joined[r["donor"]]["text"].lower() for d in DOCKETS.values()) for r in selected if r["arm"]==a) for a in ("A","H")}
(root/"receipt_summary.json").write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(out))
