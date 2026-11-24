"""Fix, collect and mask the five prequalified-history length checks."""
import csv
import datetime
import json
import secrets
import subprocess
import sys
import time
from prepare import HERE, STRONG, digest, public_note, read_rows, write_rows

DIR = HERE / "expanded"
OPPORTUNITIES = HERE.parent / "review/PREHISTORY.tsv"
OPP_HASH = "68cc621f1ad19799559004bb5417d2c9e7d48c3dd0dae7f0473da0fb83132512"


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def freeze():
    assert digest(OPPORTUNITIES) == OPP_HASH
    with OPPORTUNITIES.open() as f:
        cards = list(csv.DictReader(f,delimiter="\t"))
    eligible = {r["history_id"] for r in cards if r["qualified"] == "1"}
    assert len(cards) == 24 and len(eligible) == 5
    extended, routing, blocks = [], [], []
    for path in sorted((HERE / "inputs").glob("b*.jsonl")):
        group = read_rows(path)
        if not any(r["history_id"] in eligible for r in group):
            continue
        blocks.append(path.stem)
        for primary in group:
            long = dict(primary,id="x"+secrets.token_hex(8),max_new_tokens=1300)
            extended.append(long)
            if long["history_id"] in eligible:
                for row in [primary,long]:
                    routing.append(dict(masked_id="l"+secrets.token_hex(8),raw_id=row["id"],history_id=row["history_id"],
                                        primary_id=primary["id"],cap=row["max_new_tokens"]))
    assert len(routing) == 20 and len(extended) == 8*len(blocks)
    secrets.SystemRandom().shuffle(routing)
    write_rows(DIR / "inputs.jsonl",extended)
    write_rows(HERE / "private/length_schedule.jsonl",routing)
    frozen = dict(frozen_utc=utc(),primary_freeze_sha256=digest(HERE/"FREEZE.json"),
                  opportunity_sha256=OPP_HASH, qualified_histories=sorted(eligible),
                  affected_archived_batches=blocks, primary_n=10, expanded_focal_n=10, expanded_total=len(extended),
                  inputs_sha256=digest(DIR/"inputs.jsonl"),code_sha256=digest(HERE/"expanded.py"),
                  protocol_sha256=digest(HERE/"EXPANDED_PROTOCOL.md"),
                  schedule_sha256=digest(HERE/"private/length_schedule.jsonl"))
    with (DIR / "FREEZE.json").open("x") as f:
        json.dump(frozen,f,indent=2)
        f.write("\n")


def acquire():
    frozen = json.loads((DIR/"FREEZE.json").read_text())
    assert digest(DIR/"inputs.jsonl") == frozen["inputs_sha256"]
    assert digest(HERE/"expanded.py") == frozen["code_sha256"]
    dest = DIR / "raw.jsonl"
    assert not dest.exists()
    start,t0 = utc(),time.monotonic()
    with (DIR/"raw.log").open("x") as log:
        job = subprocess.run([str(STRONG/"infer.sh"),str(DIR/"inputs.jsonl"),str(dest)],
                             stdout=log,stderr=subprocess.STDOUT)
    elapsed,end = time.monotonic()-t0, utc()
    with (DIR/"timing.json").open("x") as f:
        json.dump(dict(start_utc=start,end_utc=end,elapsed_seconds=elapsed,returncode=job.returncode,
                       scope="whole original wrapper including queue, model reload and transfer"),f,indent=2)
        f.write("\n")
    job.check_returncode()
    print("Completed matched expanded-cap acquisition",flush=True)


def mask():
    prim = {r["id"]:r for path in sorted((HERE/"raw").glob("b*.jsonl")) for r in read_rows(path)}
    long = {r["id"]:r for r in read_rows(DIR/"raw.jsonl")}
    rows = []
    for k in read_rows(HERE/"private/length_schedule.jsonl"):
        r = (prim if k["cap"] == 650 else long)[k["raw_id"]]
        rows.append(dict(masked_id=k["masked_id"],history_id=k["history_id"],public_note=public_note(r["text"]),
                         hit_token_cap=r["truncated"]))
    write_rows(HERE/"blind/length.jsonl",sorted(rows,key=lambda x:x["masked_id"]))


if __name__ == "__main__":
    {"freeze":freeze,"acquire":acquire,"mask":mask}[sys.argv[1]]()
