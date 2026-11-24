"""Trace frozen upstream ordinary choices into the already locked receiver, without using any source proposals."""
from collections import defaultdict
from receiver import FIELDS, HERE, PRACTICE, Field, cohort, dump, jsonl,save_rows

def main():
    earlier={r["id"]:r for r in jsonl(PRACTICE/"current_choices.jsonl")}
    arms={r["id"]:r["arm"] for r in jsonl(PRACTICE/"arm_key.jsonl")}
    meta=cohort()
    outputs=[]
    for field in FIELDS:
        receiver=Field(field,meta[field])
        for batch in ("assigned_lock","stewardship_lock"):
            allrows=jsonl(HERE/batch/"results.jsonl")
            fieldrows=[r for r in allrows if r["field"]==field]
            for r in fieldrows:
                if not r.get("packets") or r["recovery"]!=r["assigned_recovery"]:
                    continue
                src=earlier[r["id"]]
                ordinary=src["ordinary"]["period_days"]
                chosen=receiver.choose({"period_days":ordinary},False,r["recovery"])
                same=(chosen["component"],chosen["aperture"])==(r["component"],r["aperture"])
                matches=[v for v in fieldrows if v["component"]==chosen["component"] and v["aperture"]==chosen["aperture"]]
                if not matches:
                    raise ValueError("new unscored decision; cannot infer actual error")
                alternative=matches[0]
                outputs.append({"id":r["id"],"arm":arms[r["id"]],"field":field,"seed":r["block_seed"],"batch":batch,
                     "assigned_recovery":r["recovery"],"ordinary_upstream_period_days":ordinary,
                     "upstream_current_period_days":src["decision"]["period_days"],"upstream_current_origin":src["decision"]["origin"],
                     "standing_receiver_aperture":chosen["aperture"],"standing_receiver_component":chosen["component"],
                     "fallback_mae":alternative["normalized_mae"],"actual_mae":r["normalized_mae"],
                     "gain":alternative["normalized_mae"]-r["normalized_mae"],"same_forecast":same,
                     "fallback_candidate_aperture_fits":chosen["candidate_fits"],"actual_candidate_aperture_fits":r["candidate_fits"]})
    save_rows(HERE/"standing_substitution.jsonl",outputs)
    for b in ("assigned_lock","stewardship_lock"):
        rs=[r for r in outputs if r["batch"]==b]
        print(b,"identical",sum(r["same_forecast"] for r in rs),"/",len(rs),"standing/actual fits",
              sum(r["fallback_candidate_aperture_fits"] for r in rs),sum(r["actual_candidate_aperture_fits"] for r in rs))
if __name__=="__main__":
    main()
