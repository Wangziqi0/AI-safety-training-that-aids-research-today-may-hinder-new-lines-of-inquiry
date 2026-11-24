"""All assigned counts and arithmetic by field, training family, seed, and their cross."""
from collections import defaultdict
from receiver import HERE, PRACTICE, jsonl, dump

def tabulate():
    substitutes=jsonl(HERE/"standing_substitution.jsonl")
    tables={}
    for b, file in (("assigned_lock","receiver_input_scanned.jsonl"),("stewardship_lock","stewardship_receiver_input_scanned.jsonl")):
        products={r["id"]:r for r in jsonl(PRACTICE/file)}
        rows=jsonl(HERE/b/"unblinded"/"all_assigned.jsonl")
        sub={r["id"]:r for r in substitutes if r["batch"]==b}
        cmp=[r for r in jsonl(HERE/b/"unblinded"/"paired_changes.jsonl") if r["comparison"]=="assigned_product_vs_matched_ordinary"]
        diffs={r["id"]:r for r in cmp}
        groups=defaultdict(list)
        for r in rows:
            for k in ("all","arm="+r["arm"],"seed="+str(r["seed"]),"field="+r["field"],
                      f"{r['field']}/{r['arm']}/{r['seed']}"):
                groups[k].append(r)
        out={}
        for k,rr in groups.items():
            ids=[r["id"] for r in rr]
            gs=[diffs[i]["gain"] for i in ids]
            out[k]={"n":len(ids),"packets":sum(len(products[i]["formed_packets"]) for i in ids),
                    "recovery_offers":sum(r["recovery"] for r in rr),
                    "sum_scaled_loss":sum(r["actual_normalized_mae"] for r in rr),
                    "mean_scaled_loss":sum(r["actual_normalized_mae"] for r in rr)/len(rr),
                    "gain_vs_downstream_ordinary_sum":sum(gs),"improved":sum(g>0 for g in gs),"worsened":sum(g<0 for g in gs),
                    "forecast_equal_to_complete_standing_substitute":sum(sub[i]["same_forecast"] for i in ids),
                    "logical_fits_actual":sum(sub[i]["actual_candidate_aperture_fits"] for i in ids),
                    "logical_fits_complete_standing":sum(sub[i]["fallback_candidate_aperture_fits"] for i in ids)}
        tables[b]=out
    dump(HERE/"ALL_ASSIGNMENTS_GROUPED.json",tables)
if __name__=="__main__":
    tabulate()
