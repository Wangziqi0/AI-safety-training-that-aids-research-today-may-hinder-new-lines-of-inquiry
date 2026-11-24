"""Verify the full three-stage source chain and reconstruct 32 mechanical trajectory rows."""
import argparse
import csv
import json
from pathlib import Path
import sys

DIR=Path(__file__).resolve().parent
sys.path.insert(0,str(DIR.parent))
from audit import REPLAY_FIELDS, as_tsv, raw_check
from prepare import HERE, OLD, ROOT, digest, message_digest, public_note, read_rows
from dockets import handoff_prompt


def keyed(rows,key):
    indexed={r[key]:r for r in rows}
    assert len(indexed)==len(rows)
    return indexed


def tsv(path):
    with path.open() as f:
        return list(csv.DictReader(f,delimiter="\t"))


def verify():
    frozen=json.loads((DIR/"FREEZE.json").read_text())
    for base,key in ((ROOT,"previous_sha256"),(DIR,"diagnostic_sha256")):
        for path,val in frozen[key].items():
            assert digest(base/path)==val,path
    checkpoints={(r["arm"],r["seed"]):r for r in json.loads((HERE/"FREEZE.json").read_text())["checkpoints"]}
    archive_sci=keyed(read_rows(OLD/"internal/scientific_raw.jsonl"),"id")
    archive_serv=keyed(read_rows(OLD/"internal/service_raw.jsonl"),"id")
    archive_math=keyed(read_rows(OLD/"internal/handoff_raw.jsonl"),"id")
    archive_desk=keyed(read_rows(OLD/"blind/desk_log.jsonl"),"id")
    service_actions=keyed(tsv(OLD/"donor_results.tsv"),"id")
    primary_keys=read_rows(HERE/"private/allocation.jsonl")
    primary_311={(k["archived_id"],k["writer_arm"]):k for k in primary_keys if k["seed"]==311}
    prior_out=keyed([r for b in ("b01","b02") for r in read_rows(HERE/"raw"/(b+".jsonl"))],"id")
    new_invest=keyed(read_rows(DIR/"raw/investigator.jsonl"),"id")
    new_final=keyed(read_rows(DIR/"raw/writer.jsonl"),"id")
    inv_req=keyed(read_rows(DIR/"investigator_inputs.jsonl"),"id")
    wr_req=keyed(read_rows(DIR/"writer_inputs.jsonl"),"id")
    inv_sched=read_rows(DIR/"private/investigators.jsonl")
    wr_sched={(r["history_id"],r["writer"]):r for r in read_rows(DIR/"private/writers.jsonl")}
    desk=keyed(read_rows(DIR/"desk_receipts.jsonl"),"history_id")
    blind_prefix=keyed(read_rows(DIR/"blind/prehistory.jsonl"),"history_id")
    blind_notes=keyed(read_rows(DIR/"blind/notes.jsonl"),"joint_id")
    generator_fields={}
    for run,ref in ((new_invest,inv_req),(new_final,wr_req)):
        assert set(run)==set(ref)
        for k,row in run.items():
            raw_check(ref[k],row,checkpoints[(row["arm"],311)])
    control_ids={k for k in new_final if k in prior_out}
    assert control_ids=={r["id"] for r in read_rows(HERE/"inputs/b02.jsonl")}
    assert len(control_ids)==8 and len(new_invest)==16 and len(new_final)==24
    for k in control_ids:
        generator_fields[k]=[v for v in REPLAY_FIELDS if new_final[k][v]!=prior_out[k][v]]
    natural_replays={}
    rows=[]
    for seq in inv_sched:
        ii=seq["id"]
        origin,invest=seq["service"],seq["investigator"]
        old_id=seq["old_id"]
        science=new_invest[ii]
        service=archive_serv[old_id]
        svc=service_actions[old_id]
        old_science=archive_sci[old_id]
        assert science["messages"]==old_science["messages"]
        assert science["messages"][:2]==[service["messages"][0],dict(role="assistant",content=service["text"])]
        if origin==invest:
            natural_replays[old_id]=[v for v in REPLAY_FIELDS if science[v]!=old_science[v]]
            receipt=archive_desk[old_id]
            mode=receipt["source"]
            prefix=archive_math[old_id]["messages"]
            scientific_out=old_science
        else:
            receipt=desk[seq["history_id"]]
            mode=receipt["mode"]
            scientific_out=science
            prefix=science["messages"]+[dict(role="assistant",content=science["text"]),
                                       dict(role="user",content=handoff_prompt(receipt["observation"]))]
            assert blind_prefix[seq["history_id"]]["chronological_messages"]==[
                dict(role=m["role"],content=public_note(m["content"])) for m in prefix]
        for writer in ("A","H"):
            if origin==invest:
                link=primary_311[old_id,writer]
                note=prior_out[link["joint_id"]]
                h=link["history_id"]
            else:
                h=seq["history_id"]
                link=wr_sched[h,writer]
                note=new_final[link["joint_id"]]
                assert blind_notes[note["id"]]==dict(joint_id=note["id"],history_id=h,public_note=public_note(note["text"]),
                                                     hit_token_cap=note["truncated"])
            assert note["messages"]==prefix
            rows.append(dict(case=seq["case"],seed=311,service=origin,investigator=invest,writer=writer,
                             historical_service_id=old_id,service_tokens=service["generated_tokens"],
                             service_protected=int(svc["raw_protected"]),service_locator=int(svc["public_locator"]),
                             service_calibration=int(svc["calibration_correct"]),service_usable=int(svc["usable_public"]),
                             service_safe_usable=int(svc["safe_usable"]),investigator_id=ii,
                             investigator_tokens=scientific_out["generated_tokens"],investigator_truncated=int(scientific_out["truncated"]),
                             desk_used=int(mode!="none"),desk_mode=mode,desk_arguments=json.dumps(receipt["arguments"]),
                             desk_observation=receipt["observation"],history_id=h,history_messages_sha256=message_digest(prefix),
                             final_id=link["joint_id"],final_tokens=note["generated_tokens"],final_truncated=int(note["truncated"]),
                             final_source="new GPU0" if origin!=invest else "archived controlled GPU1 comparison"))
    rows.sort(key=lambda r:(r["case"],r["service"],r["investigator"],r["writer"]))
    assert len(rows)==len({tuple(r[k] for k in ("case","service","investigator","writer")) for r in rows})==32
    for src in ("A","H"):
        ordered=next(b["original_order"] for b in frozen["blocks"] if b["first"]==src)
        for inv in ("A","H"):
            found=[s for s in inv_sched if s["service"]==src and s["investigator"]==inv]
            assert [s["old_id"] for s in found]==ordered
            if src!=inv:
                for writer in ("A","H"):
                    newgroup=[w for w in wr_sched.values() if w["service"]==src and w["investigator"]==inv and w["writer"]==writer]
                    assert [w["old_id"] for w in newgroup]==ordered
    info=dict(freeze_sha256=digest(DIR/"FREEZE.json"),writer_inputs=digest(DIR/"WRITER_INPUTS.json"),
              investigator_output_sha256=digest(DIR/"raw/investigator.jsonl"),
              writer_output_sha256=digest(DIR/"raw/writer.jsonl"),
              natural_investigator_device_exact=sum(not v for v in natural_replays.values()),
              natural_investigator_device_mismatches={k:v for k,v in natural_replays.items() if v},
              final_device_control_exact=sum(not v for v in generator_fields.values()),
              final_device_control_mismatches={k:v for k,v in generator_fields.items() if v},
              archived_dockets=4,fitting_seeds=1,scientific_histories=16,final_cells=32,
              complete_distinct_text_histories=len({r["history_messages_sha256"] for r in rows}),
              new_investigator_runs=8,additional_historical_investigator_replays=8,
              new_final_notes=16,additional_historical_final_device_controls=8,
              investigator_timing=json.loads((DIR/"raw/investigator.timing.json").read_text()),
              final_timing=json.loads((DIR/"raw/writer.timing.json").read_text()))
    assert info["investigator_timing"]["returncode"]==info["final_timing"]["returncode"]==0
    return {"trajectory_stages.tsv":as_tsv(rows),"device_and_inputs.json":json.dumps(info,indent=2)+"\n"}


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--record",action="store_true")
    args=ap.parse_args()
    for name,data in verify().items():
        p=DIR/name
        if args.record and not p.exists():
            with p.open("x") as f:
                f.write(data)
        else:
            assert p.read_text()==data,name
    print("Verified complete service, investigation, tool, and writing path for all 32 cells.")
