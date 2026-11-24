"""Reanalyse the archived native 1.5B probability instrument without fitting a model."""
import argparse
import csv
import json
from pathlib import Path
from statistics import mean


def contrast(aa, ah, ha, hh):
    writer = ((aa - ah) + (ha - hh)) / 2
    history = ((aa - ha) + (ah - hh)) / 2
    return {"total": aa - hh, "writer": writer, "history": history,
            "interaction": (aa - ah) - (ha - hh)}


def main(source, output):
    values = json.loads(source.read_text())
    records = []
    for fit, modes in values.items():
        if fit == "base":
            continue
        algorithm, seed = fit.split("-")
        for fold in modes["A/A"]:
            for schedule, endpoints in modes["A/A"][fold].items():
                for endpoint in endpoints:
                    cells = {k: modes[k][fold][schedule][endpoint] for k in ("A/A", "A/H", "H/A", "H/H")}
                    stats = contrast(*cells.values())
                    records.append({"algorithm": algorithm, "seed": int(seed), "fold": fold,
                                    "schedule": schedule, "endpoint": endpoint, **cells, **stats})
    output.mkdir(parents=True, exist_ok=True)
    with (output / "small_model_cross.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    error = max(abs(r["total"] - (r["history"] + r["writer"])) for r in records)
    assert len(records) == 5 * 3 * 5 * 12 and error < 2e-14
    challenge = [r for r in records if r["fold"] == "challenge" and r["endpoint"] == "correct"]
    details = {schedule: [{key: r[key] for key in ("algorithm", "seed", "total", "history", "writer", "interaction")}
                          for r in challenge if r["schedule"] == schedule] for schedule in ("natural", "late_full")}
    means = {name: {alg: {k: mean(r[k] for r in rows if r["algorithm"] == alg)
                         for k in ("total", "history", "writer", "interaction")}
                    for alg in ("sft", "rl")} for name, rows in details.items()}
    result = {"source": "Archived native grouped-token probabilities and evaluated policy values",
              "new_model_fits_or_generations": 0, "decompositions": len(records),
              "maximum_additivity_residual": error,
              "challenge_algorithm_means_probability_units": means,
              "challenge_later_accuracy_by_fit_probability_units": details,
              "complete_late_supply_max_history_component": max(abs(r["history"]) for r in details["late_full"])}
    (output / "small_model_summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("decompositions", "maximum_additivity_residual",
                                            "complete_late_supply_max_history_component")}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    main(a.source, a.output)
