"""Run a frozen analysis on portable inputs whose administration-only redactions are declared."""
import hashlib
import importlib.util
import json
import runpy
import sys
from pathlib import Path

layout=Path(sys.argv[1]).resolve(); registration=json.loads(Path(sys.argv[2]).read_bytes());script=Path(sys.argv[3]).resolve()
cross=layout/'rounds/20261121_crossed_writer_attribution/cross'
sys.path.insert(0,str(cross));import prepare


def registered_content_identity(path):
    p=Path(path).absolute(); name=p.relative_to(layout).as_posix(); actual=hashlib.sha256(p.read_bytes()).hexdigest()
    record=registration['registered_files_with_public_administrative_edits'].get(name)
    if record is None:return actual
    if actual!=record['review_sha256']:raise ValueError('Public copy does not match its listed digest: '+name)
    # Registered analyses also print the original registration identity in their receipts.
    # This explicit bridge covers only the listed redacted administrative bytes.
    return record['registered_sha256']

prepare.digest=registered_content_identity
sys.path.insert(0,str(script.parent));sys.argv=[str(script),*sys.argv[4:]]
if script.name=='replay.py' and script.parent.name=='transfer':
    spec=importlib.util.spec_from_file_location('verified_transfer_replay',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.digest=registered_content_identity
    print(json.dumps(module.replay(),indent=2))
else:
    runpy.run_path(str(script),run_name='__main__')
