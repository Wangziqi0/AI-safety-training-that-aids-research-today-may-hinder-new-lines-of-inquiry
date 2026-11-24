"""Prepare prospectively bound anonymous scientific work orders using development data only."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
PRACTICE=ROOT.parent/"practice"
DOWN=ROOT.parent/"downstream"
sys.path.insert(0,str(DOWN))
import receiver

def digest(value):
    return hashlib.sha256(value.encode() if isinstance(value,str) else value).hexdigest()

def json_bytes(obj):
    return (json.dumps(obj,sort_keys=True,ensure_ascii=False,allow_nan=False)+"\n").encode()

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        assert path.read_bytes()==data, str(path)
    else:
        with path.open("xb") as out:
            out.write(data)

def slots():
    order=[("P01","none"),("P04","none"),("P01","H"),("P01","A"),("P04","A"),("P04","H")]
    return [dict(field=f,arm=a,slot=digest(f"tess-20261120-last-step/{i}/{a}/{f}")[:12]) for i,(f,a) in enumerate(order)]

def common(f):
    meta=json.loads((DOWN/"ordinary_lock"/(f+"_access.json")).read_text())
    with np.load(PRACTICE/"fields"/(f+".npz")) as d:
        k=meta["fit_n"]
        cube=d["late_px"][:k]
        t=d["late_pt"][:k]
    p=meta["standing_periods"][0][1]
    basis=np.stack((np.ones(k),np.cos(2*np.pi*t/p),np.sin(2*np.pi*t/p)),axis=1)
    amplitudes={}
    for mask,ix in meta["masks"].items():
        flux=receiver.extract(cube,ix)
        g=np.isfinite(flux)
        beta=np.linalg.lstsq(basis[g],flux[g],rcond=None)[0]
        amplitudes[mask]=dict(mean_e_s=round(float(np.mean(flux[g])),2),semiamplitude_e_s=round(float(np.hypot(*beta[1:])),3))
    return dict(standing_period_days=dict(meta["standing_periods"]),development_samples=k,
        development_span_days=round(float(np.ptp(t)),4), development_amplitude_reference_period_days=p,
        development_photometry=amplitudes,aperture_flat_pixel_indices=meta["masks"],stamp_shape=list(cube.shape[1:]))

def prepare(row):
    f,a,slot=row["field"],row["arm"],row["slot"]
    packet=None
    provenance={}
    if a!="none":
        mapping=receiver.jsonl(PRACTICE/"arm_key.jsonl")
        ident=next(r["id"] for r in mapping if (r["field"],r["arm"],r["seed"])==(f,a,311))
        released=next(r for r in receiver.jsonl(PRACTICE/"receiver_input_scanned.jsonl") if r["id"]==ident)
        packet={k:released[k] for k in ("period_days","source_periods","formed_packets","public_text")}
        provenance=dict(source_alias=ident,source_record_sha256=digest(json_bytes(released)))
    prompt=(ROOT/"COMMON_PROMPT.txt").read_text()+"\nOrdinary field measurements\n"+json.dumps(common(f))+"\nAdditional first-sector material\n"+json.dumps(packet,ensure_ascii=False)+"\n"
    save(ROOT/"prepared"/slot/"prompt.txt",prompt.encode())
    save(ROOT/"prepared"/slot/"prompt.sha256",(digest(prompt)+"\n").encode())
    save(ROOT/"prepared"/slot/"provenance.json",json_bytes(provenance))

if __name__=="__main__":
    save(ROOT/"SLOTS.json",json_bytes(slots()))
    for row in slots():
        if row["arm"]=="none" or (PRACTICE/"receiver_input_scanned.jsonl").exists():
            prepare(row)
