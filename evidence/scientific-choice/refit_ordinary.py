"""Refit the full ordinary photometry workflow from the field arrays, without model calls."""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent / "records" / "20261120_scientific_choice_and_recovery"
sys.path.insert(0,str(BASE/"practice"))
sys.path.insert(0,str(BASE/"downstream"))
import early
import receiver


def main():
    metadata = receiver.cohort()
    seen = Counter()
    biggest = 0.0
    unique_bins = {}
    for field, details in sorted(metadata.items()):
        # Independently rerun earlier selection with no native proposal, on archived measurements.
        early_period = early.cur_decide(field,[])["period_days"]
        later = receiver.Field(field,details)
        ordinary_choices = {offer:later.choose({"period_days":early_period},False,offer)
                            for offer in (False,True)}
        with np.load(BASE/"practice"/"fields"/(field+".npz")) as raw:
            time = raw["late_pt"]
            cube = raw["late_px"]
        target = receiver.extract(cube,later.masks["spoc"])
        end = later.end
        unique_bins[field] = len(time)-end
        forecasts = {}
        for offer, decision in ordinary_choices.items():
            pixels = later.masks[decision["aperture"]]
            series = receiver.extract(cube,pixels)
            prediction = receiver.fitted(time[:end],series[:end],target[:end],
                                         decision["component"],time[end:])
            forecasts[offer] = (decision,pixels,prediction)
        for branch in ("assigned_lock","stewardship_lock"):
            directory=BASE/"downstream"/branch
            for row in receiver.jsonl(directory/"results.jsonl"):
                if row["field"]!=field or not row.get("packets"):
                    continue
                if row["recovery"]!=row["assigned_recovery"]:
                    continue
                chosen,pixels,prediction=forecasts[row["recovery"]]
                assert (row["component"],row["aperture"])==(chosen["component"],chosen["aperture"])
                with np.load(directory/"products"/(row["artifact"]+".npz")) as record:
                    np.testing.assert_array_equal(record["time"],time[end:])
                    np.testing.assert_array_equal(record["aperture_flat"],pixels)
                    np.testing.assert_allclose(record["prediction"],prediction,rtol=0,atol=1e-9)
                    biggest=max(biggest,float(np.max(np.abs(record["prediction"]-prediction))))
                assert abs(receiver.mae(target[end:],prediction)-row["mae_electrons_s"]) < 1e-9
                seen[branch]+=1
    assert len(unique_bins)==8 and sum(unique_bins.values())==1159
    assert seen == {"assigned_lock":72,"stewardship_lock":72}
    print(json.dumps({"ordinary_refits_matching_assigned_forecasts":dict(seen),
                      "distinct_test_bins":sum(unique_bins.values()),
                      "largest_flux_difference_electrons_per_s":biggest,
                      "ordinary_source_received_native_proposals":False,
                      "new_model_calls":0},indent=2))


if __name__=="__main__":
    main()
