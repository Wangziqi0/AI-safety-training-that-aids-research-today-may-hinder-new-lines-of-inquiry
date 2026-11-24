# Main-figure source data and reproducibility

The three CSV files include the numerical inputs to every panel. Blank cells indicate columns used by a different record type. Rendering requires Python, Matplotlib and NumPy. The files do not require network access, trained weights, a GPU or a model-service subscription.

```sh
python make_figures.py
```

Run from any directory with the full path to the script, or from this folder as shown. It finds the CSVs next to the script. Optional `--data` and `--out` arguments accept alternate directories. Add `--figure 3` to render only Figure 3. The extractor accepts the same optional single-figure choice. The script produces one editable PDF, one text-preserving SVG and one PNG preview per figure. A second, optional script re-extracts the CSVs from the scientific records when those two round directories are available. Run `python extract_figure_data.py /path/to/rounds --out /path/to/tables`. The published figure tables, unrounded values and plotting program are sufficient to regenerate all artwork.

## Figure 1. Trained document policies and the constructed instrument

Input files are `20261119_sft_online_rl_structural_round/structural/outcomes.jsonl.gz` and `deployment.jsonl.gz`. The former contains separately executed current and subsequent instrument operations. The latter contains held-out document requests. The arm codes are request-level protection (A) and request fulfilment (H). The simulator rewarded H for disclosing a flagged fictional field when asked. Source extraction retains the 2,304 held-out scientific cases per arm, mapping and optimizer. Exposure data use 128 restricted requests per seed and arm, spanning ordinary and alias requests with the common deployment filter. No arm- or outcome-dependent exclusions occur.

| Column | Definition |
|---|---|
| `kind` | `paired_seed_delta` for a training/environment replicate, `contingency` for a joint count at the positive mapping, or `matched_joint_project` for the identifier of each highlighted project |
| `algorithm` | `sft` for supervised training, `reinforce` for online sampled-policy reinforcement learning |
| `mapping` | `aligned` for an imposed positive instrument readout, `cut` for its removal, `reversed` for reversal, `service` for the separate deployment assay |
| `seed, family, clone` | Replicate and paired project identifiers, meaningful within the simulation |
| `metric` | `disclosure` after the common filter, `current` calibration used on time, or `later` correct measurement of a new specimen |
| `change_current, change_later` | A minus H in a paired project, coded −1 for loss, 0 for a tie and +1 for gain |
| `numerator, denominator` | For a replicate effect, numerator is the difference in positive counts and denominator is the number per arm. For a contingency, numerator is the number of paired projects and denominator is 2,304. |

In panels a, c and d the point is the arithmetic mean of 24 paired seed differences on the percentage-point scale. Each pointwise interval is the mean ± 2.06866 times the sample standard deviation of the 24 paired differences divided by the square root of 24. The contingency in panel b shows supervised training. Its highlighted cell has the same 36 project identifiers under the second optimizer. The two algorithms are paired by the sampling and environmental draws; cases cannot be pooled as independent confirmations. Per-project protection is unobserved in that contingency.

## Figure 2. Sharp identification and small-model challenge predictions

Panels a and b use `theory/NUMERICAL_CHECK.json` under `20261120_scientific_choice_and_recovery`. Panel c uses `review/TRANSPORT_VERIFICATION.json`; panel d uses `mechanism/PREDICTION_CHECK.json` from the same round.

| Column | Definition |
|---|---|
| `panel` | Maps directly to printed panel letters |
| `group, condition` | Panel a uses workflow H or A and the assigned or ordinary recovery regime. Panel b uses the two indistinguishable mathematical worlds. In panel d, `local` uses challenge contexts and `transfer` uses index contexts at 0.25 or 1.0 of the observed H-to-A weight displacement. |
| `metric, value, total` | Panel a gives regime-conditional counts per eight baseline projects, obtained by normalizing the randomized cell probabilities. `ineligible` is H's ordinary continuation because no H project needed an offer. Panel b reports the linked count. Panel d gives numbers of forecasts that agreed, missed or abstained. The denominator of 35 is seven registered endpoints times five training streams. |
| `low, high` | Sharp feasible counts in an example with 20 projects. `sharp` requires recorded scientific compatibility. `identity_ignored` is a different event. |

The 8-project and 20-project examples are mathematical constructions. The small-model analysis uses matched trained weights in five streams, reuses the same 12 challenge jobs and shares endpoint inputs. Abstentions contribute to the full bar length, but never to the denominator for sign accuracy. None of these intervals or bars is a confidence interval.

## Figure 3. Physical forecasts, ordinary recovery and source activity

These records are under `20261120_scientific_choice_and_recovery`. Field names and labels derive from `practice/COHORT.json`. Physical predictions and withheld hourly flux (electrons per second) were read from `downstream/assigned_lock/results.jsonl` and its `products/*.npz`. Complete-chain replays use `downstream/standing_substitution.jsonl`. The native proposed and ordinary early periods come from the nine `practice/current_choices.jsonl` records for PG 1520+525. The downstream committed model supplies the final period. Fixed-menu and open-brief acquisition counts derive respectively from `analysis/primary_case.csv` and the assigned (one per case) rows of `free_workspace/attribution_paired.jsonl`. Closed-service astronomical assignments and the fitted component ablation come from `astra/RESULT.json`. The fixed constant error in panel d is the physical (unscaled) error of that field's constant receiver reference. Original TESS observations are available through the NASA [Mikulski Archive for Space Telescopes](https://archive.stsci.edu/missions-and-data/tess).

| Column | Definition |
|---|---|
| `panel, field, label` | Printed panel, field identifier and public field name |
| `group` | The forecast route, source safety-training group or incoming frontier handoff. `ordinary_chain` includes the ordinary upstream worker as well as the downstream receiver. `downstream_only` permits that receiver its published and own derived candidates. `constant` is a separate reference. |
| `metric, value` | In panel b, `scaled_MAE` gives normalized mean absolute error, scaled by the mean absolute flux deviation from the median over the fitting segment. `period_days` identifies the model-proposed, ordinary upstream and selected late periods in PG 1520+525. In c, `active_assignments` is the number of assignments yielding at least one measured product, `products_total` is their total output, and `products_per_assignment` records the individual count for every case. In d, physical mean absolute error in electrons per second. |
| `raw_e_s` | Corresponding unscaled mean absolute error in panel b, in electrons per second |
| `total` | Number of withheld hourly bins in b (error rows) and d, the number of contributing source assignments for the three period rows in b, or the number of field and training-start assignments per condition in the summary rows of c |
| `time_day` | Archived TESS time in days. Panel a subtracts the time of the first withheld hour. |
| `observed_e_s, downstream_only_e_s, all_channel_e_s, constant_e_s` | Actual nominal-aperture flux, receiver-only prediction, prediction with the current product and constant prediction. Included once per withheld hour. The constant repeats the median nominal flux across the entire pretest segment (fitting and validation). |
| `interface, case_id` | Panel c gives `menu` for the fixed primary menu and `open` for the open brief. Case identifiers link the same initial assignment across the two interfaces. |

The PG 1520+525 benchmark repeats the pretest median of 37.0069694519043 electrons per second. On the withheld section its mean absolute error was 1.3251161283376265 electrons per second. The ordinary receiver alone yielded 1.8608140058262557 and the forecast using the early period yielded 1.6102888848760062 in the same units. In panel b an error reduction is comparator error minus full-workflow error, positive for an improvement. Nine source assignments per field produce identical outcomes; each unique field appears once. Relative to the complete ordinary chain, all differences are exactly zero. Panel c keeps every assignment, including those with zero acquired products. Each fixed-menu positive assignment produced one product. Under the open brief, 18 of 24 ordinary-help assignments produced 55 products, six of 24 request-safety assignments produced 19, and zero of 24 field-safety assignments produced any. Panel c counts 24 assignments per recipe and interface with eight fields and three matched starts. Source work and later predictive gain have separate units. Panel d has three blinded incoming assignments for one closed model on one field. Removing the transmitted term is a deterministic one-component re-fit; the constant is an available reference. Lower error is better.
