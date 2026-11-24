"""Invoke the established verification-host service under its existing inference lock."""
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from exact import ROOT


def utc():
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    runner = ROOT.parents[1] / "20261120_scientific_choice_and_recovery/strong/infer.sh"
    # ROOT is rounds/<this-round>/transfer; ROOT.parents[1] is rounds.
    raw = ROOT / "internal/writer_raw.jsonl"
    if raw.exists():
        raise FileExistsError(raw)
    subprocess.run(["sha256sum", "--check", "--quiet", "FROZEN.sha256"], cwd=ROOT, check=True)
    stamp = dict(start_utc=utc(), timings="Whole locked backend including transfer and possible queue")
    (ROOT / "internal/writer_start.json").write_text(json.dumps(stamp, indent=2) + "\n")
    start = time.monotonic()
    with (ROOT / "internal/writer_run.log").open("x") as log:
        child = subprocess.run([str(runner), str(ROOT / "internal/writer_input.jsonl"), str(raw)],
                               stdout=log, stderr=subprocess.STDOUT)
    stamp.update(end_utc=utc(), elapsed_seconds=time.monotonic() - start, returncode=child.returncode)
    (ROOT / "internal/writer_clock.json").write_text(json.dumps(stamp, indent=2) + "\n")
    if child.returncode:
        raise SystemExit(child.returncode)
