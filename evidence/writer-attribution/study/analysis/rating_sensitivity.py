"""Compute the finite uncertainty from two masked readings without treating grades as replicates."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def tsv(p):
    with p.open(newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def linked(rows, one, two, key, arm_key, first, second):
    a = {r[key]: r for r in one}
    b = {r[key]: r for r in two}
    assert set(a) == set(b) == {r[key] for r in rows}
    items = []
    for row in rows:
        scores = (int(a[row[key]][first]), int(b[row[key]][second]))
        assert set(scores) <= {0, 1}
        items.append({"id": row[key], "arm": row[arm_key], "case": row.get("case", row.get("task")),
                      "seed": row["seed"], "history": row.get("history_id",""),
                      "primary": scores[0], "independent": scores[1]})
    return items


def stats(rows):
    arms = {}
    for arm in sorted({r["arm"] for r in rows}):
        selected = [r for r in rows if r["arm"] == arm]
        arms[arm] = dict(n=len(selected), primary=sum(r["primary"] for r in selected),
                         independent=sum(r["independent"] for r in selected),
                         both=sum(r["primary"] and r["independent"] for r in selected),
                         either=sum(r["primary"] or r["independent"] for r in selected))
    a, h = arms["A"], arms["H"]
    assert a["n"] == h["n"]
    matches = sum(r["primary"] == r["independent"] for r in rows)
    return {"rows":len(rows), "grade_agreements":matches, "grade_disagreements":len(rows)-matches,
            "arm_counts":arms, "AH_worst_case_over_discrepant_grades":{
                "denominator":a["n"], "low_difference_count":a["both"]-h["either"],
                "high_difference_count":a["either"]-h["both"]}}


def main(root, output):
    first, second = root/"review", root/"review2"
    histories = tsv(root/"cross/graded_cells.tsv")
    heldout = [json.loads(s) for s in (root/"transfer/internal/writer_allocation.jsonl").read_text().splitlines()]
    historical = linked(histories,tsv(first/"CROSS_NOTES.tsv"),tsv(second/"CROSS_NOTES.tsv"),
                         "joint_id","writer","pass","actionable")
    strict = linked(histories,tsv(first/"ORIGINAL_DECISION.tsv"),tsv(second/"CROSS_NOTES.tsv"),
                    "joint_id","writer","original_decision","standalone_original")
    new = linked(heldout,tsv(first/"HELDOUT_NOTES.tsv"),tsv(second/"HELDOUT_NOTES.tsv"),
                 "note_id","arm","actionable","actionable")
    new_strict = linked(heldout,tsv(first/"HELDOUT_NOTES.tsv"),tsv(second/"HELDOUT_NOTES.tsv"),
                        "note_id","arm","full_exact","full_exact")
    q1 = {r["history_id"] for r in tsv(first/"PREHISTORY.tsv") if int(r["qualified"])}
    q2 = {r["history_id"] for r in tsv(second/"PREHISTORY.tsv") if r["qualification"].upper()=="QUALIFIED"}
    assert len(q1)==5 and len(q2)==6
    groups = {"archive":historical,"archive_primary_qualified":[r for r in historical if r["history"] in q1],
              "archive_independently_qualified":[r for r in historical if r["history"] in q2],
              "archive_strict":strict,"heldout":new,"heldout_math":[r for r in new if r["case"]<"T05"],
              "heldout_data":[r for r in new if r["case"]>="T05"],"heldout_strict":new_strict}
    result = {k:stats(v) for k,v in groups.items()}
    output.mkdir(parents=True, exist_ok=True)
    with (output/"two_readings.tsv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=["endpoint",*historical[0]],delimiter="\t",lineterminator="\n")
        writer.writeheader()
        for name, vals in [("archive_actionable",historical),("archive_original_claim",strict),
                           ("heldout_actionable",new),("heldout_full_exact",new_strict)]:
            writer.writerows(dict(endpoint=name,**r) for r in vals)
    (output/"rating_sensitivity.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ("archive","heldout","heldout_strict")}))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("root",type=Path);p.add_argument("output",type=Path)
    args=p.parse_args();main(args.root,args.output)
