"""Join source assignment to independently frozen scientific observations, by slot."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from statistics import median


def lines(p):
    return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]


def main(root,out):
    g=root/"review/DOWNSTREAM.tsv"
    assert hashlib.sha256(g.read_bytes()).hexdigest()=="45389e3ed72ceed49049a86f1f24a116c969a6082565a3e21717231dbf4738bb"
    with g.open(newline="") as f:
        grades={r["slot"]:r for r in csv.DictReader(f,delimiter="\t")}
    costs={r["slot"]:r for r in json.loads((root/"downstream/TOOL_AUDIT.json").read_text())}
    records=[]
    for r in lines(root/"cross/private/receiver_allocation.jsonl"):
        records.append((r["slot"],"historic",r["case"],r["writer"] or "ordinary"))
    for r in lines(root/"transfer/internal/recipient_allocation.jsonl"):
        records.append((r["recipient_id"],"heldout",r["task"],r["arm"]))
    assert len(records)==len(grades)==len(costs)==18
    rows=[]
    for slot,study,task,arm in sorted(records):
        a,c=grades[slot],costs[slot]
        rows.append(dict(slot=slot,study=study,task=task,arm=arm,demonstrated_step=int(a["demonstrated_action"]),
                         justified=int(a["justified_focal"]),full=int(a["full_exact"]),
                         named_substantive_use=int(a["explicit_substantive_use"]),use=a["note_use"],
                         arithmetic=c["additional_local_arithmetic"],time_s=c["seconds"],
                         output_tokens=c["output_tokens"],decision=a["strongest_checked_decision"],
                         first_step=a["first_substantive_action"],attribution=a["attribution_basis"]))
    result=[]
    for group in ("all","historic","heldout"):
        for arm in ("A","H","ordinary"):
            selected=[r for r in rows if r["arm"]==arm and (group=="all" or r["study"]==group)]
            result.append(dict(group=group,arm=arm,n=len(selected),
                      **{k:sum(r[k] for r in selected) for k in ("demonstrated_step","justified","full","named_substantive_use","arithmetic","output_tokens")},
                      median_s=median(r["time_s"] for r in selected)))
    out.mkdir(exist_ok=True,parents=True)
    for name,table in (("recipients",rows),("groups",result)):
        with (out/(name+".tsv")).open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(table[0]),delimiter="\t",lineterminator="\n")
            writer.writeheader();writer.writerows(table)
    print(json.dumps(result[:3]))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("root",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();main(a.root,a.out)
