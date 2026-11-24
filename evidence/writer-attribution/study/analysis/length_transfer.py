"""Join the 48 expanded-budget grades after masked assessment."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def lines(p):
    return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]


def tsv(p):
    with p.open(newline="") as f:
        return list(csv.DictReader(f,delimiter="\t"))


def main(root,out,assessor):
    versions={"review":"b97385ad2785404633a3232b0db09d01b69beb6b07cba3bc4f55159c2601bb44",
              "review2":"302711a5791892cf9ce5431b7ce44913bd06f70e859eeedda60aaf466a21979b"}
    q=root/assessor/"HELDOUT_LONG.tsv"
    assert hashlib.sha256(q.read_bytes()).hexdigest()==versions[assessor]
    short={r["note_id"]:r for r in tsv(root/assessor/"HELDOUT_NOTES.tsv")}
    short_key={r["writer_id"]:r["note_id"] for r in lines(root/"transfer/internal/writer_allocation.jsonl")}
    extended={r["note_id"]:r for r in tsv(q)}
    recs=lines(root/"budget_transfer/length_receipts.jsonl")
    assert len(recs)==len(extended)==48
    joined=[]
    for r in recs:
        s=short[short_key[r["short_id"]]]
        l=extended[r["note_id"]]
        assert s["task"]==l["task"]==r["task"]
        if r["unchanged_tokens"]:
            assert all(int(s[k])==int(l[k]) for k in ("actionable","full_exact"))
        joined.append(dict(task=r["task"],seed=r["seed"],arm=r["arm"],short_id=r["short_id"],long_id=r["note_id"],
                           unchanged=int(r["unchanged_tokens"]),prefix=int(r["short_is_prefix"]),
                           short_tokens=r["short_tokens"],long_tokens=r["long_tokens"],
                           short_cap=int(not r["short_eos"]),long_cap=int(not r["long_eos"]),
                           short_pass=int(s["actionable"]),long_pass=int(l["actionable"]),
                           short_exact=int(s["full_exact"]),long_exact=int(l["full_exact"]),explanation=l["reason"]))
    out.mkdir(parents=True,exist_ok=True)
    with (out/"heldout_budget.tsv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(joined[0]),delimiter="\t",lineterminator="\n")
        writer.writeheader();writer.writerows(joined)
    results=[]
    for arm in ("A","H"):
        for subset in ("all","math","data"):
            group=[r for r in joined if r["arm"]==arm and
                   (subset=="all" or (r["task"]<"T05")== (subset=="math"))]
            results.append(dict(arm=arm,subset=subset,n=len(group),
                         **{k:sum(r[k] for r in group) for k in ("short_cap","long_cap","short_pass","long_pass","short_exact","long_exact","unchanged","prefix")},
                         gains=sum(r["long_pass"]>r["short_pass"] for r in group),
                         losses=sum(r["long_pass"]<r["short_pass"] for r in group)))
    pair={(r["task"],r["seed"],r["arm"]):r for r in joined}
    cells={lab:0 for lab in ("A_only","H_only","both","neither")}
    for task,seed,arm in pair:
        if arm=="A":
            a=pair[task,seed,"A"]["long_pass"];h=pair[task,seed,"H"]["long_pass"]
            cells[{(1,0):"A_only",(0,1):"H_only",(1,1):"both",(0,0):"neither"}[a,h]]+=1
    result={"groups":results,"long_paired_transitions":cells,"all_prefixes_match":all(r["prefix"] for r in joined)}
    (out/"heldout_budget.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"all":[r for r in results if r["subset"]=="all"],"long_pairs":cells}))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("root",type=Path);p.add_argument("out",type=Path)
    p.add_argument("--assessor", choices=("review","review2"),default="review");a=p.parse_args();main(a.root,a.out,a.assessor)
