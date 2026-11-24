"""Verify the prospective common-cap rerun and mask it for a second scientific reading."""
import hashlib
import json
from pathlib import Path
import secrets


def rows(path):
    return [json.loads(v) for v in path.read_text().splitlines() if v.strip()]


def save(path, data):
    with path.open("x") as stream:
        stream.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in data))


def mask(base):
    old = {r["id"]:r for r in rows(base/"short_raw.jsonl")}
    new = {r["id"]:r for r in rows(base/"raw.jsonl")}
    allocation = rows(base/"allocation.jsonl")
    assert len(allocation)==len(new)==48
    notes, detail = [], []
    for k in allocation:
        a, b = old[k["short_id"]], new[k["writer_id"]]
        assert a["messages"]==b["messages"] and a["checkpoint_sha256"]==b["checkpoint_sha256"]
        assert a["batch_size"]==b["batch_size"]==4 and (a["effective_token_cap"],b["effective_token_cap"])==(650,1300)
        unchanged = a["token_ids"]==b["token_ids"]
        common_prefix = a["token_ids"]==b["token_ids"][:len(a["token_ids"])]
        detail.append({**k,"arm":a["arm"],"seed":a["seed"],"unchanged_tokens":unchanged,
                       "short_is_prefix":common_prefix,"short_eos":a["eos"],"long_eos":b["eos"],
                       "short_tokens":a["generated_tokens"],"long_tokens":b["generated_tokens"]})
        notes.append({"note_id":k["note_id"],"task":k["task"],"text":b["text"]})
    # Every longer-budget output is eligible for an independent reading. The primary
    # budget sensitivity carries forward an existing grade on exactly identical text.
    notes.sort(key=lambda x:x["note_id"])
    save(base/"masked_notes.jsonl",notes)
    save(base/"length_receipts.jsonl",detail)
    print(json.dumps({"rows":len(detail),"identical":sum(r["unchanged_tokens"] for r in detail),
                      "prefix":sum(r["short_is_prefix"] for r in detail),
                      "long_capped":sum(not r["long_eos"] for r in detail),
                      "blind_sha256":hashlib.sha256((base/"masked_notes.jsonl").read_bytes()).hexdigest()}))


if __name__=="__main__":
    mask(Path(__file__).resolve().parent)
