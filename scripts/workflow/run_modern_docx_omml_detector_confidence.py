#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.workflow.validate_modern_docx_omml import DEFAULT_INVENTORY, inspect_docx, read_json

DEFAULT_OUTPUT = ROOT / "regression_set" / "modern_docx_omml_detector_confidence_report.json"
DOCUMENT_XML = "word/document.xml"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def _namespace(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]
    return ""


def _is_word(element: ElementTree.Element, local_name: str) -> bool:
    return _namespace(element.tag) == WORD_NS and _local_name(element.tag) == local_name


def _is_repo_tracked(path: Path) -> bool:
    rel = path.resolve().relative_to(ROOT)
    proc = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(rel)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def _inventory_supported_docx(inventory_path: Path) -> List[Path]:
    inventory = read_json(inventory_path)
    cases = inventory.get("cases", [])
    if not isinstance(cases, list):
        return []

    docx_paths: List[Path] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        status = str(case.get("status", "active")).strip().lower()
        if status not in {"", "active", "local_only"}:
            continue
        if str(case.get("classification", "")).strip() != "supported":
            continue
        raw = str(case.get("source_docx", "")).strip()
        if not raw or raw == "TODO":
            continue
        path = Path(raw)
        path = path if path.is_absolute() else ROOT / path
        if path.suffix.lower() != ".docx":
            continue
        if path.exists() and _is_repo_tracked(path):
            docx_paths.append(path.resolve())
    return docx_paths


def _glob_repo_docx(*roots: Path) -> List[Path]:
    paths: List[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.docx")):
            if path.is_file() and _is_repo_tracked(path):
                paths.append(path.resolve())
    return paths


def _docx_object_stats(path: Path) -> Dict[str, int]:
    result = {
        "w_object_count": 0,
        "object_like_tag_count": 0,
    }
    try:
        with zipfile.ZipFile(path) as docx:
            if DOCUMENT_XML not in docx.namelist():
                return result
            data = docx.read(DOCUMENT_XML)
    except (OSError, zipfile.BadZipFile):
        return result

    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError:
        return result

    w_object_count = 0
    object_like_tag_count = 0
    for element in root.iter():
        name = _local_name(element.tag)
        if _is_word(element, "object"):
            w_object_count += 1
        if name in {"object", "OLEObject"}:
            object_like_tag_count += 1

    result["w_object_count"] = w_object_count
    result["object_like_tag_count"] = object_like_tag_count
    return result


def _shape_family(inspection: Dict[str, Any]) -> str:
    parseable = bool(inspection.get("document_xml_parseable"))
    if not parseable:
        return "malformed_or_unparseable"
    inline_count = int(inspection.get("inline_omath_count", 0) or 0)
    block_count = int(inspection.get("omathpara_count", 0) or 0)
    if inline_count > 0 and block_count > 0:
        return "mixed_inline_block"
    if inline_count > 0:
        return "inline_only"
    if block_count > 0:
        return "block_only"
    return "no_omml"


def _skip_classification(inspection: Dict[str, Any]) -> str:
    if not bool(inspection.get("document_xml_exists")):
        return "skip_document_xml_missing"
    if not bool(inspection.get("document_xml_parseable")):
        return "skip_document_xml_unparseable"
    if not bool(inspection.get("basic_omml_structure_present")):
        return "skip_no_native_omml_present"
    return ""


def _unresolved_classification(inspection: Dict[str, Any]) -> str:
    if bool(inspection.get("basic_omml_structure_present")) and not bool(inspection.get("basic_omml_structure_valid")):
        return "unresolved_invalid_omml_structure"
    return ""


def _to_rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def build_report(inventory_path: Path) -> Dict[str, Any]:
    corpus_paths: Set[Path] = set()
    corpus_paths.update(_inventory_supported_docx(inventory_path))
    corpus_paths.update(_glob_repo_docx(ROOT / "samples", ROOT / "regression_set"))

    files: List[Dict[str, Any]] = []
    shape_counts: Dict[str, int] = {}
    skip_counts: Dict[str, int] = {}
    unresolved_counts: Dict[str, int] = {}
    
    native_omml_present = 0
    inline_candidates = 0
    block_candidates = 0
    mixed_object_omml = 0

    for path in sorted(corpus_paths):
        inspection = inspect_docx(path)
        object_stats = _docx_object_stats(path)

        has_native_omml = bool(inspection.get("basic_omml_structure_present"))
        has_inline = int(inspection.get("inline_omath_count", 0) or 0) > 0
        has_block = int(inspection.get("omathpara_count", 0) or 0) > 0
        has_object = int(object_stats.get("object_like_tag_count", 0) or 0) > 0
        mixed_case = has_native_omml and has_object

        if has_native_omml:
            native_omml_present += 1
        if has_inline:
            inline_candidates += 1
        if has_block:
            block_candidates += 1
        if mixed_case:
            mixed_object_omml += 1

        shape = _shape_family(inspection)
        shape_counts[shape] = shape_counts.get(shape, 0) + 1

        skip_class = _skip_classification(inspection)
        if skip_class:
            skip_counts[skip_class] = skip_counts.get(skip_class, 0) + 1

        unresolved_class = _unresolved_classification(inspection)
        if unresolved_class:
            unresolved_counts[unresolved_class] = unresolved_counts.get(unresolved_class, 0) + 1

        files.append(
            {
                "file": _to_rel(path),
                "shape_family": shape,
                "native_omml_present": has_native_omml,
                "inline_candidate": has_inline,
                "block_candidate": has_block,
                "mixed_object_omml": mixed_case,
                "skip_classification": skip_class or "",
                "unresolved_classification": unresolved_class or "",
                "omath_count": int(inspection.get("omath_count", 0) or 0),
                "inline_omath_count": int(inspection.get("inline_omath_count", 0) or 0),
                "omathpara_count": int(inspection.get("omathpara_count", 0) or 0),
                "w_object_count": int(object_stats.get("w_object_count", 0) or 0),
                "object_like_tag_count": int(object_stats.get("object_like_tag_count", 0) or 0),
                "document_xml_exists": bool(inspection.get("document_xml_exists")),
                "document_xml_parseable": bool(inspection.get("document_xml_parseable")),
            }
        )

    total = len(files)
    shape_keys = set(shape_counts)
    thin_spots: List[str] = []
    if "mixed_inline_block" not in shape_keys:
        thin_spots.append("no mixed inline+block OMML shape observed")
    if "inline_only" not in shape_keys:
        thin_spots.append("no inline-only OMML shape observed")
    if "block_only" not in shape_keys:
        thin_spots.append("no block-only OMML shape observed")
    if mixed_object_omml == 0:
        thin_spots.append("no mixed embedded-object + OMML case observed in repo-tracked corpus slice")

    adequate = (
        total > 0
        and native_omml_present > 0
        and inline_candidates > 0
        and block_candidates > 0
        and len(unresolved_counts) == 0
    )

    return {
        "schema_version": "modern_docx_omml_detector_confidence.v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "scope": {
            "mode": "detector_classification_only",
            "modern_docx_only": True,
            "patch_behavior_changed": False,
            "corpus_sources": [
                "supported source_docx from regression_set/modern_docx_omml_inventory.json (repo-tracked only)",
                "repo-tracked DOCX under samples/",
                "repo-tracked DOCX under regression_set/",
            ],
        },
        "files_inspected_count": total,
        "files_inspected": files,
        "coverage": {
            "native_omml_present": {
                "files": native_omml_present,
                "total": total,
            },
            "inline_candidate": {
                "files": inline_candidates,
                "total": total,
            },
            "block_candidate": {
                "files": block_candidates,
                "total": total,
            },
            "mixed_object_omml": {
                "files": mixed_object_omml,
                "total": total,
            },
            "skip_classifications": skip_counts,
            "unresolved_classifications": unresolved_counts,
        },
        "detected_case_families": shape_counts,
        "thin_spots_or_asymmetries": thin_spots,
        "confidence_assessment": {
            "adequate_for_current_practical_modern_baseline": adequate,
            "reason": (
                "baseline coverage includes native OMML, inline candidates, block candidates, and no unresolved classifications"
                if adequate
                else "coverage is incomplete for at least one required detector baseline family"
            ),
        },
    }


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a modern DOCX detector/classification confidence report from repo-tracked corpus inputs.")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args.inventory.resolve())
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Detector confidence report: {output}")
    print(
        "Summary: "
        f"files={report['files_inspected_count']} "
        f"native={report['coverage']['native_omml_present']['files']} "
        f"inline={report['coverage']['inline_candidate']['files']} "
        f"block={report['coverage']['block_candidate']['files']} "
        f"mixed_object_omml={report['coverage']['mixed_object_omml']['files']} "
        f"unresolved={sum(report['coverage']['unresolved_classifications'].values())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
