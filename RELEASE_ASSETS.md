# Research files

[Download the publication release](https://github.com/Wangziqi0/AI-safety-training-that-aids-research-today-may-hinder-new-lines-of-inquiry/releases/tag/manuscript-v11.2). The Git tree contains the complete manuscripts, figure source data, original data-and-code archive, reporting documents and the unpacked parameters for all 24 trained adapters.

| Download | Contents |
| --- | --- |
| [Article PDF](article/Article.pdf) | Full paper with Methods, references, figures and declarations. |
| [Preprint PDF](preprint/Preprint.pdf) | The same author edition in preprint layout. |
| [Supplementary Information](supplement/SupplementaryInformation.pdf) | Complete supplemental text, results and mathematical arguments. |
| [Data_and_code.zip](reproducibility/Data_and_code.zip) | Preserved three-layer data and code distribution, including the offline verifier. |
| [Complete submission files, including Optional_trained_adapters.zip](https://github.com/Wangziqi0/AI-safety-training-that-aids-research-today-may-hinder-new-lines-of-inquiry/releases/download/manuscript-v11.2/Nature_submission_materials_V11.2.zip) | One package containing the current Article, preprint, supplement, source bundles, forms, figure PDFs, source data, metadata, data and code archive and the byte-preserved optional adapter archive. All 24 tensors are also available individually in [adapters](adapters/). |
| [Optional_trained_adapters.zip](https://github.com/Wangziqi0/AI-safety-training-that-aids-research-today-may-hinder-new-lines-of-inquiry/releases/download/manuscript-v11.2/Optional_trained_adapters.zip) | Standalone download of the original adapter archive, with the source notices and pinned model identifiers. |
| [Manuscript source bundle](submission/Nature_manuscript_source.zip) · [Preprint source bundle](submission/Preprint_source.zip) | Buildable V11.2 LaTeX and figures. |

[SHA-256 checksums and adapter inventory](PUBLICATION.json)

To rebuild both downloadable archives using the public files, run the following command from the repository root. Python 3.12.3 on Ubuntu 24.04 was used to verify the original ZIP byte streams. The builder checks both SHA-256 digests before placing the files in the output directory.

```sh
python3 tools/build_submission_bundle.py --output /tmp/manuscript-v11.2-archives
```
