#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.workflow.validate_modern_docx_omml import DEFAULT_INVENTORY, inspect_docx, read_json
DOCUMENT_XML = "word/document.xml"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
DEFAULT_OUTPUT = ROOT / "regression_set" / "modern_docx_omml_mixed_candidate_expansion_report.json"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def _namespace(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]
    return ""


def _is_word(element: ElementTree.Element, local_name: str) -> bool:
    return _namespace(element.tag) == WORD_NS and _local_name(element.tag) == local_name


def _git_tracked(path: Path) -> bool:
    try:
        rel = str(path.resolve().relative_to(ROOT))
    except ValueError:
        return False
    proc = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def _to_rel_or_abs(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _path_key(path: Path) -> str:
    return unicodedata.normalize("NFC", str(path.resolve())).casefold()


def _docx_object_counts(path: Path) -> Dict[str, int]:
    out = {"w_object_count": 0, "object_like_tag_count": 0}
    try:
        with zipfile.ZipFile(path) as docx:
            if DOCUMENT_XML not in docx.namelist():
                return out
            xml = docx.read(DOCUMENT_XML)
    except (OSError, zipfile.BadZipFile):
        return out

    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return out

    for element in root.iter():
        name = _local_name(element.tag)
        if _is_word(element, "object"):
            out["w_object_count"] += 1
        if name in {"object", "OLEObject"}:
            out["object_like_tag_count"] += 1
    return out


def _shape(inline_count: int, block_count: int) -> str:
    if inline_count > 0 and block_count > 0:
        return "mixed_inline_block"
    if inline_count > 0:
        return "inline_only"
    if block_count > 0:
        return "block_only"
    return "no_omml"


def _candidate_score(record: Dict[str, Any]) -> tuple:
    # Prefer maintainable mixed cases first: already-declared local_only evidence, then
    # mixed inline+block shape, then richer structure, then smaller practical files.
    return (
        1 if record.get("inventory_status") == "local_only" else 0,
        1 if record["shape_family"] == "mixed_inline_block" else 0,
        int(record["object_like_tag_count"]),
        int(record["omath_count"] + record["omathpara_count"]),
        -int(record["size_bytes"]),
    )


def _inventory_cases(inventory_path: Path) -> Dict[str, Dict[str, Any]]:
    inventory = read_json(inventory_path)
    cases = inventory.get("cases", [])
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(cases, list):
        return out
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id", "")).strip()
        source = str(case.get("source_docx", "")).strip()
        if not case_id or not source:
            continue
        path = Path(source)
        if not path.is_absolute():
            path = (ROOT / path).resolve()
        out[_path_key(path)] = {
            "case_id": case_id,
            "status": str(case.get("status", "")).strip() or "active",
            "classification": str(case.get("classification", "")).strip() or "unknown",
        }
    return out


def scan_candidates(roots: List[Path], inventory_path: Path) -> Dict[str, Any]:
    inventory_index = _inventory_cases(inventory_path)
    files: List[Path] = []
    for scan_root in roots:
        if not scan_root.exists():
            continue
        files.extend(path for path in scan_root.rglob("*.docx") if path.is_file())
    files = sorted(set(path.resolve() for path in files))

    inspected = 0
    parse_failures = 0
    mixed_records: List[Dict[str, Any]] = []

    for path in files:
        inspected += 1
        info = inspect_docx(path)
        object_counts = _docx_object_counts(path)
        parseable = bool(info.get("document_xml_parseable"))
        if not parseable:
            parse_failures += 1

        omath_count = int(info.get("omath_count", 0) or 0)
        block_count = int(info.get("omathpara_count", 0) or 0)
        inline_count = int(info.get("inline_omath_count", 0) or 0)
        object_like = int(object_counts.get("object_like_tag_count", 0) or 0)

        if (omath_count > 0 or block_count > 0) and object_like > 0:
            inv = inventory_index.get(_path_key(path), {})
            record = {
                "file": _to_rel_or_abs(path),
                "git_tracked": _git_tracked(path),
                "size_bytes": int(path.stat().st_size),
                "shape_family": _shape(inline_count, block_count),
                "native_omml_present": bool(info.get("basic_omml_structure_present")),
                "omath_count": omath_count,
                "inline_omath_count": inline_count,
                "omathpara_count": block_count,
                "w_object_count": int(object_counts.get("w_object_count", 0) or 0),
                "object_like_tag_count": object_like,
                "inventory_case_id": inv.get("case_id"),
                "inventory_status": inv.get("status"),
                "inventory_classification": inv.get("classification"),
            }
            mixed_records.append(record)

    mixed_records.sort(key=_candidate_score, reverse=True)

    selected: Optional[Dict[str, Any]] = mixed_records[0] if mixed_records else None
    tracked_candidates = [item for item in mixed_records if item["git_tracked"]]

    if selected is None:
        decision = {
            "selected_candidate": None,
            "action": "document_only_future_fixture_target",
            "reason": "no mixed embedded-object + native OMML candidate found in scanned local/repo sources",
        }
    elif tracked_candidates:
        decision = {
            "selected_candidate": selected,
            "action": "promote_to_repo_tracked_fixture_inventory",
            "reason": "at least one mixed candidate is already repo-tracked and suitable for direct promotion",
        }
    elif selected.get("inventory_status") == "local_only":
        decision = {
            "selected_candidate": selected,
            "action": "keep_local_only_confidence_evidence",
            "reason": "best mixed candidate exists and is already wired as local_only; no safe repo-tracked source available",
        }
    else:
        decision = {
            "selected_candidate": selected,
            "action": "document_only_future_fixture_target",
            "reason": "mixed candidate exists locally but is not repo-tracked and not clearly safe for fixture promotion",
        }

    return {
        "schema_version": "modern_docx_omml_mixed_candidate_expansion.v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "scope": {
            "modern_docx_only": True,
            "patch_behavior_changed": False,
            "scan_roots": [_to_rel_or_abs(path) for path in roots],
        },
        "scan_summary": {
            "docx_files_seen": inspected,
            "document_xml_parse_failures": parse_failures,
            "mixed_object_omml_candidates": len(mixed_records),
            "repo_tracked_mixed_candidates": len(tracked_candidates),
        },
        "mixed_candidates_top": mixed_records[:20],
        "selection_decision": decision,
    }


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan local modern DOCX corpus for mixed embedded-object + native OMML candidates.")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--scan-root",
        action="append",
        dest="scan_roots",
        default=[],
        help="Directory roots to scan for DOCX files. Default: samples/, regression_set/, in/",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    roots = [Path(item).resolve() for item in args.scan_roots] if args.scan_roots else [
        (ROOT / "samples").resolve(),
        (ROOT / "regression_set").resolve(),
        (ROOT / "in").resolve(),
    ]

    report = scan_candidates(roots, args.inventory.resolve())
    out = args.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    decision = report["selection_decision"]
    print(f"Mixed candidate report: {out}")
    print(
        "Summary: "
        f"docx_seen={report['scan_summary']['docx_files_seen']} "
        f"mixed_candidates={report['scan_summary']['mixed_object_omml_candidates']} "
        f"repo_tracked_mixed={report['scan_summary']['repo_tracked_mixed_candidates']} "
        f"action={decision['action']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
