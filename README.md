# AI safety training that aids research today may hinder new lines of inquiry

**Yifan Chen** · Independent researcher · [ORCID 0009-0008-8344-1149](https://orcid.org/0009-0008-8344-1149)

[Read the full article on GitHub](MANUSCRIPT.md) · [Article PDF, 29 pages](article/Article.pdf) · [Preprint PDF, 24 pages](preprint/Preprint.pdf) · [Supplementary Information, 24 pages](supplement/SupplementaryInformation.pdf)

This repository accompanies author edition **V11.2**. The earlier public preprint, version 3.0, appeared under the title *AI safety training that aids current research may hinder future discovery*. [Zenodo version 3.0](https://doi.org/10.5281/zenodo.24442721)

## Research question

A result can be correct even when one collaborator recovers evidence another omitted. Can a training practice that protects users and supports useful research also change which leads people and models raise, test and carry forward?

We held the scientific record, decoding, batch order and output budget fixed and varied the trained Qwen3-8B model that wrote a handoff. On one public task the protection-trained writer questioned a check already present in the record. The next model tested that objection and rejected it. On an archived mathematical task the ordinary-help investigator commissioned a scan, found a counterexample at scale 9 and omitted it from the note. The protection-trained writer passed the counterexample on. A separate model, given only the public problem, independently proved the same correction. [Article](MANUSCRIPT.md) · [Experimental records](evidence/writer-attribution/study/RESULTS.md)

| Records and output allowance | Usable notes under request-level protection | Usable notes under ordinary help |
| --- | ---: | ---: |
| Eight new public tasks × three matched training seeds, 650 tokens | 8/24 | 18/24 |
| The same new tasks and seeds, 1,300 tokens | 13/24 | 18/24 |
| Five archived histories prequalified for sufficient evidence, 650 tokens | 4/5 | 0/5 |
| All 24 archived histories, 650 tokens | 4/24 | 0/24 |

All 18 frontier-model continuations on six selected problems reached justified decisions, including the six given only the public problem. Across eight astronomical fields, ordinary workflows reproduced each field’s forecast in all nine assigned configurations, yielding 72 matched comparisons. Whether repeated beneficial collaboration leaves a later-needed question or method unformed, or prevents its timely recovery at comparable cost, remains open. [Supplementary Information](supplement/SupplementaryInformation.pdf)

## Repository guide

| Material | Where to find it |
| --- | --- |
| Article, including Methods, references, figures and declarations | [Full reading copy](MANUSCRIPT.md) · [PDF](article/Article.pdf) · [LaTeX entry point](article/Article.tex) |
| Preprint and supplement | [Preprint source](preprint/Preprint.tex) · [Supplement source](supplement/SupplementaryInformation.tex) |
| Five main figures, supplementary figure and their numerical tables | [Figure files](figures/) · [Figure 5 rendering notes](figures/RENDERING.md) |
| Complete submitted-paper source bundles, reporting forms, checklist responses and metadata | [Submission materials](submission/README.md) |
| Recorded data, software, formal mathematics and study protocols | [Replay instructions](reproducibility/README.md) · [Original data and code archive](reproducibility/Data_and_code.zip) |
| Browse the studies without unpacking an archive | [Writer attribution](evidence/writer-attribution/) · [Proof handoff](evidence/proof-handoff/) · [Scientific choice and recovery](evidence/scientific-choice/) |
| Twenty-four trained adapters | [Extracted weights and upstream notices](adapters/) · [Research files release](RELEASE_ASSETS.md) |
| Citation, versions and integrity checks | [Citation](CITATION.cff) · [Checksums](PUBLICATION.json) |

## Reproduce the saved results

From the repository root on Linux or macOS with a suitable Python environment, extract the archived record into a new directory and run its verifier. The full replay uses NumPy, SciPy, Astropy and Matplotlib. No hosted model requests or new training are needed.

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r reproducibility/requirements-replay.txt
python -m zipfile -e reproducibility/Data_and_code.zip replay
python -B replay/verify_evidence.py --prior
```

The expected top-level fields are `verified: true` and `new_model_calls: 0`. The full numerical result of the release check is available in [replay-result.json](reproducibility/replay-result.json). To typeset the PDFs with Tectonic and Liberation Serif, run each command from its document directory.

```sh
(cd article && tectonic Article.tex)
(cd preprint && tectonic Preprint.tex)
(cd supplement && tectonic SupplementaryInformation.tex)
```

## Keywords

AI safety training · large language model alignment · AI for science · scientific discovery · human–AI collaboration · scientific reasoning · research evaluation · causal inference · reproducible research · formal verification.

## Licensing

Original software is available under Apache-2.0. The original manuscript, figures and research data are available under CC BY 4.0. Publisher forms, public datasets, model dependencies and other third-party works retain their own terms. [Licensing and attribution](LICENSE_STATUS.md)
