"""Prepare and mask separate field-level-protection diagnostics and hidden reference cards."""
import secrets
import sys
from pathlib import Path
from prepare import HERE, OLD, message_digest, public_note, read_rows, write_rows

SEC = HERE / "secondary"


def identifier(prefix):
    return prefix + secrets.token_hex(8)


def make():
    handoffs = read_rows(OLD / "internal/handoff_input.jsonl")
    services = read_rows(OLD / "internal/service_input.jsonl")
    historical = {r["id"]:r for r in handoffs}
    by_service = {(r["case"],r["seed"],r["arm"]):r for r in services}
    requests, anchors, service_anchors, batch_order = [], [], [], []
    for bat in read_rows(HERE / "private/batches.jsonl"):
        originals = [historical[i] for i in bat["original_order"]]
        primary = read_rows(HERE / "inputs" / (bat["batch"] + ".jsonl"))
        group = []
        for old in originals:
            source_writer = [r for r in primary if r["messages"] == old["messages"] and r["arm"] == old["arm"]]
            assert len(source_writer) == 1
            anchor = source_writer[0]
            b = dict(anchor, id=identifier("q"), arm="B")
            requests.append(b)
            group.append(b["id"])
            for row, origin in ((b,"B"),(anchor,"regenerated original")):
                anchors.append(dict(secondary_id=identifier("n"), history_id=b["history_id"],
                                    lookup=row["id"], source=origin))
        batch_order.append(dict(stage="handoff", historical_batch=bat["batch"], ordered_ids=group))
        if bat["history_arm"] != "A":
            continue
        group = []
        for old in originals:
            a = by_service[(old["case"], old["seed"], "A")]
            h = by_service[(old["case"], old["seed"], "H")]
            assert a["messages"] == h["messages"] and a["max_new_tokens"] == h["max_new_tokens"] == 192
            b = dict(a, id=identifier("q"), arm="B")
            requests.append(b)
            group.append(b["id"])
            for row in (a,h,b):
                service_anchors.append(dict(secondary_id=identifier("s"), lookup=row["id"],
                                            case=row["case"], seed=row["seed"], writer=row["arm"],
                                            messages_sha256=message_digest(row["messages"])))
        batch_order.append(dict(stage="service", seed=bat["seed"], historical_A_service_order=bat["original_order"],
                                ordered_ids=group))
    assert len(requests) == 36 and len(anchors) == 48 and len(service_anchors) == 36
    write_rows(SEC / "inputs.jsonl", requests)
    write_rows(SEC / "batch_order.jsonl", batch_order)
    for name, rows in (("secondary_notes",anchors),("secondary_service",service_anchors)):
        secrets.SystemRandom().shuffle(rows)
        write_rows(HERE / "private" / (name + ".jsonl"), rows)


def mask():
    primary = {r["id"]:r for p in sorted((HERE / "raw").glob("b*.jsonl")) for r in read_rows(p)}
    b = {r["id"]:r for r in read_rows(SEC / "raw.jsonl")}
    original = {r["id"]:r for r in read_rows(OLD / "internal/service_raw.jsonl")}
    assert len(b) == 36 and len(primary) == 48 and len(original) == 24
    notes = []
    for key in read_rows(HERE / "private/secondary_notes.jsonl"):
        r = (b if key["source"] == "B" else primary)[key["lookup"]]
        notes.append(dict(secondary_id=key["secondary_id"],history_id=key["history_id"],
                          public_note=public_note(r["text"]),hit_token_cap=r["truncated"]))
    services = []
    for key in read_rows(HERE / "private/secondary_service.jsonl"):
        r = (b if key["writer"] == "B" else original)[key["lookup"]]
        message = r["messages"][0]["content"]
        services.append(dict(secondary_id=key["secondary_id"],public_request=public_note(message),
                             public_reply=public_note(r["text"]),hit_token_cap=r["truncated"]))
    write_rows(HERE / "blind/secondary/notes.jsonl", sorted(notes,key=lambda r:r["secondary_id"]))
    write_rows(HERE / "blind/secondary/services.jsonl", sorted(services,key=lambda r:r["secondary_id"]))


if __name__ == "__main__":
    {"prepare":make,"mask":mask}[sys.argv[1]]()
