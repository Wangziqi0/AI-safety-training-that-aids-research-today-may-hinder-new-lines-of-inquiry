#!/bin/bash
set -euo pipefail
input=$(realpath "$1")
output=$(realpath -m "$2")
test ! -e "$output" && test -f "$input"
test -d "$(dirname "$output")"
job=$(ssh -o BatchMode=yes node22 'mktemp -d /home/amd/maofield-scientific-choice-20261120/strong/jobs/request.XXXXXXXX')
scp -q -- "$input" "node22:$job/input.jsonl"
ssh -o BatchMode=yes node22 "cd /home/amd/maofield-scientific-choice-20261120/strong && flock inference.lock env CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=2 HF_HUB_OFFLINE=1 /home/amd/maofield-envs/py312-cu128/bin/python infer_batch.py '$job/input.jsonl' '$job/output.jsonl'"
scp -q -- "node22:$job/output.jsonl" "$output.partial"
mv -Tn -- "$output.partial" "$output"
test ! -e "$output.partial"
