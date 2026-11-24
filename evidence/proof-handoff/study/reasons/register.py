"""Define a separate prospective, paired information-content intervention."""
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOBS = {
    "private_future": {
        "docket": "Our appendix concerns the scientific proof action that a receiving investigator can actually take. A sender knows a public mathematical type u. A receiver privately knows its future desk y. The sender does not know y. The allowed pairs (u,y) and their nonempty finite intervals of acceptable positive even integers I(u,y) are common knowledge. One message based on u is sent. After reading it, the receiver must pick a witness in I(u,y). Review the draft sentence: if for every individual desk its intervals can be pierced by two witnesses, one binary message always suffices. Decide whether it should be printed and establish a valid replacement if necessary. Our next derivation needs to know exactly when two messages suffice; any rigorous approach is welcome.",
        "lead": "The interval method works when the sender already knows which desk will use the result.",
        "warrant": "Consider whether a fixed label for one type agrees across different desks. A short cycle of required distinctions would test this.",
        "status": "The working file presents the available intervals separately under each desk and records the two permitted messages for the forthcoming revision.",
        "full": "Correct verdict, valid finite counterexample, and necessary and sufficient common labelling/graph condition with a valid proof for finite intervals."
    },
    "ordinary_recovery": {
        "docket": "Our manuscript credits ordinary work for recovering a missed direction. In two possible later states z=0 or 1, indistinguishable to the receiving worker at the time of action, normal work has two available settings k=0 or 1. The actual setting, chosen once before the state can be learned, succeeds exactly if k=z. The baseline scientific message is identical. The draft drops both states from the loss calculation because each has a normal setting that would succeed. Decide what recovery can actually be claimed, including the sharp worst-state success probability if randomization is allowed. State a general criterion for attributing guaranteed recovery with the information available when acting; the appendix will use it to define substitution.",
        "lead": "An ordinary configuration can separately meet the scientific need in each of the two states.",
        "warrant": "Write one receiver rule before choosing the state and evaluate it in both states. Compare that order with choosing a rule separately afterwards.",
        "status": "Both configurations are documented in the current workbook, along with the information available before the decision and the quantities requested for the appendix.",
        "full": "Distinguishes per-state availability from an implementable common policy, certifies no deterministic guarantee, proves and attains minimax probability 1/2, gives a general criterion."
    },
    "alternate_methods": {
        "docket": "In a proof-handoff study each public scientific type is associated with its set of admissible even witnesses. Any one witness in the set suffices. A sender may choose one label per type, and a receiver must take the same action for types with the same label. In a proposed extension to alternative proof methods, each admissible set can be the union of up to two finite even-grid intervals. The paper proposes to merge all types in any group whose sets intersect pairwise, without checking anything further. Decide whether the rule works, construct the smallest counterexample in numbers of types if possible, and give the exact general feasibility criterion for a label group. The result will determine the treatment of scientific substitutes in the supplement.",
        "lead": "Pairwise intersection suffices within a family of single intervals on a line.",
        "warrant": "Check whether different pairs can share different witnesses. A small concrete family can distinguish all-pairs agreement from a single common action.",
        "status": "The diagram places the alternative witnesses on an ordered grid and lists the pairs that the draft proposes to group together.",
        "full": "Correct verdict, explicit valid counterexample of three types with pairwise intersection, exact common-intersection criterion, and justification of minimality."
    }
}


def main():
    manifest = ROOT / "FREEZE.json"
    if manifest.exists():
        raise SystemExit("Registration already exists")
    assignments = [(job, arm) for job in JOBS for arm in ("warrant", "status")]
    random.Random(2026112101).shuffle(assignments)
    key = []
    instructions = ("Independently decide what mathematical work to do and deliver a concise checked argument "
                    "for the editor, up to 450 words. You may refute, repair or replace the draft, stop if unresolvable, "
                    "or identify a better direction. State briefly which part of the note, if any, you used. "
                    "One optional small exact calculation (up to 41 points) is available from the desk on request.")
    for j, (name, arm) in enumerate(assignments):
        record = JOBS[name]
        cue = record[arm]
        other = record["warrant" if arm == "status" else "status"]
        assert len(other.split()) == len(cue.split())
        prompt = f"{record['docket']}\n\nWorking note: {record['lead']} {cue}\n\n{instructions}\n"
        slot = "w" + hashlib.sha256(f"handoff-registered-20261121-{j}".encode()).hexdigest()[:12]
        path = ROOT / "slots" / slot
        path.mkdir(parents=True)
        (path / "docket.txt").write_text(prompt)
        key.append({"slot": slot, "case": name, "arm": arm,
                    "packet_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                    "cue_words": len(cue.split()), "criterion": record["full"]})
    manifest.write_text(json.dumps({"registered_utc": datetime.now(timezone.utc).isoformat(),
                                    "assignments": key}, indent=2) + "\n")
    print(" ".join(r["slot"] for r in key))


if __name__ == "__main__":
    main()
