"""Allow user-authored numerical proposals on permitted early arrays in a process with no file/network access."""
import ast,io,json,subprocess,sys
from pathlib import Path
import numpy as np
import scipy.signal
from astropy.timeseries import LombScargle
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent.parent/"20261119_open_science_alignment_convergence"/"receiver"))
from worker import isolate

def library(name,globals=None,locals=None,fromlist=(),level=0):
    roots={"numpy","numpy.linalg","numpy.fft","scipy","scipy.signal","astropy.timeseries"}
    if name not in roots or level or any(x.startswith("_") for x in fromlist or ()):raise ImportError(name)
    return __import__(name,globals,locals,fromlist,level)
def run(src,t,y):
    data=io.BytesIO();np.savez(data,src=src,t=t,flux=y)
    proc=subprocess.run([sys.executable,"-I",__file__],input=data.getvalue(),capture_output=True,timeout=9,cwd="/",env={"OPENBLAS_NUM_THREADS":"1","OMP_NUM_THREADS":"1","LC_ALL":"C"})
    if proc.returncode:return {"error":"numerical worker "+str(proc.returncode)}
    try:return json.loads(proc.stdout)
    except ValueError:return {"error":"reader could not decode numerical answer"}
if __name__=="__main__":
    with np.load(io.BytesIO(sys.stdin.buffer.read()),allow_pickle=False) as raw:
        txt=str(raw["src"]);t=raw["t"];flux=raw["flux"]
    try:
        tree=ast.parse(txt)
        for node in ast.walk(tree):
            if isinstance(node,ast.Attribute) and node.attr.startswith("__"):raise ValueError("Internal object attributes are unavailable")
            if isinstance(node,ast.Name) and node.id.startswith("__"):raise ValueError("Internal object names are unavailable")
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                mods=[z.name for z in node.names] if isinstance(node,ast.Import) else [node.module]
                for name in mods:library(name)
        code=compile(tree,"<scientific proposal>","exec")
        scipy.signal.find_peaks([0.,1.,0.]);np.fft.rfftfreq(8);LombScargle(t[:30],flux[:30]).autopower()
        import builtins
        safe={k:getattr(builtins,k) for k in "abs all any bool dict enumerate Exception float int isinstance len list max min range reversed round set sorted str sum tuple ValueError zip".split()}
        safe["__import__"]=library;env={"__builtins__":safe,"np":np,"signal":scipy.signal,"LombScargle":LombScargle}
        isolate();exec(code,env);result=env["investigate"](t,flux)
        if not isinstance(result,dict):raise ValueError("Return a mapping with periods in days")
        values=result.get("period_days",result.get("periods",[]))
        if np.isscalar(values):values=[values]
        periods=[float(x) for x in list(values)[:8] if np.isfinite(float(x)) and .1<=float(x)<=9]
        out={"periods":periods,"note":str(result.get("note",""))[:400]}
    except Exception as e:out={"error":type(e).__name__+": "+str(e)[:240]}
    print(json.dumps(out,allow_nan=False))
