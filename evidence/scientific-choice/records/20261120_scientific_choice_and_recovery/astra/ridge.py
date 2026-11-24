"""Execute the explicit P04 H scientist method. No observed flux beyond the fit prefix is an input."""
import numpy as np

def forecast(t,flux,when,periods):
    reference=t[0]
    def basis(times):
        columns=[np.ones(len(times))]
        for p in periods:
            phase=2*np.pi*(times-reference)/p
            columns.extend([np.sin(phase),np.cos(phase)])
        return np.column_stack(columns)
    X,xtest=basis(t),basis(when)
    def estimate(start,end,short,orbit):
        mat,y=X[start:end],flux[start:end]
        good=np.isfinite(y)&np.isfinite(mat).all(axis=1)
        mat,y=mat[good],y[good]
        regs=[0.]+[v for p in periods for v in ([orbit,orbit] if p==13.7 else [short,short])]
        return np.linalg.solve(mat.T@mat/len(y)+np.diag(regs),mat.T@y/len(y))
    trials=[]
    n=len(t)
    folds=[(n*k//10,n*(k+3)//10) for k in (5,6,7)]
    for short in (.01,.1,1.,10.,100.):
        for orbit in (.01,.1,1.,10.,100.):
            errors=[]
            for train,end in folds:
                beta=estimate(0,train,short,orbit)
                errors.append(float(np.nanmean(abs(flux[train:end]-X[train:end]@beta))))
            trials.append(dict(short=short,orbit=orbit,fold_mae=errors,avg_mae=float(np.mean(errors))))
    best=min(trials,key=lambda r:(r["avg_mae"],-r["orbit"],-r["short"]))
    beta=estimate(0,n,best["short"],best["orbit"])
    return xtest@beta,dict(periods=periods,elapsed_ref=reference,folds=folds,penalties=best,all_trials=trials,beta=beta.tolist())
