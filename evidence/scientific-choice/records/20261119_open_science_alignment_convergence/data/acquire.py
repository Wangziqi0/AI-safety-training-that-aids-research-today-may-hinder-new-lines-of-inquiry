"""Download named public SPOC records without proxy/credentials; pack real early/later data.

No scientific treatment model or predicted method is used for selection.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import numpy as np
from astropy.io import fits

HERE=Path(__file__).resolve().parent
HOST="https://stpubdata.s3.amazonaws.com"

def session():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))

def retrieve(target,sector,product,cache):
    tic=int(target["tic"]);key=f"{tic:016d}"
    branch=f"tess/public/tid/s{sector:04d}/"+"/".join(key[i:i+4] for i in range(0,16,4))+"/"
    with session().open(HOST+"/?"+urllib.parse.urlencode({"list-type":"2","prefix":branch}),timeout=35) as resp:
        xml=ET.fromstring(resp.read())
    objects=[(x.findtext("{*}Key"),int(x.findtext("{*}Size")),x.findtext("{*}ETag").strip('"')) for x in xml.findall("{*}Contents")]
    match=[x for x in objects if x[0].endswith("-s_"+product+".fits")]
    if len(match)!=1:raise RuntimeError(f"Found {len(match)} standard {product} for {target['family']} sector {sector}")
    remote,size,etag=match[0];name=Path(remote).name;dest=cache/name
    if not dest.is_file() or dest.stat().st_size!=size:
        part=dest.with_suffix(".part")
        for attempt in range(4):
            offset=part.stat().st_size if part.exists() else 0
            if offset==size:break
            try:
                req=urllib.request.Request(HOST+"/"+remote,headers={"Range":f"bytes={offset}-{size-1}"} if offset else {})
                with session().open(req,timeout=45) as src:
                    if offset and (src.status!=206 or not src.headers.get("Content-Range","").startswith(f"bytes {offset}-")):
                        raise IOError("Server did not resume pinned object")
                    with part.open("ab" if offset else "wb") as out:
                        while block:=src.read(512*1024):out.write(block)
                if part.stat().st_size==size:break
            except (OSError,TimeoutError) as exc:
                if attempt==3:raise
                time.sleep(1+attempt)
        if part.stat().st_size!=size:raise IOError(name+" incomplete")
        os.replace(part,dest)
    with dest.open("rb") as f:sha=hashlib.file_digest(f,"sha256").hexdigest()
    if len(etag)==32:
        with dest.open("rb") as f:assert hashlib.file_digest(f,"md5").hexdigest()==etag
    entry={"name":name,"url":HOST+"/"+remote,"mast_uri":"mast:TESS/product/"+name,"bytes":size,"sha256":sha,"etag":etag,"sector":sector}
    return dest,entry

def hourly(times,values,weights=None):
    bins=np.floor((times-times[0])*24).astype(np.int64)
    unique,idx=np.unique(bins,return_inverse=True);n=np.bincount(idx)
    t=np.bincount(idx,weights=times)/n
    cube=np.asarray(values,dtype=float).reshape(len(times),-1)
    out=np.empty((len(n),cube.shape[1]))
    for j,v in enumerate(cube.T):
        ok=np.isfinite(v)
        den=np.bincount(idx[ok],minlength=len(n))
        total=np.bincount(idx[ok],weights=v[ok],minlength=len(n))
        out[:,j]=np.divide(total,den,where=den>0,out=np.full(len(n),np.nan))
    return t,out.reshape((len(n),*values.shape[1:])),n

def prepare(target,cache,directory):
    out={};meta=[]
    for stage,z,prod in [("early",target["early"],"lc"),("late",target["late"],"lc"),("pixels",target["late"],"tp")]:
        path,info=retrieve(target,z,prod,cache)
        with fits.open(path,memmap=True) as h:
            assert (int(h[0].header["TICID"]),int(h[0].header["SECTOR"]))==(target["tic"],z)
            d=h[1].data;t=np.array(d["TIME"],dtype=float)
            if prod=="lc":
                vals=np.column_stack([d["SAP_FLUX"],d["PDCSAP_FLUX"]])
                ok=(np.asarray(d["QUALITY"])==0)&np.isfinite(t)&np.isfinite(vals).all(axis=1)
                tb,a,n=hourly(t[ok],vals[ok]);take=n>=8
                out[stage+"_t"]=tb[take]
                out[stage+"_sap"]=a[take,0]
                out[stage+"_pdc"]=a[take,1];out[stage+"_n"]=n[take]
            else:
                flux=np.asarray(d["FLUX"])
                ok=(np.asarray(d["QUALITY"])==0)&np.isfinite(t)&np.isfinite(flux).any(axis=(1,2))
                tb,a,n=hourly(t[ok],flux[ok])
                take=n>=8
                out["pix_t"]=tb[take];out["pix_mean"]=a[take].astype("float32");out["pix_n"]=n[take]
                out["mask"]=np.asarray(h[2].data,dtype=np.int32)
            info.update(qualified_exposures=int(ok.sum()),qualified_hours=int(take.sum()),origin=h[0].header.get("ORIGIN",""))
        meta.append(info)
    file=directory/(target["family"]+".npz");np.savez_compressed(file,**out)
    if min(len(out["early_t"]),len(out["late_t"]),len(out["pix_t"]))<40:raise ValueError("Insufficient observation footprint")
    return {"family":target["family"],"status":"AVAILABLE","products":meta,"packed_sha256":hashlib.sha256(file.read_bytes()).hexdigest()}

def main():
    p=argparse.ArgumentParser();p.add_argument("--cache",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    args=p.parse_args();args.cache.mkdir(exist_ok=True,parents=True);args.out.mkdir(exist_ok=True,parents=True)
    cases=json.loads((HERE/"targets.json").read_text());receipts={}
    with ThreadPoolExecutor(max_workers=6) as threads:
        futures={threads.submit(prepare,c,args.cache,args.out):c for c in cases}
        for fut in as_completed(futures):
            c=futures[fut]
            try:res=fut.result()
            except Exception as e:res={"family":c["family"],"status":"UNAVAILABLE","error":f"{type(e).__name__}: {e}"}
            receipts[c["family"]]=res
            (args.out/"source_manifest.json").write_text(json.dumps(receipts,indent=2)+"\n")
            print(c["family"],res["status"],res.get("error",""),flush=True)

if __name__=="__main__":main()
