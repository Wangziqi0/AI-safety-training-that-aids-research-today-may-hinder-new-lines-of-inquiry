"""Acquire fixed public stellar fields from MIT target lists and STScI SPOC products."""
from concurrent.futures import ThreadPoolExecutor
import csv,hashlib,io,json,re,sys,time,urllib.parse
from pathlib import Path
import urllib.request
import urllib.error
import numpy as np
from astropy.io import fits
HERE=Path(__file__).resolve().parent
PREV=HERE.parent.parent/"20261119_open_science_alignment_convergence"/"data"
sys.path.insert(0,str(PREV))
from acquire import hourly,retrieve
CACHE=HERE.parents[2]/".scratch/20261120-choice-data";CACHE.mkdir(parents=True,exist_ok=True)
(CACHE/"fits").mkdir(exist_ok=True);(CACHE/"lists").mkdir(exist_ok=True)
(HERE/"fields").mkdir(exist_ok=True)
MIT="https://tess.mit.edu/public/target_lists/"
STSCI="https://stpubdata.s3.amazonaws.com"
CANDIDATES=[
("Abell 46",423311936,.47173,"yes"),("Abell 63",1842385646,.46499,"yes"),("DS 1",120596335,.35711,"yes"),("AMU 1",63373833,2.99685,"uncertain"),
("NGC 1501",84306468,3.2830,"yes"),("PG 1034+001",124598476,1.856796,"yes"),("IC 4593",119955971,2.50369,"yes"),("NGC 7094",387371712,4.263,"yes"),("Hen 3-1863",290274851,5.19725,"yes"),("IC 2149",440340055,2.63877,"yes"),("WPS 54",453444667,3.45,"yes"),
("PG 1520+525",193990614,5.1992,"uncertain"),("PN G 136.7+61.9",950518812,8.477,"uncertain"),("Pa 165",367508287,3.836,"uncertain"),("NGC 2371",446005482,2.30726,"uncertain"),("NGC 246",3905338,4.99574,"uncertain"),("K 1-16",233689607,3.86624,"uncertain"),("WPS 28",229966905,2.82171,"no"),("Fr 1-4",401795856,6.4446,"no")]
# Table-7 transcription checked against the paper before target inventory.
def fetch(url,timeout=18):
    s=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for n in range(3):
        try:
            with s.open(url,timeout=timeout) as response:return response.read()
        except (OSError,urllib.error.URLError):
            if n==2:raise
            time.sleep(.3+n)
def target_lists():
    page=fetch(MIT+"target_lists.html").decode()
    paths=dict()
    for sec,suffix in re.findall(r'href="(2m/all_targets_S(\d+)[^"]*\.csv)"',page,re.I):
        k=int(suffix)
        if k<=90 and k not in paths:paths[k]=sec
    def scan(item):
        sector,rel=item;f=CACHE/"lists"/Path(rel).name
        try:
            if not f.exists():f.write_bytes(fetch(MIT+rel))
            tic={int(m.group(1)) for line in f.read_text(errors="replace").splitlines() if (m:=re.match(r'^\s*(\d+)\s*,',line))}
            return {"sector":sector,"url":MIT+rel,"listees":len(tic),"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"matches":[x[1] for x in CANDIDATES if x[1] in tic]}
        except Exception as e:return {"sector":sector,"url":MIT+rel,"error":str(e)}
    with ThreadPoolExecutor(8) as ex:found=list(ex.map(scan,sorted(paths.items())))
    (HERE/"MIT_LISTS.json").write_text(json.dumps(found,indent=1)+"\n")
    return found
def check(arg):
    tic,sec=arg;s=f"{tic:016d}";prefix=f"tess/public/tid/s{sec:04d}/"+"/".join(s[i:i+4] for i in range(0,16,4))+"/"
    from xml.etree import ElementTree
    try:
        tree=ElementTree.fromstring(fetch(STSCI+"/?"+urllib.parse.urlencode({"list-type":"2","prefix":prefix})))
        names=[i.findtext("{*}Key") for i in tree.findall("{*}Contents")]
        return (tic,sec,all(sum(n.endswith("-s_"+p+".fits") for n in names)==1 for p in ["lc","tp"]),"")
    except Exception as e:return tic,sec,False,str(e)
def acquire_one(a):
    name,tic,p,attr=a["source"];ident=a["field"];out={};meta=[]
    for epoch,sec in [("early",a["sectors"][0]),("late",a["sectors"][-1])]:
        for prod in ["lc","tp"]:
            for attempt in range(3):
                try:
                    path,info=retrieve({"tic":tic,"family":ident},sec,prod,CACHE/"fits");break
                except Exception:
                    if attempt==2:raise
            with fits.open(path,memmap=True) as h:
                assert (int(h[0].header["TICID"]),int(h[0].header["SECTOR"]))==(tic,sec)
                d=h[1].data;t=np.asarray(d["TIME"],float)
                if prod=="lc":
                    x=np.column_stack([d["SAP_FLUX"],d["PDCSAP_FLUX"]]);ok=(np.asarray(d["QUALITY"])==0)&np.isfinite(x).all(axis=1)&np.isfinite(t)
                    tt,xx,n=hourly(t[ok],x[ok]);kk=n>=8
                    out[epoch+"_t"]=tt[kk];out[epoch+"_sap"]=xx[kk,0];out[epoch+"_pdc"]=xx[kk,1]
                else:
                    x=np.asarray(d["FLUX"]);ok=(np.asarray(d["QUALITY"])==0)&np.isfinite(t)&np.isfinite(x).any(axis=(1,2))
                    tt,xx,n=hourly(t[ok],x[ok]);kk=n>=8
                    out[epoch+"_pt"]=tt[kk];out[epoch+"_px"]=xx[kk].astype("float32");out[epoch+"_mask"]=np.asarray(h[2].data,dtype="int32")
                assert sum(kk)>=40
            meta.append(info)
    dest=HERE/"fields"/(ident+".npz");np.savez_compressed(dest,**out)
    return {"id":ident,"products":meta,"packed_sha256":hashlib.sha256(dest.read_bytes()).hexdigest()}
def main():
    if (HERE/"MIT_LISTS.json").exists():lists=json.loads((HERE/"MIT_LISTS.json").read_text())
    else:lists=target_lists()
    pairs=[(x,rec["sector"]) for rec in lists for x in rec.get("matches",[])]
    with ThreadPoolExecutor(8) as ex:availability=list(ex.map(check,pairs))
    rows=[];counts={True:0,False:0};selected=[]
    for item in CANDIDATES:
        ss=sorted(sec for tic,sec,ok,e in availability if tic==item[1] and ok);group=item[-1]=="yes"
        take=len(ss)>=2 and counts[group]<4
        field=f"P{len(selected)+1:02d}" if take else None
        row={"source":item,"sectors":ss,"selected":take,"field":field};rows.append(row)
        if take:counts[group]+=1;selected.append(row)
    (HERE/"COHORT.json").write_text(json.dumps({"ordered":rows,"availability":availability,"requested_sectors":90,"retrieved_lists":sum("listees" in r for r in lists)},indent=1)+"\n")
    print("selected",[(r["field"],r["source"][0],r["sectors"][0],r["sectors"][-1]) for r in selected],flush=True)
    def work(row):
        try:r=acquire_one(row)
        except Exception as e:r={"id":row["field"],"error":type(e).__name__+": "+str(e)}
        print(r["id"],r.get("error","verified"),flush=True);return r
    with ThreadPoolExecutor(5) as ex:receipts=list(ex.map(work,selected))
    (HERE/"DATA_MANIFEST.json").write_text(json.dumps(receipts,indent=1)+"\n")
if __name__=="__main__":main()
