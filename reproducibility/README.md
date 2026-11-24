# Reproduce the study

[Data_and_code.zip](Data_and_code.zip) is the original, byte-preserved scientific archive distributed with this author edition. Its SHA-256 is recorded in [PUBLICATION.json](../PUBLICATION.json). The archived README and programs describe the study as it was prepared for review. This repository publishes the author's release of those records.

1. Create an environment with Python 3.12 and the versions in [requirements-replay.txt](requirements-replay.txt).
2. Extract `Data_and_code.zip` into an empty directory. From that directory run `python -B verify_evidence.py --prior`.
3. Compare the top-level `verified` and `new_model_calls` fields and numerical results with the [release replay](replay-result.json). Leave Python assertions enabled.

The verifier reconstructs the study layout in a temporary directory, checks digests, regenerates source tables and replays the prior records. It reads 276 saved 8B generations from the attribution study. The six selected downstream problems each have one model run for each note condition and one run on the public problem alone. The 72 astronomy assignments represent eight field-specific forecasts across nine configurations per field. Signed differences across datasets and successful ordinary recovery are part of the result.

For reading on GitHub, [evidence](../evidence/) presents the contents of all three archive layers as directories. The data ZIP preserves the original nested archives used by the historical checksum tests. Use that ZIP for the one-command replay. In the experiment records, `private` and `internal` denote unmasked, study-generated assignments or inputs. The public source register distinguishes original outputs, transformed public observations and third-party works. Some historical launchers record the paths of the original validation host. The offline verifier and the commands above work in a fresh directory.

The [adapter folder](../adapters/) contains 15 1.5B and nine 8B fitted adapters. Base weights and access to any hosted models are separate. For weight-based work, overlay the adapter `records/` directory on the innermost scientific-choice archive and follow that study's [reproduction guide](../evidence/scientific-choice/README.md). Running a fresh model can produce a new observation.

The manuscript's main figures 1–5 correspond to outer-archive figures **4, 5, 1, 2, 3**, respectively. The submitted PDF of Fig. 5d labels the forecasted quantity as an outcome shift. Its numerical source data are unchanged. [Figure rendering guide](../figures/RENDERING.md)
