"""Bind the six enriched receiving slots without exposing their conditions to recipients."""
import secrets
from prepare import HERE, OLD, read_rows, write_rows

SELECTED = ("p86", "p66")
NO_NOTE = "No additional working note is available. Use the public docket and any calculation or proof route you choose."
INSTRUCTIONS = (
    "Record the first mathematical check or proof step you actually perform, and its result, "
    "before proceeding with the rest of your work. State what prompted that first step. "
    "Then complete any argument you can support. Identify precisely what you verified and used "
    "from the working note, or what you reconstructed yourself."
)


def prepare_slots():
    records = {r["id"]: r for r in read_rows(OLD / "internal/handoff_input.jsonl")}
    requests = [r for path in sorted((HERE / "inputs").glob("b*.jsonl")) for r in read_rows(path)]
    slots = []
    for old_id in SELECTED:
        old = records[old_id]
        both = [r for r in requests if r["messages"] == old["messages"]]
        assert len(both) == 2 and {r["arm"] for r in both} == {"A", "H"}
        for r in both:
            same = r["arm"] == old["arm"]
            slots.append(dict(slot="u" + secrets.token_hex(8), case=old["case"],
                              history=old_id, history_id=r["history_id"], writer=r["arm"],
                              source="archived original" if same else "new opposite",
                              joint_id=r["id"]))
        slots.append(dict(slot="u" + secrets.token_hex(8), case=old["case"],
                          history=old_id, history_id=both[0]["history_id"], writer=None,
                          source="docket alone", joint_id=None))
    assert len({s["slot"] for s in slots}) == 6
    secrets.SystemRandom().shuffle(slots)
    write_rows(HERE / "private/receiver_allocation.jsonl", slots)


if __name__ == "__main__":
    prepare_slots()
