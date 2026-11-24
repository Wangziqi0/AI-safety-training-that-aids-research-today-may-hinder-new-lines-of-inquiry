"""Independently reproduce the unusual ridge forecasts using centered, augmented least squares."""
import json
import numpy as np
from register import ROOT, DOWN, PRACTICE, receiver, digest, json_bytes, save
r=next(x for x in json.loads((ROOT/"RESULT.json").read_text()) if isinstance(x.get("period_days"),list))
f=r["field"]
with np.load(PRACTICE/"fields"/(f+".npz")) as ds:
    t=ds["late_pt"]; cube=ds["late_px"]
meta=json.loads((DOWN/"ordinary_lock"/(f+"_access.json")).read_text())
y=receiver.extract(cube,meta["masks"]["spoc"])
end=meta["fit_n"]+meta["validation_n"]
receipts={}
for key,periods,file in (("full",r["period_days"],r["slot"]+".npz"),
                ("leave_supplied_term_out",[p for p in r["period_days"] if p!=1.175171],r["slot"]+"_term_out.npz")):
    D=np.stack([fn(2*np.pi*(t-t[0])/p) for p in periods for fn in (np.sin,np.cos)],axis=1)
    def predict(n,start,stop,short,orbit):
        yy=y[:n]
        X=D[:n]; finite=np.isfinite(yy)
        yy=yy[finite]; X=X[finite]
        xmean=np.mean(X,axis=0); ymean=np.mean(yy)
        weight=np.repeat([orbit if p==13.7 else short for p in periods],2)
        Xaug=np.vstack((X-xmean,np.diag(np.sqrt(len(yy)*weight))))
        zaug=np.concatenate((yy-ymean,np.zeros(len(weight))))
        beta=np.linalg.lstsq(Xaug,zaug,rcond=None)[0]
        return ymean+(D[start:stop]-xmean)@beta
    trials=[]
    for lam in (.01,.1,1.,10.,100.):
        for orbit in (.01,.1,1.,10.,100.):
            errors=[]
            for k in (5,6,7):
                first=end*k//10;last=end*(k+3)//10
                errors.append(float(np.mean(abs(y[first:last]-predict(first,first,last,lam,orbit)))))
            trials.append((np.mean(errors),-orbit,-lam))
    _,mo,ml=min(trials)
    final=predict(end,end,len(t),-ml,-mo)
    archived=np.load(ROOT/"predictions"/file)["prediction"]
    error=float(np.max(abs(archived-final)))
    assert error<1e-9
    receipts[key]=dict(lambda_short=-ml,lambda_orbit=-mo,max_abs_difference_e_s=error,
                        heldout_mae_e_s=float(np.mean(abs(y[end:]-final))))
save(ROOT/"RIDGE_REPLAY.json",json_bytes(receipts))
print(receipts)
