"""Finite synthetic instrument; all environmental draws are distinct from policy sampling."""
import hashlib
import random
from functools import lru_cache


def rng(*parts):
    return random.Random(int.from_bytes(hashlib.blake2b(repr(parts).encode(), digest_size=12).digest(), "big"))


@lru_cache(maxsize=4096)
def family_law(seed, split, family):
    generator = rng("instrument family", seed, split, family)
    features = [generator.choice((-1, 1)), generator.choice((-1, 1))]
    ordinary = 2 * features[0] * features[1]
    return features, -ordinary if generator.random() < 0.15 else ordinary


@lru_cache(maxsize=8192)
def project(seed, split, family, clone):
    r = rng("target", seed, split, family, clone)
    center = r.randrange(8, 81)
    return center, r.random(), r.random(), r.random()


def reading(seed, split, family, specimen, position):
    center = project(seed, split, family, specimen)[0]
    return center + family_law(seed, split, family)[1] * position


def accept_current(seed, split, family, clone, command):
    """Calibrate an acquisition offset on the source specimen, then physically read it."""
    return reading(seed, split, family, clone, 0) + command


def next_reading(seed, split, family, clone, position, trim):
    """A different specimen has a fresh intercept. Command trim in signal units."""
    specimen = 1000 + clone
    return reading(seed, split, family, specimen, position) + trim


def certificate(seed, split, family):
    """Ordinary reference service, independent of whether source took a second read."""
    return reading(seed, split, family, 2000, 1) - reading(seed, split, family, 2000, 0)
