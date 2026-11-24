"""Allocate opaque reader IDs once, then assemble blind records without displaying notes."""
import argparse
import json
import secrets
from exact import ROOT


def rows(name):
    return [json.loads(s) for s in (ROOT / name).read_text().splitlines() if s.strip()]


def write_new_jsonl(path, records):
    with path.open("x") as out:
        for row in records:
            print(json.dumps(row, ensure_ascii=False), file=out)


def allocate():
    rng = secrets.SystemRandom()
    note_keys = []
    for row in rows("internal/writer_input.jsonl"):
        note_keys.append(dict(note_id="t" + secrets.token_hex(8), writer_id=row["id"],
                              arm=row["arm"], seed=row["seed"], task=row["task"]))
    rng.shuffle(note_keys)
    recipients = []
    for task in ("T01", "T03", "T05", "T07"):
        for arm in ("A", "H", "ordinary"):
            key = next((r["note_id"] for r in note_keys if r["task"] == task and
                        r["seed"] == 617 and r["arm"] == arm), None)
            recipients.append(dict(recipient_id="r" + secrets.token_hex(8), note_id=key,
                                   arm=arm, seed=617 if key else None, task=task))
    rng.shuffle(recipients)
    assert len({r["note_id"] for r in note_keys}) == 72
    assert len({r["recipient_id"] for r in recipients}) == 12
    assert sum(r["note_id"] is None for r in recipients) == 4
    write_new_jsonl(ROOT / "internal/writer_allocation.jsonl", note_keys)
    write_new_jsonl(ROOT / "internal/recipient_allocation.jsonl", recipients)


def distribute():
    raw_rows = rows("internal/writer_raw.jsonl")
    assert len(raw_rows) == 72 and len({r["id"] for r in raw_rows}) == 72
    raw = {r["id"]: r for r in raw_rows}
    intake = {r["id"]: r for r in rows("internal/writer_input.jsonl")}
    assert set(raw) == set(intake)
    checkpoint = {}
    for row in raw_rows:
        for key in intake[row["id"]]:
            assert row[key] == intake[row["id"]][key]
        token = (row["arm"], row["seed"])
        expected = checkpoint.setdefault(token, row["checkpoint_sha256"])
        assert expected == row["checkpoint_sha256"]
        assert row["batch_size"] == 4 and row["effective_token_cap"] == 650
        assert row["generated_tokens"] == len(row["token_ids"])
        assert row["eos"] != row["truncated"]
    assert len(set(checkpoint.values())) == 9
    for task in ("T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08"):
        counts = {r["context_tokens"] for r in raw_rows if r["task"] == task}
        assert len(counts) == 1
    notes = []
    costs = []
    for key in rows("internal/writer_allocation.jsonl"):
        row = raw[key["writer_id"]]
        notes.append(dict(note_id=key["note_id"], task=key["task"], history_id=key["task"],
                          text=row["text"]))
        costs.append(dict(note_id=key["note_id"], context_tokens=row["context_tokens"],
                          tokens=row["generated_tokens"], truncated=row["truncated"],
                          eos=row["eos"], batch_size=row["batch_size"], cap=row["effective_token_cap"]))
    note_index = {r["note_id"]: r["text"] for r in notes}
    problems = {r["task"]: r["receiving_prompt"] for r in rows("public/problems.jsonl")}
    recipients = []
    for key in rows("internal/recipient_allocation.jsonl"):
        note = note_index.get(key["note_id"])
        folder = "No working note accompanied the public record." if note is None else (
            "A colleague supplied the following working note. You may use or replace it.\n\n" + note)
        recipients.append(dict(recipient_id=key["recipient_id"], task=key["task"],
                               prompt=problems[key["task"]] + "\n\n" + folder))
    write_new_jsonl(ROOT / "blind/writer_notes.jsonl", notes)
    write_new_jsonl(ROOT / "blind/writer_telemetry.jsonl", costs)
    write_new_jsonl(ROOT / "blind/recipient_packets.jsonl", recipients)
    return len(notes), len(recipients)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("effect", choices=["allocate", "distribute"])
    args = parser.parse_args()
    if args.effect == "allocate":
        allocate()
    else:
        print(distribute())
