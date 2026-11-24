# Replaying the controlled handoff and its checks

The frozen six primary requests in inputs/ each contain an original four-history block routed to both fitted Qwen3-8B writers. Every original inference message is in each request. raw/ contains all 48 replies, their token IDs, EOS and cap flags, observed context lengths, base and fitted identities, interval receipts and wrapper logs. The separate secondary/ and expanded/ directories hold full requests and outputs for the other trained recipe and increased token allowance. The five opportunity-qualified histories were chosen before the primary notes were released. One pair of writer outputs at each budget is graded per eligible history. Other expanded outputs preserve the exact four-position batches only.

The frozen original model driver is rounds/20261120_scientific_choice_and_recovery/strong/infer.sh. Its unmodified interface accepts an input JSONL file and a fresh output path, places GPU work in the existing verification-host inference lock, and returns the complete output. For a primary block supply one exact inputs/bNN.jsonl. For the specificity or length check supply secondary/inputs.jsonl or expanded/inputs.jsonl. FREEZE.json and expanded/FREEZE.json bind all inputs, the named base and training checkpoints, inference code, source artifacts, scoring rules or their locations, and the fixed allocation digests. Retain original raw files when comparing future replays.

After the blind score lock, running the following in cross/ with Python's standard library verifies the primary and secondary records against the archived evidence and already generated local receipts.

```sh
python3 -B audit.py
python3 -B length_audit.py
```

The first materialization uses the same commands with --record; subsequent runs compare the exact derived receipts. audit.json, cell_metadata.tsv and service_receipts.tsv expose token counts, per-stage duration, exact historical replay differences if present, and each unrestricted-service receipt. length_audit.json and length_cells.tsv identify the ten prospectively scored writer–history cells and compare their first 650 tokens, stopping condition and expanded public text. Receiver packet verification checks the actual archival note, prospective opposite-writer note and no-note alternative for both selected dockets. The primary mathematical conclusion additionally requires the independent opportunity and final note grades; downstream use additionally requires the recipients' recorded subsequent work.
