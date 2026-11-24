"""Compare the extra allowance with the frozen primary raw generation on its five eligible histories."""
import argparse
import json
from audit import as_tsv, raw_check
from expanded import DIR, OPPORTUNITIES
from prepare import HERE, digest, public_note, read_rows


def audit():
    frozen = json.loads((DIR/"FREEZE.json").read_text())
    assert digest(DIR/"inputs.jsonl") == frozen["inputs_sha256"]
    assert digest(OPPORTUNITIES) == frozen["opportunity_sha256"]
    assert digest(HERE/"EXPANDED_PROTOCOL.md") == frozen["protocol_sha256"]
    assert digest(HERE/"expanded.py") == frozen["code_sha256"]
    assert digest(HERE/"private/length_schedule.jsonl") == frozen["schedule_sha256"]
    assert digest(HERE/"FREEZE.json") == frozen["primary_freeze_sha256"]
    primary_freeze = json.loads((HERE/"FREEZE.json").read_text())
    checkpoints = {(r["arm"],r["seed"]):r for r in primary_freeze["checkpoints"]}
    eligible = set(frozen["qualified_histories"])
    originals = [r for b in frozen["affected_archived_batches"]
                 for r in read_rows(HERE/"raw"/(b+".jsonl"))]
    long = read_rows(DIR/"raw.jsonl")
    requests = read_rows(DIR/"inputs.jsonl")
    assert len(originals) == len(long) == len(requests) == frozen["expanded_total"]
    by_id = {r["id"]:r for r in [*originals,*long]}
    blind = {r["masked_id"]:r for r in read_rows(HERE/"blind/length.jsonl")}
    routing = read_rows(HERE/"private/length_schedule.jsonl")
    assert len(routing) == len(blind) == 20
    for route in routing:
        r = by_id[route["raw_id"]]
        assert blind[route["masked_id"]] == dict(masked_id=route["masked_id"],history_id=r["history_id"],
                                                public_note=public_note(r["text"]),hit_token_cap=r["truncated"])
    route_ids = {r["raw_id"]:r["masked_id"] for r in routing}
    cells = []
    for old,req,out in zip(originals,requests,long,strict=True):
        raw_check(req,out,checkpoints[out["arm"],out["seed"]])
        assert all(out[k]==old[k] for k in ("messages","arm","seed","case","history_id","context_tokens"))
        if out["history_id"] not in eligible:
            continue
        a,z = old["token_ids"],out["token_ids"]
        common = next((i for i,(x,y) in enumerate(zip(a,z)) if x!=y),min(len(a),len(z)))
        cells.append(dict(history_id=out["history_id"],case=out["case"],seed=out["seed"],writer=out["arm"],
                          primary_joint_id=old["id"],expanded_joint_id=out["id"],
                          masked_primary=route_ids[old["id"]],masked_expanded=route_ids[out["id"]],
                          tokens_650=len(a),tokens_1300=len(z),truncated_650=int(old["truncated"]),
                          truncated_1300=int(out["truncated"]),common_token_prefix=common,
                          prefix_match=int(common==len(a)),same_tokens=int(a==z),
                          same_public_text=int(public_note(old["text"])==public_note(out["text"]))))
    assert len(cells) == 10
    timing = json.loads((DIR/"timing.json").read_text())
    assert timing["returncode"] == 0 and timing["elapsed_seconds"]>0
    result = dict(freeze_sha256=digest(DIR/"FREEZE.json"),raw_sha256=digest(DIR/"raw.jsonl"),
                  n_qualified_histories=len(eligible),n_scored=len(cells),generated_cells=len(long),
                  batch_fillers=len(long)-len(cells),timing=timing,
                  exact_primary_prefix=sum(r["prefix_match"] for r in cells),
                  unchanged_token_sequences=sum(r["same_tokens"] for r in cells),
                  changed_public_text=sum(1-r["same_public_text"] for r in cells),
                  truncated_650=sum(r["truncated_650"] for r in cells),
                  truncated_1300=sum(r["truncated_1300"] for r in cells))
    return {"length_audit.json":json.dumps(result,indent=2)+"\n","length_cells.tsv":as_tsv(cells)}


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--record",action="store_true")
    args=parser.parse_args()
    for name,body in audit().items():
        path=HERE/name
        if args.record and not path.exists():
            with path.open("x") as stream:
                stream.write(body)
        else:
            assert path.read_text()==body,name
    print("Verified the five selected histories and both budget conditions, including numerical batch fillers.")
