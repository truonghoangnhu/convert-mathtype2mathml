#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SCHEMA_VERSION = "docx_export_parity_report.v1"

TITLE_RE = re.compile(r"(?is)<title>(.*?)</title>")
QUESTION_HEADER_RE = re.compile(r"(?iu)^\s*câu\s*(\d{1,3})\b")
SECTION_HEADING_RE = re.compile(r"(?iu)^\s*phần\s*([ivxlcdm]+|\d+)\b")
ANSWER_HEADING_RE = re.compile(
    r"(?iu)\b(?:bảng\s*đáp\s*án|đáp\s*án|tóm\s*tắt\s*đáp\s*án|đáp\s*án\s*tham\s*khảo)\b"
)
SOLUTION_CUE_RE = re.compile(r"(?iu)\b(?:lời\s*giải|hướng\s*dẫn\s*giải|giải\s*thích)\b")
IMG_TAG_RE = re.compile(r"(?is)<img\b[^>]*>")
MATH_TAG_RE = re.compile(r"(?is)<(?:\w+:)?math\b.*?</(?:\w+:)?math>")

DEFAULT_PARITY_POLICY: Dict[str, Any] = {
    "schema_version": "docx_export_parity_policy.v1",
    "mode": "teacher_exam_prototype",
    "thresholds": {
        "max_question_count_delta": 0,
        "min_section_title_coverage": 0.75,
        "min_math_presence_ratio": 0.90,
        "min_image_presence_ratio": 0.80,
        "require_answer_summary_heading_in_docx": True,
        "require_answer_lines_when_source_has_summary": True,
    },
    "severity_map": {
        "parity_question_count_mismatch": "blocker",
        "parity_section_title_coverage_low": "warning",
        "parity_math_presence_low": "blocker",
        "parity_image_presence_low": "warning",
        "parity_answer_summary_missing_heading": "warning",
        "parity_answer_summary_missing_lines": "warning",
        "parity_solution_presence_mismatch": "info",
    },
}


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _safe_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _severity_for(policy: Dict[str, Any], code: str, fallback: str) -> str:
    sev_map = policy.get("severity_map", {})
    if not isinstance(sev_map, dict):
        return fallback
    value = str(sev_map.get(code, fallback)).strip().lower()
    if value in {"info", "warning", "error", "blocker"}:
        return value
    return fallback


def _normalize_text(text: str) -> str:
    text = (text or "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _extract_title_from_html(html_text: str) -> str:
    match = TITLE_RE.search(html_text or "")
    if match:
        return _normalize_text(match.group(1))
    return ""


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    if ":" in tag:
        return tag.split(":", 1)[1]
    return tag


def _load_parser_module() -> Any:
    module_name = "_docx_export_parity_contract_parser"
    if module_name in sys.modules:
        return sys.modules[module_name]
    parser_path = Path(__file__).resolve().parents[1] / "contracts" / "generate_output_contract.py"
    spec = importlib.util.spec_from_file_location(module_name, str(parser_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load parser module from {parser_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_docx_metrics(docx_path: Path) -> Dict[str, Any]:
    with zipfile.ZipFile(docx_path, "r") as zf:
        document_xml = zf.read("word/document.xml")
        media_files = [name for name in zf.namelist() if name.startswith("word/media/")]

    root = ET.fromstring(document_xml)
    paragraphs: List[str] = []
    question_count = 0
    question_numbers: List[int] = []
    section_titles: List[str] = []
    answer_line_count = 0
    has_answer_heading = False
    solution_presence = False
    in_answer_section = False
    docx_title = ""

    math_count = 0
    drawing_count = 0
    min_extent_cx: Optional[int] = None
    min_extent_cy: Optional[int] = None
    suspicious_scale_count = 0
    for elem in root.iter():
        lname = _local_name(elem.tag).lower()
        if lname == "omath":
            math_count += 1
        elif lname == "drawing":
            drawing_count += 1
        elif lname == "extent":
            cx = _safe_int(elem.get("cx"), 0)
            cy = _safe_int(elem.get("cy"), 0)
            if cx > 0:
                min_extent_cx = cx if min_extent_cx is None else min(min_extent_cx, cx)
            if cy > 0:
                min_extent_cy = cy if min_extent_cy is None else min(min_extent_cy, cy)
            if cx > 0 and cy > 0 and min(cx, cy) < 300000:
                suspicious_scale_count += 1

    for p in root.iter():
        if _local_name(p.tag).lower() != "p":
            continue
        text_parts: List[str] = []
        for child in p.iter():
            if _local_name(child.tag).lower() == "t" and child.text:
                text_parts.append(child.text)
        para_text = _normalize_text("".join(text_parts))
        if not para_text:
            continue
        paragraphs.append(para_text)
        if not docx_title:
            docx_title = para_text
        if para_text.lower().startswith("teacher answer section") or ANSWER_HEADING_RE.search(para_text):
            has_answer_heading = True
            in_answer_section = True
            continue
        if not in_answer_section and QUESTION_HEADER_RE.match(para_text):
            q_match = QUESTION_HEADER_RE.match(para_text)
            if q_match:
                question_numbers.append(int(q_match.group(1)))
            question_count += 1
        if not in_answer_section and SECTION_HEADING_RE.match(para_text):
            section_titles.append(para_text)
        if in_answer_section and re.match(r"(?iu)^\s*câu\s*\d+\s*:", para_text):
            answer_line_count += 1
        if SOLUTION_CUE_RE.search(para_text):
            solution_presence = True

    section_titles_unique = []
    seen = set()
    for title in section_titles:
        k = title.lower()
        if k in seen:
            continue
        seen.add(k)
        section_titles_unique.append(title)

    return {
        "question_count": question_count,
        "question_numbers": question_numbers,
        "section_titles": section_titles_unique,
        "math_count": math_count,
        "drawing_count": drawing_count,
        "media_file_count": len(media_files),
        "has_answer_heading": has_answer_heading,
        "answer_line_count": answer_line_count,
        "solution_presence": solution_presence,
        "paragraph_count": len(paragraphs),
        "docx_title": docx_title,
        "min_extent_cx": min_extent_cx or 0,
        "min_extent_cy": min_extent_cy or 0,
        "suspicious_scale_count": suspicious_scale_count,
    }


def _extract_source_metrics(exam_bundle_path: Path) -> Dict[str, Any]:
    bundle = _load_json(exam_bundle_path)
    source = bundle.get("source", {}) if isinstance(bundle.get("source"), dict) else {}
    html_path_raw = str(source.get("html_path", "")).strip()
    if not html_path_raw:
        raise FileNotFoundError("exam_bundle.source.html_path is missing.")
    html_path = Path(html_path_raw).resolve()
    html_text = html_path.read_text(encoding="utf-8")
    html_title = _extract_title_from_html(html_text)

    parser_module = _load_parser_module()
    parsed = parser_module.parse_html_structure(html_text)
    blocks = list(parsed.get("blocks", []))
    questions = list(parsed.get("questions", []))

    answer_cutoff: Optional[int] = None
    for block in blocks:
        text = getattr(block, "text", "") or ""
        if ANSWER_HEADING_RE.search(text):
            answer_cutoff = int(getattr(block, "block_index", 0))
            break

    if answer_cutoff is None:
        filtered_blocks = blocks
        filtered_questions = questions
    else:
        filtered_blocks = [b for b in blocks if int(getattr(b, "block_index", 0)) < answer_cutoff]
        filtered_questions = [q for q in questions if int(getattr(q, "start_block_index", 0)) < answer_cutoff]

    section_titles: List[str] = []
    section_seen = set()
    math_count = 0
    image_count = 0
    question_numbers: List[int] = []
    last_question_number: Optional[int] = None
    text_join = []
    for block in filtered_blocks:
        block_text = _normalize_text(getattr(block, "text", "") or "")
        if block_text:
            text_join.append(block_text)
            if SECTION_HEADING_RE.match(block_text):
                k = block_text.lower()
                if k not in section_seen:
                    section_seen.add(k)
                    section_titles.append(block_text)
            q_match = QUESTION_HEADER_RE.match(block_text)
            if q_match:
                qn = int(q_match.group(1))
                if last_question_number != qn:
                    question_numbers.append(qn)
                    last_question_number = qn
        block_html = getattr(block, "html", "") or ""
        math_count += len(MATH_TAG_RE.findall(block_html))
        image_count += len(IMG_TAG_RE.findall(block_html))

    answer_summary = bundle.get("answer_summary", {}) if isinstance(bundle.get("answer_summary"), dict) else {}
    summary_entries = answer_summary.get("entries", [])
    source_has_answer_summary = bool(answer_summary.get("present")) and isinstance(summary_entries, list) and len(summary_entries) > 0
    solution_presence = bool(SOLUTION_CUE_RE.search(" ".join(text_join)))

    return {
        "bundle_id": str(bundle.get("bundle_id", "")),
        "exam_bundle_path": str(exam_bundle_path),
        "html_path": str(html_path),
        "exam_title": html_title,
        "question_count": len(filtered_questions),
        "question_numbers": question_numbers,
        "section_titles": section_titles,
        "math_count": math_count,
        "image_count": image_count,
        "source_has_answer_summary": source_has_answer_summary,
        "source_answer_summary_entry_count": len(summary_entries) if isinstance(summary_entries, list) else 0,
        "solution_presence": solution_presence,
    }


def _evaluate_parity(
    *,
    source: Dict[str, Any],
    docx: Dict[str, Any],
    policy: Dict[str, Any],
) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    thresholds = policy.get("thresholds", {})
    if not isinstance(thresholds, dict):
        thresholds = {}

    findings: List[Dict[str, Any]] = []
    source_title = _normalize_text(str(source.get("exam_title", "")).strip())
    docx_title = _normalize_text(str(docx.get("docx_title", "")).strip())
    if not source_title or not docx_title:
        findings.append(
            {
                "code": "parity_title_missing",
                "severity": "blocker",
                "message": f"Exam title missing in parity comparison (source_title_present={bool(source_title)}, docx_title_present={bool(docx_title)}).",
            }
        )
    elif source_title != docx_title:
        findings.append(
            {
                "code": "parity_title_mismatch",
                "severity": "warning",
                "message": f"Exam title differs between source and DOCX (source='{source_title}', docx='{docx_title}').",
            }
        )

    question_delta = abs(_safe_int(docx.get("question_count"), 0) - _safe_int(source.get("question_count"), 0))
    max_question_delta = _safe_int(thresholds.get("max_question_count_delta"), 0)
    if question_delta > max_question_delta:
        findings.append(
            {
                "code": "parity_question_count_mismatch",
                "severity": _severity_for(policy, "parity_question_count_mismatch", "blocker"),
                "message": f"Question count delta {question_delta} exceeds allowed {max_question_delta}.",
            }
        )

    src_qnums = [int(q) for q in source.get("question_numbers", []) if str(q).strip().isdigit()]
    doc_qnums = [int(q) for q in docx.get("question_numbers", []) if str(q).strip().isdigit()]
    if src_qnums != doc_qnums:
        findings.append(
            {
                "code": "parity_question_order_mismatch",
                "severity": "blocker",
                "message": "Question order differs between source and exported DOCX.",
            }
        )

    src_sections = [str(s).lower() for s in source.get("section_titles", []) if str(s).strip()]
    doc_sections = [str(s).lower() for s in docx.get("section_titles", []) if str(s).strip()]
    src_set = set(src_sections)
    doc_set = set(doc_sections)
    if len(src_set) != len(doc_set):
        findings.append(
            {
                "code": "parity_section_count_mismatch",
                "severity": "blocker",
                "message": f"Section count differs between source ({len(src_set)}) and DOCX ({len(doc_set)}).",
            }
        )
    if src_set:
        coverage = len(src_set & doc_set) / float(len(src_set))
    else:
        coverage = 1.0
    min_coverage = _safe_float(thresholds.get("min_section_title_coverage"), 0.75)
    if coverage < min_coverage:
        findings.append(
            {
                "code": "parity_section_title_coverage_low",
                "severity": _severity_for(policy, "parity_section_title_coverage_low", "warning"),
                "message": f"Section title coverage {coverage:.4f} is below threshold {min_coverage:.4f}.",
            }
        )

    source_math = _safe_int(source.get("math_count"), 0)
    doc_math = _safe_int(docx.get("math_count"), 0)
    math_ratio = (float(doc_math) / float(source_math)) if source_math > 0 else 1.0
    min_math_ratio = _safe_float(thresholds.get("min_math_presence_ratio"), 0.90)
    if source_math > 0 and math_ratio < min_math_ratio:
        findings.append(
            {
                "code": "parity_math_presence_low",
                "severity": _severity_for(policy, "parity_math_presence_low", "blocker"),
                "message": f"Math presence ratio {math_ratio:.4f} is below threshold {min_math_ratio:.4f}.",
            }
        )

    source_img = _safe_int(source.get("image_count"), 0)
    doc_img = _safe_int(docx.get("drawing_count"), 0)
    image_ratio = (float(doc_img) / float(source_img)) if source_img > 0 else 1.0
    min_img_ratio = _safe_float(thresholds.get("min_image_presence_ratio"), 0.80)
    if source_img > 0 and doc_img == 0:
        findings.append(
            {
                "code": "parity_essential_image_missing",
                "severity": "blocker",
                "message": "Source contains images but DOCX contains no embedded drawings.",
            }
        )
    elif source_img > 0 and image_ratio < min_img_ratio:
        findings.append(
            {
                "code": "parity_image_presence_low",
                "severity": _severity_for(policy, "parity_image_presence_low", "warning"),
                "message": f"Image presence ratio {image_ratio:.4f} is below threshold {min_img_ratio:.4f}.",
            }
        )

    min_extent_cx = _safe_int(docx.get("min_extent_cx"), 0)
    min_extent_cy = _safe_int(docx.get("min_extent_cy"), 0)
    suspicious_scale_count = _safe_int(docx.get("suspicious_scale_count"), 0)
    if suspicious_scale_count > 0:
        findings.append(
            {
                "code": "parity_image_scale_suspicious",
                "severity": "warning",
                "message": (
                    "One or more embedded drawings are unusually small; "
                    f"min_extent_cx={min_extent_cx}, min_extent_cy={min_extent_cy}, suspicious_count={suspicious_scale_count}."
                ),
            }
        )

    require_summary_heading = bool(thresholds.get("require_answer_summary_heading_in_docx", True))
    if require_summary_heading and not bool(docx.get("has_answer_heading")):
        findings.append(
            {
                "code": "parity_answer_summary_missing_heading",
                "severity": _severity_for(policy, "parity_answer_summary_missing_heading", "warning"),
                "message": "Teacher answer summary heading is missing in DOCX output.",
            }
        )

    require_summary_lines = bool(thresholds.get("require_answer_lines_when_source_has_summary", True))
    if require_summary_lines and bool(source.get("source_has_answer_summary")) and _safe_int(docx.get("answer_line_count"), 0) == 0:
        findings.append(
            {
                "code": "parity_answer_summary_missing_lines",
                "severity": _severity_for(policy, "parity_answer_summary_missing_lines", "warning"),
                "message": "Source has answer summary entries but DOCX has no answer lines.",
            }
        )

    if bool(source.get("solution_presence")) != bool(docx.get("solution_presence")):
        findings.append(
            {
                "code": "parity_solution_presence_mismatch",
                "severity": _severity_for(policy, "parity_solution_presence_mismatch", "info"),
                "message": (
                    "Solution cue presence differs between source and exported DOCX "
                    f"(source={bool(source.get('solution_presence'))}, docx={bool(docx.get('solution_presence'))})."
                ),
            }
        )

    blocker_count = sum(1 for f in findings if str(f.get("severity", "")).lower() == "blocker")
    warning_count = sum(1 for f in findings if str(f.get("severity", "")).lower() in {"warning", "error"})
    if blocker_count > 0:
        verdict = "blocked"
    elif warning_count > 0:
        verdict = "needs_review"
    else:
        verdict = "parity_ok"

    checks = {
        "question_count": {
            "source": _safe_int(source.get("question_count"), 0),
            "docx": _safe_int(docx.get("question_count"), 0),
            "delta": question_delta,
            "allowed_delta_max": max_question_delta,
            "passed": question_delta <= max_question_delta,
        },
        "question_order": {
            "source": source.get("question_numbers", []),
            "docx": docx.get("question_numbers", []),
            "passed": src_qnums == doc_qnums,
        },
        "title": {
            "source": source_title,
            "docx": docx_title,
            "passed": bool(source_title) and bool(docx_title) and source_title == docx_title,
        },
        "section_titles": {
            "source_count": len(src_set),
            "docx_count": len(doc_set),
            "coverage_ratio": round(coverage, 6),
            "required_min_ratio": round(min_coverage, 6),
            "passed": coverage >= min_coverage,
        },
        "math_presence": {
            "source_count": source_math,
            "docx_count": doc_math,
            "ratio": round(math_ratio, 6),
            "required_min_ratio": round(min_math_ratio, 6),
            "passed": (source_math == 0 or math_ratio >= min_math_ratio),
        },
        "image_presence": {
            "source_count": source_img,
            "docx_count": doc_img,
            "ratio": round(image_ratio, 6),
            "required_min_ratio": round(min_img_ratio, 6),
            "passed": (source_img == 0 or image_ratio >= min_img_ratio),
        },
        "image_scale": {
            "min_extent_cx": min_extent_cx,
            "min_extent_cy": min_extent_cy,
            "suspicious_count": suspicious_scale_count,
            "passed": suspicious_scale_count == 0,
        },
        "answer_summary": {
            "source_has_summary": bool(source.get("source_has_answer_summary")),
            "docx_has_heading": bool(docx.get("has_answer_heading")),
            "docx_answer_line_count": _safe_int(docx.get("answer_line_count"), 0),
            "passed": not any(
                f.get("code") in {"parity_answer_summary_missing_heading", "parity_answer_summary_missing_lines"}
                for f in findings
            ),
        },
        "solution_presence": {
            "source": bool(source.get("solution_presence")),
            "docx": bool(docx.get("solution_presence")),
            "passed": bool(source.get("solution_presence")) == bool(docx.get("solution_presence")),
        },
    }
    return verdict, findings, checks


def run_parity_review(
    *,
    exam_bundle_path: Path,
    exported_docx_path: Path,
    output_report_path: Path,
    output_md_path: Optional[Path] = None,
    policy_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    policy = _merge_dict(DEFAULT_PARITY_POLICY, policy_override or {})
    report: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "docx_export_parity_report",
        "exam_bundle_path": str(exam_bundle_path.resolve()),
        "exported_docx_path": str(exported_docx_path.resolve()),
        "policy": policy,
        "source_metrics": {},
        "docx_metrics": {},
        "checks": {},
        "findings": [],
        "warnings_count": 0,
        "blockers_count": 0,
        "verdict": "blocked",
    }
    try:
        source_metrics = _extract_source_metrics(exam_bundle_path.resolve())
    except Exception as ex:  # noqa: BLE001
        report["findings"] = [
            {
                "code": "parity_source_read_failed",
                "severity": "blocker",
                "message": f"Unable to read source bundle/html for parity: {ex}",
            }
        ]
        report["blockers_count"] = 1
        report["warnings_count"] = 0
        report["verdict"] = "blocked"
        output_report_path.parent.mkdir(parents=True, exist_ok=True)
        output_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    try:
        docx_metrics = _extract_docx_metrics(exported_docx_path.resolve())
    except Exception as ex:  # noqa: BLE001
        report["source_metrics"] = source_metrics
        report["findings"] = [
            {
                "code": "parity_docx_read_failed",
                "severity": "blocker",
                "message": f"Unable to read exported DOCX for parity: {ex}",
            }
        ]
        report["blockers_count"] = 1
        report["warnings_count"] = 0
        report["verdict"] = "blocked"
        output_report_path.parent.mkdir(parents=True, exist_ok=True)
        output_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    verdict, findings, checks = _evaluate_parity(source=source_metrics, docx=docx_metrics, policy=policy)
    report["source_metrics"] = source_metrics
    report["docx_metrics"] = docx_metrics
    report["checks"] = checks
    report["findings"] = findings
    report["warnings_count"] = sum(1 for f in findings if str(f.get("severity", "")).lower() in {"warning", "error"})
    report["blockers_count"] = sum(1 for f in findings if str(f.get("severity", "")).lower() == "blocker")
    report["verdict"] = verdict
    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    output_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if output_md_path is not None:
        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        output_md_path.write_text(_render_markdown(report), encoding="utf-8")
    return report


def _render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# DOCX Export Parity Report")
    lines.append("")
    lines.append(f"- Verdict: `{report.get('verdict', '')}`")
    lines.append(f"- Source bundle: `{report.get('exam_bundle_path', '')}`")
    lines.append(f"- Exported DOCX: `{report.get('exported_docx_path', '')}`")
    lines.append("")
    lines.append("## Checks")
    checks = report.get("checks", {})
    if isinstance(checks, dict):
        for key in ["title", "question_count", "question_order", "section_titles", "math_presence", "image_presence", "answer_summary", "solution_presence"]:
            item = checks.get(key, {})
            if isinstance(item, dict):
                passed = item.get("passed", False)
                lines.append(f"- `{key}`: `{passed}`")
    lines.append("")
    lines.append("## Findings")
    findings = report.get("findings", [])
    if findings:
        for finding in findings:
            lines.append(
                f"- `{finding.get('severity', '')}` `{finding.get('code', '')}`: {finding.get('message', '')}"
            )
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DOCX export parity review: exported DOCX vs source exam_bundle/HTML.")
    parser.add_argument("--exam-bundle", required=True, type=Path)
    parser.add_argument("--exported-docx", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="Output parity report JSON path.")
    parser.add_argument(
        "--md-out",
        type=Path,
        default=None,
        help="Optional markdown summary output path.",
    )
    parser.add_argument(
        "--policy-json",
        default="",
        help="Optional policy override JSON file.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    policy_override = None
    if args.policy_json:
        policy_path = Path(args.policy_json).resolve()
        try:
            policy_override = _load_json(policy_path)
        except Exception as ex:  # noqa: BLE001
            print(f"[ERROR] Failed to load parity policy JSON: {policy_path} ({ex})", file=sys.stderr)
            return 2
    report = run_parity_review(
        exam_bundle_path=args.exam_bundle.resolve(),
        exported_docx_path=args.exported_docx.resolve(),
        output_report_path=args.out.resolve(),
        output_md_path=args.md_out.resolve() if args.md_out else None,
        policy_override=policy_override,
    )
    if report.get("verdict") == "blocked":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
