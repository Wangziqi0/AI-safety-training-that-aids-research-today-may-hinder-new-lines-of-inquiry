"""Independent fresh GPU load: replay the original first batch and execute one live trajectory."""
import argparse
import json
import os
import sys
from pathlib import Path

import torch
from assay import protocol, score_model
from instrument import decided, deliver, dump, lines, source_result

arg = argparse.ArgumentParser()
arg.add_argument("--prior", type=Path, required=True)
arg.add_argument("--root", type=Path, default=Path("."))
arg.add_argument("--out", type=Path, required=True)
args = arg.parse_args()
assert os.environ["CUDA_VISIBLE_DEVICES"] == "0" and torch.cuda.device_count() == 1
sys.path.insert(0,str(args.prior.resolve()))
from model import load, restore
torch.set_num_threads(2)
torch.manual_seed(20261120)
tok, model = load(args.prior/"base")
model = model.float().eval()
weight = restore(model,args.prior/"observed/sft-1901-A/adapter.pt")
jobs=json.loads((args.root/"UNITS.json").read_text())
contexts, maps, names, _ = protocol(tok,jobs,model.config.vocab_size)
args.out.mkdir(parents=True,exist_ok=True)
out=args.out/"eight_contexts.jsonl"
score_model(model,tok,contexts[:8],maps,names,out,8)
rows=lines(out)
orig=lines(args.root/"formal/sft-1901-A.jsonl")[:8]
assert rows==orig
by_state={(r["role"],r["state"]):r for r in rows if r["id"]==jobs[0]["id"]}
t1=by_state["source","plain"]["draws"][0]
first=source_result(jobs[0],t1[2])
actual_record=deliver(jobs[0],first,"late",False)
t2=by_state["reader",actual_record["record"]]["draws"][0]
final=decided(jobs[0],t2[2])
prop=torch.cuda.get_device_properties(0)
dump(args.out/"GPU_REPLAY.json",dict(status="PASS",physical_uuid=str(prop.uuid),gpu=prop.name,
     visible=os.environ["CUDA_VISIBLE_DEVICES"],adapter_parameters_sha256=weight,
     replayed_whole_categorical_vector_digests=len(rows),all_digests_groups_draws_exact=(rows==orig),
     first_job=jobs[0]["id"],rep=0,regime="natural",first_token=t1,first_execution=first,
     executed_receiver_record=actual_record,second_token=t2,second_execution=final))
