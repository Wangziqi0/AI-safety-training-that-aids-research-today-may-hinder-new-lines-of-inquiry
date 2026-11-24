import gzip
import hashlib
import json
import random
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
STRUCT = ROOT.parent / "structural"
CONFIG = json.loads((STRUCT / "config.json").read_text())
SEEDS = CONFIG["seeds"]
ALGOS = CONFIG["algorithms"]
ARMS = CONFIG["arms"]
SHAPES = [(4, 8), (8,), (8, 2), (2,)]


def stable(*parts):
    return int.from_bytes(hashlib.sha256(repr(parts).encode()).digest()[:12], "big")


def blind(*parts):
    return f"{stable('storage', *parts):024x}"


def jsonl(name):
    with gzip.open(ROOT / name, "rt") as stream:
        for line in stream:
            yield json.loads(line)


def write(stream, obj):
    stream.write(json.dumps(obj, separators=(",", ":"), allow_nan=False) + "\n")


def init(seed):
    rng = np.random.default_rng(stable("init", seed))
    return np.concatenate([((rng.normal(0, .2, size=shape)) if len(shape) > 1 else np.zeros(shape)).ravel()
                           for shape in SHAPES])


def unpack(vec):
    chunks = np.split(vec, np.cumsum([np.prod(shape) for shape in SHAPES])[:-1])
    return [part.reshape(shape) for part, shape in zip(chunks, SHAPES)]


def forward(w, categories):
    inp, bias, out, outbias = unpack(w)
    h = np.tanh(inp[categories] + bias)
    return h, h @ out + outbias


def category(features):
    assert len(features) == 2 and all(v in (-1, 1) for v in features)
    return 2 * int(features[0] == 1) + int(features[1] == 1)
