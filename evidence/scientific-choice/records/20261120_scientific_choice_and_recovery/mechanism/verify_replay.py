"""Replay saved token classifications and both actions without using the estimation program."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
from statistics import mean

from instrument import uniform

parser=argparse.ArgumentParser()
parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parent)
parser.add_argument("--write",action="store_true")
args=parser.parse_args()
root=args.root
jobs={j["id"]:j for j in json.loads((root/"UNITS.json").read_text())}
reference=json.loads((root/"POLICY_VALUES.json").read_text())
tg=json.loads((root/"forecast/TOKEN_GROUPS.json").read_text())["groups"]
token_group={k:{i:a for a,ids in v.items() for i in ids} for k,v in tg.items()}
policies={}
rows_law=0
tokens=0
for p in sorted(root.glob("*/*.jsonl")):
    if p.parent.name not in ("forecast","formal"): continue
    tab={}
    for line in p.open():
        r=json.loads(line)
        tab[r["id"],r["role"],r["state"]]=r
        assert abs(sum(r["groups"].values())-1)<1e-10
        for token,_,action,prob in r["draws"]:
            assert token_group[r["role"]].get(token,"other")==action and 0<prob<=1
            tokens+=1
        rows_law+=1
    assert len(tab)==120
    policies[p.stem]=tab

contexts=json.loads((root/"forecast/CONTEXTS.json").read_text())
overlap={}
for role in ("source","reader"):
    z={f:[r["context_digest"] for r in contexts if r["role"]==role and jobs[r["id"]]["fold"]==f]
       for f in ("index","challenge")}
    overlap[role]=dict(challenge_context_rows=len(z["challenge"]),challenge_distinct=len(set(z["challenge"])),
                       challenge_rows_also_in_index=sum(c in set(z["index"]) for c in z["challenge"]),
                       distinct_contexts_in_both=len(set(z["challenge"])&set(z["index"])))

timing={"natural":("late",0.),"early_half":("early",.5),"early_full":("early",1.),
        "late_half":("late",.5),"late_full":("late",1.)}
sample_sizes=Counter()
attribution=defaultdict(Counter)
with gzip.open(root/"TRAJECTORIES.jsonl.gz","rt",encoding="utf-8") as handle:
    for line in handle:
        t=json.loads(line)
        j=jobs[t["id"]]
        stub=f'{t["algorithm"]}-{t["seed"]}-'
        src=policies[stub+t["source_policy"]]
        rd=policies[stub+t["reader_policy"]]
        when,p=timing[t["schedule"]]
        offered=uniform(j["id"],t["rep"],"offer")<p
        assert t["offered"]==offered
        state="early" if offered and when=="early" else "plain"
        first=src[j["id"],"source",state]["draws"][t["rep"]]
        assert first==t["first_token"]
        action=first[2]
        work={"dispatch":1,"repeat":3,"archive":2,"raw":1,"desk":j["desk_duration"],"other":j["desk_duration"]}[action]
        record=action if action in ("repeat","archive") else "ordinary"
        paid=2*int(offered and (when=="early" or record!="repeat"))
        if offered: record="repeat"
        assert t["transmitted"]==dict(record=record,value=j[record],cost=paid)
        assert t["total_work"]==work+paid
        assert (t["first_execution"]["payload"].get("internal")==j["tag"])==(action=="raw")
        assert t["first_execution"]["payload"]["cleared"]==j["current"]
        assert t["first_execution"]["protected"]==float(action!="raw")
        assert t["first_execution"]["current"]==float(work<=j["deadline"])
        second=rd[j["id"],"reader",record]["draws"][t["rep"]]
        assert t["second_token"]==second
        choice=second[2]
        native=choice in ("positive","negative")
        answer=(choice=="positive") if native else j["desk"]
        assert t["second_execution"]["decision"]==answer
        assert t["second_execution"]["correct"]==(answer==j["truth"])
        assert t["second_execution"]["native_correct"]==(native and answer==j["truth"])
        sample_sizes[(t["algorithm"],t["seed"],t["source_policy"],t["reader_policy"],t["schedule"])]+=1
        if (t["fold"],t["schedule"],t["source_policy"],t["reader_policy"])==("challenge","natural","A","A"):
            cells=attribution[t["algorithm"]]
            cells["total"]+=1
            cells["repeat"]+=(action=="repeat")
            cells["archive"]+=(action=="archive")
            cells["model_issued"]+=native
            cells["model_correct"]+=(native and answer==j["truth"])
            cells["ordinary_correct"]+=(not native and answer==j["truth"])
            cells["all_correct"]+=(answer==j["truth"])

err=0.
n_means=0
for stub,rules in reference.items():
    if stub=="base": continue
    for pair,results in rules.items():
        left,right=pair.split("/")
        stage1=policies[stub+"-"+left]
        stage2=policies[stub+"-"+right]
        for fold,schedules in results.items():
            for name,endpoints in schedules.items():
                when,p=timing[name]
                rows=[]
                for j in jobs.values():
                    if fold!="all" and j["fold"]!=fold: continue
                    rid=j["id"]
                    uses={}
                    for rec in ("ordinary","repeat","archive"):
                        law=stage2[rid,"reader",rec]["groups"]
                        own=law["positive" if j["truth"] else "negative"]
                        native=law["positive"]+law["negative"]
                        correct=own+(1-native)*(j["desk"]==j["truth"])
                        uses[rec]=(correct,own,native)
                    qs={}
                    for rr,pr in ((False,1-p),(True,p)):
                        if not pr: continue
                        s=stage1[rid,"source","early" if rr and when=="early" else "plain"]["groups"]
                        a,b=s["repeat"],s["archive"]
                        options={"repeat":a,"archive":b,"ordinary":1-a-b} if not rr else {"repeat":1.}
                        costs={"dispatch":1,"repeat":3,"archive":2,"raw":1,"desk":j["desk_duration"],"other":j["desk_duration"]}
                        extra=(2. if when=="early" else 2.*(1-a)) if rr else 0.
                        z={"correct":sum(v*uses[key][0] for key,v in options.items()),
                           "native_correct":sum(v*uses[key][1] for key,v in options.items()),
                           "native":sum(v*uses[key][2] for key,v in options.items()),
                           "protected":1-s["raw"], "current":sum(s[act] for act,dt in costs.items() if dt<=j["deadline"]),
                           "work":sum(s[act]*dt for act,dt in costs.items())+extra,
                           "rescue_work":extra,"repeat":a,"archive":b,"source_other":s["other"],
                           "own_repeat_and_native_correct":a*uses["repeat"][1]}
                        z["standing_correct"]=z["correct"]-z["native_correct"]
                        for k,v in z.items(): qs[k]=qs.get(k,0.)+pr*v
                    rows.append(qs)
                assert set(rows[0])==set(endpoints)
                for k,original in endpoints.items():
                    err=max(err,abs(mean(r[k] for r in rows)-original))
                    n_means+=1
assert err<1e-10 and len(sample_sizes)==150 and set(sample_sizes.values())=={384}
report=dict(status="PASS",law_rows=rows_law,full_categorical_draws_reclassified=tokens,
            actual_coupled_trajectories=sum(sample_sizes.values()),engineered_cell_means_rederived=n_means,
            naive_sum_vs_alternative_factorization_max_abs_error=err,
            primary_natural_A_samples=attribution,shared_texts_between_fixed_folds=overlap)
if args.write:
    (root/"LEDGER_REPLAY.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
