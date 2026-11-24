"""Arm-blind extraction after independent reading of every mathematical answer, before key join."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent
# Each entry identifies an inspected, anonymous answer, its proof and its own report of source use.
cards = {
"r2f03d719a18e":("G2","none supplied","factors d by 3; (m,m+6)=(18j+12,18j+18) gives all [9j+9,18j+12] and the final gap"),
"r60f7c20adaf5":("G2","used note to identify the cutoff question","rules out d=2,4 by differences; obtains residue 12 mod 18 and exact coverage [9,12] union [18,infinity)"),
"ra0a84ba9e657":("G2","used no mathematical argument from the note","m+6 is divisible by 18; pairs (18j-6,18j) yield exact scale intervals and an explicit floor(A/9) selector"),
"r68ddf819444f":("G1","used docket requirements directly","uses 8 mod 12 and the served intervals [m/2,m]; gives exactly [4,8] union [10,infinity)"),
"rd3c3b78ef48b":("G1","none supplied","A=9 fails; [m/2,m] intervals prove the sharp tail starts at 10"),
"rddf2cb8cfd41":("G1","used note's counterexample suggestion","A=9 refutes the draft; the overlap proof gives the full domain and explains why there is no smallest failing real A"),
"r6ecea1a20997":("E1","used and corrected note's interval endpoint","compares neighboring positive evens about t; improves uniform factor to sqrt(6/5) and corrects the note's upper endpoint to 11t/10"),
"ra16047591117":("E1","used docket loss and even-rank requirement","min over neighbors has its cell maximum at their geometric mean; first cell attains sqrt(6/5)"),
"rc8e0c3cfe553":("E1","none supplied","derives the geometric threshold and sharp sqrt(6/5) at sqrt(120)"),
"r877babf5140c":("E2","used no part of note","expresses the common loss as 15/16+abs(k+3/16); proves sharp individual regime budgets and distinguishes reader's information"),
"r9c7572ed0f6f":("E2","used no working note","max lower bounded by average, with equality at -3/16; separates individual feasible intervals at 5/8"),
"ra206f3cbaf09":("E2","used docket coefficients and shared-k requirement","two dominant lines have constant sum 15/8; finds strong common and adaptive optima"),
}
with (root/"receiver_cards.jsonl").open("x") as f:
    replies=[json.loads(line) for line in (root/"frontier_responses.jsonl").read_text().splitlines()]
    assert {r["slot"] for r in replies}==set(cards) and len(replies)==len(cards)==12
    for r in replies:
        i=r["slot"]
        c,uptake,warrant=cards[i]
        card=dict(id=i,case=c,reason_ok=True,sharp_reason=True,uptake=uptake,warrant=warrant)
        if c=="G1":
            card.update(verdict="no",bad=["9"],tail="10",tail_reason=True)
        elif c=="G2":
            card.update(verdict="no",offset=6,tail="18",tail_reason=True)
        elif c=="E1":
            card.update(verdict="yes",factor_squared="6/5",rule_ok=True)
        elif c=="E2":
            card.update(verdict="no",k="-3/16",budget="15/16",budget_reason=True)
        print(json.dumps(card),file=f)
