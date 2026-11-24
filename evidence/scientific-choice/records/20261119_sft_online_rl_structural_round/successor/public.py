"""Independent source of standard center measurements; exports no slopes."""
import gzip
import sys
from common import ROOT, STRUCT, SEEDS, write
sys.path.insert(0, str(STRUCT))
from world import family_law, reading


def main():
    with gzip.open(ROOT / "public.jsonl.gz", "wt") as out:
        for seed in SEEDS:
            for family in range(24):
                for clone in range(4):
                    for slot in range(2):
                        key = 2 * clone + slot
                        write(out, dict(seed=seed, family=family, clone=clone, slot=slot,
                                        features=family_law(seed, "public", family)[0],
                                        center=reading(seed, "public", family, key, 0)))


if __name__ == "__main__":
    main()
