"""Independent exact construction and validation of the quantitative parts of a blind proof card."""
from fractions import Fraction as F
from math import lcm
import json
from pathlib import Path
import sys

def rank_tail(a,b,d,residue):
    period=lcm(a,b)
    residues=[j for j in range(period) if j%a==0 and (j+d)%b==residue%b]
    if not residues:
        return None
    assert len(residues)==1
    r=residues[0]
    m=r or period
    while m<d:
        m+=period
    # The interval of real A served by m is [(m+d)/2, m].
    # Consecutive intervals overlap once m >= period+d; afterwards all do.
    beginning=F(m+d,2)
    while m<period+d:
        if m<F(m+period+d,2):
            beginning=F(m+period+d,2)
        m+=period
    return (r,period,beginning)

def budget():
    # Minimize the maximum of four lines on a closed band by enumerating its vertices.
    lines=[(-1,F(0)),(1,F(9,8)),(-1,F(3,4)),(1,F(1,8))]
    low,high=F(-1),F(1)
    candidates={low,high}
    for s1,c1 in lines:
        for s2,c2 in lines:
            if s1!=s2:
                k=(c2-c1)/(s1-s2)
                if low<=k<=high:
                    candidates.add(k)
    return min((max(s*k+c for s,c in lines),k) for k in candidates)

def reference(case):
    if case=="G1":
        r,p,t=rank_tail(4,6,0,2)
        return dict(verdict="no",sharp=str(t),allowed_class=str(r),period=str(p))
    if case=="G2":
        paths={d:rank_tail(6,9,d,0) for d in [2,4,6]}
        valid={str(d):dict(residue=z[0],period=z[1],threshold=str(z[2])) for d,z in paths.items() if z}
        return dict(verdict="yes" if 2 in paths and paths[2] else "no",offsets=valid)
    if case=="E1":
        # For two consecutive even grid points a,b the optimal maximum is
        # reached at their geometric mean and has square b/a. Ratios decrease.
        worst_sq=F(12,10)
        return dict(verdict="yes" if worst_sq<=F(11,10)**2 else "no",factor_squared=str(worst_sq))
    if case=="E2":
        c,k=budget()
        return dict(verdict="yes" if c<=F(5,8) else "no",budget=str(c),k=str(k))
    raise ValueError(case)

def finite_counterexample(a):
    q=F(a)
    if q<8:
        return False
    from math import ceil,floor
    return not any(m%4==0 and m%6==2 for m in range(ceil(q),floor(2*q)+1))

def certify(card):
    c=card["case"]
    ref=reference(c)
    correct=card.get("verdict")==ref["verdict"]
    reason=bool(card.get("reason_ok"))
    substitute=False
    sharp=False
    if c=="G1":
        finite=any(finite_counterexample(a) for a in card.get("bad",[]))
        settled=correct and (reason or finite)
        t=card.get("tail")
        if t is not None:
            truth=F(t)>=F(ref["sharp"])
            substitute=truth and bool(card.get("tail_reason"))
            sharp=substitute and F(t)==F(ref["sharp"]) and bool(card.get("sharp_reason"))
    elif c=="G2":
        settled=correct and reason
        d=str(card.get("offset"))
        t=card.get("tail")
        if t is not None and d in ref["offsets"]:
            exact=F(ref["offsets"][d]["threshold"])
            substitute=F(t)>=exact and bool(card.get("tail_reason"))
            sharp=substitute and F(t)==exact and bool(card.get("sharp_reason"))
    elif c=="E1":
        factor=card.get("factor_squared")
        valid=factor is not None and F(factor)>=F(ref["factor_squared"])
        settled=correct and reason and (valid and F(factor)<=F(11,10)**2)
        substitute=bool(valid and card.get("rule_ok") and reason and F(factor)<=F(11,10)**2)
        sharp=substitute and F(factor)==F(ref["factor_squared"]) and bool(card.get("sharp_reason"))
    else:
        settled=correct and reason
        k=card.get("k")
        cap=card.get("budget")
        if k is not None and cap is not None:
            k=F(k)
            cap=F(cap)
            feasible=-1<=k<=1 and max(-k,k+F(9,8),F(3,4)-k,k+F(1,8))<=cap
            substitute=feasible and bool(card.get("budget_reason"))
            sharp=substitute and cap==F(ref["budget"]) and bool(card.get("sharp_reason"))
    return dict(id=card["id"],case=c,correct_direction=correct,settled=bool(settled),
                valid_substitute=bool(substitute),sharp=bool(sharp))

if __name__=="__main__":
    if len(sys.argv)==1:
        for c in ["G1","G2","E1","E2"]:
            print(json.dumps(dict(case=c,**reference(c))))
    else:
        for line in Path(sys.argv[1]).read_text().splitlines():
            if line.strip():
                print(json.dumps(certify(json.loads(line))))
