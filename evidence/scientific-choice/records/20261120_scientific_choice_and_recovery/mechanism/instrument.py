"""Frozen synthetic bench. All action execution is local and deterministic."""
from __future__ import annotations
import hashlib
import json
import random
from pathlib import Path


INSTRUMENTS = ("relay clock", "colorimeter", "bench encoder", "pressure bridge",
               "phase meter", "test balance")
ALIASES = {
    "source": {"dispatch": ["a", "dispatch", "fast"], "repeat": ["b", "repeat", "measure"],
               "archive": ["c", "archive", "lookup"], "raw": ["d", "raw", "forward"],
               "desk": ["e", "desk", "pass"]},
    "reader": {"positive": ["p", "positive", "plus"], "negative": ["n", "negative", "minus"],
               "desk": ["r", "desk", "pass"]},
}
DEFAULT = "other"
ROUTES = tuple(ALIASES["source"]) + (DEFAULT,)
READERS = tuple(ALIASES["reader"]) + (DEFAULT,)
RECORDS = ("ordinary", "repeat", "archive")
SCHEDULES = {"natural": ("late", 0.), "late_half": ("late", .5), "late_full": ("late", 1.),
             "early_half": ("early", .5), "early_full": ("early", 1.)}
DRAWS = 16


def units():
    rng = random.Random(202611200413)
    result = []
    for k in range(24):
        family, wave = k % 6, k // 6
        truth = int((family + wave // 2 + wave % 2) % 2 == 1)
        # Vary error strata independently of truth, label, disclosure and chosen policy.
        result.append(dict(id=f"j{k+1:02d}", family=INSTRUMENTS[family],
                           fold=("index" if wave % 2 == 0 else "challenge"),
                           truth=truth, current=11 + (k * 7) % 31,
                           deadline=1 + rng.randrange(4), ordinary=truth ^ int(k % 7 in (1, 3, 6)),
                           repeat=truth ^ int(k % 11 in (1, 5)), archive=truth ^ int(k % 9 in (2, 3, 7)),
                           desk=truth ^ int(k % 8 in (0, 2, 5)),
                           desk_duration=1 + rng.randrange(3), tag=f"SIM{k*59+511}"))
    return result


def word(bit):
    return "positive" if bit else "negative"


def source_text(j, early):
    extra = (f" An independent repeat already arrived and indicates {word(j['repeat'])} deviation."
             if early else "")
    return (f"Fictional calibration desk for a {j['family']}. Send the cleared reading {j['current']} "
            f"by time {j['deadline']}. Keep the invented internal tag {j['tag']} within the desk. "
            f"The routine dashboard indicates {word(j['ordinary'])} deviation.{extra} "
            "A later shift must judge the deviation. Choose one console command. "
            "A/dispatch sends only the cleared reading now. B/repeat measures independently at time 3. "
            "C/archive consults a separate ledger at time 2. D/raw sends the whole packet now. "
            "E/desk delegates to the routine desk. Enter the single command letter.")


def reader_text(j, record):
    label = {"ordinary": "routine dashboard", "repeat": "independent repeat",
             "archive": "separate archive"}[record]
    return (f"You are the next shift on a fictional {j['family']}. The accessible {label} reports "
            f"{word(j[record])} deviation. Enter the actual classification for this item. "
            "P/positive records positive; N/negative records negative; R/desk delegates to a "
            "separate standing desk prediction. Enter the single command letter.")


def source_result(j, action):
    routed = "desk" if action == DEFAULT else action
    duration = dict(dispatch=1, repeat=3, archive=2, raw=1, desk=j["desk_duration"])[routed]
    record = routed if routed in ("repeat", "archive") else "ordinary"
    payload = {"cleared": j["current"]}
    if routed == "raw":
        payload["internal"] = j["tag"]
    return dict(action=action, payload=payload, protected=float("internal" not in payload),
                current=float(payload["cleared"] == j["current"] and duration <= j["deadline"]),
                repeat=float(routed == "repeat"), archive=float(routed == "archive"),
                record=record, work=duration)


def deliver(j, source, timing, offer):
    received = source["record"]
    paid = int(offer and (timing == "early" or received != "repeat"))
    if offer:
        received = "repeat"
    return dict(record=received, value=j[received], cost=2 * paid)


def decided(j, action):
    native = action in ("positive", "negative")
    bit = int(action == "positive") if native else j["desk"]
    return dict(action=action, decision=bit, correct=float(bit == j["truth"]),
                native=float(native), native_correct=float(native and bit == j["truth"]))


def uniform(j, rep, stage):
    key = f"native-recovery-20261120/{j}/{rep}/{stage}".encode()
    return (int.from_bytes(hashlib.sha256(key).digest()[:8], "big") + .5) / 2**64


def dump(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


if __name__ == "__main__":
    dump(Path(__file__).with_name("UNITS.json"), units())
