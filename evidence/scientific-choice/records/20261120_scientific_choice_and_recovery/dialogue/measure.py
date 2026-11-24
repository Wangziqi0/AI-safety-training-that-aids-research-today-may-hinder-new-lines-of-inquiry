from pathlib import Path
import sys,json
import numpy as np
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/'practice'))
from early import data,part,design
def measure(field,p):
    d=data(field);use=part(d['pt'])==0;t=d['pt'][use];px=d['px'][use];ap=(d['mask']&2)!=0
    good=np.isfinite(px).all(axis=0)
    yy,xx=np.indices(ap.shape);G=design(t,p)
    def amp(x):
        c=np.linalg.lstsq(G,x,rcond=None)[0];return np.hypot(c[2],c[3])
    a=np.full(ap.shape,np.nan);a[good]=amp(px[:,good])
    coord=lambda v:list(map(int,np.unravel_index(np.nanargmax(v),v.shape)))
    peak=coord(a);core=coord(np.where(ap&good,np.mean(px,axis=0),np.nan));outside=coord(np.where(~ap,a,np.nan))
    return dict(field=field,period_days=p,n=int(len(t)),finite_pixels=int(good.sum()),peak_rc=peak,peak_inside=bool(ap[tuple(peak)]),core_rc=core,core_amp=float(a[tuple(core)]),pipeline_amp=float(amp(px[:,ap&good].sum(axis=1))),outside_rc=outside,outside_amp=float(a[tuple(outside)]),peak_amp=float(a[tuple(peak)]),units='electrons/second',centroid_aperture_xy_amp_pixel=[float(amp((px[:,ap&good]*axis[ap&good]).sum(axis=1)/px[:,ap&good].sum(axis=1))) for axis in [xx,yy]])
if __name__=='__main__':
    for f,p in [('P01',.471341),('P04',1.175171)]: print(json.dumps(measure(f,p)))
