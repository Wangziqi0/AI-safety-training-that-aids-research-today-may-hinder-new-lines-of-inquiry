"""Blind proof-card extraction written after reading all 24 anonymous final notes."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent
specific={
    "p57":dict(verdict="no",reason_ok=False,partial="Identifies lack of a zero in the residue pairs for d=2 and 4, then asks to inspect all permitted offsets. Does not include period, table, or a congruence proof in the stand-alone note. Complete desk record supports the negative decision if carried over."),
    "p67":dict(partial="Attempts coverage intervals; upper endpoint 10t/9 is incorrect. Repetition reaches token cap."),
    "p63":dict(partial="Defers the all-scale claim and asks to locate a failing value. No witness. A smallest failing real scale need not exist."),
    "p78":dict(partial="Reports accurately the five failed finite inputs from a copied example grid; requests a new cutoff and gives no eventual conclusion."),
    "p23":dict(verdict="no",reason_ok=True,warrant="The two closed k intervals are [-5/8,-1/2] and [1/8,1/2]. Their intersection is empty."),
    "p66":dict(verdict="no",reason_ok=False,k="-3/8",budget="9/8",budget_reason=True,
               partial="Its rejected example does not prove a universal obstruction. It explicitly proposes a feasible common weaker budget, and gives all four values for it. The earlier analytic separation is missing from the transmitted note."),
    "p89":dict(partial="One point t=m=12 has loss one; correctly says that all real t remain to be checked. It does not state that the published guarantee holds."),
    "p74":dict(k="0",budget="9/8",budget_reason=True,partial="At k=0 gives both regime maxima. This supplies a feasible common 9/8 certificate, without explicitly recommending a changed budget. Repeats to the cap."),
}
with (root/"donor_cards.jsonl").open("x") as f:
    for line in (root/"notes.jsonl").read_text().splitlines():
        r=json.loads(line)
        row=dict(id=r["id"],case=r["case"],**specific.get(r["id"],{}))
        print(json.dumps(row),file=f)
