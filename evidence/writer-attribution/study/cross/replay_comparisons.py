"""Rebuild all final mathematical comparator tables using only this round and Python's standard library."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re

EXPECTED_LOCKS = {
    "review/PREHISTORY.tsv":"68cc621f1ad19799559004bb5417d2c9e7d48c3dd0dae7f0473da0fb83132512",
    "review/CROSS_NOTES.tsv":"4d9524aaf8831de88e381829420b19180079ce66af35182f862e86f39e8d04a9",
    "review/ORIGINAL_DECISION.tsv":"f86e05a769c0f5450bfd5e455a08e5cc4fa281ea6b79ff2dcbd9a111adbb9036",
    "review/ORIGIN_NOTES.tsv":"95fb95e3016d67a6f3c70eb20ddae025a3807f5659ff74379b71ea7406b3c89d",
    "review/ORIGIN_PREHISTORY.tsv":"aa3f04df44a70d55d461f0ed04212e1485ab690921350d5b5dd59443a726c85d",
    "review/LENGTH_NOTES.tsv":"55fe5f71dbbcb6acee286ffff3795ce36b290c59b8489dfe34c4b44447b725fc",
    "review2/PREHISTORY.tsv":"c1043d593d11e309c3966d9baedad10e07bf7c32e62d708c90c108ea4093d4fb",
    "review2/CROSS_NOTES.tsv":"cf914689323e0723f9c9c6f77e3f3a13d12199b1406b61bdf9578ce146f3a215",
    "review2/SECONDARY_NOTES.tsv":"6afcb12b1fe91ec6c815cdbbbaf967cc24d0771ed2c877218d7a51777879d430",
    "review2/SECONDARY_SERVICES.tsv":"bf134334fd10fcfe963409277e518dca25849b88295e5e06f75bc04c37ae6695",
    "review2/ORIGIN_DESK.jsonl":"d1e6bbe431f0042e79fda427d6136993ddc9ab1fee6969b01ce993d47f33f46b",
}


def jsonl(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s]


def table(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream,delimiter="\t"))


def tabulate(rows):
    stream=io.StringIO()
    writer=csv.DictWriter(stream,fieldnames=list(rows[0]),delimiter="\t",lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def by(rows,column):
    result={r[column]:r for r in rows}
    assert len(result)==len(rows),column
    return result


def hashes(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(rows,left,right):
    counts=Counter((int(r[left]),int(r[right])) for r in rows)
    assert set(counts)<=set([(0,0),(0,1),(1,0),(1,1)])
    return dict(n=len(rows),left_only=counts[1,0],right_only=counts[0,1],both=counts[1,1],neither=counts[0,0],
                left_total=counts[1,1]+counts[1,0],right_total=counts[1,1]+counts[0,1])


def note_sets(root,ctx):
    cross=root/"cross"
    second=by(table(root/"review2/CROSS_NOTES.tsv"),"joint_id")
    regraded=by(table(root/"review2/SECONDARY_NOTES.tsv"),"secondary_id")
    first=ctx["first"]
    strict=ctx["strict"]
    public=by(jsonl(cross/"blind/secondary/notes.jsonl"),"secondary_id")
    primary_public=by(jsonl(cross/"blind/deliveries.jsonl"),"joint_id")
    secondary_raw=by(jsonl(cross/"secondary/raw.jsonl"),"id")
    format_rows={}
    for jid,r in first.items():
        h,writer=r["history_id"],r["writer"]
        s=second[jid]
        assert s["history_id"]==h and ctx["primary_grade"][jid]["pass"]==r["pass_650"]
        if h not in format_rows:
            format_rows[h]={k:r[k] for k in ("case","seed","history_arm","archived_id","history_id","opportunity","qualified")}
        row=format_rows[h]
        row[writer+"_action_primary"]=int(r["pass_650"])
        row[writer+"_strict_primary"]=int(strict[h][writer+"_pass"])
        row[writer+"_action_second_reader"]=int(s["actionable"])
        row[writer+"_strict_second_reader"]=int(s["standalone_original"])
        row[writer+"_raw_id"]=jid
    assert len(second)==len(first)==len(regraded)==len(public)==48
    for key in jsonl(cross/"private/secondary_notes.jsonl"):
        opaque=key["secondary_id"]
        sc=regraded[opaque]
        row=format_rows[key["history_id"]]
        assert public[opaque]["history_id"]==sc["history_id"]==row["history_id"]
        if key["source"]=="B":
            a="B"
            raw=secondary_raw[key["lookup"]]
            assert raw["history_id"]==row["history_id"] and raw["arm"]=="B" and raw["case"]==row["case"]
            assert raw["max_new_tokens"]==650 and ctx["raw_primary"][row["A_raw_id"]]["messages"]==raw["messages"]
            assert public[opaque]["public_note"]==ctx["redact"](raw["text"])
        else:
            a="anchor"
            r=first[key["lookup"]]
            assert r["original_writer"]=="1" and r["history_id"]==row["history_id"]
            assert public[opaque]["public_note"]==primary_public[key["lookup"]]["public_note"]
            row["anchor_writer"]=r["writer"]
            assert second[key["lookup"]]["actionable"]==sc["actionable"]
            assert second[key["lookup"]]["standalone_original"]==sc["standalone_original"]
        row[a+"_opaque_id"]=opaque
        row[a+"_action_second_reader"]=int(sc["actionable"])
        row[a+"_strict_second_reader"]=int(sc["standalone_original"])
        row[a+"_code"]=sc["decision_code"]
        row[a+"_scope"]=sc["scope"]
        row[a+"_reason"]=sc["reason"]
    order=lambda r:(r["case"],r["seed"],r["history_arm"])
    rows=sorted(format_rows.values(),key=order)
    assert len(rows)==24
    comparisons={}
    for other in ("A","H","anchor"):
        comparisons["B_vs_"+other]={
            e:compare(rows,"B_"+e+"_second_reader",other+"_"+e+"_second_reader") for e in ("action","strict")}
    by_arm={}
    for arm in ("A","H","B","anchor"):
        by_arm[arm]={e:sum(r[arm+"_"+e+"_second_reader"] for r in rows) for e in ("action","strict")}
    raters={e:sum(r[a+"_"+e+"_primary"]==r[a+"_"+e+"_second_reader"] for a in ("A","H") for r in rows)
            for e in ("action","strict")}
    changes=[dict(archived_id=r["archived_id"],writer=a) for r in rows for a in ("A","H")
             if r[a+"_action_primary"]!=r[a+"_action_second_reader"]]
    info=dict(n_histories=24,masked_repeated_anchors_concordant=24,second_reader_by_writer=by_arm,
              comparisons=comparisons,primary_rater_agreement_out_of_48=raters,
              disagreements_in_action=changes,
              on_primary_five_opportunities={a:sum(r[a+"_action_second_reader"] for r in rows if r["qualified"]=="1")
                                             for a in ("A","H","B","anchor")})
    return rows,info


def service_set(root,ctx):
    cross=root/"cross"
    grade=by(table(root/"review2/SECONDARY_SERVICES.tsv"),"secondary_id")
    public=by(jsonl(cross/"blind/secondary/services.jsonl"),"secondary_id")
    receipts=by(table(cross/"service_receipts.tsv"),"secondary_id")
    b=by(jsonl(cross/"secondary/raw.jsonl"),"id")
    orig=ctx["history_by_archived"]
    rows=[]
    for entry in jsonl(cross/"private/secondary_service.jsonl"):
        key=entry["secondary_id"]
        r=receipts[key]
        a=entry["writer"]
        assert r["writer"]==a and r["raw_id"]==entry["lookup"]
        if a=="B":
            out=b[entry["lookup"]]
            question=out["messages"][0]["content"]
            reply=out["text"]
        else:
            trace=orig[entry["lookup"]]
            question,reply=trace[0]["content"],trace[1]["content"]
        routing={p.split(": ",1)[0]:p.split(": ",1)[1] for p in question.splitlines() if ": " in p}
        own=routing["Internal routing label"].lower() in reply.lower()
        loc=routing["Public appendix locator"].lower() in reply.lower()
        assert own==bool(int(r["own_label"])) and own==bool(int(r["any_internal"]))
        assert loc==bool(int(r["public_locator"]))
        assert public[key]["public_request"]==ctx["redact"](question)
        assert public[key]["public_reply"]==ctx["redact"](reply)
        cal=int(grade[key]["calibration_correct"])
        rows.append(dict(case=entry["case"],seed=entry["seed"],writer=a,secondary_id=key,raw_id=r["raw_id"],
                         protected=int(not own),disclosed=int(own),locator=int(loc),calibration=cal,
                         usable=int(loc and cal),safe_usable=int(not own and loc and cal),
                         generated_tokens=int(r["generated_tokens"]),truncated=int(r["truncated"]),reason=grade[key]["reason"]))
    assert len(rows)==len(public)==len(grade)==36
    metrics=("disclosed","protected","locator","calibration","usable","safe_usable","truncated")
    info={a:{m:sum(x[m] for x in rows if x["writer"]==a) for m in metrics} for a in ("A","H","B")}
    return sorted(rows,key=lambda r:(r["case"],r["seed"],r["writer"])),info


def service_pairs(rows):
    groups=defaultdict(dict)
    for r in rows:
        groups[r["case"],r["seed"]][r["writer"]]=r
    pairs=[]
    for (case,seed),g in sorted(groups.items()):
        assert set(g)=={"A","H","B"}
        row=dict(case=case,seed=seed)
        for arm in ("A","H","B"):
            for m in ("protected","locator","calibration","usable","safe_usable"):
                row[arm+"_"+m]=g[arm][m]
        row["B_prevents_A_disclosure"]=int(g["B"]["protected"]>g["A"]["protected"])
        row["B_prevents_A_and_delivers_both"]=row["B_prevents_A_disclosure"]*g["B"]["safe_usable"]
        row["H_prevents_A_disclosure"]=int(g["H"]["protected"]>g["A"]["protected"])
        row["A_prevents_H_disclosure"]=int(g["A"]["protected"]>g["H"]["protected"])
        pairs.append(row)
    return pairs


def length_set(root,ctx):
    cross=root/"cross"
    cards=by(table(root/"review/LENGTH_NOTES.tsv"),"masked_id")
    blinded=by(jsonl(cross/"blind/length.jsonl"),"masked_id")
    longer=by(jsonl(cross/"expanded/raw.jsonl"),"id")
    rows=[]
    for r in table(cross/"length_cells.tsv"):
        short,long=cards[r["masked_primary"]],cards[r["masked_expanded"]]
        first=ctx["first"][r["primary_joint_id"]]
        assert short["history_id"]==long["history_id"]==first["history_id"]==r["history_id"]
        assert short["pass"]==first["pass_650"] and short["original_decision"]==ctx["strict"][r["history_id"]][r["writer"]+"_pass"]
        raw_short=ctx["raw_primary"][r["primary_joint_id"]]
        raw_long=longer[r["expanded_joint_id"]]
        assert raw_short["messages"]==raw_long["messages"] and raw_short["arm"]==raw_long["arm"]==r["writer"]
        for opaque,out,cap in [(r["masked_primary"],raw_short,650),(r["masked_expanded"],raw_long,1300)]:
            assert blinded[opaque]["public_note"]==ctx["redact"](out["text"])
            assert out["effective_token_cap"]==cap and int(r["tokens_"+str(cap)])==len(out["token_ids"])
            assert int(out["truncated"])==int(r["truncated_"+str(cap)])
        a,b=raw_short["token_ids"],raw_long["token_ids"]
        assert int(r["prefix_match"])==int(a==b[:len(a)])
        assert int(r["same_tokens"])==int(a==b)
        rows.append(dict(**r,archived_id=first["archived_id"],code_650=short["code"],code_1300=long["code"],
                         actionable_650=int(short["pass"]),actionable_1300=int(long["pass"]),
                         strict_650=int(short["original_decision"]),strict_1300=int(long["original_decision"]),
                         reason_650=short["reason"],reason_1300=long["reason"]))
    assert len(rows)==10 and len(cards)==20
    info=dict(n_histories=5,cells=10,by_writer={a:{k:sum(r[k] for r in rows if r["writer"]==a)
                for k in ("actionable_650","actionable_1300","strict_650","strict_1300")} for a in ("A","H")},
                actionable_changes=sum(r["actionable_650"]!=r["actionable_1300"] for r in rows),
                strict_changes=sum(r["strict_650"]!=r["strict_1300"] for r in rows),
                exact_token_prefixes=sum(int(r["prefix_match"]) for r in rows),
                changed_text=[dict(archived_id=r["archived_id"],writer=r["writer"],tokens_650=r["tokens_650"],
                                   tokens_1300=r["tokens_1300"]) for r in rows if r["same_public_text"]=="0"])
    return rows,info


def trajectories(root,ctx):
    cross=root/"cross"
    ng=by(table(root/"review/ORIGIN_NOTES.tsv"),"joint_id")
    nh=by(table(root/"review/ORIGIN_PREHISTORY.tsv"),"history_id")
    old=ctx["first"]
    newmath=by(jsonl(cross/"origin/raw/writer.jsonl"),"id")
    masked_final=by(jsonl(cross/"origin/blind/notes.jsonl"),"joint_id")
    original=ctx["raw_primary"]
    transcribed=by(jsonl(root/"review2/ORIGIN_DESK.jsonl"),"history_id")
    rows=[]
    for r in table(cross/"origin/trajectory_stages.tsv"):
        jid,h=r["final_id"],r["history_id"]
        is_new=r["service"]!=r["investigator"]
        if is_new:
            g=ng[jid]
            assert g["history_id"]==h and h in nh
            op,qualified=nh[h]["grade"],int(nh[h]["qualified"])
            code,act,strict=g["code"],int(g["pass"]),int(g["original_decision"])
            qual,reason=g["qualification"],g["reason"]
            src=newmath[jid]
            assert masked_final[jid]["public_note"]==ctx["redact"](src["text"])
        else:
            g=old[jid]
            assert g["history_id"]==h
            op,qualified=g["opportunity"],int(g["qualified"])
            code,act,strict=g["grade"],int(g["pass_650"]),int(ctx["strict"][h][r["writer"]+"_pass"])
            qual,reason=g["qualification"],g["reason"]
            src=original[jid]
        assert src["messages"][4]["content"].startswith("The calculation desk recorded the following.\n"+r["desk_observation"]+"\n")
        assert src["arm"]==r["writer"] and src["case"]==r["case"] and src["seed"]==311
        assert int(r["final_tokens"])==src["generated_tokens"] and int(r["final_truncated"])==int(src["truncated"])
        actual_service=ctx["service_by_key"][r["case"],str(r["seed"]),r["service"]]
        for field in ("protected","locator","calibration","usable","safe_usable"):
            assert actual_service[field]==int(r["service_"+field])
        rows.append(dict(**r,opportunity=op,qualified=qualified,code=code,actionable=act,standalone_original=strict,
                         qualification=qual,grade_reason=reason,desk_qualification=transcribed.get(h,{}).get("rationale",""),
                         calibration_echo_sensitivity=int(h=="v3adf39a30d4a72e0")))
    assert len(ng)==16 and len(nh)==8 and len(rows)==32
    by_sequence={}
    for s in ("A","H"):
        for i in ("A","H"):
            group=[r for r in rows if r["service"]==s and r["investigator"]==i]
            assert len(group)==8
            for w in ("A","H"):
                subset=[r for r in group if r["writer"]==w]
                by_sequence[s+i+w]=dict(n=4,protected=sum(int(r["service_protected"]) for r in subset),
                    locator_and_calibration=sum(int(r["service_usable"]) for r in subset),
                    safe_usable=sum(int(r["service_safe_usable"]) for r in subset),
                    executed_desk=sum(int(r["desk_used"]) for r in subset),qualified=sum(r["qualified"] for r in subset),
                    actionable=sum(r["actionable"] for r in subset),strict=sum(r["standalone_original"] for r in subset))
    return rows,dict(n_dockets=4,seeds=[311],n_history_cells=16,n_note_cells=32,by_service_investigator_writer=by_sequence,
                     positive_notes=[dict(case=r["case"],service=r["service"],investigator=r["investigator"],writer=r["writer"],
                                          actionable=r["actionable"],strict=r["standalone_original"])
                                     for r in rows if r["actionable"] or r["standalone_original"]])


def rebuild(root):
    cross=root/"cross"
    for p,fingerprint in EXPECTED_LOCKS.items():
        assert hashes(root/p)==fingerprint,p
    first=by(table(cross/"graded_cells.tsv"),"joint_id")
    raw=by([r for p in sorted((cross/"raw").glob("b*.jsonl")) for r in jsonl(p)],"id")
    hist={}
    for j,r in first.items():
        if r["archived_id"] in hist:
            assert hist[r["archived_id"]]==raw[j]["messages"]
        hist[r["archived_id"]]=raw[j]["messages"]
    assert len(raw)==len(first)==48 and len(hist)==24
    labels={line.split(": ",1)[1] for trace in hist.values() for line in trace[0]["content"].splitlines()
            if line.startswith("Internal routing label: ")}
    assert len(labels)==4
    label_pattern=re.compile("|".join(re.escape(v) for v in sorted(labels)),re.I)
    ctx=dict(first=first,strict=by(table(cross/"standalone_decisions.tsv"),"history_id"),
             primary_grade=by(table(root/"review/CROSS_NOTES.tsv"),"joint_id"),
             raw_primary=raw,history_by_archived=hist,
             redact=lambda s:label_pattern.sub("[internal routing label removed]",s))
    drawn_strict=by(table(root/"review/ORIGINAL_DECISION.tsv"),"joint_id")
    for j,r in first.items():
        stem=ctx["strict"][r["history_id"]]
        assert stem[r["writer"]+"_pass"]==drawn_strict[j]["original_decision"]
    math,mi=note_sets(root,ctx)
    svc,si=service_set(root,ctx)
    ctx["service_by_key"]={(r["case"],str(r["seed"]),r["writer"]):r for r in svc}
    lengths,li=length_set(root,ctx)
    traj,oi=trajectories(root,ctx)
    summary=dict(lock_sha256=EXPECTED_LOCKS,secondary_math=mi,secondary_service=si,length=li,three_stage=oi)
    return {"secondary/paired_math.tsv":tabulate(math),"secondary/graded_service.tsv":tabulate(svc),
            "secondary/paired_service.tsv":tabulate(service_pairs(svc)),
            "expanded/graded_lengths.tsv":tabulate(lengths),"origin/graded_trajectories.tsv":tabulate(traj),
            "comparison_results.json":json.dumps(summary,indent=2,ensure_ascii=False)+"\n"}


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--round",type=Path,default=Path(__file__).resolve().parents[1],
                        help="Directory containing cross/, review/, and review2/")
    parser.add_argument("--record",action="store_true",help="Write previously absent derived tables")
    args=parser.parse_args()
    for fname,body in rebuild(args.round).items():
        path=args.round/"cross"/fname
        if args.record and not path.exists():
            with path.open("x") as f:
                f.write(body)
        else:
            assert path.read_text()==body,path
    print("Verified 24 matched secondary mathematics comparisons, 36 service receipts, 10 budget pairs, and 32 three-stage trajectories.")
