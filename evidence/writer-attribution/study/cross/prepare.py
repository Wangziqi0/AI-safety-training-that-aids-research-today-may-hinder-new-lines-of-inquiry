"""Prepare the masked records and exact archived microbatches before acquisition."""
import hashlib
import itertools
import json
from pathlib import Path
import secrets
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT / "rounds/20261121_proof_handoff_submission/experiment"
STRONG = ROOT / "rounds/20261120_scientific_choice_and_recovery/strong"
CROSSED = ROOT / "coordination/20261121_handoff_attribution_preparation/crossed_handoffs.jsonl"
sys.path.insert(0, str(OLD))
from workflow import public_note


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def message_digest(messages):
    blob = json.dumps(messages, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def write_rows(path, rows):
    with path.open("x") as output:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False), file=output)


def prepare():
    originals = read_rows(OLD / "internal/handoff_input.jsonl")
    archive = read_rows(OLD / "internal/handoff_raw.jsonl")
    cross_list = read_rows(CROSSED)
    crossed = {r["history_id"]: r for r in cross_list}
    previous = {r["id"]: r for r in archive}
    assert len(originals) == len(previous) == len(archive) == len(cross_list) == len(crossed) == 24
    assert [r["id"] for r in originals] == [r["id"] for r in archive]
    assert {r["id"] for r in originals} == set(crossed)
    randomizer = secrets.SystemRandom()
    histories, allocation, batch_manifest = [], [], []
    batches = itertools.groupby(sorted(originals, key=lambda x: (x["seed"], x["arm"])),
                                key=lambda x: (x["seed"], x["arm"]))
    for index, ((seed, source_arm), group) in enumerate(batches, 1):
        inputs = list(group)
        assert len(inputs) == 4 and {r["case"] for r in inputs} == {"G1", "G2", "E1", "E2"}
        assert seed in (311, 617, 929) and source_arm in ("A", "H")
        name = f"b{index:02d}"
        requests = []
        for ordinal, r in enumerate(inputs):
            c, old_out = crossed[r["id"]], previous[r["id"]]
            assert all(old_out[k] == v for k, v in r.items())
            assert old_out["batch_size"] == 4 and old_out["effective_token_cap"] == 650
            assert c["history_arm"] == r["arm"] and {c["arm"], r["arm"]} == {"A", "H"}
            assert all(r[k] == c[k] for k in ("messages", "seed", "case", "max_new_tokens"))
            assert r["max_new_tokens"] == 650
            assert [m["role"] for m in r["messages"]] == ["user","assistant","user","assistant","user"]
            h_id = "h" + secrets.token_hex(8)
            transcript = [dict(role=m["role"], content=public_note(m["content"])) for m in r["messages"]]
            histories.append(dict(history_id=h_id, chronological_messages=transcript))
            for actual in (r, c):
                joint_id = "j" + secrets.token_hex(8)
                writer = actual["arm"]
                # The generator tokenizes only 'messages'. All metadata are outside the prompt.
                requests.append(dict(id=joint_id, history_id=h_id, case=r["case"], arm=writer,
                                     seed=seed, messages=actual["messages"], max_new_tokens=650))
                allocation.append(dict(joint_id=joint_id, history_id=h_id, archived_id=r["id"],
                                       prepared_id=actual["id"], case=r["case"], seed=seed,
                                       history_arm=source_arm, writer_arm=writer, batch=name,
                                       position=ordinal, messages_sha256=message_digest(r["messages"])))
        for arm in ("A", "H"):
            assert [a["messages"] for a in requests if a["arm"] == arm] == [r["messages"] for r in inputs]
        path = HERE / "inputs" / (name + ".jsonl")
        write_rows(path, requests)
        batch_manifest.append(dict(batch=name, seed=seed, history_arm=source_arm,
                                   original_order=[r["id"] for r in inputs],
                                   ordered_message_sha256=[message_digest(r["messages"]) for r in inputs],
                                   archived_context_tokens=[previous[r["id"]]["context_tokens"] for r in inputs],
                                   input_sha256=digest(path)))
    assert len({r["joint_id"] for r in allocation}) == 48
    assert len({r["history_id"] for r in histories}) == 24
    randomizer.shuffle(histories)
    randomizer.shuffle(allocation)
    write_rows(HERE / "blind/prehistory.jsonl", histories)
    write_rows(HERE / "private/allocation.jsonl", allocation)
    write_rows(HERE / "private/batches.jsonl", batch_manifest)


if __name__ == "__main__":
    prepare()
