"""Initial material, legitimate optical requests and current recipient for early time series only."""
from functools import lru_cache
from pathlib import Path
import json,math,time
import numpy as np
from astropy.timeseries import LombScargle
from scipy.signal import find_peaks
HERE=Path(__file__).resolve().parent

@lru_cache(None)
def data(field):
    # Deliberately load only first-epoch arrays.
    full=HERE/"fields"/(field+".npz")
    early_only=HERE/"early_ready"/(field+".npz")
    with np.load(full if full.exists() else early_only) as f:
        names=[n for n in f.files if n.startswith("early_")]
        d={n[6:]:f[n] for n in names}
    if "pt" in d:d["pt"]=d["pt"]-d["t"][0]
    d["t"]=d["t"]-d["t"][0]
    for k in ["pdc","sap"]:d[k]=(d[k]/np.nanmedian(d[k])-1)*1000.
    return d

def part(t):return np.floor(t+.00000001).astype(int)%3

def trend(t):return np.column_stack([np.ones(len(t)),t/30.])
def design(t,p):
    if p is None:return trend(t)
    return np.column_stack([trend(t),np.sin(2*np.pi*t/p),np.cos(2*np.pi*t/p)])
def err(t,y,p,k=1):
    a=part(t)==0;b=part(t)==k;X=design(t,p);co=np.linalg.lstsq(X[a],y[a],rcond=None)[0]
    pr=X[b]@co;m=float(np.mean((pr-y[b])**2))
    return m,co,pr
def search(t,y,k=5):
    good=np.isfinite(t)&np.isfinite(y);t=t[good];y=y[good]
    if len(t)<18:return []
    freq=np.linspace(1/9.,10.,max(800,int(np.ptp(t)*9.9*9)+1))
    periodogram=LombScargle(t,y).power(freq);ix=list(find_peaks(periodogram)[0])+[0,len(freq)-1]
    out=[]
    for i in sorted(ix,key=lambda i:-periodogram[i]):
        p=1/freq[i]
        if all(abs(1/p-1/v["period_days"])>1/np.ptp(t) for v in out):
            out.append({"period_days":round(float(p),6),"relative_power":round(float(periodogram[i]),6)})
        if len(out)>=k:break
    return out
@lru_cache(None)
def initial(field):
    d=data(field);t,y=d["t"],d["pdc"];idx=part(t)==0
    return {"discovery_hours":int(sum(idx)),"time_span_days":round(float(np.ptp(t[idx])),3),"pdc_candidates":search(t[idx],y[idx],3),"flux_ppt_10_50_90":np.percentile(y[idx],[10,50,90]).round(2).tolist()}
def fitvar(t,y,p):
    if len(t)<12:return 0.
    X=design(t,p);co=np.linalg.lstsq(X,y,rcond=None)[0]
    return float(np.hypot(co[2],co[3]))
@lru_cache(None)
def probe(field,kind,p):
    d=data(field);t,y=d["t"],d["pdc"];ix=part(t)==0;t=t[ix];y=y[ix]
    base={"kind":kind,"period_days":round(float(p),6)}
    if kind=="catalogue":
        row=next(r for r in json.loads((HERE/"COHORT.json").read_text())["ordered"] if r["field"]==field)
        return dict(base,period_days=float(row["source"][2]),values={"published_period_days":float(row["source"][2]),"published_source_attribution":row["source"][3]},scientific_note="Published Table 7 candidate for comparison, not late-sector validation.")
    if kind=="aperture":
        pt=d["pt"];px=d["px"];keep=part(pt)==0;pt,px=pt[keep],px[keep];mx=px.reshape(len(pt),-1)
        sel=np.all(np.isfinite(mx),axis=0);amp=np.full(mx.shape[1],np.nan)
        if np.any(sel):
            w=np.linalg.lstsq(design(pt,p),mx[:,sel],rcond=None)[0];amp[sel]=np.hypot(w[2],w[3])
        amp=amp.reshape(px.shape[1:]);opt=(d["mask"]&2)!=0
        if not np.isfinite(amp).any():return dict(base,values={},scientific_note="No finite pixel amplitude.")
        rc=np.unravel_index(np.nanargmax(amp),amp.shape);rankdata=amp[np.isfinite(amp)]
        return dict(base,values={"peak_pixel_rc":[int(x) for x in rc],"in_pipeline_aperture":bool(opt[rc]),
            "peak_amplitude_e_per_s":round(float(amp[rc]),4),"median_full_pixel_amplitude":round(float(np.median(rankdata)),4),
            "optimal_pixel_count":int(opt.sum()),"shape":list(amp.shape)},scientific_note="Early discovery-block harmonic image; an outside peak flags possible re-extraction, not a source identity.")
    if kind=="spectrum":
        return dict(base,values={"pdc_peaks":search(t,y,6),"sap_peaks":search(t,d["sap"][ix],4)},scientific_note="Ordinary independent period scan on the available discovery blocks.")
    if kind=="harmonics":
        return dict(base,values={"period_amplitude_pairs":[[round(q,6),round(fitvar(t,y,q),4)] for q in [p/2,p,2*p] if .1<=q<=9]},scientific_note="Frequency-family amplitudes on early discovery photons, in parts per thousand.")
    if kind=="stability":
        mid=np.median(t)
        return dict(base,values={"first_half_amplitude_ppt":round(fitvar(t[t<=mid],y[t<=mid],p),4),"second_half_amplitude_ppt":round(fitvar(t[t>mid],y[t>mid],p),4)},scientific_note="Within discovery blocks only; estimates from two chronological halves.")
    raise ValueError(kind)
def cur_decide(field,source):
    d=data(field);t,y=d["t"],d["pdc"]
    refs=[None]+[r["period_days"] for r in initial(field)["pdc_candidates"][:2]]
    pool=[(p,"ordinary") for p in refs]
    for p in source:
        if .1<=p<=9 and all(other is None or abs(p-other)>max(1.e-6,1.e-5*other) for other,_ in pool):pool.append((p,"source"))
    costs=[err(t,y,p,1)[0] for p,_ in pool];win=int(np.argmin(costs))
    p,origin=pool[win]
    return {"period_days":p,"origin":origin,"validation_mse_ppt2":float(costs[win]),"validation_candidates":[[f,o,e] for (f,o),e in zip(pool,costs)],"fit":err(t,y,p,1)[1].tolist(),"current_decision":"hold_trend" if p is None else "forward_ephemeris"}
def current_test(field,decision):
    d=data(field);t,y=d["t"],d["pdc"];p=decision["period_days"]
    e,_,pred=err(t,y,p,2);et,_,_=err(t,y,None,2)
    import hashlib
    return {"test_hours":len(pred),"held_current_mse_ppt2":e,"trend_mse_ppt2":et,"accepted_period_beats_trend":p is not None and e<et,"prediction_sha256":hashlib.sha256(pred.tobytes()).hexdigest()}
