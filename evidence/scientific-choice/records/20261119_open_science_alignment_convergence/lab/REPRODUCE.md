# Run the trained open model and reproduce the measures

The working directory on node22 is `/home/amd/scratch/open-science-align-20261119`. Run the following commands there with the existing interpreter. Each output directory below must be new, or contain no selected output filenames. Specify `--base` to point to an independently downloaded, verified source. The intervention programs require PyTorch, Transformers and a CUDA-enabled GPU. No privileged service is needed. The preserved adapters occupy approximately 4.4 MB each. The source checkpoint is shared, 3.09 GB.

```bash
py=/home/amd/maofield-envs/py312-cu128/bin/python
export CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2
"$py" train.py --out reproduce-weights sft-1901-H sft-1901-A sft-1901-B
"$py" inference.py --checkpoints reproduce-weights --heldout --models base sft-1901-H sft-1901-A sft-1901-B --max-new 96 --out reproduce-docs
"$py" inference.py --input arbitrary.jsonl --models sft-1901-H --max-new 384 --out new-greedy
"$py" trajectory.py sample --input arbitrary.jsonl --models base sft-1901-A --max-new 384 --temperature 0.8 --out new-samples
"$py" trajectory.py score --input new-samples/base.jsonl --models base sft-1901-A sft-1901-H --max-new 384 --temperature 0.8 --out new-scores
```

For all SFT streams repeat using seeds 2311 and 2903. For the RL program replace the method tag with `rl` and use seeds 1901 and 2311. Never mix output directories from different recipes. The JSONL keys are `id`, `prompt`, optional `system` and optional integer `draw_seed` for per-row sampling. Provide a different fixed draw seed for genuinely independent replicate trajectories. The default seed intentionally couples prompts if none is provided. For counterfactual scoring retain all original context and generated IDs, EOS or length cap, model, temperature and draw-seed metadata. Equal batch shape reduces floating point replay differences; the supplied software smoke replays with identical per-token probabilities. Sampling, scoring, greedy decoding and training remain distinct.

Calculate paired metrics locally with `python3 analyze.py heldout DEPLOYMENT.json` and checkpoint verification with `python3 verify.py observed CHECKPOINTS.json`. For common F, zero adapters are algebraically inert (no extra common warmup). The inference and trajectory functions accept free text or code as model output. Executing returned code or acting on scientific suggestions is the independently specified receiver's responsibility.
