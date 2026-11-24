"""Replay the reported transfer comparisons without generating model text or contacting a service."""
import csv
import hashlib
import json
import tempfile
from pathlib import Path

from analyze import main as make_tables
from exact import ROOT, DATA, scientific_references
from mask import rows

PRIMARY_GRADES = "82d9a374b800d4dcc085bd4b0a3149e21f202ea4d82145d7e5bd50e18f8aedb3"
SECOND_GRADES = "30a2c6fe2fe2310fe3209ff8b5bb85592d85361c8e0d357dd851c838db2dd570"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_tsv(path):
    with path.open(newline="") as data:
        return list(csv.DictReader(data, delimiter="\t"))


def reading_sensitivity(official, second, cases):
    selected = [r for r in official if r["task"] in cases]
    by_arm = {}
    for arm in ("A", "H", "B"):
        pairs = [(int(row["actionable"]), int(second[row["note_id"]]["actionable"]))
                 for row in selected if row["arm"] == arm]
        by_arm[arm] = dict(n=len(pairs), primary=sum(x for x, y in pairs),
                           second=sum(y for x, y in pairs), either=sum(max(t) for t in pairs),
                           both=sum(min(t) for t in pairs))
    return dict(arms=by_arm, actionable_agreement=sum(row["actionable"] == second[row["note_id"]]["actionable"]
                                                      for row in selected),
                exact_agreement=sum(row["full_exact"] == second[row["note_id"]]["full_exact"]
                                    for row in selected), notes=len(selected),
                smallest_A_minus_H=by_arm["A"]["both"] - by_arm["H"]["either"],
                largest_A_minus_H=by_arm["A"]["either"] - by_arm["H"]["both"],
                A_H_paired_denominator=by_arm["A"]["n"])


def replay():
    for entry in (ROOT / "FROZEN.sha256").read_text().splitlines():
        expected, name = entry.split(maxsplit=1)
        assert digest(ROOT / name) == expected, name
    reference = json.loads((ROOT / "ordinary/reference.json").read_text())
    assert json.loads(json.dumps(scientific_references())) == reference
    source = json.loads((ROOT / "ordinary/source_replay.json").read_text())
    assert source["rows"] == 103 and source["derived_csv_sha256"] == digest(DATA)

    inputs = {r["id"]: r for r in rows("internal/writer_input.jsonl")}
    raw = {r["id"]: r for r in rows("internal/writer_raw.jsonl")}
    notes = {r["note_id"]: r for r in rows("blind/writer_notes.jsonl")}
    keys = {r["note_id"]: r for r in rows("internal/writer_allocation.jsonl")}
    assert len(inputs) == len(raw) == len(notes) == len(keys) == 72
    assert inputs.keys() == raw.keys() and notes.keys() == keys.keys()
    fingerprints = {}
    for note_id, key in keys.items():
        r = raw[key["writer_id"]]
        assert all(r[k] == v for k, v in inputs[r["id"]].items())
        assert notes[note_id]["task"] == key["task"] == r["task"] and notes[note_id]["text"] == r["text"]
        assert r["generated_tokens"] == len(r["token_ids"]) and r["effective_token_cap"] == 650
        assert r["eos"] != r["truncated"] and r["batch_size"] == 4
        assert r["checkpoint_sha256"] == fingerprints.setdefault((r["arm"], r["seed"]), r["checkpoint_sha256"])
    assert len(set(fingerprints.values())) == 9
    for task in reference:
        matched = [r for r in raw.values() if r["task"] == task]
        assert len(matched) == 9 and all(r["messages"] == matched[0]["messages"] for r in matched)
        assert len({r["context_tokens"] for r in matched}) == 1
    receipt = json.loads((ROOT / "ACQUISITION.json").read_text())
    assert digest(ROOT / "blind/writer_notes.jsonl") == receipt["pooled_notes_sha256"]
    assert digest(ROOT / "blind/recipient_packets.jsonl") == receipt["pooled_recipient_packets_sha256"]
    primary_file = ROOT.parent / "review/HELDOUT_NOTES.tsv"
    independent_file = ROOT.parent / "review2/HELDOUT_NOTES.tsv"
    assert digest(independent_file) == SECOND_GRADES
    with tempfile.TemporaryDirectory() as temp:
        target = Path(temp)
        make_tables(primary_file, PRIMARY_GRADES, target)
        files = ("writer_scores.tsv", "paired_comparisons.tsv", "arm_summary.tsv")
        for name in files:
            assert (target / name).read_bytes() == (ROOT / name).read_bytes(), name
    official = read_tsv(ROOT / "writer_scores.tsv")
    second = {r["note_id"]: r for r in read_tsv(independent_file)}
    assert set(second) == set(notes)
    return dict(status="EXACT_PRIMARY_REPLAY_PASSED", sources=8, writer_notes=len(notes),
                selected_receiver_packets=len(rows("blind/recipient_packets.jsonl")),
                original_source_sha256=source["source_sha256"], team_csv_sha256=digest(DATA),
                matched_scientific_inputs=True, checkpoint_count=9,
                primary_grade_sha256=PRIMARY_GRADES, independent_grade_sha256=SECOND_GRADES,
                offline_regenerated_tables={name: digest(ROOT / name) for name in files},
                heldout_reader_sensitivity={
                    "all": reading_sensitivity(official, second, set(reference)),
                    "math": reading_sensitivity(official, second, {t for t in reference if t < "T05"}),
                    "data": reading_sensitivity(official, second, {t for t in reference if t >= "T05"})})


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2))
