"""Regenerate the deidentified public extract from the authors' immutable RDS."""
import csv
import hashlib
import io
import json
import platform
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen

import pandas
import pyreadr

REV = "c2721bb6c2ddfad2633d9ab0a01dc514ec956923"
ORIGINAL = f"https://raw.githubusercontent.com/I4Replication/AI-Games/{REV}/data/AI%20games.rds"
NAMES = ("Human-Only", "AI-Assisted", "AI-Led")
SOURCE_DIGEST = "0f69c9d842cb25dfb6b79aa48dd8c0202c53802bb53d6d024a8574dc86bebb86"
EXTRACT_DIGEST = "3b514e3598e6f6cbd12ae5e31a63400c3e5f0a50374297e0cdaaf90e1642b7b2"

if sys.argv[1:] == ["--stdin"]:
    raw = sys.stdin.buffer.read()
elif not sys.argv[1:]:
    with urlopen(ORIGINAL, timeout=20) as response:
        raw = response.read()
else:
    raise SystemExit("Usage: python verify_public_source.py [--stdin]")
assert hashlib.sha256(raw).hexdigest() == SOURCE_DIGEST
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "public.rds"
    path.write_bytes(raw)
    frame = pyreadr.read_r(str(path))[None][["branch", "reproduction", "major_errors"]]
assert len(frame) == 103 and not frame.isna().any().any()
teams = sorted((NAMES.index(s), int(r), int(d)) for s, r, d in frame.itertuples(index=False, name=None))
buf = io.StringIO()
writer = csv.writer(buf, lineterminator="\n")
writer.writerow(["mode", "reproduced", "major_errors"])
writer.writerows(teams)
derivative = buf.getvalue().encode("utf-8")
assert hashlib.sha256(derivative).hexdigest() == EXTRACT_DIGEST
print(json.dumps(dict(source=ORIGINAL, source_bytes=len(raw), source_sha256=SOURCE_DIGEST,
                      derived_csv_bytes=len(derivative), derived_csv_sha256=EXTRACT_DIGEST,
                      rows=len(teams), selected_columns=["branch", "reproduction", "major_errors"],
                      python=platform.python_version(), pandas=pandas.__version__,
                      pyreadr=pyreadr.__version__), indent=2))
