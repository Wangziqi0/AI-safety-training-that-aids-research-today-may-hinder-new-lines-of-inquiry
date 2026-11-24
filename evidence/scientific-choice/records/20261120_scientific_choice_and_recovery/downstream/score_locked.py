"""Apply previously locked photometry/period decisions to untouched late observations."""
import argparse
import hashlib
from pathlib import Path
import numpy as np
from receiver import HERE, PRACTICE, FIELDS, design, digest, dump, extract, fitted, json, jsonl, mae, save_rows

def compact_key(field, mask, component):
    stable=json.dumps([field,mask,component],separators=(",",":"))
    return field+"_"+hashlib.sha256(stable.encode()).hexdigest()[:16]

def fit_map(t, cube, component, optimal, end):
    values=cube[:end].reshape(end,-1)
    result=np.full(values.shape[1],np.nan)
    if not isinstance(component,(float,int)):
        return result.reshape(cube.shape[1:]), None, None
    basis=design(t[:end],component)
    phase=np.linspace(0,2*np.pi,100,endpoint=False)
    profile=np.stack((np.cos(phase),np.sin(phase),np.cos(2*phase),np.sin(2*phase)),axis=1)
    for j,series in enumerate(values.T):
        keep=np.isfinite(series)
        if keep.sum()<max(10,.95*end):
            continue
        beta=np.linalg.lstsq(basis[keep],series[keep],rcond=None)[0]
        result[j]=np.ptp(profile @ beta[1:])
    if not np.isfinite(result).any():
        return result.reshape(cube.shape[1:]),None,None
    peak=int(np.nanargmax(result))
    return result.reshape(cube.shape[1:]),peak,bool(peak not in optimal)

def score(base):
    lock=json.loads((base/"CHOICES_LOCK.json").read_text())
    for raw, expected in lock["files"].items():
        path=Path(raw)
        if not path.is_absolute():
            path=HERE.parent/path
        if digest(path)!=expected:
            raise ValueError(f"data changed since commitment: {path}")
    if (base/"SCORED_LOCK.json").exists():
        raise FileExistsError("this decision set was already scored")
    selections=jsonl(base/"choices.jsonl")
    outcomes=[]
    artifacts=base/"products"
    artifacts.mkdir(exist_ok=True)
    for field in FIELDS:
        plans=[r for r in selections if r["field"]==field]
        meta=json.loads((base/(field+"_access.json")).read_text())
        with np.load(PRACTICE/"fields"/(field+".npz")) as ds:
            cube=ds["late_px"]; t=ds["late_pt"]
        fit=meta["fit_n"];end=fit+meta["validation_n"]
        observed=extract(cube,meta["masks"]["spoc"])
        test=observed[end:]
        # Fixed normalization, independent of product and all held-out target observations.
        scale=float(np.nanmean(abs(observed[:fit]-np.nanmedian(observed[:fit]))))
        if not np.isfinite(scale) or scale<=0:
            raise ValueError(f"undefined physical flux scale: {field}")
        monotone=mae(test,np.full(len(test),np.nanmedian(observed[:end])))/scale
        values={}
        aperture_fluxes={name:extract(cube,mask) for name,mask in meta["masks"].items()}
        np.savez_compressed(artifacts/(field+"_observed.npz"),time=t[end:],spoc_flux=test,
                            all_time=t,fit_end=fit,validation_end=end,
                            fit_scale=scale,units="electron/s",**aperture_fluxes)
        for row in plans:
            key=compact_key(field,row["aperture"],row["component"])
            if key not in values:
                mask=meta["masks"][row["aperture"]]
                series=extract(cube,mask)
                pred=fitted(t[:end],series[:end],observed[:end],row["component"],t[end:])
                loss=mae(test,pred)
                amp,peak,flag=fit_map(t,cube,row["component"],meta["masks"]["spoc"],end)
                mode={"constant":"STOP_CONSTANT","trend":"TREND_ONLY"}.get(row["component"],
                    "PERIODIC_PERIPHERAL_FOLLOWUP" if flag else "PERIODIC_TARGET_FOLLOWUP")
                if isinstance(row["component"],float) and flag is None:
                    mode="PERIODIC_SPATIAL_STATUS_UNKNOWN"
                if not np.isfinite(loss):
                    raise ValueError(f"no test forecast: {key}")
                np.savez_compressed(artifacts/(key+".npz"),time=t[end:],prediction=pred,
                        aperture_flat=np.asarray(mask),shape=np.array(amp.shape),
                        peak_to_peak_amplitude=amp,units="electron/s")
                values[key]={"artifact":key,"mae_electrons_s":loss,"normalized_mae":loss/scale,
                        "stop_normalized_mae":monotone,"improvement_over_stop":monotone-loss/scale,
                        "disposition":mode,"peak_pixel_flat":peak,"peripheral_flag":flag,
                        "test_n":int(np.sum(np.isfinite(test)&np.isfinite(pred)))}
            outcomes.append({**row,**values[key]})
    save_rows(base/"results.jsonl",outcomes)
    dump(base/"SCORED_LOCK.json",{"n_products":lock["assigned_products"],"n_decisions":len(outcomes),
        "n_unique_predictions":len(set(r["artifact"] for r in outcomes)),
        "scores_sha256":digest(base/"results.jsonl"),"choices_lock_sha256":digest(base/"CHOICES_LOCK.json"),
        "implementation_sha256":digest(Path(__file__))})
    print(f"scored {len(outcomes)} locked decisions in {base}")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("base",type=Path)
    score(parser.parse_args().base)
