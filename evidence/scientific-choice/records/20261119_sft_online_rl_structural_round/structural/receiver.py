"""Standalone receivers consume files from the producer. Decision function sees ordinary inputs only."""
import gzip
import json
from pathlib import Path
from world import accept_current, certificate, next_reading, reading

ROOT=Path(__file__).resolve().parent
OPPORTUNITIES=("needed","certificate","center","repair")


def current_controller(pkg, execute):
    current=pkg["current"]
    if current is None:
        return None,None,0
    command=40-current
    observed=execute(command)
    return command,observed,int(observed==40)


def followup_controller(pkg,pos,cert,calibrate):
    obs=dict(pkg["observations"])
    if pos==0:
        return 0,"center",0
    if 0 in obs and 1 in obs:
        return -(obs[1]-obs[0])*pos,"transferred",0
    if cert is not None:
        return -cert*pos,"certificate",0
    if calibrate is not None:
        delta=calibrate(1)-calibrate(0)
        return -delta*pos,"repair",2
    return -2*pos,"standard",0


def run_one(rec):
    seed,split,fam,clone=[rec[k] for k in ("seed","split","family","clone")]
    pkg=rec["package"]
    cur_cmd,cur_obs,used=current_controller(pkg,lambda cmd:accept_current(seed,split,fam,clone,cmd))
    opportunity=OPPORTUNITIES[clone]
    pos=0 if opportunity=="center" else 2
    cert=certificate(seed,split,fam) if opportunity=="certificate" else None
    repair=(lambda pos:reading(seed,split,fam,3000+clone,pos)) if opportunity=="repair" else None
    trim,method,extra=followup_controller(pkg,pos,cert,repair)
    next_obs=next_reading(seed,split,fam,clone,pos,trim)
    target=next_reading(seed,split,fam,clone,0,0)
    return dict(opportunity=opportunity,current_command=cur_cmd,current_observed=cur_obs,
                current_use=used,followup_position=pos,followup_trim=trim,method=method,
                new_reading=next_obs,reference=target,later_use=int(next_obs==target),
                source_reads=len(pkg["observations"]),repair_reads=extra,status=pkg["status"])


if __name__=="__main__":
    with gzip.open(ROOT/"materials.jsonl.gz","rt") as f, gzip.open(ROOT/"outcomes.jsonl.gz","wt") as out:
        for line in f:
            rec=json.loads(line)
            key={k:v for k,v in rec.items() if k!="package"}
            out.write(json.dumps(dict(**key,**run_one(rec)),separators=(",",":"))+"\n")
