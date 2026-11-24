"""Wait for both audited batches, lock independently, then score and summarize."""
import subprocess
import sys
import time
from receiver import HERE, PRACTICE, digest, dump

names={"assigned_lock":"receiver_input_scanned.jsonl",
       "stewardship_lock":"stewardship_receiver_input_scanned.jsonl"}
while not all((HERE/b/"CHOICES_LOCK.json").is_file() for b in names):
    for output,source in names.items():
        base=HERE/output
        path=PRACTICE/source
        if (base/"CHOICES_LOCK.json").exists() or not path.is_file():
            continue
        # A complete 72-row read prevents opening an in-progress transport file.
        if len(path.read_text().splitlines())!=72:
            continue
        subprocess.run([sys.executable,str(HERE/"receiver.py"),"--products",str(path),
              "--mapping",str(PRACTICE/"receiver_allocation.jsonl"),"--out",str(base)],check=True)
    if not all((HERE/b/"CHOICES_LOCK.json").is_file() for b in names):
        time.sleep(3)
dump(HERE/"BOTH_DECISIONS_LOCKED.json",{b:digest(HERE/b/"CHOICES_LOCK.json") for b in names})
for output in names:
    base=HERE/output
    if not (base/"SCORED_LOCK.json").exists():
        subprocess.run([sys.executable,str(HERE/"score_locked.py"),str(base)],check=True)
    subprocess.run([sys.executable,str(HERE/"summarize.py"),str(base)],check=True)
