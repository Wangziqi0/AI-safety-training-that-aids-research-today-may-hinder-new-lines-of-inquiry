"""Collect the independently masked seed-311 sequential assignment diagnostic."""
import argparse
import csv
from datetime import datetime, timezone
from fractions import Fraction
import json
from pathlib import Path
import secrets
import subprocess
import sys
import time

DIR=Path(__file__).resolve().parent
sys.path.insert(0,str(DIR.parent))
from prepare import HERE, OLD, ROOT, STRONG, digest, message_digest, public_note, read_rows, write_rows
from dockets import handoff_prompt
from desk import parse_query, tabulate

WRAP=STRONG.parent/"dialogue/infer_gpu0.sh"
ORIG=OLD/"internal"
NONE="No calculation was requested in operational terms; no output was generated."


def utc():
    return datetime.now(timezone.utc).isoformat()


def code(prefix):
    return prefix+secrets.token_hex(8)


def transcript(messages):
    return [dict(role=m["role"],content=public_note(m["content"])) for m in messages]


def once_json(path,row):
    with path.open("x") as f:
        json.dump(row,f,indent=2)
        f.write("\n")


def freeze():
    pri=json.loads((HERE/"FREEZE.json").read_text())
    old=[r for r in read_rows(ORIG/"scientific_input.jsonl") if r["seed"]==311]
    archived={r["id"]:r for r in read_rows(ORIG/"scientific_raw.jsonl") if r["seed"]==311}
    assert len(old)==len(archived)==8
    requests, route, note_schedule, block_order=[],[],[],[]
    for origin in ("A","H"):
        original_rows=[r for r in old if r["arm"]==origin]
        assert len(original_rows)==4
        original_order=[r["id"] for r in original_rows]
        b=next(b for b in pri["batches"] if b["seed"]==311 and b["history_arm"]==origin)
        assert original_order==b["original_order"]
        block_order.append(dict(first=origin,original_order=original_order,primary_file=b["batch"]))
        for r in original_rows:
            assert r["max_new_tokens"]==560 and len(r["messages"])==3
            src=archived[r["id"]]
            assert all(src[k]==v for k,v in r.items()) and src["batch_size"]==4
            for inv in ("A","H"):
                h=code("v") if inv!=origin else None
                q=code("e")
                out=dict(r,id=q,arm=inv)
                requests.append(out)
                route.append(dict(id=q,history_id=h,old_id=r["id"],case=r["case"],service=origin,investigator=inv,
                                  archived_investigator=inv==origin,source_messages_sha256=message_digest(r["messages"])))
                if h:
                    for writer in ("A","H"):
                        note_schedule.append(dict(joint_id=code("y"),history_id=h,investigator_id=q,case=r["case"],
                                                  service=origin,investigator=inv,writer=writer,old_id=r["id"]))
    assert len(route)==16 and len(note_schedule)==16
    write_rows(DIR/"investigator_inputs.jsonl",requests)
    write_rows(DIR/"private/investigators.jsonl",route)
    write_rows(DIR/"private/writers.jsonl",note_schedule)
    current=[ORIG/(n+".jsonl") for n in ("scientific_input","scientific_raw","service_input","service_raw","handoff_raw")]
    current += [OLD/"workflow.py",OLD/"desk.py",OLD/"dockets.py",OLD/"PROTOCOL.md",
                OLD/"blind/desk_log.jsonl",WRAP,STRONG/"infer_batch.py",STRONG/"runtime.py",
                HERE/"FREEZE.json",HERE/"primary_results.json",HERE/"standalone_results.json",HERE/"inputs/b02.jsonl",
                HERE/"raw/b02.jsonl",HERE.parent/"review/RUBRIC.md",HERE.parent/"review/ORIGINAL_DECISION.tsv"]
    identity=subprocess.check_output(["ssh","-o","BatchMode=yes","verification-host",
                     "cd $MODEL_STUDY/strong && "
                     "nvidia-smi --id=0 --query-gpu=name,uuid,memory.total,memory.free,utilization.gpu --format=csv,noheader && "
                     "ls -l inference-gpu0.lock && sha256sum infer_batch.py runtime.py weights/[AH]-311/adapter.pt"],text=True)
    assert "device-identifier-removed" in identity
    for item in pri["checkpoints"]:
        if item["arm"] in ("A","H") and item["seed"]==311:
            assert item["adapter_file_sha256"] in identity
    local=["PROTOCOL.md","study.py","investigator_inputs.jsonl","private/investigators.jsonl","private/writers.jsonl"]
    once_json(DIR/"FREEZE.json",dict(frozen_utc=utc(),phase="post-primary exploratory, prior to new origin investigator outputs",
              seed=311,blocks=block_order,n_new_investigations=8,n_archived_investigator_replays=8,n_new_final_notes=16,
              n_matched_natural_writer_device_controls=8,device=identity,
              previous_sha256={str(p.relative_to(ROOT)):digest(p) for p in current},
              diagnostic_sha256={p:digest(DIR/p) for p in local}))


def run(stage):
    f=json.loads((DIR/"FREEZE.json").read_text())
    assert all(digest(DIR/p)==v for p,v in f["diagnostic_sha256"].items())
    inp=DIR/(stage+"_inputs.jsonl")
    if stage=="writer":
        seal=json.loads((DIR/"WRITER_INPUTS.json").read_text())
        assert digest(inp)==seal["inputs_sha256"]
    dest=DIR/"raw"/(stage+".jsonl")
    assert not dest.exists()
    t,start=time.monotonic(),utc()
    with dest.with_suffix(".log").open("x") as log:
        proc=subprocess.run([str(WRAP),str(inp),str(dest)],stdout=log,stderr=subprocess.STDOUT)
    once_json(dest.with_suffix(".timing.json"),dict(start_utc=start,end_utc=utc(),elapsed_seconds=time.monotonic()-t,
                 returncode=proc.returncode,scope="full GPU0 wrapper, including dedicated lock and model load"))
    proc.check_returncode()
    print(stage,"completed",flush=True)


def classify():
    old=read_rows(ORIG/"scientific_raw.jsonl")
    original_desk={r["id"]:r for r in read_rows(OLD/"blind/desk_log.jsonl")}
    original={r["id"]:r for r in old}
    routes=read_rows(DIR/"private/investigators.jsonl")
    out={r["id"]:r for r in read_rows(DIR/"raw/investigator.jsonl")}
    requests={r["id"]:r for r in read_rows(DIR/"investigator_inputs.jsonl")}
    auto,packets,checks=[],[],[]
    for k in routes:
        r=out[k["id"]]
        assert all(r[x]==v for x,v in requests[r["id"]].items()) and r["effective_token_cap"]==560 and r["batch_size"]==4
        if k["archived_investigator"]:
            ref=original[k["old_id"]]
            fields=["text","token_ids","eos","truncated","context_tokens","effective_token_cap","batch_size","checkpoint_sha256"]
            checks.append(dict(id=k["old_id"],matched=all(ref[i]==r[i] for i in fields),
                               differing=[i for i in fields if ref[i]!=r[i]]))
            continue
        chronological=r["messages"]+[dict(role="assistant",content=r["text"])]
        match=[x for x in old if x["messages"]==r["messages"] and x["text"]==r["text"]]
        args=parse_query(r["text"])
        if match:
            receipts=[original_desk[m["id"]] for m in match]
            assert all(x["observation"]==receipts[0]["observation"] for x in receipts)
            first=receipts[0]
            pre=dict(mode=first["source"],arguments=first["arguments"],observation=first["observation"],basis="identical historical conversation and choice")
        elif args:
            pre=dict(mode="specified",arguments=args,observation=tabulate(k["case"],args),basis="original explicit CHECK parser")
        else:
            pre=dict(mode="requires_blind_plain_language",arguments=None,observation=None,basis="independent transcription required")
        auto.append(dict(history_id=k["history_id"],**pre))
        packets.append(dict(history_id=k["history_id"],chronological_messages=transcript(chronological),
                            desk_status=pre["mode"],parsed_arguments=pre["arguments"]))
    assert len(packets)==len(checks)==8
    write_rows(DIR/"private/automatic_desk.jsonl",auto)
    write_rows(DIR/"blind/desk_choices.jsonl",sorted(packets,key=lambda x:x["history_id"]))
    write_rows(DIR/"investigator_device_replay.jsonl",checks)
    print("Masked inquiry choices prepared:",len(packets),"; plain language needed:",
          sum(r["mode"]=="requires_blind_plain_language" for r in auto),"; device controls exact:",sum(r["matched"] for r in checks))


def desk_results(submitted):
    adjudications={r["history_id"]:r for r in read_rows(submitted)}
    auto={r["history_id"]:r for r in read_rows(DIR/"private/automatic_desk.jsonl")}
    expected={h for h,r in auto.items() if r["mode"]=="requires_blind_plain_language"}
    assert set(adjudications)==expected
    routes={r["history_id"]:r for r in read_rows(DIR/"private/investigators.jsonl") if r["history_id"]}
    raw={r["id"]:r for r in read_rows(DIR/"raw/investigator.jsonl")}
    hist,receipts={},[]
    for h,r in auto.items():
        k=routes[h]
        row=raw[k["id"]]
        if h in adjudications:
            decision=adjudications[h]
            mode=decision["mode"]
            if mode=="none":
                obs=NONE
            elif mode=="grid":
                obs=tabulate(k["case"],decision["arguments"])
            elif mode=="rank_loss":
                assert k["case"]=="E1"
                t,m=map(Fraction,decision["arguments"])
                assert t>0 and m>0 and m.denominator==1 and m%2==0
                obs=f"At t={t} and m={m} the exact loss is {max(t/m,m/t)}."
            elif mode=="residue_period":
                assert k["case"]=="G2"
                ds=list(map(int,decision["arguments"]))
                assert ds and set(ds)<=set([2,4,6])
                parts=[]
                for d in ds:
                    vals=[(m,(m+d)%9) for m in range(0,18,6)]
                    parts.append(f"d={d}, pairs (m mod 18, (m+d) mod 9) across one full period: {vals}.")
                if all((m+d)%9!=0 for d in ds for m in range(0,18,6)):
                    parts.append("No residue in either list has second component zero.")
                obs=" ".join(parts)
            else:
                raise ValueError("An independently identified new operation requires exact bounded implementation: "+str(decision))
            receipt=dict(history_id=h,mode=mode,arguments=decision.get("arguments"),observation=obs,
                         basis="independent masked transcription",quote=decision.get("quote",""),rationale=decision.get("rationale",""))
        else:
            receipt=r
        receipts.append(receipt)
        messages=row["messages"]+[dict(role="assistant",content=row["text"]),dict(role="user",content=handoff_prompt(receipt["observation"]))]
        hist[h]=messages
    write_rows(DIR/"desk_receipts.jsonl",receipts)
    write_rows(DIR/"blind/prehistory.jsonl",sorted((dict(history_id=h,chronological_messages=transcript(m)) for h,m in hist.items()),key=lambda x:x["history_id"]))
    writers=read_rows(DIR/"private/writers.jsonl")
    requests=[dict(id=w["joint_id"],history_id=w["history_id"],arm=w["writer"],seed=311,
                  case=w["case"],messages=hist[w["history_id"]],max_new_tokens=650) for w in writers]
    device_controls=read_rows(HERE/"inputs/b02.jsonl")
    requests+=device_controls
    assert len(requests)==24 and len({r["id"] for r in requests})==24
    write_rows(DIR/"writer_inputs.jsonl",requests)
    once_json(DIR/"WRITER_INPUTS.json",dict(time_utc=utc(),inputs_sha256=digest(DIR/"writer_inputs.jsonl"),
        prehistory_sha256=digest(DIR/"blind/prehistory.jsonl"),desk_sha256=digest(DIR/"desk_receipts.jsonl"),
        adjudication_sha256=digest(submitted),primary_seed311_h_origin_input_sha256=digest(HERE/"inputs/b02.jsonl"),
        new_histories=8,new_deliveries=16,device_controls=8))


def mask(lock,certificate):
    assert digest(lock)==certificate
    out={r["id"]:r for r in read_rows(DIR/"raw/writer.jsonl")}
    sched=read_rows(DIR/"private/writers.jsonl")
    cards=[]
    for w in sched:
        r=out[w["joint_id"]]
        cards.append(dict(joint_id=r["id"],history_id=w["history_id"],public_note=public_note(r["text"]),
                          hit_token_cap=r["truncated"]))
    assert len(cards)==16 and len(out)==24
    write_rows(DIR/"blind/notes.jsonl",sorted(cards,key=lambda x:x["joint_id"]))
    print("Released 16 blinded new final-writer notes and withheld eight device-control copies.")


if __name__=="__main__":
    cmd=sys.argv[1]
    if cmd=="freeze": freeze()
    elif cmd in ("investigator","writer"): run(cmd)
    elif cmd=="classify": classify()
    elif cmd=="desk": desk_results(Path(sys.argv[2]))
    elif cmd=="mask": mask(Path(sys.argv[2]),sys.argv[3])
    else: raise ValueError(cmd)
