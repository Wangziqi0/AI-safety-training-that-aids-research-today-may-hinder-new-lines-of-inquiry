"""Replay the masked secondary assessment of standalone original mathematical decisions."""
import argparse
import json
from audit import as_tsv
from prepare import HERE, digest
from primary_results import REVIEW, directions, tsv

LOCK = "f86e05a769c0f5450bfd5e455a08e5cc4fa281ea6b79ff2dcbd9a111adbb9036"


def analyse():
    assert digest(REVIEW/"ORIGINAL_DECISION.tsv") == LOCK
    cards = {r["joint_id"]:r for r in tsv(REVIEW/"ORIGINAL_DECISION.tsv")}
    primary = tsv(HERE/"paired_outcomes.tsv")
    rows = []
    for p in primary:
        row={k:p[k] for k in ("history_id","archived_id","case","seed","history_arm","opportunity","qualified")}
        for a in ("A","H"):
            r=cards[p[a+"_joint_id"]]
            assert r["history_id"]==p["history_id"]
            row[a+"_pass"]=int(r["original_decision"])
            row[a+"_reason"]=r["reason"]
        rows.append(row)
    assert len(cards)==48 and len(rows)==24
    result=dict(grade_sha256=LOCK,note="masked second pass after primary lock",
                all=directions(rows),qualified=directions([r for r in rows if r["qualified"]=="1"]),
                by_origin={a:directions([r for r in rows if r["history_arm"]==a]) for a in ("A","H")},
                positive_ids={a:[r["archived_id"] for r in rows if r[a+"_pass"]] for a in ("A","H")})
    return {"standalone_decisions.tsv":as_tsv(rows),"standalone_results.json":json.dumps(result,indent=2)+"\n"}


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--record",action="store_true")
    args=parser.parse_args()
    for n,b in analyse().items():
        p=HERE/n
        if args.record and not p.exists():
            with p.open("x") as f:
                f.write(b)
        else:
            assert p.read_text()==b,n
    print("Verified the secondary 48-note standalone mathematical decisions.")
