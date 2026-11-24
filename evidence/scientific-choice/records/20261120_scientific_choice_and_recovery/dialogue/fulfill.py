"""Execute each selected analysis on the discovery blocks and keep the returned numbers."""
from adjudicate import read,write,HERE
from measure import measure,part,data,design
from astropy.timeseries import LombScargle
import numpy as np
def fulfill(field,p,operation):
    d=data(field);u=part(d['pt'])==0;t=d['pt'][u];pixels=d['px'][u]
    a=measure(field,p) if 'pixel_' in operation or 'contrast' in operation or 'core_pipeline' in operation else {}
    out={}
    if 'contrast' in operation:
        out['core_pipeline_outside']=a
    if 'core_pipeline' in operation:
        out['core_pipeline']={k:a[k] for k in ('core_rc','core_amp','pipeline_amp','units')}
    if 'pixel_candidate' in operation:
        out['candidate_pixel_fit']={k:a[k] for k in ('peak_rc','peak_inside','peak_amp','period_days','finite_pixels','units')}
        out['candidate_pixel_fit']['limit']='spatial signal proxy only; no object-level attribution'
    if 'pixel_periodogram' in operation:
        f=np.linspace(1/9,10,max(800,int(np.ptp(t)*9.9*9)+1))
        ps=[]
        for i,j in np.ndindex(pixels.shape[1:]):
            y=pixels[:,i,j];good=np.isfinite(y)
            if good.sum()<12:continue
            ls=LombScargle(t[good],y[good]);s=ls.power(f);idx=int(np.nanargmax(s))
            ps.append(dict(rc=[i,j],peak_days=float(1/f[idx]),peak_power=float(s[idx]),power_at_candidate=float(ls.power(1/p)),inside=bool((d['mask'][i,j]&2)!=0)))
        out['pixel_periodograms']=dict(frequency_min_per_day=float(f[0]),frequency_max_per_day=float(f[-1]),n_grid=len(f),pixels=ps)
    if 'light_' in operation:
        u=part(d['t'])==0;lt=d['t'][u];y=d['pdc'][u];y=(y+1000)/np.median(y+1000)*1000-1000
        ls=LombScargle(lt,y);f=np.linspace(1/9,10,max(800,int(np.ptp(lt)*9.9*9)+1))
        co=np.linalg.lstsq(design(lt,p),y,rcond=None)[0]
        out['light_curve']=dict(period_days=p,candidate_amplitude_ppt=float(np.hypot(*co[2:])),power_at_candidate=float(ls.power(1/p)))
        if 'light_periodogram' in operation:
            s=ls.power(f);from scipy.signal import find_peaks
            ix=find_peaks(s)[0];out['light_curve']['top_period_power']=[[float(1/f[j]),float(s[j])] for j in ix[np.argsort(-s[ix])[:5]]]
    return out
if __name__=='__main__':
    import sys
    stage=sys.argv[1];codes=read(stage+'_codes.jsonl');raw={x['id']:x for x in read(stage+'_raw.jsonl')}
    results=[]
    for c in codes:
        r=raw[c['id']];p=.471341 if '0.471341' in r['messages'][1]['content'] else 1.175171;f='P01' if p==.471341 else 'P04'
        payload=fulfill(f,p,c['operation'])
        results.append(dict(id=c['id'],field=f,period_days=p,operation=c['operation'],results=payload))
    write(stage+'_fulfilled.jsonl',results)
