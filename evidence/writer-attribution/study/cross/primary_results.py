"""Join frozen independent mathematical judgements to the two assigned writers."""
import argparse
import csv
from collections import Counter, defaultdict
import json
from audit import REPLAY_FIELDS, as_tsv, raw_check
from prepare import HERE, OLD, digest, message_digest, read_rows

REVIEW = HERE.parent / "review"
OPP = "68cc621f1ad19799559004bb5417d2c9e7d48c3dd0dae7f0473da0fb83132512"
GRADES = "4d9524aaf8831de88e381829420b19180079ce66af35182f862e86f39e8d04a9"


def tsv(path):
    with path.open() as stream:
        return list(csv.DictReader(stream,delimiter="\t"))


def directions(rows):
    a = sum(r["A_pass"] for r in rows)
    h = sum(r["H_pass"] for r in rows)
    return dict(n=len(rows),A=a,H=h,A_only=sum(r["A_pass"]>r["H_pass"] for r in rows),
                H_only=sum(r["A_pass"]<r["H_pass"] for r in rows),
                both=sum(r["A_pass"]==r["H_pass"]==1 for r in rows),
                neither=sum(r["A_pass"]==r["H_pass"]==0 for r in rows),
                signed_A_minus_H=(a-h)/len(rows) if rows else None)


def analyse():
    assert digest(REVIEW/"PREHISTORY.tsv") == OPP and digest(REVIEW/"CROSS_NOTES.tsv") == GRADES
    hist = {r["history_id"]:r for r in tsv(REVIEW/"PREHISTORY.tsv")}
    grades = {r["joint_id"]:r for r in tsv(REVIEW/"CROSS_NOTES.tsv")}
    private = read_rows(HERE/"private/allocation.jsonl")
    raw = {r["id"]:r for p in sorted((HERE/"raw").glob("b*.jsonl")) for r in read_rows(p)}
    old = {r["id"]:r for r in read_rows(OLD/"internal/handoff_raw.jsonl")}
    freeze = json.loads((HERE/"FREEZE.json").read_text())
    chk = {(r["arm"],r["seed"]):r for r in freeze["checkpoints"]}
    reqs = {r["id"]:r for p in sorted((HERE/"inputs").glob("b*.jsonl")) for r in read_rows(p)}
    assert len(hist) == 24 and len(private) == len(raw) == len(grades) == 48
    grouped = defaultdict(dict)
    cells, replay = [], {}
    for k in private:
        r,g,op,ref = raw[k["joint_id"]],grades[k["joint_id"]],hist[k["history_id"]],old[k["archived_id"]]
        a = k["writer_arm"]
        raw_check(reqs[r["id"]],r,chk[a,k["seed"]])
        assert message_digest(r["messages"]) == k["messages_sha256"]
        assert ref["messages"] == r["messages"] and r["context_tokens"] == ref["context_tokens"]
        assert r["history_id"] == g["history_id"] == k["history_id"]
        assert r["arm"] == a and r["seed"] == k["seed"] and ref["arm"] == k["history_arm"]
        assert int(g["qualified_history"]) == int(op["qualified"])
        assert g["code"] != "UNASSESSABLE" and int(g["pass"]) == int(g["code"] in ("ORIGINAL","EQUIVALENT","NEW"))
        same = ref["arm"] == a
        if same:
            replay[ref["id"]] = [field for field in REPLAY_FIELDS if r[field] != ref[field]]
        row = dict(case=k["case"],seed=k["seed"],history_arm=k["history_arm"],archived_id=k["archived_id"],
                   history_id=k["history_id"],writer=a,joint_id=k["joint_id"],original_writer=int(same),
                   opportunity=op["grade"],qualified=int(op["qualified"]),grade=g["code"],pass_650=int(g["pass"]),
                   focal_reason=g["focal_reason"],other_valid_action=g["other_valid_action"],activity=g["activity"],
                   qualification=g["qualification"],reason=g["reason"],tokens=r["generated_tokens"],
                   truncated=int(r["truncated"]))
        cells.append(row)
        grouped[k["history_id"]][a] = row
    assert len(replay) == len(grouped) == 24
    pairs = []
    for h, ab in grouped.items():
        a,b = ab["A"],ab["H"]
        assert a["qualified"] == b["qualified"] and a["archived_id"] == b["archived_id"]
        p = {k:a[k] for k in ("case","seed","history_arm","archived_id","history_id","opportunity","qualified")}
        for writer,r in ab.items():
            p[writer+"_joint_id"] = r["joint_id"]
            p[writer+"_grade"],p[writer+"_pass"] = r["grade"],r["pass_650"]
            p[writer+"_focal"],p[writer+"_other_valid_action"] = r["focal_reason"],r["other_valid_action"]
            p[writer+"_tokens"],p[writer+"_truncated"] = r["tokens"],r["truncated"]
        pairs.append(p)
    sort_key = lambda r:(r["case"],r["seed"],r["history_arm"],r.get("writer",""))
    cells.sort(key=sort_key)
    pairs.sort(key=sort_key)
    timings = [json.loads(p.read_text()) for p in sorted((HERE/"raw").glob("b*.timing.json"))]
    assert len(timings)==6 and all(x["returncode"]==0 for x in timings)
    report = dict(all=directions(pairs),prequalified=directions([r for r in pairs if r["qualified"]]),
                  unqualified=directions([r for r in pairs if not r["qualified"]]),
                  by_origin={a:directions([r for r in pairs if r["history_arm"]==a]) for a in ("A","H")},
                  by_seed={s:directions([r for r in pairs if r["seed"]==s]) for s in (311,617,929)},
                  by_docket={c:directions([r for r in pairs if r["case"]==c]) for c in ("G1","G2","E1","E2")},
                  same_writer_exact=sum(not v for v in replay.values()),same_writer_differences={k:v for k,v in replay.items() if v},
                  checked_replay_fields=list(REPLAY_FIELDS),elapsed_wrapper_seconds=sum(t["elapsed_seconds"] for t in timings),
                  timings=timings,histories=len(hist),distinct_model_histories=len({message_digest(r["messages"]) for r in old.values()}),
                  grade_counts={},truncations={},tokens={},qualified_focal_counts={},reason_opportunities=dict(Counter(r["grade"] for r in hist.values())))
    for arm in ("A","H"):
        rows = [r for r in cells if r["writer"]==arm]
        report["grade_counts"][arm] = dict(Counter(r["grade"] for r in rows))
        report["qualified_focal_counts"][arm] = dict(Counter(r["focal_reason"] for r in rows if r["qualified"]))
        report["truncations"][arm] = sum(r["truncated"] for r in rows)
        report["tokens"][arm] = sum(r["tokens"] for r in rows)
    return {"primary_results.json":json.dumps(report,indent=2)+"\n",
            "graded_cells.tsv":as_tsv(cells),"paired_outcomes.tsv":as_tsv(pairs)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--record",action="store_true")
    args = parser.parse_args()
    for fname,body in analyse().items():
        p=HERE/fname
        if args.record and not p.exists():
            with p.open("x") as out:
                out.write(body)
        else:
            assert p.read_text()==body,fname
    print("Verified independent judgements and the complete matched primary assignment.")
