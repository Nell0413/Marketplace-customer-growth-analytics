#!/usr/bin/env python3
"""Read a PBIX archive without modifying it; optionally inspect its import model.

The standard-library mode checks report JSON, references between pages, and
canvas bounds. --model additionally requires the optional pbixray package.
This does not execute DAX, Power Query, or the Power BI visual renderer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path


DEFAULT_PBIX = (
    Path(__file__).resolve().parents[1]
    / "powerbi"
    / "Dashboard_Commercial_Fulfilment_Final.pbix"
)
FILE_CONTENTS = re.compile(r'(File\.Contents\(\s*")([^"\r\n]+)("\s*\))')


def walk(value):
    """Yield each JSON object, for field references stored at different depths."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def read_report(pbix: Path) -> dict:
    result = {"pages": [], "errors": [], "warnings": []}
    with zipfile.ZipFile(pbix) as archive:
        bad_member = archive.testzip()
        if bad_member:
            result["errors"].append(f"Archive CRC failed: {bad_member}")
        names = archive.namelist()
        if len(names) != len(set(names)):
            result["errors"].append("Archive contains duplicate member names")
        definitions = {}
        for name in names:
            if name.startswith("Report/definition/") and name.endswith(".json"):
                try:
                    definitions[name] = json.loads(archive.read(name))
                except (UnicodeError, json.JSONDecodeError) as exc:
                    result["errors"].append(f"Invalid JSON: {name}: {exc}")
        page_paths = sorted(n for n in definitions if n.endswith("/page.json"))
        if not page_paths:
            result["errors"].append("No PBIR page definitions found")
        for page_path in page_paths:
            page = definitions[page_path]
            folder = page_path.rsplit("/", 1)[0]
            page_summary = {
                "name": page.get("name"),
                "display_name": page.get("displayName"),
                "width": page.get("width"),
                "height": page.get("height"),
                "visuals": [],
            }
            seen_ids = set()
            for name, item in definitions.items():
                if not name.startswith(folder + "/visuals/") or not name.endswith("/visual.json"):
                    continue
                visual_id = item.get("name")
                if visual_id in seen_ids:
                    result["errors"].append(f"Duplicate visual ID in {folder}: {visual_id}")
                seen_ids.add(visual_id)
                pos = item.get("position", {})
                try:
                    x, y, width, height = (float(pos[key]) for key in ("x", "y", "width", "height"))
                    if min(x, y) < 0 or min(width, height) <= 0 or x + width > page["width"] + 0.01 or y + height > page["height"] + 0.01:
                        result["errors"].append(f"Visual outside canvas: {visual_id}")
                except (KeyError, TypeError, ValueError):
                    result["errors"].append(f"Invalid position: {visual_id}")
                references = sorted({str(v["queryRef"]) for v in walk(item) if "queryRef" in v})
                text_runs = [v["value"] for v in walk(item) if "textStyle" in v and isinstance(v.get("value"), str)]
                visual = item.get("visual", {})
                page_summary["visuals"].append({
                    "id": visual_id,
                    "type": visual.get("visualType"),
                    "position": pos,
                    "references": references,
                    "text": text_runs,
                })
            result["pages"].append(page_summary)
        order = definitions.get("Report/definition/pages/pages.json", {})
        page_names = {page["name"] for page in result["pages"]}
        for name in order.get("pageOrder", []):
            if name not in page_names:
                result["errors"].append(f"Page order references absent page: {name}")
        active_page = order.get("activePageName")
        if active_page and active_page not in page_names:
            result["errors"].append(f"Active page does not exist: {active_page}")
        result["report_json_files"] = len(definitions)
        result["contains_import_model"] = "DataModel" in names
    return result


def redact_query(expression: str) -> str:
    def replace(match):
        filename = re.split(r"[/\\]", match.group(2))[-1]
        return f'{match.group(1)}[LOCAL_SOURCE]/{filename}{match.group(3)}'
    return FILE_CONTENTS.sub(replace, expression)


def read_model(pbix: Path, reveal_source_paths: bool) -> dict:
    try:
        from pbixray import PBIXRay
    except ImportError as exc:
        raise RuntimeError("Optional model inspection requires: pip install pbixray==0.15.5") from exc
    from importlib.metadata import version

    # DataFrame.to_json normalises nullable scalar types before JSON output.
    def records(frame):
        return json.loads(frame.to_json(orient="records"))

    with PBIXRay(str(pbix)) as model:
        queries = records(model.power_query)
        local_queries = [q["TableName"] for q in queries if FILE_CONTENTS.search(q.get("Expression", ""))]
        if not reveal_source_paths:
            for query in queries:
                query["Expression"] = redact_query(query.get("Expression", ""))
        return {
            "extractor": f"pbixray {version('pbixray')}",
            "tables": list(model.tables),
            "relationships": records(model.relationships),
            "measures": records(model.dax_measures),
            "calculated_columns": records(model.dax_columns),
            "queries": queries,
            "parameters": records(model.m_parameters),
            "literal_file_source_queries": local_queries,
            "source_paths_redacted": not reveal_source_paths,
        }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pbix", nargs="?", type=Path, default=DEFAULT_PBIX)
    parser.add_argument("--model", action="store_true", help="Read model metadata using optional pbixray")
    parser.add_argument("--reveal-source-paths", action="store_true", help="Include private original source paths in model output; do not commit that output")
    parser.add_argument("--require-portable", action="store_true", help="Fail if --model detects literal file sources")
    parser.add_argument("--output", type=Path, help="Write generated JSON to this file instead of stdout")
    args = parser.parse_args(argv)
    if (args.require_portable or args.reveal_source_paths) and not args.model:
        parser.error("--require-portable and --reveal-source-paths require --model")
    try:
        fingerprint = hashlib.sha256(args.pbix.read_bytes()).hexdigest()
        result = read_report(args.pbix)
        result["file_name"] = args.pbix.name
        result["sha256"] = fingerprint
        result["verification_scope"] = "Static archive/model inspection only; no Power BI Desktop rendering, DAX execution or refresh."
        if args.model:
            result["model"] = read_model(args.pbix, args.reveal_source_paths)
            literal_sources = result["model"]["literal_file_source_queries"]
            if literal_sources:
                result["warnings"].append("Original model uses literal file sources: " + ", ".join(literal_sources))
                if args.require_portable:
                    result["errors"].append("Portable-source requirement failed: literal File.Contents paths remain")
        if hashlib.sha256(args.pbix.read_bytes()).hexdigest() != fingerprint:
            result["errors"].append("PBIX changed during inspection")
        content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(content, encoding="utf-8")
            print(f"Inspected {args.pbix.name}: {len(result['pages'])} pages, {len(result['errors'])} errors, {len(result['warnings'])} warnings; output: {args.output}")
        else:
            print(content, end="")
        return 1 if result["errors"] else 0
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        print(f"Inspection failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
