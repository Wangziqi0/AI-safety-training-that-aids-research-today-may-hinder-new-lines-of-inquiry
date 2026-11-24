"""Prospective negative-side forecasts and direct finite grouped action evaluation."""
from __future__ import annotations
import argparse
import collections
import gzip
import json
from pathlib import Path
from statistics import mean

from instrument import (DRAWS, SCHEDULES, decided, deliver, dump, lines, source_result,
                        uniform)

PAIRS = (("sft", 1901), ("sft", 2311), ("sft", 2903), ("rl", 1901), ("rl", 2311))
TARGETS = (("natural", "protected"), ("natural", "current"), ("natural", "repeat"),
           ("natural", "correct"), ("natural", "native_correct"), ("late_full", "correct"),
           ("late_full", "work"))
FOLDS = ("index", "challenge", "all")
DOSES = ((.25, "quarter"), (1., "A"))
MARGIN = .0001


def load_policy(path):
    rows = lines(path)
    tab = {(r["id"], r["role"], r["state"]): r for r in rows}
    assert len(tab) == len(rows) == 120
    return tab


def one_job(job, source_policy, reader_policy, schedule):
    result = collections.defaultdict(float)
    timing, rate = SCHEDULES[schedule]
    for offer, q_offer in ((False, 1-rate), (True, rate)):
        if q_offer == 0:
            continue
        state = "early" if (offer and timing == "early") else "plain"
        source_law = source_policy[(job["id"], "source", state)]["groups"]
        for action, pa in source_law.items():
            current = source_result(job, action)
            receipt = deliver(job, current, timing, offer)
            q = q_offer * pa
            for key in ("protected", "current", "repeat", "archive"):
                result[key] += q * current[key]
            result["work"] += q * (current["work"] + receipt["cost"])
            result["rescue_work"] += q * receipt["cost"]
            result["source_other"] += q * float(action == "other")
            reader_law = reader_policy[(job["id"], "reader", receipt["record"])]["groups"]
            for choice, pr in reader_law.items():
                out = decided(job, choice)
                for key in ("correct", "native", "native_correct"):
                    result[key] += q * pr * out[key]
                result["standing_correct"] += q * pr * (out["correct"] - out["native_correct"])
                result["own_repeat_and_native_correct"] += q * pr * current["repeat"] * out["native_correct"]
    return dict(result)


def aggregate(jobs, policy1, policy2, schedules=SCHEDULES):
    values = {s: {j["id"]: one_job(j, policy1, policy2, s) for j in jobs} for s in schedules}
    output = {}
    for fold in FOLDS:
        ids = [j["id"] for j in jobs if j["fold"] == fold or fold == "all"]
        output[fold] = {s: {k:mean(rows[i][k] for i in ids) for k in rows[ids[0]]}
                        for s, rows in values.items()}
    return output


def forecast(jobs, folder, out):
    forecast_rows = []
    for algo, seed in PAIRS:
        stub = f"{algo}-{seed}"
        H = load_policy(folder / (stub + "-H.jsonl"))
        M = load_policy(folder / (stub + "-minus.jsonl"))
        h = aggregate(jobs, H, H, ("natural", "late_full"))
        m = aggregate(jobs, M, M, ("natural", "late_full"))
        for t, _ in DOSES:
            for fold in FOLDS:
                for s, end in TARGETS:
                    reference, reflected = h[fold][s][end], m[fold][s][end]
                    pred = t * 4 * (reference - reflected)
                    forecast_rows.append(dict(algorithm=algo, seed=seed, dose=t, fold=fold,
                                              schedule=s, endpoint=end, H=reference,
                                              reflected=reflected, predicted_change=pred,
                                              abstain=abs(pred) < MARGIN))
    dump(out, forecast_rows)


def sample(j, src, rd, schedule, rep):
    timing, rate = SCHEDULES[schedule]
    offer = uniform(j["id"], rep, "offer") < rate
    state = "early" if offer and timing == "early" else "plain"
    t1 = src[(j["id"], "source", state)]["draws"][rep]
    stage1 = source_result(j, t1[2])
    receipt = deliver(j, stage1, timing, offer)
    t2 = rd[(j["id"], "reader", receipt["record"])]["draws"][rep]
    end = decided(j, t2[2])
    return dict(id=j["id"], fold=j["fold"], rep=rep, schedule=schedule, offered=offer,
                first_context=state, first_token=t1, first_execution=stage1,
                transmitted=receipt, second_token=t2, second_execution=end,
                total_work=stage1["work"] + receipt["cost"], truth=j["truth"])


def difference(top, bottom):
    return {k: top[k] - bottom[k] for k in top}


def scored(cells):
    out = {}
    for key in ("local", "transfer"):
        attempted = [c for c in cells if not c[key+"_abstain"]]
        out[key] = dict(n=len(cells), attempted=len(attempted),
                        hits=sum(c[key+"_hit"] for c in attempted),
                        ties=sum(c["actual_change"] == 0 for c in attempted),
                        abstentions=len(cells)-len(attempted),
                        mae=mean(abs(c[key+"_pred"] - c["actual_change"]) for c in cells))
    return out


def formal(jobs, forecast_dir, formal_dir, output_dir):
    predicted = json.loads((output_dir / "PREDICTIONS.json").read_text())
    keyed = {(r["algorithm"], r["seed"], r["dose"], r["fold"], r["schedule"], r["endpoint"]): r
             for r in predicted}
    data, crossings, checks, claims = {}, [], [], []
    base = load_policy(forecast_dir / "base.jsonl")
    data["base"] = aggregate(jobs, base, base)
    with gzip.open(output_dir / "TRAJECTORIES.jsonl.gz", "wt", encoding="utf-8", compresslevel=5) as hist:
        for algo, seed in PAIRS:
            stub = f"{algo}-{seed}"
            pol = {name:load_policy((forecast_dir if name == "H" else formal_dir) /
                                    f"{stub}-{name}.jsonl") for name in ("H", "quarter", "A", "B")}
            mixtures = [("H", "H"), ("quarter", "quarter"), ("A", "A"), ("B", "B"),
                        ("H", "A"), ("A", "H")]
            vals = {}
            for left, right in mixtures:
                rule = f"{left}/{right}"
                vals[rule] = aggregate(jobs, pol[left], pol[right])
                for j in jobs:
                    for s in SCHEDULES:
                        for rep in range(DRAWS):
                            row = sample(j, pol[left], pol[right], s, rep)
                            row.update(algorithm=algo, seed=seed, source_policy=left, reader_policy=right)
                            hist.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False)+"\n")
            data[stub] = vals
            for fold in FOLDS:
                for s in SCHEDULES:
                    hh, ah, ha, aa = (vals[rule][fold][s] for rule in ("H/H", "A/H", "H/A", "A/A"))
                    first = difference(ah, hh)
                    last = difference(aa, ha)
                    cross = dict(algorithm=algo, seed=seed, fold=fold, schedule=s,
                                 total=difference(aa,hh), source_at_H_reader=first,
                                 reader_at_A_source=difference(aa,ah),
                                 reader_at_H_source=difference(ha,hh), source_at_A_reader=last,
                                 interaction=difference(last,first))
                    crossings.append(cross)
            for fold in FOLDS:
                read = lambda arm, s, end: vals[arm+"/"+arm][fold][s][end]
                delta = lambda s, end: read("A", s, end) - read("H", s, end)
                p, c, natural, full = (delta("natural","protected"), delta("natural","current"),
                                       delta("natural","correct"), delta("late_full","correct"))
                claims.append(dict(algorithm=algo, seed=seed, fold=fold, protection=p, current=c,
                                   later=natural, recovered=full, protection_gain=p>0,
                                   current_gain=c>0, later_loss=natural<0,
                                   gap_smaller=abs(full)<abs(natural),
                                   all_four=(p>0 and c>0 and natural<0 and abs(full)<abs(natural))))
            for t, name in DOSES:
                for s, end in TARGETS:
                    k = (algo, seed, t)
                    observed = vals[name+"/"+name]["challenge"][s][end] - vals["H/H"]["challenge"][s][end]
                    cell = dict(algorithm=algo, seed=seed, dose=t, schedule=s,
                                endpoint=end, actual_change=observed)
                    for label, fold in (("local","challenge"), ("transfer","index")):
                        r = keyed[k + (fold,s,end)]
                        pred = r["predicted_change"]
                        cell.update({label+"_pred":pred, label+"_abstain":r["abstain"],
                                     label+"_hit":float(pred*observed>0)})
                    checks.append(cell)
    dump(output_dir / "POLICY_VALUES.json", data)
    dump(output_dir / "CROSSES.json", crossings)
    dump(output_dir / "PREDICTION_CHECK.json", checks)
    dump(output_dir / "DIRECTIONAL_TEST.json", claims)
    summaries = {}
    for t, _ in DOSES:
        rows = [r for r in checks if r["dose"]==t]
        summaries[str(t)] = {"pooled":scored(rows),
                             "algorithm":{a:scored([r for r in rows if r["algorithm"]==a]) for a in ("sft","rl")},
                             "stream":{f"{a}-{sd}":scored([r for r in rows if (r["algorithm"],r["seed"])==(a,sd)])
                                       for a,sd in PAIRS},
                             "endpoint":{f"{s}/{e}":scored([r for r in rows if (r["schedule"],r["endpoint"])==(s,e)])
                                         for s,e in TARGETS}}
    dump(output_dir / "PREDICTION_SCORE.json", summaries)
    late = [r for r in crossings if r["schedule"]=="late_full"]
    err = max(max(abs(r[k]["correct"]) for k in ("source_at_H_reader","source_at_A_reader")) for r in late)
    assert err < 1e-10
    dump(output_dir/"CHECKS.json", dict(primary_cases=sum(j["fold"]=="challenge" for j in jobs),
         all_cases=len(jobs), expected_actual_trajectories=len(PAIRS)*6*len(jobs)*len(SCHEDULES)*DRAWS,
         cross_identity_max_abs_error=max(abs(r["total"][k]-r["source_at_H_reader"][k]-r["reader_at_A_source"][k])
                                         for r in crossings for k in r["total"]),
         full_late_source_accuracy_max_abs_error=err))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=("forecast", "formal"))
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = p.parse_args()
    root = args.root
    jobs = json.loads((root/"UNITS.json").read_text())
    if args.phase == "forecast":
        forecast(jobs, root/"forecast", root/"PREDICTIONS.json")
    else:
        formal(jobs, root/"forecast", root/"formal", root)
