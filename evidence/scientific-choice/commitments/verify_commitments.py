"""Re-read historical manifest formats, recompute SHA-256 values and list exceptions."""
import argparse
import hashlib
import json
from zipfile import ZipFile
from collections import Counter
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def dependencies(path, kind, cwd):
    """Return the digest and original path at the time represented by each manifest."""
    if kind == "sha256":
        return [(cwd / line[66:], line[:64]) for line in path.read_text().splitlines() if line]
    if kind == "prompt":
        return [(path.with_name("prompt.txt"), path.read_text().strip())]
    data = json.loads(path.read_text())
    if kind == "choices":
        return [(cwd / key, value) for key, value in data["files"].items()]
    if kind == "scored":
        return [(path.with_name("results.jsonl"), data["scores_sha256"]),
                (path.with_name("CHOICES_LOCK.json"), data["choices_lock_sha256"]),
                (cwd / "downstream/score_locked.py", data["implementation_sha256"])]
    if kind == "batches":
        return [(path.parent / slot / "CHOICES_LOCK.json", value) for slot, value in data.items()]
    if kind == "hosted_decisions":
        return [(path.parent / "runs" / row["slot"] / "final_message.md", row["raw_response_sha256"])
                for row in data if "raw_response_sha256" in row]
    if kind == "hosted_forecasts":
        checks = [(path.with_name("DECISIONS.json"), data["decision_sha256"])]
        for row in data["forecasts"]:
            checks.append((path.parent / "predictions" / row["file"], row["prediction_sha256"]))
            if row["ablation_sha256"]:
                checks.append((path.parent / "predictions" / (row["slot"]+"_term_out.npz"), row["ablation_sha256"]))
        return checks
    raise ValueError("Unknown manifest kind "+kind)


def verify_scientific_records(root):
    field=root/"records/20261120_scientific_choice_and_recovery"
    native=root/"records/20261119_open_science_alignment_convergence/structural"
    released={}
    for line in (field/"practice/receiver_input_scanned.jsonl").read_text().splitlines():
        obj=json.loads(line)
        serial=(json.dumps(obj,sort_keys=True,ensure_ascii=False,allow_nan=False)+"\n").encode()
        released[obj["id"]]=hashlib.sha256(serial).hexdigest()
    identity_checked=0
    slots=json.loads((field/"astra/SLOTS.json").read_text())
    for slot in slots:
        proof=json.loads((field/"astra/prepared"/slot["slot"]/"provenance.json").read_text())
        if slot["arm"]=="none":
            assert proof=={}
        else:
            assert released[proof["source_alias"]]==proof["source_record_sha256"]
            identity_checked+=1
    verified_bases=0
    for path in sorted((native/"roots").glob("*/forecast.json")):
        expected=json.loads(path.read_text())["base_hash"]
        digest_state=hashlib.sha256()
        with ZipFile(path.with_name("base.pt")) as model:
            buffers=[n for n in model.namelist() if "/data/" in n]
            for name in sorted(buffers,key=lambda s:int(s.rsplit("/",1)[1])):
                digest_state.update(model.read(name))
        if digest_state.hexdigest()!=expected:
            raise ValueError("Base tensor hash differs at "+str(path))
        verified_bases+=1
    assert verified_bases==12 and identity_checked==4 and len(slots)==6
    return {"hosted_handoff_sources_matched":identity_checked,"hosted_ordinary_no_offer_sources":2,
            "independently_hashed_learned_root_tensor_states":verified_bases}

def verify(root):
    root = root.resolve()
    index = json.loads((root / "commitments/inventory.json").read_text())
    counts = Counter()
    details = []
    for receipt in index["manifests"]:
        path = root / receipt["manifest"]
        cwd = root / receipt["working_directory"]
        if digest(path) != receipt["copy_sha256"]:
            raise ValueError("Historical manifest changed: "+receipt["manifest"])
        edges = dependencies(path, receipt["kind"], cwd)
        summary = Counter()
        for raw, expected in edges:
            relative = str(raw.resolve().relative_to(root))
            ref = receipt["overrides"].get(relative, {})
            status = ref.get("status", "exact")
            if status == "withheld":
                if digest_condition_invalid(expected):
                    raise ValueError("Invalid historical digest "+relative)
            else:
                actual = root / ref.get("file", relative)
                if not actual.resolve().is_relative_to(root) or digest(actual) != expected:
                    raise ValueError("Hash mismatch at "+str(actual)+" declared by "+str(path))
            counts[status] += 1
            summary[status] += 1
        details.append({"manifest":receipt["manifest"],"working_directory":receipt["working_directory"],**summary})
    for item in index["protocols"]:
        if digest(root / item["path"]) != item["packaging_sha256"]:
            raise ValueError("Protocol copy differs: "+item["path"])
    return {"manifests":len(index["manifests"]),"historical_digest_comparisons":sum(counts.values()),
            "counts":dict(counts),"additional_scientific_checks":verify_scientific_records(root),"separately_inventoried_protocol_files":len(index["protocols"]),"details":details}


def digest_condition_invalid(value):
    return len(value) != 64 or any(char not in "0123456789abcdef" for char in value)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--details", action="store_true")
    args = parser.parse_args()
    result = verify(args.root)
    if not args.details:
        result.pop("details")
    print(json.dumps(result, indent=2))
