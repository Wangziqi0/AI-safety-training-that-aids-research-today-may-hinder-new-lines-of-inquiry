"""Acquire the six matched blocks using the archived, lock-protected verification-host interface."""
import datetime
import json
from pathlib import Path
import subprocess
import time
from prepare import HERE, STRONG, digest


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def acquire():
    freeze = json.loads((HERE / "FREEZE.json").read_text())
    assert (HERE / "PREHISTORY_DELIVERED.txt").exists()
    assert all(digest(HERE / rel) == val for rel, val in freeze["local_cross_files"].items())
    primary = [(batch["batch"], HERE / "inputs" / (batch["batch"] + ".jsonl"),
                HERE / "raw" / (batch["batch"] + ".jsonl"), batch["input_sha256"])
               for batch in freeze["batches"]]
    secondary = ("secondary", HERE / "secondary/inputs.jsonl", HERE / "secondary/raw.jsonl",
                 freeze["local_cross_files"]["secondary/inputs.jsonl"])
    for name, source, dest, expected in [*primary, secondary]:
        assert digest(source) == expected
        receipt = dest.with_suffix(".timing.json")
        if dest.exists() or receipt.exists():
            raise FileExistsError(f"Output already exists for {name}")
        start, start_clock = utc(), time.monotonic()
        with dest.with_suffix(".log").open("x") as log:
            status = subprocess.run([str(STRONG / "infer.sh"), str(source), str(dest)],
                                    stdout=log, stderr=subprocess.STDOUT)
        elapsed, finish = time.monotonic()-start_clock, utc()
        with receipt.open("x") as fh:
            json.dump(dict(batch=name, start_utc=start, end_utc=finish,
                           elapsed_seconds=elapsed, scope="whole wrapper including lock wait/model load and transfer",
                           returncode=status.returncode), fh, indent=2)
            fh.write("\n")
        status.check_returncode()
        print(f"{name} complete ({elapsed:.3f} s).", flush=True)


if __name__ == "__main__":
    acquire()
