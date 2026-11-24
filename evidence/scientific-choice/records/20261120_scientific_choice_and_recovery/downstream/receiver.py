"""Independent TESS photometry receiver. Lock only reads early data and late prefixes."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from astropy.timeseries import LombScargle

HERE = Path(__file__).resolve().parent
PRACTICE = HERE.parent / "practice"
FIELDS = [f"P{i:02d}" for i in range(1, 9)]
PMIN, PMAX = 0.2, 12.0

def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")

def jsonl(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]

def readrows(path):
    return json.loads(path.read_text()) if path.suffix == ".json" else jsonl(path)

def save_rows(path, rows):
    with path.open("w") as out:
        for row in rows:
            out.write(json.dumps(row, allow_nan=False) + "\n")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def period(value):
    if isinstance(value, dict):
        value = value.get("period_days")
    try:
        p = float(value)
    except (ValueError, TypeError):
        return None
    return p if PMIN <= p <= PMAX else None

def first_peak(t, flux):
    good = np.isfinite(t) & np.isfinite(flux)
    x, y = t[good], flux[good]
    if len(x) < 12 or np.std(y) <= 0:
        return None, 0
    frequencies, power = LombScargle(x, y).autopower(
        minimum_frequency=1 / PMAX, maximum_frequency=1 / PMIN, samples_per_peak=8)
    good = np.isfinite(power) & (frequencies <= 1 / PMIN)
    if not np.any(good):
        return None, len(power)
    return float(1 / frequencies[good][np.argmax(power[good])]), len(power)

def apertures(cube, bitmask):
    shape = bitmask.shape
    pixels = cube.reshape(len(cube), -1)
    valid = np.isfinite(pixels).sum(axis=0) >= .95 * len(pixels)
    med = np.full(pixels.shape[1], -np.inf)
    med[valid] = np.nanmedian(pixels[:, valid], axis=0)
    optimal = np.flatnonzero((bitmask.ravel() & 2) != 0)
    if not len(optimal):
        raise ValueError("SPOC aperture is empty")
    ordered = optimal[np.argsort(-med[optimal], kind="stable")]
    split = (len(ordered) + 1) // 2
    outside = np.flatnonzero(valid & ((bitmask.ravel() & 2) == 0))
    outside = outside[np.argsort(-med[outside], kind="stable")][:4]
    masks = {"spoc": optimal, "core": ordered[:split], "rim": ordered[split:], "outside": outside}
    return {key: value.tolist() for key, value in masks.items() if len(value)}

def extract(cube, indices):
    data = cube.reshape(len(cube), -1)[:, indices]
    return data.sum(axis=1, dtype=np.float64)

def design(t, p):
    phase = 2 * np.pi * t / p
    return np.column_stack((np.ones(len(t)), np.cos(phase), np.sin(phase),
                            np.cos(2 * phase), np.sin(2 * phase)))

def fitted(t, source, target, p, when):
    keep = np.isfinite(t) & np.isfinite(target) & np.isfinite(source)
    x, y = t[keep], target[keep]
    if len(x) < 10:
        return None
    if p == "constant":
        return np.full(len(when), np.median(y))
    if p == "trend":
        return np.polynomial.Polynomial.fit(x, y, deg=1)(when)
    basis = design(x, p)
    coefficients = np.linalg.lstsq(basis, source[keep], rcond=None)[0]
    wave = basis[:, 1:] @ coefficients[1:]
    common = np.column_stack((np.ones(len(wave)), wave))
    offset, scale = np.linalg.lstsq(common, y, rcond=None)[0]
    return offset + scale * (design(when, p)[:, 1:] @ coefficients[1:])

def mae(y, pred):
    if pred is None:
        return float("inf")
    keep = np.isfinite(y) & np.isfinite(pred)
    return float(np.mean(abs(y[keep] - pred[keep]))) if keep.any() else float("inf")

def split_counts(n):
    return int(.45 * n), int(.70 * n)

def cohort():
    return {r["field"]: r for r in json.loads((PRACTICE / "COHORT.json").read_text())["ordered"] if r["selected"]}

def release_schedule():
    rng = np.random.default_rng(202611200641)
    assignment = []
    for i, field in enumerate(FIELDS):
        for seed in range(3):
            recovered = set(rng.permutation(3)[:1 + (i+seed)%2].tolist())
            assignment.extend({"field":field, "seed_rank":seed, "slot":slot, "recovery":slot in recovered} for slot in range(3))
    return assignment

class Field:
    def __init__(self, field, metadata):
        self.field = field
        self.fit_cache = {}
        self.searches = {}
        with np.load(PRACTICE / "fields" / (field + ".npz")) as ds:
            n = len(ds["late_pt"])
            self.fit, self.end = split_counts(n)
            self.test_count = n - self.end
            # The selection process has no reference to any late flux after self.end.
            self.t = ds["late_pt"][:self.end].copy()
            cube = ds["late_px"][:self.end].copy()
            self.masks = apertures(cube[:self.fit], ds["late_mask"])
            self.series = {k: extract(cube, v) for k,v in self.masks.items()}
            self.ordinary = [("published", metadata["source"][2])]
            for name in ("sap", "pdc"):
                p, count = first_peak(ds["early_t"], ds["early_" + name])
                self.ordinary.append(("early_" + name, p))
                self.searches["early_" + name] = count
            p, count = first_peak(self.t[:self.fit], self.series["spoc"][:self.fit])
            self.ordinary.append(("late_fit_spoc", p))
            self.searches["late_fit_spoc"] = count
            start = time.process_time()
            early = ds["early_px"]
            outer = apertures(early, ds["early_mask"]).get("outside", [])
            self.recovery = {"kind":"early_outer_four_pixel_scan","period_days":None,
                "values":{"flat_pixel_indices":outer,"hourly_samples":len(early),"trial_frequencies":0},
                "scientific_note":"Dominant early modulation in the brightest available non-SPOC pixels; spatial origin remains uncertain."}
            if outer:
                p, count = first_peak(ds["early_pt"], extract(early, outer))
                self.recovery["period_days"] = p
                self.recovery["values"]["trial_frequencies"] = count
            self.recovery["values"]["cpu_seconds_observed"] = time.process_time() - start
        self.meta={"field":field, "early_sector":metadata["sectors"][0], "late_sector":metadata["sectors"][-1],
                   "fit_n":self.fit, "validation_n":self.end-self.fit, "test_n":self.test_count,
                   "masks":self.masks, "standing_periods":self.ordinary, "search_frequencies": self.searches,
                   "independent_recovery":self.recovery}

    def choose(self, product, packets, recovery):
        candidates = list(self.ordinary)
        if product:
            candidates.append(("submitted_current", product.get("period_days")))
            for i, source in enumerate(product.get("source_periods") or []):
                candidates.append((f"standing_source_{i}", source))
            if packets:
                for i, source in enumerate(product.get("formed_packets") or []):
                    candidates.append((f"formed_packet_{i}", source))
        if recovery:
            candidates.append(("independent_recovery", self.recovery["period_days"]))
        # Dictionary retains first attribution for duplicates. Independently recurring periods need no transmission.
        names = {}
        for origin, raw in candidates:
            p = period(raw)
            if p is None:
                continue
            for factor in (1.0, .5, 2.0):
                if PMIN <= p * factor <= PMAX:
                    names.setdefault(p * factor, (origin,factor))
        options = [("constant","spoc","standing_stop",1.), ("trend","spoc","standing_trend",1.)]
        options += [(p, name, origin, factor) for p,(origin,factor) in names.items() for name in self.masks]
        target = self.series["spoc"]
        best = None
        for p, mask, origin, factor in options:
            key = (p,mask)
            if key not in self.fit_cache:
                pred = fitted(self.t[:self.fit], self.series[mask][:self.fit], target[:self.fit],
                              p, self.t[self.fit:])
                self.fit_cache[key] = mae(target[self.fit:], pred)
            loss = self.fit_cache[key]
            if best is None or loss < best["validation_mae"]:
                best = {"component":p,"aperture":mask,"origin":origin,"period_multiplier":factor,"validation_mae":loss}
        if not np.isfinite(best["validation_mae"]):
            raise ValueError("no finite forecast on validation")
        return dict(best,hypotheses=len(names),candidate_fits=len(options))

def allocation(rows, mapping):
    if not rows:
        return {}
    if len(rows)!=72 or len(mapping)!=72 or len({r["id"] for r in rows})!=72:
        raise ValueError("expected 72 distinct blinded products and 72 mapping rows")
    levels = sorted(set(r["block_seed"] for r in mapping))
    if len(levels)!=3:
        raise ValueError("expected three block seed levels")
    release = {(r["field"],r["seed_rank"],r["slot"]):r["recovery"] for r in release_schedule()}
    public = {r["id"]:r for r in rows}
    result={}
    seen=set()
    for m in mapping:
        ident=m["id"]
        key=(public[ident]["field"],levels.index(m["block_seed"]),m["slot"])
        if key in seen or ident in result:
            raise ValueError("duplicate blocked slot")
        seen.add(key)
        result[ident]=dict(block_seed=m["block_seed"],slot=m["slot"],assigned_recovery=release[key])
    return result

def lock(args):
    rows = readrows(args.products) if args.products else []
    mapping = readrows(args.mapping) if args.mapping else []
    assignments=allocation(rows,mapping)
    args.out.mkdir(exist_ok=True)
    if (args.out/"CHOICES_LOCK.json").exists():
        raise FileExistsError("existing decision lock")
    metadata=cohort()
    choices=[]
    for field in FIELDS:
        f=Field(field, metadata[field])
        dump(args.out/(field+"_access.json"),f.meta)
        for on in (False,True):
            choices.append({"id":"ordinary_"+field,"field":field,"variant":"ordinary_recovery" if on else "ordinary",
                            "recovery":on,"packets":False,**f.choose(None,False,on)})
        for product in (r for r in rows if r["field"]==field):
            for on in (False,True):
                for packets in (False,True):
                    variant=("handoff" if packets else "current") + ("_recovery" if on else "")
                    choices.append({"id":product["id"],"field":field,"variant":variant,"recovery":on,
                                    "packets":packets,**assignments[product["id"]],**f.choose(product,packets,on)})
    save_rows(args.out/"choices.jsonl",choices)
    files=[Path(__file__), HERE/"PREREG.md", args.out/"choices.jsonl"]
    files += [args.out/(f+"_access.json") for f in FIELDS]
    if rows:
        files.extend([args.products,args.mapping])
    dump(args.out/"CHOICES_LOCK.json",{"files":{str(f.relative_to(HERE.parent)) if f.is_relative_to(HERE.parent) else str(f):digest(f) for f in files},
        "assigned_products":len(rows),"choices":len(choices),"phase":"numerical extraction and temporal hypotheses locked; no final target flux scored"})
    print(f"locked {len(choices)} choices in {args.out}")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--products",type=Path)
    parser.add_argument("--mapping",type=Path)
    args=parser.parse_args()
    if bool(args.products) != bool(args.mapping):
        parser.error("products and mapping must be supplied together")
    lock(args)
