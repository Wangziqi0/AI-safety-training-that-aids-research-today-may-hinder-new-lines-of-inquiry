#!/usr/bin/env python3
"""Rebuild both downloadable ZIPs from the public Git tree and verify their hashes."""
import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def file_below(directory, relative):
    path = (directory / relative).resolve()
    if not path.is_relative_to(directory.resolve()) or not path.is_file():
        raise ValueError(f"Missing or outside the input tree: {relative}")
    return path


def build_adapters(output):
    layout = json.loads((ROOT / "tools/adapter-zip-metadata.json").read_text())
    with ZipFile(output, "w") as archive:
        for row in layout["files"]:
            source = file_below(ROOT / "adapters", row["path"])
            info = ZipInfo(row["path"], tuple(row["modified"]))
            info.create_system = 3
            info.external_attr = row["mode"] << 16
            archive.writestr(info, source.read_bytes(), compress_type=ZIP_DEFLATED,
                             compresslevel=layout["compression_level"])


def submission_source(name, adapter_zip):
    named_files = {
        "data_and_code/Optional_trained_adapters.zip": adapter_zip,
        "data_and_code/Data_and_code.zip": ROOT / "reproducibility/Data_and_code.zip",
        "for_author/REPRODUCIBILITY.md": ROOT / "submission/Reproducibility.md",
        "for_author/Submission_metadata.md": ROOT / "submission/Submission_metadata.md",
    }
    if name in named_files:
        return named_files[name]
    roots = {
        "manuscript": "article", "preprint": "preprint", "supplement": "supplement",
        "figures": "figures", "source_data": "figures", "source": "submission",
        "editorial": "submission",
    }
    path = PurePosixPath(name)
    return file_below(ROOT / roots[path.parts[0]], Path(*path.parts[1:]))


def build_submission(output, members, adapter_zip):
    with ZipFile(output, "w", allowZip64=True) as archive:
        for name in sorted(members):
            source = submission_source(name, adapter_zip)
            info = ZipInfo(name, (2026, 11, 24, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = ZIP_STORED if source.suffix == ".zip" else ZIP_DEFLATED
            with source.open("rb") as src, archive.open(info, "w") as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    destination = parser.parse_args().output.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    publication = json.loads((ROOT / "PUBLICATION.json").read_text())
    adapter_spec = publication["optional_adapter_archive"]
    bundle_spec = publication["public_submission_bundle"]
    with tempfile.TemporaryDirectory(prefix=".paper-build-", dir=destination) as name:
        temporary = Path(name)
        adapters = temporary / adapter_spec["name"]
        bundle = temporary / bundle_spec["filename"]
        build_adapters(adapters)
        if checksum(adapters) != adapter_spec["sha256"]:
            raise RuntimeError("Adapter archive differs from the registered SHA-256.")
        build_submission(bundle, bundle_spec["files"], adapters)
        if checksum(bundle) != bundle_spec["sha256"]:
            raise RuntimeError("Submission archive differs from the registered SHA-256.")
        for path in (adapters, bundle):
            target = destination / path.name
            if target.exists() and checksum(target) != checksum(path):
                raise FileExistsError(f"Existing file differs: {target}")
        for path in (adapters, bundle):
            target = destination / path.name
            if not target.exists():
                os.replace(path, target)
            print(f"{checksum(target)}  {target.name}")


if __name__ == "__main__":
    main()
