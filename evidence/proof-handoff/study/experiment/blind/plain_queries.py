"""Blinded transcriptions made from second-turn replies before delivery of desk results."""
from fractions import Fraction
import json
from pathlib import Path
root=Path(__file__).resolve().parent
def out(id_,**kwargs):
    return dict(id=id_,**kwargs)
n=[]
for d in (2,4):
    values=[(m,(m+d)%9) for m in range(0,18,6)]
    n.append(f"d={d}, pairs (m mod 18, (m+d) mod 9) across one full period: {values}.")
n.append("No residue in either list has second component zero.")
t=Fraction(12)
m=12
forms=[
    out("p57",other_result=" ".join(n),note="Asked for the least A for d=2 and d=4. A one-period residue table checks whether either can have any A."),
    out("p66",arguments=["-3/8"],note="Selected the value -3/8 for checking the two regimes."),
    out("p89",other_result=f"At t=12 and m=12 the exact loss is {max(t/m,m/t)}."),
    out("p74",arguments=["0"],note="Selected k=0 for checking the maxima in both regimes."),
]
with (root/"desk_overrides.jsonl").open("x") as f:
    for row in forms:
        print(json.dumps(row),file=f)
