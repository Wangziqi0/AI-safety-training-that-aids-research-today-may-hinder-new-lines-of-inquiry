"""Bind checked inputs, historical outcomes and verification-host execution identities before acquisition."""
from datetime import datetime, timezone
import json
import subprocess
from prepare import CROSSED, HERE, OLD, ROOT, STRONG, digest, read_rows


def freeze():
    assert not list((HERE / "raw").glob("b*.jsonl"))
    source_paths = [
        CROSSED, CROSSED.parent / "README.md", OLD / "internal/handoff_input.jsonl",
        OLD / "internal/handoff_raw.jsonl", OLD / "PROTOCOL.md", OLD / "workflow.py",
        OLD / "dockets.py", OLD / "EDITORIAL_REFERENCE.md", OLD / "DONOR_REPORT.md",
        STRONG / "infer.sh", STRONG / "infer_batch.py", STRONG / "runtime.py",
        STRONG / "BASE_RECEIPT.json", STRONG / "PLAN.md", STRONG / "service_raw.jsonl",
        OLD / "internal/service_input.jsonl", OLD / "internal/service_raw.jsonl",
    ]
    query = ("cd $MODEL_STUDY/strong && "
             "sha256sum runtime.py infer_batch.py weights/[ABH]-*/manifest.json weights/[ABH]-*/adapter.pt")
    response = subprocess.check_output(["ssh", "-o", "BatchMode=yes", "verification-host", query], text=True)
    remote = {word[1]: word[0] for word in (line.split() for line in response.splitlines())}
    assert all(digest(STRONG / n) == remote[n] for n in ("runtime.py", "infer_batch.py"))
    old_rows = read_rows(OLD / "internal/handoff_raw.jsonl")
    earlier_b_rows = [r for r in read_rows(STRONG / "service_raw.jsonl") if r["arm"] == "B"]
    identities = []
    for path in sorted((STRONG / "weights").glob("[ABH]-*/manifest.json")):
        manifest = json.loads(path.read_text())
        rel = path.relative_to(STRONG)
        assert digest(path) == remote[str(rel)]
        assert manifest["file_sha256"] == remote[str(rel.with_name("adapter.pt"))]
        source = earlier_b_rows if manifest["arm"] == "B" else old_rows
        records = [r for r in source if r["seed"] == manifest["seed"] and r["arm"] == manifest["arm"]]
        assert len(records) == (16 if manifest["arm"] == "B" else 4)
        assert all(r["base_revision"] == manifest["base"] and
                   r["checkpoint_sha256"] == manifest["checkpoint_sha256"] for r in records)
        identities.append(dict(seed=manifest["seed"], arm=manifest["arm"],
                               base_revision=manifest["base"], checkpoint_sha256=manifest["checkpoint_sha256"],
                               adapter_file_sha256=manifest["file_sha256"], manifest_sha256=digest(path)))
    assert len(identities) == 9
    platform_query = ("hostname && nvidia-smi --id=1 --query-gpu=name,uuid,driver_version --format=csv,noheader && "
                      "python3 -c "
                      "'from importlib.metadata import version; import platform; "
                      "print(platform.python_version(),version(\"torch\"),version(\"transformers\"))'")
    platform_lines = subprocess.check_output(["ssh", "-o", "BatchMode=yes", "verification-host", platform_query],
                                             text=True).splitlines()
    local_files = ["PREHISTORY_DELIVERED.txt", "PROTOCOL.md", "prepare.py", "receiver_design.py",
                   "acquire.py", "mask_deliveries.py", "freeze.py", "blind/prehistory.jsonl",
                   "private/allocation.jsonl", "private/receiver_allocation.jsonl", "private/batches.jsonl",
                   "secondary.py", "SECONDARY_PROTOCOL.md", "secondary/inputs.jsonl", "secondary/batch_order.jsonl",
                   "private/secondary_notes.jsonl", "private/secondary_service.jsonl"]
    record = dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
                  external_immutable_inputs={str(p.relative_to(ROOT)): digest(p) for p in source_paths},
                  local_cross_files={name:digest(HERE / name) for name in local_files},
                  batches=read_rows(HERE / "private/batches.jsonl"), checkpoints=identities,
                  remote_runtime_sha256={n:remote[n] for n in ("runtime.py", "infer_batch.py")},
                  platform=platform_lines, seed_role="paired fitted training seeds; greedy generation",
                  grain="six ordered four-history batches each evaluated on both fitted writers",
                  total=48, original_replays=24, opposite_interventions=24,
                  secondary=dict(handoff_b=24, first_service_b=12))
    with (HERE / "FREEZE.json").open("x") as out:
        json.dump(record, out, indent=2, ensure_ascii=False)
        out.write("\n")


if __name__ == "__main__":
    freeze()
