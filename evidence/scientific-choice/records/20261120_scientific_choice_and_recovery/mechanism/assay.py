"""Evaluate the unrestricted native next-token laws at both decisions on node22."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
from instrument import ALIASES, DEFAULT, DRAWS, RECORDS, dump, reader_text, source_text, uniform

PAIRS = (("sft", 1901), ("sft", 2311), ("sft", 2903), ("rl", 1901), ("rl", 2311))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def score_model(model, tokenizer, contexts, mapping, group_names, dst, batch_size):
    with dst.open("x") as out, torch.inference_mode():
        for start in range(0, len(contexts), batch_size):
            batch = contexts[start:start + batch_size]
            starts = [r["ids"] for r in batch]
            lengths = torch.tensor(list(map(len, starts)), device="cuda")
            ids = torch.full((len(starts), int(lengths.max())), tokenizer.pad_token_id,
                             dtype=torch.long, device="cuda")
            for i, seq in enumerate(starts):
                ids[i, :len(seq)] = torch.tensor(seq, device="cuda")
            mask = torch.arange(ids.shape[1], device="cuda")[None, :] < lengths[:, None]
            hidden = model.model(input_ids=ids, attention_mask=mask, use_cache=False).last_hidden_state
            final = hidden[torch.arange(len(batch), device="cuda"), lengths - 1]
            logits = model.lm_head(final).cpu().numpy()
            for row, values in zip(batch, logits):
                role, job = row["role"], row["id"]
                probs = np.exp(values.astype(np.float64) - float(values.max()))
                probs /= probs.sum()
                mass = np.bincount(mapping[role], weights=probs, minlength=len(group_names[role]))
                cdf = probs.cumsum()
                cdf[-1] = 1.
                draws = []
                for rep in range(DRAWS):
                    token = int(np.searchsorted(cdf, uniform(job, rep, role), side="right"))
                    draws.append([token, tokenizer.decode([token], skip_special_tokens=False),
                                  group_names[role][mapping[role][token]], float(probs[token])])
                record = dict(id=job, role=role, state=row["state"],
                              context_digest=row["context_digest"], native_vocab=len(probs),
                              probability_dtype="little-endian float64",
                              probability_digest=digest(probs.astype("<f8", copy=False).tobytes()),
                              groups=dict(zip(group_names[role], mass.tolist())), draws=draws)
                assert abs(float(mass.sum()) - 1.) < 1e-10
                out.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")


def protocol(tokenizer, jobs, vocab):
    contexts = []
    for job in jobs:
        prompts = [("source", "plain", source_text(job, False)),
                   ("source", "early", source_text(job, True))]
        prompts += [("reader", rec, reader_text(job, rec)) for rec in RECORDS]
        for role, state, prompt in prompts:
            ids = tokenizer.apply_chat_template([{"role": "user", "content": prompt}],
                    tokenize=True, add_generation_prompt=True, return_dict=False)
            contexts.append(dict(id=job["id"], role=role, state=state, prompt=prompt, ids=ids,
                                 context_digest=digest(np.asarray(ids, dtype="<i4").tobytes())))
    names = {role: list(groups) + [DEFAULT] for role, groups in ALIASES.items()}
    maps = {role: np.full(vocab, len(kinds) - 1, dtype=np.int32) for role, kinds in names.items()}
    alias = {role: {word: names[role].index(kind) for kind, words in groups.items() for word in words}
             for role, groups in ALIASES.items()}
    for i in range(0, vocab, 2048):
        token_texts = tokenizer.batch_decode([[t] for t in range(i, min(i+2048, vocab))],
                                              skip_special_tokens=False)
        for ix, text in enumerate(token_texts, start=i):
            for role in names:
                value = alias[role].get(text.strip().casefold())
                if value is not None:
                    maps[role][ix] = value
    tokens = {role: {kind: np.where(maps[role] == n)[0].tolist() for n, kind in enumerate(kinds[:-1])}
              for role, kinds in names.items()}
    return contexts, maps, names, tokens


def main():
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=("forecast", "formal"))
    p.add_argument("--prior", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--batch", type=int, default=8)
    args = p.parse_args()
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0" and torch.cuda.device_count() == 1
    sys.path.insert(0, str(args.prior.resolve()))
    from model import load, sha_file, fingerprint
    import transformers
    torch.manual_seed(20261120)
    torch.set_num_threads(2)
    args.out.mkdir(parents=True, exist_ok=True)
    if args.phase == "formal":
        if not Path("FORECAST.sha256").is_file():
            raise RuntimeError("Missing prospective forecast lock")
    tokenizer, model = load(args.prior / "base")
    model = model.float().eval()
    jobs = json.loads(Path(__file__).with_name("UNITS.json").read_text())
    rs, maps, names, token_ids = protocol(tokenizer, jobs, model.config.vocab_size)
    receive = dict(vocab_size=model.config.vocab_size, groups=token_ids,
                   other="All remaining native IDs including unused special slots")
    if args.phase == "forecast":
        dump(args.out / "CONTEXTS.json", rs)
        dump(args.out / "TOKEN_GROUPS.json", receive)
    else:
        assert json.loads(Path("forecast/CONTEXTS.json").read_text()) == rs
        assert json.loads(Path("forecast/TOKEN_GROUPS.json").read_text()) == receive
    runtime = dict(phase=args.phase, torch=torch.__version__, transformers=transformers.__version__,
                   gpu=torch.cuda.get_device_name(0), visible=os.environ["CUDA_VISIBLE_DEVICES"],
                   base_sha256=sha_file(args.prior/"base/model.safetensors"),
                   dtype="FP32 evaluation of fixed FP16 source and archived FP32 LoRA",
                   cases=len(jobs), contexts=len(rs), batch_size=args.batch, bounds=[])
    assert runtime["base_sha256"] == "c1b9b30e907950516ba3c646bdf570d8084c25a6410a0cdca80cf04b11bc13a8"
    params = {n:p for n,p in model.named_parameters() if p.requires_grad}
    if args.phase == "forecast":
        score_model(model, tokenizer, rs, maps, names, args.out/"base.jsonl", args.batch)
        print("sealed base", flush=True)
    for algo, seed in PAIRS:
        arms = {}
        for arm in ("H", "A", "B"):
            d = args.prior / "observed" / f"{algo}-{seed}-{arm}"
            state = torch.load(d/"adapter.pt", weights_only=True, map_location="cpu")
            manifest = json.loads((d/"manifest.json").read_text())
            assert set(params) == set(state) and fingerprint(state) == manifest["weight_sha256"]
            runtime["bounds"].append(dict(label=f"{algo}-{seed}-{arm}", parameters=fingerprint(state)))
            arms[arm] = state
        variants = [("H", 0.), ("minus", -.25)] if args.phase == "forecast" else [
                        ("quarter", .25), ("A", 1.), ("B", None)]
        for name, dose in variants:
            with torch.no_grad():
                for key, param in params.items():
                    if name in ("H", "A", "B"):
                        value = arms[name][key]
                    else:
                        value = torch.lerp(arms["H"][key], arms["A"][key], dose)
                    param.copy_(value)
            path = args.out / f"{algo}-{seed}-{name}.jsonl"
            score_model(model, tokenizer, rs, maps, names, path, args.batch)
            print(f"sealed {path.name}", flush=True)
    dump(args.out / "NATIVE_RUN.json", runtime)


if __name__ == "__main__":
    main()
