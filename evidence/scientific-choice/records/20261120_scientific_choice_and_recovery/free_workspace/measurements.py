from functools import lru_cache
from pathlib import Path
import sys
import numpy as np
from astropy.timeseries import LombScargle
from scipy.signal import find_peaks
PR=Path(__file__).resolve().parent.parent/'practice'
sys.path.insert(0,str(PR))
import early
from early import part,design,search

@lru_cache(None)
def normalized(field):
    with np.load(PR/'fields'/(field+'.npz')) as src:
        d={k[6:]:src[k] for k in src.files if k.startswith('early_')}
    start=d['t'][0]
    d['t']=d['t']-start
    d['pt']=d['pt']-start
    for key in ('pdc','sap'):
        d[key]=1000*(d[key]/np.nanmedian(d[key][part(d['t'])==0])-1)
    return d

early.data=normalized
def fit(t,y,p,n=1):
    ok=np.isfinite(t)&np.isfinite(y)
    t,y=t[ok],y[ok]
    if len(t)<5+2*n:raise ValueError('insufficient finite measurements')
    X=np.column_stack([np.ones(len(t)),t-t.mean()]+[h(2*np.pi*j*t/p) for j in range(1,n+1) for h in (np.sin,np.cos)])
    co=np.linalg.lstsq(X,y,rcond=None)[0]
    return co,X@co,y-X@co
def rd(x):
    v=float(x)
    return round(v,6) if np.isfinite(v) else None
def grid(t):return np.linspace(1/9,10,max(800,int(np.ptp(t)*9.9*9)+1))
def phase(t,y,p):
    co,pred,res=fit(t,y,p,2)
    ph=(t/p)%1
    bins=[y[(ph>=j/10)&(ph<(j+1)/10)] for j in range(10)]
    return dict(bin_median_ppt=[rd(np.median(v)) if len(v) else None for v in bins],
                bin_count=[len(v) for v in bins],two_harmonic_residual_rms_ppt=rd(np.mean(res**2)**.5),
                fundamental_amp_ppt=rd(np.hypot(*co[2:4])),second_amp_ppt=rd(np.hypot(*co[4:6])))
def peak(t,y):
    r=search(t,y,3)
    return r[0] if r else None
@lru_cache(None)
def measure(field,kind,p):
    d=normalized(field); sel=part(d['t'])==0; t=d['t'][sel]; y=d['pdc'][sel]
    ps=part(d['pt'])==0; pt,px=d['pt'][ps],d['px'][ps];mask=(d['mask']&2)!=0
    base={'kind':kind,'period_days':p}
    if kind=='fold':
        ans=phase(t,y,p);note='Ten phase-bin medians and two-harmonic least squares on discovery PDC. Unit is parts per thousand.'
    elif kind=='spectrum':
        ans={'PDC_peaks':search(t,y,4),'SAP_peaks':search(t,d['sap'][sel],4)};note='Independent floating-mean Lomb–Scargle periodograms, 0.1 to 9 d.'
    elif kind=='harmonics':
        ans={}
        for k in (.5,1.,2.):
            q=k*p
            if .1<=q<=9:
                a,b,r=fit(t,y,q,2)
                ans[str(rd(q))]=dict(rms=rd(np.mean(r**2)**.5),fundamental=rd(np.hypot(*a[2:4])),second=rd(np.hypot(*a[4:6])))
        note='Compared fundamental plus second-harmonic fits at half, candidate and double period.'
    elif kind=='temporal':
        ans={}
        for tag,m in [('early',t<=np.median(t)),('late',t>np.median(t))]:
            c,_,r=fit(t[m],y[m],p)
            ans[tag]=dict(n=int(m.sum()),strongest=peak(t[m],y[m]),amplitude_ppt=rd(np.hypot(*c[2:])),
                          phase_cycles_from_common_t0=rd(np.arctan2(c[3],c[2])/(2*np.pi)))
        note='Split discovery blocks at their median time; independent period search plus common-epoch amplitude and phase at requested period.'
    elif kind=='window':
        f=grid(t);w=abs(np.exp(-2j*np.pi*t[:,None]*f).mean(axis=0))**2
        ix=find_peaks(w)[0];ix=ix[np.argsort(-w[ix])][:5]
        ans=dict(top_window_frequency_power=[[rd(f[j]),rd(w[j])] for j in ix],
                 window_power_at_candidate=rd(abs(np.exp(2j*np.pi*t/p).mean())**2),frequency_resolution_per_day=rd(1/np.ptp(t)))
        note='Unweighted spectral window from actual discovery timestamps. Window coincidences flag potential aliases.'
    elif kind=='residual':
        _,_,r=fit(t,y,p,1);ans={'residual_peaks':search(t,r,4),'residual_rms_ppt':rd(np.mean(r*r)**.5)}
        note='Subtracted least-squares sinusoid and linear trend from discovery PDC, then recomputed Lomb–Scargle.'
    elif kind=='uncertainty':
        f=np.linspace(max(1/9,1/p-1/np.ptp(t)),min(10,1/p+1/np.ptp(t)),300)
        dates=np.unique(np.floor(t+1e-8))
        vals=[]
        for day in dates:
            ix=np.floor(t+1e-8)!=day
            if ix.sum()>=15:vals.append(1/f[np.argmax(LombScargle(t[ix],y[ix]).power(f))])
        ans={'local_leave_one_discovery_day_out_range_days':[rd(min(vals)),rd(max(vals))],
             'blocks':len(vals),'rayleigh_width_at_candidate_days':rd(p*p/np.ptp(t))}
        note='Sensitivity of local frequency maximum to deleting each observed day. This finite range is not a probabilistic confidence interval.'
    elif kind=='fap':
        ls=LombScargle(t,y);v=float(ls.power(1/p));ans={'relative_power':rd(v),'Baluev_FAP':float(ls.false_alarm_probability(v,method='baluev',minimum_frequency=1/9,maximum_frequency=10))}
        note='Approximate Lomb–Scargle maximum-peak false alarm under independent Gaussian noise over 1/9–10 cycles/day; correlated red noise not calibrated.'
    elif kind=='pixel':
        ans=early.probe(field,'aperture',p)['values'];note='Pixelwise sinusoidal amplitude; map maximum inside/outside pipeline mask is a warning, not an established source identity.'
    elif kind=='apertures':
        ans={}
        for label,selpx in [('pipeline',mask),('outside',~mask),('central_3x3',np.indices(mask.shape)[0]*0==1)]:
            if label=='central_3x3':
                i,j=np.array(mask.shape)//2;selpx[i-1:i+2,j-1:j+2]=True
            goodpx=selpx & (np.isfinite(px).mean(axis=0)>.98)
            if not goodpx.any():continue
            series=np.nansum(px[:,goodpx],axis=1);med=np.median(series)
            if med==0:continue
            z=(series/med-1)*1000;c,_,_=fit(pt,z,p)
            ans[label]=dict(pixels=int(goodpx.sum()),peak=peak(pt,z),amplitude_ppt=rd(np.hypot(*c[2:])))
        note='Discovery-pixel extractions summed separately over pipeline, outside, and central 3x3 masks; amplitude and strongest period compare spatial origin, without calibrated background.'
    elif kind=='centroid':
        flat=px.reshape(len(px),-1);good=mask.flatten()&(np.isfinite(flat).mean(axis=0)>.98)
        rr,cc=np.indices(mask.shape);z=flat[:,good];w=np.where(np.isfinite(z),z,0)
        axes=[]
        for axis in [rr,cc]:
            pos=(w@axis.flatten()[good])/w.sum(axis=1);c,_,_=fit(pt,pos,p)
            axes.append({'candidate_amplitude_pixels':rd(np.hypot(*c[2:])), 'peak':peak(pt,pos)})
        ans={'stamp_rows_columns':axes};note='Flux-weighted discovery centroid within pipeline aperture. No external pointing correction or astrometric match.'
    elif kind in ('inventory','inspect','quality','mean','pixel_corr'):
        with np.load(PR/'fields'/(field+'.npz')) as file:
            t0=float(file['early_t'][0]);raw_pd=file['early_pdc'][sel]
        if kind=='inventory':
            ans={'telescope':'TESS','discovery_rows':len(t),'start_archive_time':rd(t0+t.min()),'end_archive_time':rd(t0+t.max()),
                 'span_days':rd(np.ptp(t)),'median_table_spacing_days':rd(np.median(np.diff(t))),
                 'stamp_dimensions':list(mask.shape),'pipeline_aperture_pixels':int(mask.sum()),'stamp_rows':len(pt)}
            note='Counts/timestamps for first-sector discovery blocks in archived hourly binned tables, not the native exposure time. Each row of pixels is a stamp. Anonymous field retained.'
        elif kind=='inspect':
            ii=np.linspace(0,len(t)-1,8,dtype=int);m=np.nanmedian(px,axis=0);center=np.array(m.shape)//2;i,j=center
            ans={'discovery_time_ppt_samples':[[rd(t[a]),rd(y[a])] for a in ii],
                 'median_central_3x3_stamp_electrons_per_s':[[rd(v) for v in row] for row in m[i-1:i+2,j-1:j+2]]}
            note='Eight actual time-ordered measurements and central portion of temporal median stamp; compact table.'
        elif kind=='quality':
            freq=1/p
            c,_,res=fit(t,y,p)
            ans={'n_finite_pdc':int(np.isfinite(y).sum()),'stamp_finite_fraction':rd(np.isfinite(px).mean()),
                 'pdc_median_absolute_deviation_ppt':rd(np.median(abs(y-np.median(y)))),
                 'largest_sampling_gap_days':rd(np.diff(t).max()),'linear_trend_with_sinusoid_ppt_per_day':rd(c[1])}
            note='Recorded finite coverage, gap and fitted drift on discovery blocks. Instrument-specific engineering logs absent.'
        elif kind=='mean':
            ans={'mean_archive_PDC':rd(np.mean(raw_pd)),'mean_normalized_ppt':rd(np.mean(y)), 'sample_sd_ppt':rd(np.std(y,ddof=1))}
            note='Arithmetic mean of discovery-block observations and sample standard deviation; raw archive units are electrons per second.'
        else:
            ix=np.searchsorted(pt,t);ix=np.clip(ix,0,len(pt)-1)
            prev=np.maximum(0,ix-1);ix=np.where(abs(t-pt[prev])<abs(t-pt[ix]),prev,ix); keep=abs(t-pt[ix])<.021
            if keep.sum()<10:raise ValueError('too few matched PDC/pixel times')
            a=px[ix[keep]].reshape(keep.sum(),-1);y1=y[keep];corr=[]
            for j in range(a.shape[1]):
                ok=np.isfinite(a[:,j])&np.isfinite(y1)
                if ok.sum()>=15 and np.std(a[ok,j])>0:
                    corr.append((float(np.corrcoef(a[ok,j],y1[ok])[0,1]),j))
            corr.sort(key=lambda v:-abs(v[0]))
            ans={'matched_rows':int(keep.sum()),'top_absolute_pearson_r':[[rd(v),list(map(int,np.unravel_index(j,mask.shape))),bool(mask.flat[j])] for v,j in corr[:4]]}
            note='Zero-lag Pearson cross-correlation between PDC flux and pixels matched within 0.021 days; aperture-integrated and individual pixel series share photons.'
        return dict(kind=kind,period_days=None,values=ans,scientific_note=note)
    elif kind=='catalogue':
        record=early.probe(field,'catalogue',p)
        return record
    else:raise ValueError(kind)
    return dict(base,values=ans,scientific_note=note)
