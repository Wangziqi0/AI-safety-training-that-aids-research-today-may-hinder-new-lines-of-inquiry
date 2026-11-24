"""Build masked notes and receiving packets without printing any answer or arm assignment."""
import hashlib
import sys
from prepare import HERE, OLD, digest, public_note, read_rows, write_rows
from receiver_design import NO_NOTE, INSTRUCTIONS
from dockets import receiver_prompt


def mask(opportunity_lock, expected_hash):
    lock = opportunity_lock.read_bytes()
    assert hashlib.sha256(lock).hexdigest() == expected_hash
    outputs = [r for path in sorted((HERE / "raw").glob("b*.jsonl")) for r in read_rows(path)]
    assert len(outputs) == len({r["id"] for r in outputs}) == 48
    # The public packets have no archived IDs, recipe, seed, checkpoint, or model grouping.
    packets = [dict(joint_id=r["id"], history_id=r["history_id"],
                    public_note=public_note(r["text"]), hit_token_cap=r["truncated"])
               for r in sorted(outputs, key=lambda x: x["id"])]
    assert len({p["history_id"] for p in packets}) == 24
    assert all(sum(p["history_id"] == q["history_id"] for p in packets) == 2 for q in packets)
    write_rows(HERE / "blind/deliveries.jsonl", packets)
    old_records = {r["id"]: r for r in read_rows(OLD / "internal/handoff_raw.jsonl")}
    new_records = {r["id"]: r for r in outputs}
    # Only this mechanical dispatcher uses the receiving schedule. Its mapping is withheld
    # from recipients and graders. The primary policy allocation is not loaded.
    slots = read_rows(HERE / "private/receiver_allocation.jsonl")
    for row in slots:
        if row["source"] == "docket alone":
            note = NO_NOTE
        elif row["source"] == "archived original":
            note = public_note(old_records[row["history"]]["text"])
        else:
            note = public_note(new_records[row["joint_id"]]["text"])
        packet = dict(slot=row["slot"], prompt=receiver_prompt(row["case"], note) + "\n\n" + INSTRUCTIONS)
        write_rows(HERE / "blind/receivers" / (row["slot"] + ".jsonl"), [packet])
    print("Sealed masked notes:", len(packets), digest(HERE / "blind/deliveries.jsonl"))
    print("Sealed independent receiving packets:", len(slots))


if __name__ == "__main__":
    from pathlib import Path
    mask(Path(sys.argv[1]), sys.argv[2])
