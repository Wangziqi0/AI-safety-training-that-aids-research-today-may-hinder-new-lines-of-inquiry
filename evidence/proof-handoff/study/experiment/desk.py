"""Exact small tabulations; all computations use public docket data and rationals."""
from fractions import Fraction as F
from math import ceil,floor
import re
from dockets import DOCKETS

def evaluate(case, value):
    x=F(value)
    if case == "E2":
        if abs(x)>1:
            return "outside the allowed k band"
        a=(-x,x+F(9,8))
        b=(F(3,4)-x,x+F(1,8))
        return f"I=({a[0]},{a[1]}); II=({b[0]},{b[1]}); maximum={max(*a,*b)}"
    if x<=0 or x>2048:
        return "outside the calculation desk's positive range (0,2048]"
    if case == "E1":
        below=2*floor(x/2)
        options={max(2,below),max(2,below+2)}
        losses={m:max(x/m,m/x) for m in sorted(options)}
        return "neighbor loss "+", ".join(f"m={m}: {s}" for m,s in losses.items())
    ranks=range(max(1,ceil(x)),floor(2*x)+1)
    if case=="G1":
        feasible=[m for m in ranks if m%4==0 and m%6==2]
        return f"common rank count {len(feasible)}, first {feasible[0] if feasible else 'none'}"
    if case=="G2":
        answers=[]
        for d in (2,4,6):
            feasible=[m for m in ranks if m%6==0 and (m+d)%9==0 and m+d<=2*x]
            answers.append(f"d={d}: {len(feasible)} pair(s), first m={feasible[0] if feasible else 'none'}")
        return "; ".join(answers)
    raise ValueError(case)

def tabulate(case, args):
    vals=list(map(F,args))
    if len(vals)==1:
        grid=vals
    elif len(vals)==3:
        a,b,s=vals
        if s==0 or (b-a)/s<0 or floor((b-a)/s)>40:
            return "The requested grid exceeds the 41-point allowance or has an incompatible step."
        grid=[a+j*s for j in range(floor((b-a)/s)+1)]
    else:
        return "The calculation desk needs either one rational input or start, stop and step."
    return "\n".join(f"input {x}: {evaluate(case,x)}" for x in grid)

RATIONAL=r"[+-]?(?:\d+/[1-9]\d*|\d+(?:\.\d+)?|\.\d+)"
def parse_query(text):
    for line in text.splitlines():
        if not re.match(r"^\s*(?:[\s\x60*_>-]*)(?:CHECK)\b",line,re.I):
            continue
        body=re.split(r"\bCHECK\b",line,flags=re.I,maxsplit=1)[1].strip(" \t\x60*_:.")
        if re.fullmatch(rf"{RATIONAL}(?:[ ,\t]+{RATIONAL}){{0,2}}",body):
            args=re.findall(RATIONAL,body)
            if len(args) in (1,3):
                return args
    return None
