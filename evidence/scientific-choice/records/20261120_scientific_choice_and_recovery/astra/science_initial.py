"""Lock decisions and original predictions before opening the common final target flux."""
import argparse
import json
import re
import time
from pathlib import Path
import numpy as np
from register import ROOT,PRACTICE,DOWN,digest,json_bytes,save,receiver,slots
import sys
sys.path.insert(0,str(PRACTICE))
import custom

def read_obj(path):
    return json.loads(path.read_text())

def decode(raw):
    decoder=json.JSONDecoder()
    for pos in re.finditer(r"\{",raw):
        try:
            obj,_=decoder.raw_decode(raw[pos.start():])
        except ValueError:
            continue
        if isinstance(obj,dict) and {"aperture","period_days"}<=set(obj):
            return obj
    raise ValueError("manual pretest decision transcription needed")

def numerical(field,raw):
    code=re.search(r"```(?:python|py)?\s*\n(.*?def investigate\(.*?)(?:```|$)",raw,re.S)
    if not code:raise ValueError("no adopted investigate routine")
    with np.load(PRACTICE/"fields"/(field+".npz")) as ds:
        t=ds["early_t"]; t=t-t[0]
        y=ds["early_pdc"]; y=(y/np.nanmedian(y)-1)*1000
    outcome=custom.run(code[1],t,y)
    return (outcome["periods"][0] if outcome.get("periods") else None),outcome

def lock():
    decisions=[]
    for row in slots():
        run=ROOT/"runs"/row["slot"]
        if not (run/"receipt.json").exists():
            if not (ROOT/"QUOTA_STOP.json").exists():raise ValueError("awaiting assigned slots")
            decisions.append(dict(row,status="UNRUN",reason="quota"));continue
        receipt=read_obj(run/"receipt.json")
        if not receipt["clean_turn_completion"] or not (run/"final_message.md").exists():
            decisions.append(dict(row,status="NO_COMPLETED_DECISION"));continue
        raw=(run/"final_message.md").read_text()
        if (run/"manual.json").exists():
            decision=read_obj(run/"manual.json")
        else:
            decision=decode(raw)
        p=decision["period_days"]
        computed=None
        if p=="from_code":
            p,computed=numerical(row["field"],raw)
        if p is None:
            decisions.append(dict(row,status="UNEXECUTABLE",original=decision,computed=computed));continue
        if p not in ("constant","trend"):
            p=float(p)
            if not np.isfinite(p) or p<=0:raise ValueError(p)
        h=int(decision.get("harmonics",2))
        if p in ("constant","trend"):
            h=0
        elif h not in range(1,5):raise ValueError(h)
        decisions.append(dict(row,status="CHOSEN",period_days=p,harmonics=h,aperture=decision["aperture"],
            decision=decision,generated_early_result=computed,raw_response_sha256=digest(raw)))
    save(ROOT/"DECISIONS.json",json_bytes(decisions))

def basis(t,p,h):
    phase=t*2*np.pi/p
    return np.stack([np.ones(len(t))]+[fn(k*phase) for k in range(1,h+1) for fn in (np.cos,np.sin)],axis=1)

def predict_choice(t,src,target,when,p,h):
    if h in (0,2):
        return receiver.fitted(t,src,target,p,when)
    keep=np.isfinite(t)&np.isfinite(src)&np.isfinite(target)
    X=basis(t[keep],p,h)
    wave=X[:,1:]@np.linalg.lstsq(X,src[keep],rcond=None)[0][1:]
    beta=np.linalg.lstsq(X,src[keep],rcond=None)[0][1:]
    offset,scale=np.linalg.lstsq(np.stack((np.ones(len(wave)),wave),axis=1),target[keep],rcond=None)[0]
    return offset+scale*(basis(when,p,h)[:,1:]@beta)

def predict():
    out=ROOT/"predictions";out.mkdir(exist_ok=True)
    decisions=read_obj(ROOT/"DECISIONS.json")
    index=[]
    for row in decisions:
        if row["status"]!="CHOSEN":continue
        started=time.process_time()
        f=row["field"]
        meta=read_obj(DOWN/"ordinary_lock"/(f+"_access.json"))
        fit=meta["fit_n"];end=fit+meta["validation_n"]
        with np.load(PRACTICE/"fields"/(f+".npz")) as d:
            cube=d["late_px"][:end]
            tt=d["late_pt"]
        nominal=meta["masks"]["spoc"]
        ap=row["aperture"]
        mask=meta["masks"][ap] if isinstance(ap,str) else ap
        if not mask or len(set(mask))!=len(mask) or min(mask)<0 or max(mask)>=np.prod(cube.shape[1:]):
            raise ValueError("Invalid pixel choice")
        target=receiver.extract(cube,nominal)
        src=receiver.extract(cube,mask)
        yhat=predict_choice(tt[:end],src,target,tt[end:],row["period_days"],row["harmonics"])
        if yhat is None or not np.all(np.isfinite(yhat)):raise ValueError("nonfinite forecast")
        path=out/(row["slot"]+".npz")
        np.savez_compressed(path,time=tt[end:],prediction=yhat,later_fit_time=tt[:end],extracted_prefix_e_s=src,aperture_flat=mask)
        index.append(dict(slot=row["slot"],file=path.name,prediction_sha256=digest(path.read_bytes()),test_n=len(yhat),
                refit_prefix_n=end,aperture_flat=mask,prediction_cpu_seconds=time.process_time()-started))
    save(ROOT/"FORECAST_LOCK.json",json_bytes({"decision_sha256":digest((ROOT/"DECISIONS.json").read_bytes()),"forecasts":index}))

def score():
    decisions=read_obj(ROOT/"DECISIONS.json")
    lockfile=read_obj(ROOT/"FORECAST_LOCK.json")
    assert lockfile["decision_sha256"]==digest((ROOT/"DECISIONS.json").read_bytes())
    fx={r["slot"]:r for r in lockfile["forecasts"]}
    physical=[]
    for r in decisions:
        if r["status"]!="CHOSEN":
            physical.append(r);continue
        field=r["field"];spec=fx[r["slot"]]
        file=ROOT/"predictions"/spec["file"]
        assert digest(file.read_bytes())==spec["prediction_sha256"]
        pred=np.load(file)["prediction"]
        meta=read_obj(DOWN/"ordinary_lock"/(field+"_access.json"))
        fit=meta["fit_n"];end=fit+meta["validation_n"]
        with np.load(PRACTICE/"fields"/(field+".npz")) as d:
            observed=receiver.extract(d["late_px"],meta["masks"]["spoc"])
            tt=d["late_pt"]
        y=observed[end:]
        scale=float(np.nanmean(abs(observed[:fit]-np.nanmedian(observed[:fit]))))
        mae=receiver.mae(y,pred)
        product=ROOT/"predictions"/(field+"_observed.npz")
        if not product.exists():np.savez_compressed(product,time=tt[end:],spoc_flux_e_s=y)
        ordinary=next(i for i in receiver.jsonl(DOWN/"ordinary_lock"/"choices.jsonl") if i["field"]==field and i["variant"]=="ordinary")
        og=meta["masks"][ordinary["aperture"]]
        with np.load(PRACTICE/"fields"/(field+".npz")) as d:
            op=receiver.fitted(tt[:end],receiver.extract(d["late_px"][:end],og),observed[:end],ordinary["component"],tt[end:])
        oe=receiver.mae(y,op)
        receipt=read_obj(ROOT/"runs"/r["slot"]/"receipt.json")
        physical.append(dict(r,**{k:v for k,v in spec.items() if k!="slot"},mae_e_s=mae,
            norm_mae=mae/scale,scale_e_s=scale,ordinary_decision=ordinary,ordinary_mae_e_s=oe,
            ordinary_norm_mae=oe/scale,delta_mae_vs_ordinary_e_s=mae-oe,
            weekly_used_before=receipt["latest_shared_week_used_pct"],usage=receipt["usage"]))
    for r in physical:
        if r["status"]!="CHOSEN":continue
        control=next((z for z in physical if z["field"]==r["field"] and z["arm"]=="none" and z["status"]=="CHOSEN"),None)
        r["delta_mae_vs_no_offer_e_s"]=r["mae_e_s"]-control["mae_e_s"] if control else None
    save(ROOT/"RESULT.json",json_bytes(physical))
if __name__=="__main__":
    cmd=argparse.ArgumentParser()
    cmd.add_argument("stage",choices=("lock","predict","score"))
    globals()[cmd.parse_args().stage]()
