#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


SCHEMA_VERSION = "docx_side_audit.v1"


def _flatten_text(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        flattened: List[str] = []
        for item in value:
            flattened.extend(_flatten_text(item))
        return flattened
    return []


def _heuristic_heading_hints(lines: Iterable[str], limit: int = 24) -> List[str]:
    hints: List[str] = []
    for line in lines:
        text = re.sub(r"\s+", " ", str(line)).strip()
        if not text:
            continue
        if len(text) > 140:
            continue
        if re.match(r"(?iu)^(?:đề|phần|câu|hướng dẫn|bài|mục|chủ đề)\b", text):
            hints.append(text)
        elif text.isupper() and len(text) >= 6:
            hints.append(text)
        elif re.match(r"^\d+[\).\]]\s+", text):
            hints.append(text)
        if len(hints) >= limit:
            break
    return hints


def _heuristic_list_hints(lines: Iterable[str], limit: int = 24) -> List[str]:
    hints: List[str] = []
    for line in lines:
        text = re.sub(r"\s+", " ", str(line)).strip()
        if not text:
            continue
        if re.match(r"(?iu)^(?:[-*•]|(?:\d+|[a-z])[\).\]])\s+", text):
            hints.append(text)
        if len(hints) >= limit:
            break
    return hints


def _heuristic_numbering_hints(lines: Iterable[str], limit: int = 24) -> List[str]:
    hints: List[str] = []
    for line in lines:
        text = re.sub(r"\s+", " ", str(line)).strip()
        if not text:
            continue
        if re.search(r"(?iu)^\s*(?:câu|question)\s*\d{1,3}\b", text) or re.search(r"^\s*\d+[\).\]]\s+", text):
            hints.append(text)
        if len(hints) >= limit:
            break
    return hints


def _max_nested_depth(value: Any, depth: int = 0) -> int:
    if isinstance(value, str):
        return depth
    if isinstance(value, (list, tuple)) and value:
        return max(_max_nested_depth(item, depth + 1) for item in value)
    return depth


def audit_docx(docx_path: Path) -> Dict[str, Any]:
    audit: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "docx_side_audit",
        "available": False,
        "docx_path": str(docx_path.resolve()),
        "text_char_count": 0,
        "paragraph_count": 0,
        "table_depth_max": 0,
        "image_count": 0,
        "heading_hints": [],
        "list_hints": [],
        "numbering_hints": [],
        "notes": [],
    }

    try:
        from docx2python import docx2python  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency fallback
        audit["notes"].append(f"docx2python_unavailable:{exc.__class__.__name__}")
        return audit

    try:
        with docx2python(str(docx_path)) as result:
            body = getattr(result, "body", [])
            text = getattr(result, "text", "")
            images = getattr(result, "images", {})
            flattened = [line.strip() for line in _flatten_text(body) if str(line).strip()]
            audit["available"] = True
            audit["text_char_count"] = len(str(text or ""))
            audit["paragraph_count"] = len(flattened)
            audit["table_depth_max"] = _max_nested_depth(body)
            audit["image_count"] = len(images) if isinstance(images, dict) else 0
            audit["heading_hints"] = _heuristic_heading_hints(flattened)
            audit["list_hints"] = _heuristic_list_hints(flattened)
            audit["numbering_hints"] = _heuristic_numbering_hints(flattened)
            if audit["image_count"] == 0:
                audit["notes"].append("no_embedded_images_detected")
    except Exception as exc:  # pragma: no cover - best-effort audit helper
        audit["notes"].append(f"docx2python_failed:{exc.__class__.__name__}:{exc}")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a docx2python side audit for debugging only.")
    parser.add_argument("--docx", type=Path, required=True, help="Path to the source DOCX file")
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output path")
    args = parser.parse_args()

    audit = audit_docx(args.docx)
    payload = json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
