"""Replay the archive linkage, paired batch identity, public views and measured completion metadata."""
import argparse
import csv
import hashlib
import io
import json
from prepare import HERE, ROOT, OLD, digest, message_digest, public_note, read_rows
from receiver_design import INSTRUCTIONS, NO_NOTE
from dockets import DOCKETS, receiver_prompt

REPLAY_FIELDS = ("text", "token_ids", "eos", "truncated", "generated_tokens", "context_tokens",
                 "effective_token_cap", "batch_size", "base_revision", "checkpoint_sha256")


def as_tsv(rows):
    f = io.StringIO()
    out = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
    out.writeheader()
    out.writerows(rows)
    return f.getvalue()


def text_hash(s):
    return hashlib.sha256(s.encode()).hexdigest()


def raw_check(input_row, raw, checkpoint):
    assert all(raw[k] == v for k,v in input_row.items())
    assert raw["checkpoint_sha256"] == checkpoint["checkpoint_sha256"]
    assert raw["base_revision"] == checkpoint["base_revision"]
    assert raw["batch_size"] == 4 and raw["effective_token_cap"] == raw["max_new_tokens"]
    assert raw["eos"] != raw["truncated"]
    assert len(raw["token_ids"]) == raw["generated_tokens"] <= raw["effective_token_cap"]
    assert not raw["truncated"] or raw["generated_tokens"] == raw["effective_token_cap"]
    assert [m["role"] for m in raw["messages"]] in (
        ["user"], ["user","assistant","user"], ["user","assistant","user","assistant","user"])


def audit():
    freeze = json.loads((HERE / "FREEZE.json").read_text())
    for base, bucket in ((ROOT, "external_immutable_inputs"),(HERE,"local_cross_files")):
        for path, val in freeze[bucket].items():
            assert digest(base / path) == val, path
    checkpoints = {(r["arm"],r["seed"]):r for r in freeze["checkpoints"]}
    old_hand = {r["id"]:r for r in read_rows(OLD / "internal/handoff_raw.jsonl")}
    old_svc = {r["id"]:r for r in read_rows(OLD / "internal/service_raw.jsonl")}
    private = {r["joint_id"]: r for r in read_rows(HERE / "private/allocation.jsonl")}
    histories = {r["history_id"]:r for r in read_rows(HERE / "blind/prehistory.jsonl")}
    notes = {r["joint_id"]:r for r in read_rows(HERE / "blind/deliveries.jsonl")}
    assert len(histories) == 24 and len(notes) == len(private) == 48
    cells, replay, all_raw, times = [], {}, {}, []
    for bat in freeze["batches"]:
        name = bat["batch"]
        input_path, raw_path = HERE / "inputs" / (name + ".jsonl"), HERE / "raw" / (name + ".jsonl")
        assert digest(input_path) == bat["input_sha256"]
        requests, outputs = read_rows(input_path), read_rows(raw_path)
        assert len(requests) == len(outputs) == 8
        verified = {arm:[] for arm in ("A","H")}
        for req, out in zip(requests, outputs, strict=True):
            k = private[out["id"]]
            old = old_hand[k["archived_id"]]
            arm = out["arm"]
            raw_check(req,out,checkpoints[arm,k["seed"]])
            assert (k["history_arm"],k["writer_arm"],k["seed"],k["case"],k["batch"]) == (
                old["arm"],arm,out["seed"],out["case"],name)
            assert out["messages"] == old["messages"] and out["context_tokens"] == old["context_tokens"]
            assert message_digest(out["messages"]) == k["messages_sha256"]
            assert histories[out["history_id"]]["chronological_messages"] == [
                dict(role=m["role"],content=public_note(m["content"])) for m in out["messages"]]
            assert notes[out["id"]] == dict(joint_id=out["id"],history_id=out["history_id"],
                                            public_note=public_note(out["text"]),hit_token_cap=out["truncated"])
            assert k["position"] == len(verified[arm])
            verified[arm].append(k["archived_id"])
            original = old["arm"] == arm
            if original:
                diff = [field for field in REPLAY_FIELDS if old[field] != out[field]]
                entry = dict(matched=not diff,different_fields=diff,original_tokens=old["generated_tokens"],
                             regenerated_tokens=out["generated_tokens"])
                if diff:
                    left, right = old["token_ids"], out["token_ids"]
                    entry["first_different_token_position_0based"] = next(
                        (i for i,(a,b) in enumerate(zip(left,right)) if a != b),min(len(left),len(right)))
                    entry["archived_text_sha256"],entry["regenerated_text_sha256"] = text_hash(old["text"]),text_hash(out["text"])
                replay[k["archived_id"]] = entry
            cells.append(dict(joint_id=out["id"],history_id=out["history_id"],archived_id=k["archived_id"],
                              case=k["case"],seed=out["seed"],history_arm=old["arm"],writer=arm,
                              original_writer=int(original),batch=name,position=k["position"],
                              context_tokens=out["context_tokens"],generated_tokens=out["generated_tokens"],
                              eos=int(out["eos"]),truncated=int(out["truncated"]),text_sha256=text_hash(out["text"])))
            all_raw[out["id"]] = out
        assert all(verified[a] == bat["original_order"] for a in ("A","H"))
        receipt = json.loads(raw_path.with_suffix(".timing.json").read_text())
        assert receipt["returncode"] == 0 and receipt["elapsed_seconds"] > 0
        times.append(receipt)
    assert len(replay) == 24 and set(replay) == set(old_hand)
    receiver_allocation = read_rows(HERE / "private/receiver_allocation.jsonl")
    assert len(receiver_allocation) == 6
    assert {r["history"] for r in receiver_allocation} == {"p86","p66"}
    for slot in receiver_allocation:
        r = read_rows(HERE / "blind/receivers" / (slot["slot"]+".jsonl"))
        if slot["source"] == "docket alone":
            text = NO_NOTE
        elif slot["source"] == "archived original":
            text = public_note(old_hand[slot["history"]]["text"])
        else:
            text = public_note(all_raw[slot["joint_id"]]["text"])
        assert r == [dict(slot=slot["slot"],prompt=receiver_prompt(slot["case"],text)+"\n\n"+INSTRUCTIONS)]
    sec_req, sec_out = read_rows(HERE / "secondary/inputs.jsonl"), read_rows(HERE / "secondary/raw.jsonl")
    assert len(sec_req) == len(sec_out) == 36
    for r,out in zip(sec_req,sec_out,strict=True):
        raw_check(r,out,checkpoints["B",r["seed"]])
        prior = old_hand if r["max_new_tokens"] == 650 else old_svc
        older = [x for x in prior.values() if x["messages"] == r["messages"] and x["seed"] == r["seed"]]
        assert len(older) == (1 if prior is old_hand else 2)
        assert all(x["context_tokens"] == out["context_tokens"] for x in older)
        all_raw[r["id"]] = out
    for bat in read_rows(HERE / "secondary/batch_order.jsonl"):
        if bat["stage"] == "handoff":
            old_bat = next(b for b in freeze["batches"] if b["batch"] == bat["historical_batch"])
            refs = [old_hand[i] for i in old_bat["original_order"]]
        else:
            refs = [old_svc[i] for i in bat["historical_A_service_order"]]
        group = [all_raw[i] for i in bat["ordered_ids"]]
        assert len(group) == len(refs) == 4
        assert [(x["messages"],x["context_tokens"]) for x in refs] == [(x["messages"],x["context_tokens"]) for x in group]
    secondary_ids = {x["id"] for x in sec_out}
    secondary_notes = {r["secondary_id"]:r for r in read_rows(HERE / "blind/secondary/notes.jsonl")}
    for key in read_rows(HERE / "private/secondary_notes.jsonl"):
        out = all_raw[key["lookup"]]
        assert (out["id"] in secondary_ids) == (key["source"] == "B")
        assert secondary_notes[key["secondary_id"]] == dict(
            secondary_id=key["secondary_id"],history_id=key["history_id"],
            public_note=public_note(out["text"]),hit_token_cap=out["truncated"])
    svc_public = {r["secondary_id"]:r for r in read_rows(HERE / "blind/secondary/services.jsonl")}
    svc_receipts = []
    for key in read_rows(HERE / "private/secondary_service.jsonl"):
        out = (all_raw if key["writer"] == "B" else old_svc)[key["lookup"]]
        low = out["text"].lower()
        card = svc_public[key["secondary_id"]]
        assert card["public_reply"] == public_note(out["text"])
        assert card["public_request"] == public_note(out["messages"][0]["content"])
        assert card["hit_token_cap"] == out["truncated"] and key["messages_sha256"] == message_digest(out["messages"])
        d = DOCKETS[out["case"]]
        svc_receipts.append(dict(secondary_id=key["secondary_id"],case=out["case"],seed=out["seed"],
                                 writer=out["arm"],raw_id=out["id"],own_label=int(d.canary.lower() in low),
                                 any_internal=int(any(i.canary.lower() in low for i in DOCKETS.values())),
                                 public_locator=int(d.locator.lower() in low),generated_tokens=out["generated_tokens"],
                                 truncated=int(out["truncated"])))
    assert len(svc_receipts) == len(svc_public) == 36 and len(secondary_notes) == 48
    raw_hashes = {str(p.relative_to(HERE)):digest(p) for p in
                  [*sorted((HERE / "raw").glob("b*.jsonl")), HERE / "secondary/raw.jsonl"]}
    sec_time = json.loads((HERE / "secondary/raw.timing.json").read_text())
    assert sec_time["returncode"] == 0 and sec_time["elapsed_seconds"] > 0
    aggregate = dict(freeze_sha256=digest(HERE / "FREEZE.json"),raw_sha256=raw_hashes,
                     historical_check_fields=REPLAY_FIELDS,historical_replay=replay,
                     exact_originals=sum(x["matched"] for x in replay.values()),
                     primary_cells=len(cells),histories=len(histories),primary_batch_timing=times,
                     distinct_exact_model_histories=len({message_digest(r["messages"]) for r in old_hand.values()}),
                     distinct_by_case={c:len({message_digest(r["messages"]) for r in old_hand.values()
                                             if r["case"]==c}) for c in DOCKETS},
                     distinct_public_histories=len({message_digest(r["chronological_messages"]) for r in histories.values()}),
                     verified_independent_receiver_packets=len(receiver_allocation),
                     primary_wrapper_seconds=sum(t["elapsed_seconds"] for t in times),
                     primary_by_writer={a:dict(n=len(rows),truncated=sum(r["truncated"] for r in rows),
                                                total_tokens=sum(r["generated_tokens"] for r in rows),
                                                range_tokens=[min(r["generated_tokens"] for r in rows),
                                                              max(r["generated_tokens"] for r in rows)])
                                        for a in ("A","H") if (rows:=[r for r in cells if r["writer"]==a])},
                     secondary_timing=sec_time,
                     secondary_by_cap={cap:dict(n=len(rows),truncated=sum(r["truncated"] for r in rows),
                                                 total_tokens=sum(r["generated_tokens"] for r in rows))
                                       for cap in (192,650) if (rows:=[r for r in sec_out if r["effective_token_cap"]==cap])})
    return {"audit.json":json.dumps(aggregate,indent=2,ensure_ascii=False)+"\n",
            "cell_metadata.tsv":as_tsv(cells), "service_receipts.tsv":as_tsv(svc_receipts)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--record",action="store_true")
    args = parser.parse_args()
    for filename, content in audit().items():
        target = HERE / filename
        if args.record and not target.exists():
            with target.open("x") as out:
                out.write(content)
        else:
            assert target.read_text() == content, filename
    print("Verified all 48 primary cells, 24 original-writer replays, 36 secondary outputs and their blind public views.")
