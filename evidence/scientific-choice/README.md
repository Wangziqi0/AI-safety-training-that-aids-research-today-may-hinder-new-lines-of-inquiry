# Data and code for independent examination

This archive accompanies *Can safety training make AI more cautious and leave promising scientific questions unexplored?* It contains inputs, saved scientific outputs and analysis code for the reported comparisons. These files are provided for manuscript review. The author plans a Zenodo deposit under Apache License 2.0 for original code and CC BY 4.0 for original data. Third-party material retains its own licensing terms, listed in PUBLIC_SOURCES.md. The new deposit has no assigned DOI.

## Reproduce the figures and main results

Extract the archive into a working directory. Python 3.10 or later, NumPy and SciPy are required for the numerical check. Matplotlib is also required to render the figures. From that directory run:

~~~sh
python verify.py
python figures/make_figures.py --out rendered_figures
~~~

The first command reconstructs the matched project identities from both instrument arms, counts the separate protection requests, checks both complete ordinary astronomical workflows, recalculates PG 1520+525 flux errors and the human project rank reversals, solves the direction-identification examples, and regenerates all three source-data tables from the instrument, policy, forecast and identification records. It performs no model calls and uses a temporary directory for regenerated tables. Exact filenames and units for each plot are given in figures/SOURCE_DATA.md. Numeric comparisons use the unrounded records.

The numerical demo ran in approximately two seconds on a Linux x86_64 system with Python 3.12.14, NumPy 2.4.3 and SciPy 1.18.1, excluding installation, extraction, plot rendering and new training. Expected results include 36 shared calibration projects, 72 reconstructed forecasts per handoff implementation, 404 reversals among 814 initially ordered project pairs, and feasible direction-specific counts from 8 to 14 in the 20-project example.

For an end-to-end check of the ordinary astronomical workflow, install Astropy (tested with 7.2.0) alongside NumPy and SciPy and run **python refit_ordinary.py**. This second command repeats the early period search without any native proposal, reselects the later period and aperture for each recovery condition, and refits on measured flux before comparing every held-out prediction and selected pixel with the archived model-assisted workflows. The short demo above instead reads the archived equality records and recalculates selected physical errors. These tests use separate study files and no service calls.

The local study commitments are documented in COMMITMENTS.md. From the extracted root run **python commitments/verify_commitments.py** to verify the available original inputs. The inventory reports exact originals, alternative historical versions and intentionally withheld administrative dependencies separately. These checks verify recorded contents. The study does not claim independent public timestamping of those records.

## Underlying material

| Directory below records | Content and use |
|---|---|
| 20261119_sft_online_rl_structural_round/structural | Original 27-parameter policies and environment, all source measurements, separate deployment requests and case-level downstream records. The standard-library programs producer.py, receiver.py, analysis.py, joint.py and verify.py are the generation and analysis sequence. Run the sequence only in a disposable copy. |
| 20261119_sft_online_rl_structural_round/successor | Selected training materials, gradients, fitted two-head successors, actual adoption and discarded-reading outcomes. The independent numerical verifier reads the supplied training and result arrays. |
| 20261119_open_science_alignment_convergence/lab | Training code, adapter manifests and optimisation logs for the five 1.5B streams. The corresponding public parent model is Qwen2.5-Coder-1.5B-Instruct. |
| 20261119_open_science_alignment_convergence/structural | Independently initialised learned-decoder calculations, with the frozen forecasts and evaluation for all 12 roots reported in Supplementary Information. |
| 20261120_scientific_choice_and_recovery/theory and review | Mathematical counterworlds, linear programs, partial-identification checks and independent finite solutions. Run theory/direction_transport.py for the feasible tables. |
| 20261120_scientific_choice_and_recovery/mechanism | Source and receiver action definitions, all saved full-vocabulary grouped probability measurements, draws, frozen forecasts and exact scoring for the 1.5B study. The arrays store action probabilities and full-vector digests. Rebuilding original full logit vectors also requires the base and adapters. |
| 20261120_scientific_choice_and_recovery/strong | Training, inference and scoring code with the nine 8B adapter manifests, training traces and study office requests. The original runtime.py is preserved at its committed path. In a disposable copy of strong, replace runtime.py with commitments/portable/runtime.py and set QWEN3_BASE to a local copy of public revision b968826d9c46dd6066d109eabc6255188de91218. Only the base directory lookup is adapted. |
| 20261120_scientific_choice_and_recovery/practice, downstream and analysis | Exact astronomical input URLs and checksums, eight analysis-ready field arrays, source actions, selected apertures, withheld observations and forecasts. Numerical reconstruction is possible without a telescope observation, new model generation or a network connection. |
| 20261120_scientific_choice_and_recovery/free_workspace, astra and dialogue | Alternative interface, annotation and raw decisions, fixed hosted prompts and scientific answers, predicted flux arrays, component ablation and scripted communication records. No credentials, transcript of the surrounding study-management conversations or private model weights are required. |
| 20261120_scientific_choice_and_recovery/field | Number-only proposal and execution totals for 43 linked projects, acquisition and analysis scripts, exact public upstream versions and sensitivity summaries. Running analyze.py with its acquisition option obtains the public inputs needed to reproduce additional original-rating analyses. Statements from the external 50-person experiment are reported by its authors and are not reanalysed here. |

The optional adapter archive can be extracted over the same directory to supply 15 small-model and nine 8B trained parameter updates. The public pretrained weights are obtained separately. Full model regeneration additionally requires a suitable GPU, PyTorch and Transformers. Offline calculations use the saved scientific records. The six service decisions were one-time observations. Reissuing their prompts would produce a different experiment.
