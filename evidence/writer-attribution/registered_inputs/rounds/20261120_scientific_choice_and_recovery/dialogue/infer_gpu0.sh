#!/bin/bash
set -euo pipefail
input=$(realpath "$1")
output=$(realpath -m "$2")
test ! -e "$output" && test -f "$input"
test -d "$(dirname "$output")"
job=$(ssh -o BatchMode=yes verification-host 'mktemp -d $MODEL_STUDY/strong/jobs/request.XXXXXXXX')
scp -q -- "$input" "verification-host:$job/input.jsonl"
ssh -o BatchMode=yes verification-host "cd $MODEL_STUDY/strong && flock inference-gpu0.lock env CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2 HF_HUB_OFFLINE=1 python3 infer_batch.py '$job/input.jsonl' '$job/output.jsonl'"
scp -q -- "verification-host:$job/output.jsonl" "$output.partial"
mv -Tn -- "$output.partial" "$output"
test ! -e "$output.partial"
