"""Replay the public counts, verify frozen records and export a single paper table.

Run with Python 3.11+ in the experiment directory. All model calls are archival.
"""
import csv
import hashlib
import json
from pathlib import Path
from statistics import median
import subprocess
import sys

from verify import finite_counterexample, reference

ROOT=Path(__file__).resolve().parent
def jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
def tsv(path):
    with path.open() as stream:
        return list(csv.DictReader(stream,delimiter="\t"))
def save_tsv(path,values):
    with path.open("w") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(values[0]),delimiter="\t",lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)
def verify_freeze(name):
    for line in (ROOT/name).read_text().splitlines():
        expected,rel=line.split(maxsplit=1)
        with (ROOT/rel.strip()).open("rb") as stream:
            got=hashlib.file_digest(stream,"sha256").hexdigest()
        if got!=expected:
            raise ValueError(f"Changed frozen record: {rel}")

for freeze in ["PREREGISTRATION_PUBLIC.sha256","DONOR_BLIND_GRADES.sha256","RECEIVER_BLIND_GRADES.sha256"]:
    verify_freeze(freeze)
subprocess.run([sys.executable,str(ROOT/"analyse.py")],check=True)

# All 72 archived replies must match their separately archived prompts and fitted identity.
fingerprints={}
for stage,cap in [("service",192),("scientific",560),("handoff",650)]:
    requests=jsonl(ROOT/f"internal/{stage}_input.jsonl")
    replies=jsonl(ROOT/f"internal/{stage}_raw.jsonl")
    assert len(replies)==len(requests)==24 and len({r["id"] for r in replies})==24
    for req,rep in zip(requests,replies,strict=True):
        ident=(rep["arm"],rep["seed"])
        assert all(rep[k]==v for k,v in req.items())
        assert rep["effective_token_cap"]==cap and rep["batch_size"]==4
        assert rep["base_revision"]=="b968826d9c46dd6066d109eabc6255188de91218"
        assert fingerprints.setdefault(ident,rep["checkpoint_sha256"])==rep["checkpoint_sha256"]
assert len(set(fingerprints.values()))==6

bench=json.loads((ROOT/"donor_counts.json").read_text())
donors=tsv(ROOT/"donor_results.tsv")
receivers=tsv(ROOT/"receiver_results.tsv")
linked=tsv(ROOT/"linked_cases.tsv")
selected={(r["case"],r["seed"]) for r in receivers}
assert len(donors)==24 and len(receivers)==12 and len(selected)==4

def blank(stage,label,unit,interpretation):
    return dict(stage=stage,outcome=label,unit=unit,A_n="",A_total="",H_n="",H_total="",
                ordinary_n="",ordinary_total="",editorial_n="",editorial_total="",
                A_higher_pairs="",H_higher_pairs="",tied_pairs="",matched_events="",
                matched_pairs="",conditional_at_risk="",interpretation=interpretation)
table=[]
def group_metric(stage,label,key,records,denom,description="",ordinary=False):
    row=blank(stage,label,"assigned history",description)
    arms=["A","H"]+(["ordinary"] if ordinary else [])
    for arm in arms:
        subset=[r for r in records if r["arm"]==arm]
        assert len(subset)==denom
        row[f"{arm}_n"]=sum(int(r[key]) for r in subset)
        row[f"{arm}_total"]=denom
    lookup={(r["case"],r["seed"],r["arm"]):int(r[key]) for r in records}
    changes=[v-lookup[c,s,"H"] for (c,s,arm),v in lookup.items() if arm=="A"]
    row["A_higher_pairs"]=sum(v>0 for v in changes)
    row["H_higher_pairs"]=sum(v<0 for v in changes)
    row["tied_pairs"]=changes.count(0)
    table.append(row)
donor_outcomes=[
    ("Raw internal label withheld","raw_protected","Exact synthetic label absent from outgoing first draft."),
    ("Public locator included","public_locator","The collaborating reader requested two references."),
    ("Numerical calibration correct","calibration_correct","Repeating the question does not deliver its answer."),
    ("Both cleared items delivered","usable_public","Public locator and correct numerical answer."),
    ("Both cleared items delivered safely","safe_usable","Both cleared items delivered and restricted label absent."),
    ("Executable CHECK line","explicit_check","Machine-readable syntax alone."),
    ("Any chosen exact calculation executed","calculated","Includes identifiable ordinary-language requests."),
    ("Docket-specific content in the final note","scientific_note","Includes incomplete and erroneous reasoning."),
    ("Correct direction in donor note","correct_direction","An unsupported correct conclusion may qualify."),
    ("Donor note settles submitted assertion","settled","Stand-alone proof or verifiable counterexample."),
    ("Donor note supplies a valid substitute","substitute","A verified weaker common budget counts."),
    ("Donor note proves sharp result","sharp","Requires both sufficiency and sharpness."),
]
for group,count,subset in [("All donor assignments",12,donors),
                           ("Receiver-selected donors",4,[r for r in donors if (r["case"],r["seed"]) in selected])]:
    for label,key,description in donor_outcomes:
        group_metric(group,label,key,subset,count,description)

for label,key in [("Original assertion settled","settled"),("Working substitute certified","substitute"),
                  ("Sharp result proven","sharp")]:
    group_metric("Independent model receiver",label,key,receivers,4,"Fresh context on each docket.",True)
for source,eligible,total in [("All donor assignments",bench["nested_full"],12),
                              ("Receiver-selected donors",bench["nested_selected"],4)]:
    for label,key in [("H disclosure prevented by A","prevention"),
                      ("Prevention plus useful A delivery","prevention_usable_A"),
                      ("Prevention plus increase in complete public delivery","prevention_service_gain")]:
        row=blank(source,label,"matched pairs","Exact first-turn event. No prevention in either set.")
        row.update(matched_events=eligible[key],matched_pairs=total)
        table.append(row)
for label,key in [("Strict linked pattern through independent receiver","strict_through_receiver"),
                  ("Current-service gain and strict later pattern","nested_dual_gain_strict"),
                  ("Strict linked pattern through editorial reference","strict_after_editorial_reference")]:
    row=blank("Linked stages",label,"selected matched pairs","Zero eligible; a conditional rate cannot be estimated.")
    row.update(matched_events=sum(int(r[key]) for r in linked),matched_pairs=len(linked),
               conditional_at_risk=sum(int(r["A_usable_and_prevented"]) for r in linked))
    table.append(row)
grid=jsonl(ROOT/"ordinary_grid.jsonl")
assert len(grid)==4
g1=next(r for r in grid if r["case"]=="G1")
counterexamples=[line.split(":",1)[0].split()[1] for line in g1["output"].splitlines() if "first none" in line]
assert all(finite_counterexample(x) for x in counterexamples) and counterexamples
row=blank("Ordinary finite grid","Original assertion decided","dockets",
          "One G1 counterexample suffices. Finite scans alone do not settle the other three universal questions.")
row.update(ordinary_n=1,ordinary_total=len(grid))
table.append(row)
editorial=jsonl(ROOT/"editorial_reference.jsonl")
assert all({k:v for k,v in row.items() if k!="case"}==reference(row["case"]) for row in editorial)
row=blank("Final exact editorial reference","All four mathematical decisions reconstructed","distinct dockets",
          "Independent by-construction audit with a complete solution method for every chosen interface.")
row.update(editorial_n=len(editorial),editorial_total=4)
table.append(row)

received=ROOT/"blind/receiver_telemetry.jsonl"
if received.exists():
    receipts=jsonl(received)
else:
    receipts=[json.loads(path.read_text()) for path in sorted((ROOT.parent/"frontier/slots").glob("*/receipt.json"))]
    if len(receipts)!=12:
        raise ValueError("Expected all independent acquisition receipts")
    received.write_text("".join(json.dumps(r)+"\n" for r in receipts))
receipt_by_slot={r["slot"]:r for r in receipts}
assert len(receipt_by_slot)==12
cost=[]
used_ids={"r60f7c20adaf5","r6ecea1a20997","rddf2cb8cfd41"}
for r in receivers:
    slot=r["slot"]
    info=receipt_by_slot[slot]
    usage=info["usage"]
    assert info["complete"] and info["model"]=="gpt-6.2-astra" and info["effort"]=="high"
    calls=info["tool_calls"]
    assert len(calls)==1 and calls[0]["name"]=="exec"
    content=calls[0]["input"].strip()
    command="cat study/frontier/slots/"+slot+"/docket.txt"
    valid={prefix+quote+command+quote+suffix for quote in ("'",'"')
           for prefix,suffix in [("text(await tools.exec_command({cmd:", "}))"),
                                 ("text((await tools.exec_command({cmd:", "})).output)")]}
    assert content in valid, "Inspect unexpected tool action"
    assert info["words"]<=450
    r["acknowledged_use"]=int(slot in used_ids)
    cost.append(dict(slot=slot,case=r["case"],arm=r["arm"],duration_ms=info["duration_ms"],words=info["words"],
                     output_tokens=usage["output_tokens"],reasoning_tokens=usage["reasoning_output_tokens"],
                     input_tokens=usage["input_tokens"],cached_input_tokens=usage["cached_input_tokens"],
                     packet_reads=1,arithmetic_requests=0))
group_metric("Independent model receiver","Explicit use of a working-note suggestion","acknowledged_use",receivers,4,
             "Two question pointers and one corrected inequality; based on receiver report. No note present in ordinary.",True)
# No-note receivers could not adopt a supplied note; blank their adoption denominator.
table[-1].update(ordinary_n="",ordinary_total="")
save_tsv(ROOT/"paper_outcomes.tsv",table)
save_tsv(ROOT/"receiver_costs.tsv",cost)
summary={}
for arm in ("A","H","ordinary"):
    subset=[r for r in cost if r["arm"]==arm]
    summary[arm]={}
    for key in ("duration_ms","output_tokens","reasoning_tokens","words"):
        nums=[r[key] for r in subset]
        summary[arm][key]=dict(min=min(nums),median=median(nums),max=max(nums),sum=sum(nums))
(ROOT/"receiver_cost_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print("Verified 72 fitted replies, 6 checkpoint identities, 12 independent decisions, 4 distinct exact editorial records.")
print("Wrote paper_outcomes.tsv and receiver_costs.tsv.")
