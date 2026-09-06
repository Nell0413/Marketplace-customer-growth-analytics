#!/usr/bin/env python3
"""Build a non-destructive PBIX layout candidate. Desktop validation is required.

The imported DataModel, DAX and Power Query sources are not changed. The original
PBIX is never overwritten. This is not a Power BI compiler or refresh engine.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import zipfile
from pathlib import Path

from inspect_pbix import DEFAULT_PBIX, read_report

PAGE = "Report/definition/pages/commercial/visuals/"


def literal(value):
    return {"expr": {"Literal": {"Value": value}}}


def patch_visuals(definitions):
    def visual(name):
        return definitions[f"{PAGE}{name}/visual.json"]

    scatter = visual("7bc55ec2e575d539aed1")
    # Automatic axes keep low-performing states visible after slicing. Do not
    # clip percentages below 80% or force all subsets onto the full-data GMV scale.
    objects = scatter["visual"]["objects"]
    objects["categoryAxis"][0]["properties"].pop("start", None)
    objects["categoryAxis"][0]["properties"]["end"] = literal("1D")
    objects["valueAxis"][0]["properties"].pop("end", None)
    objects["categoryLabels"][0]["properties"]["fontSize"] = literal("9D")
    scatter["position"].update(y=279, height=240)

    low_review = visual("ff9e459478e8dc0c4493")
    low_review["visual"]["objects"]["valueAxis"][0]["properties"]["end"] = literal("1D")

    monthly = visual("9b140d1b57331f295972")
    axis = monthly["visual"]["objects"]["categoryAxis"][0]["properties"]
    axis["axisType"] = literal("'Continuous'")
    axis["fontSize"] = literal("9D")
    # The imported year_month column is a date (first of each month). A continuous
    # month axis uses ticks instead of squeezing all 24 category labels into 428px.
    for key in ("preferredCategoryWidth", "maxMarginFactor", "concatenateLabels"):
        axis.pop(key, None)
    query = monthly["visual"]["query"]
    projection = query["queryState"]["Category"]["projections"][0]
    projection["field"]["Column"]["Property"] = "year_month"
    projection["queryRef"] = "dim_date.year_month"
    projection["format"] = "MMM yyyy"
    query["sortDefinition"]["sort"][0]["field"]["Column"]["Property"] = "year_month"

    title = visual("11ca9f13ab266843569b")
    title["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["value"] = "Actions | full-data baseline"
    return definitions


def build(source: Path, destination: Path):
    if destination.exists() or source.resolve() == destination.resolve():
        raise ValueError("Destination must be a new file; the original is never overwritten")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    with zipfile.ZipFile(source) as original:
        definitions = {
            name: json.loads(original.read(name))
            for name in original.namelist()
            if name.startswith(PAGE) and name.endswith("/visual.json")
        }
        before = {name: json.dumps(value, sort_keys=True) for name, value in definitions.items()}
        patch_visuals(definitions)
        changed = {name: value for name, value in definitions.items() if json.dumps(value, sort_keys=True) != before[name]}
        if len(changed) != 4:
            raise ValueError("Unexpected report structure: expected exactly four visual changes")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as candidate:
            for info in original.infolist():
                # Old authoring integrity metadata cannot describe the edited report.
                # Desktop must regenerate it when the candidate is opened and saved.
                if info.filename == "SecurityBindings":
                    continue
                content = original.read(info.filename)
                if info.filename in changed:
                    content = json.dumps(changed[info.filename], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                elif info.filename == "[Content_Types].xml":
                    content = content.replace(b'<Override PartName="/SecurityBindings" ContentType="" />', b'')
                # writestr mutates ZipInfo offsets; never mutate the source reader's metadata.
                candidate.writestr(copy.copy(info), content)
        with zipfile.ZipFile(destination) as candidate:
            if candidate.read("DataModel") != original.read("DataModel"):
                raise ValueError("Imported model changed unexpectedly")
            changed_members = [name for name in candidate.namelist() if candidate.read(name) != original.read(name)]
            if set(changed_members) != set(changed) | {"[Content_Types].xml"}:
                raise ValueError("Unexpected archive member changed")
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
        raise ValueError("Original PBIX changed unexpectedly")
    check = read_report(destination)
    if check["errors"]:
        raise ValueError(check["errors"])
    return {"file": destination.name, "source_sha256": source_hash,
            "candidate_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "changed_visuals": list(changed), "static_errors": check["errors"],
            "data_model_unchanged": True,
            "status": "REQUIRES Windows Power BI Desktop open/save, visual and filter checks; source paths remain unchanged"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_PBIX)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output), indent=2))


if __name__ == "__main__":
    main()
