#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html as html_lib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import xml.etree.ElementTree as ET


DOCX_EXPORT_REPORT_SCHEMA_VERSION = "docx_export_report.v1"
DOCX_EXPORT_FAILURE_POLICY_SCHEMA_VERSION = "docx_export_failure_policy.v1"

WORD_NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
}

REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
DC_NS = "http://purl.org/dc/elements/1.1/"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DCTERMS_NS = "http://purl.org/dc/terms/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
XML_NS = "http://www.w3.org/XML/1998/namespace"

TITLE_RE = re.compile(r"(?is)<title>(.*?)</title>")
OUTER_BLOCK_RE = re.compile(r"(?is)^<([a-z0-9]+)\b([^>]*)>(.*)</\1>\s*$")
ATTR_RE = re.compile(r"([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')")
ANSWER_HEADING_RE = re.compile(
    r"(?iu)\b(?:bảng\s*đáp\s*án|đáp\s*án|tóm\s*tắt\s*đáp\s*án|đáp\s*án\s*tham\s*khảo)\b"
)
SECTION_HEADING_RE = re.compile(r"(?iu)^\s*phần\s*([ivxlcdm]+|\d+)\b")

TOKEN_RE = re.compile(
    r"(?is)<(?:\w+:)?math\b.*?</(?:\w+:)?math>|<img\b[^>]*>|<br\s*/?>|<[^>]+>"
)
MATH_TOKEN_RE = re.compile(r"(?is)^<(?:\w+:)?math\b.*?</(?:\w+:)?math>$")
IMG_TOKEN_RE = re.compile(r"(?is)^<img\b[^>]*>$")
BR_TOKEN_RE = re.compile(r"(?is)^<br\s*/?>$")
TABLE_ROW_RE = re.compile(r"(?is)<tr\b[^>]*>(.*?)</tr>")
TABLE_CELL_RE = re.compile(r"(?is)<t[dh]\b[^>]*>(.*?)</t[dh]>")

SUPPORTED_IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}

EMU_PER_PX = 9525
MAX_IMAGE_WIDTH_EMU = 5_800_000
MAX_IMAGE_HEIGHT_EMU = 8_000_000

DEFAULT_FAILURE_POLICY: Dict[str, Any] = {
    "schema_version": DOCX_EXPORT_FAILURE_POLICY_SCHEMA_VERSION,
    "mode": "prototype_teacher_exam",
    "thresholds": {
        "math_failed_ratio_warning_max": 0.02,
        "math_failed_count_warning_max": 2,
        "math_failed_ratio_blocker": 0.10,
        "math_failed_count_blocker": 10,
        "image_failed_ratio_warning_max": 0.10,
        "image_failed_count_warning_max": 3,
        "image_failed_ratio_blocker": 0.25,
        "image_failed_count_blocker": 8,
    },
    "severity_map": {
        "answer_summary_zone_missing_with_questions": "warning",
        "answer_summary_zone_missing_without_questions": "info",
        "answer_summary_missing_for_teacher_export": "warning",
        "math_degradation_within_tolerance": "warning",
        "math_degradation_exceeded": "blocker",
        "image_degradation_within_tolerance": "warning",
        "image_degradation_exceeded": "blocker",
        "openability_soffice_unavailable": "warning",
        "docx_zip_integrity_failed": "blocker",
        "docx_openability_failed": "blocker",
    },
}


for prefix, uri in WORD_NS.items():
    ET.register_namespace(prefix, uri)
ET.register_namespace("cp", CP_NS)
ET.register_namespace("dc", DC_NS)
ET.register_namespace("dcterms", DCTERMS_NS)
ET.register_namespace("xsi", XSI_NS)


@dataclass
class ExportIssue:
    code: str
    severity: str
    message: str
    exam_id: str = ""
    question_id: str = ""
    location: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "exam_id": self.exam_id,
            "question_id": self.question_id,
            "location": self.location,
        }


def _qn(prefix: str, local: str) -> str:
    return f"{{{WORD_NS[prefix]}}}{local}"


def _xml_attr(ns: str, local: str) -> str:
    return f"{{{ns}}}{local}"


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    if ":" in tag:
        return tag.split(":", 1)[1]
    return tag


def _parse_attrs(raw_tag: str) -> Dict[str, str]:
    attrs: Dict[str, str] = {}
    for key, value1, value2 in ATTR_RE.findall(raw_tag):
        attrs[key.lower()] = value1 if value1 != "" else value2
    return attrs


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    out = html_lib.unescape(text)
    out = out.replace("\xa0", " ")
    out = out.replace("\r", " ").replace("\n", " ")
    out = re.sub(r"\s+", " ", out)
    return out


def _set_text_with_space_preserve(node: ET.Element, text: str) -> None:
    node.text = text
    if text.startswith(" ") or text.endswith(" ") or "  " in text:
        node.set(_xml_attr(XML_NS, "space"), "preserve")


def _load_contract_parser_module() -> Any:
    module_name = "_docx_export_contract_parser"
    if module_name in sys.modules:
        return sys.modules[module_name]
    parser_path = Path(__file__).resolve().parents[1] / "contracts" / "generate_output_contract.py"
    spec = importlib.util.spec_from_file_location(module_name, str(parser_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load parser module: {parser_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _extract_title(html_text: str, fallback_name: str) -> str:
    m = TITLE_RE.search(html_text or "")
    if m:
        title = _normalize_text(m.group(1)).strip()
        if title:
            return title
    return fallback_name


def _find_answer_cutoff_index(blocks: Iterable[Any]) -> Optional[int]:
    for block in blocks:
        text = getattr(block, "text", "") or ""
        if ANSWER_HEADING_RE.search(text):
            return int(getattr(block, "block_index", 0))
    return None


def _resolve_image_path(src: str, html_path: Path, asset_dir: Optional[Path]) -> Optional[Path]:
    src = (src or "").strip()
    if not src:
        return None
    candidate = Path(src)
    candidates: List[Path] = []
    if candidate.is_absolute():
        candidates.append(candidate)
    else:
        candidates.append((html_path.parent / src).resolve())
        if asset_dir:
            candidates.append((asset_dir / src).resolve())
            candidates.append((asset_dir / candidate.name).resolve())

    seen = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.exists() and path.is_file():
            return path
    return None


def _parse_png_size(data: bytes) -> Optional[Tuple[int, int]]:
    if len(data) < 24:
        return None
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    width = int.from_bytes(data[16:20], "big", signed=False)
    height = int.from_bytes(data[20:24], "big", signed=False)
    if width > 0 and height > 0:
        return (width, height)
    return None


def _parse_gif_size(data: bytes) -> Optional[Tuple[int, int]]:
    if len(data) < 10:
        return None
    if not (data.startswith(b"GIF87a") or data.startswith(b"GIF89a")):
        return None
    width = int.from_bytes(data[6:8], "little", signed=False)
    height = int.from_bytes(data[8:10], "little", signed=False)
    if width > 0 and height > 0:
        return (width, height)
    return None


def _parse_jpeg_size(data: bytes) -> Optional[Tuple[int, int]]:
    if len(data) < 4 or not data.startswith(b"\xFF\xD8"):
        return None
    i = 2
    data_len = len(data)
    sof_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while i + 9 < data_len:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        i += 2
        if marker in (0xD8, 0xD9):
            continue
        if i + 1 >= data_len:
            break
        seg_len = int.from_bytes(data[i : i + 2], "big", signed=False)
        if seg_len < 2 or i + seg_len > data_len:
            break
        if marker in sof_markers and seg_len >= 7:
            h = int.from_bytes(data[i + 3 : i + 5], "big", signed=False)
            w = int.from_bytes(data[i + 5 : i + 7], "big", signed=False)
            if w > 0 and h > 0:
                return (w, h)
        i += seg_len
    return None


def _extract_image_size_px(data: bytes, ext: str) -> Optional[Tuple[int, int]]:
    ext = ext.lower()
    if ext == ".png":
        return _parse_png_size(data)
    if ext in {".jpg", ".jpeg"}:
        return _parse_jpeg_size(data)
    if ext == ".gif":
        return _parse_gif_size(data)
    return None


def _scale_to_fit(cx: int, cy: int, max_cx: int, max_cy: int) -> Tuple[int, int]:
    if cx <= 0 or cy <= 0:
        return (max_cx // 2, max_cy // 4)
    scale = min(max_cx / cx, max_cy / cy, 1.0)
    return (max(1, int(cx * scale)), max(1, int(cy * scale)))


def _make_issue(
    issues: List[ExportIssue],
    code: str,
    severity: str,
    message: str,
    exam_id: str = "",
    question_id: str = "",
    location: str = "",
) -> None:
    issues.append(
        ExportIssue(
            code=code,
            severity=severity,
            message=message,
            exam_id=exam_id,
            question_id=question_id,
            location=location,
        )
    )


def _merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _resolve_failure_policy(options: Dict[str, Any]) -> Dict[str, Any]:
    override = options.get("failure_policy")
    if not isinstance(override, dict):
        return json.loads(json.dumps(DEFAULT_FAILURE_POLICY))
    return _merge_dict(json.loads(json.dumps(DEFAULT_FAILURE_POLICY)), override)


def _severity_for(policy: Dict[str, Any], key: str, fallback: str) -> str:
    severity_map = policy.get("severity_map", {})
    if not isinstance(severity_map, dict):
        return fallback
    value = str(severity_map.get(key, fallback)).strip().lower()
    if value in {"info", "warning", "error", "blocker"}:
        return value
    return fallback


def _safe_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _apply_failure_policy(
    *,
    report: Dict[str, Any],
    issues: List[ExportIssue],
    policy: Dict[str, Any],
) -> Dict[str, Any]:
    thresholds = policy.get("thresholds", {})
    if not isinstance(thresholds, dict):
        thresholds = {}
    metrics = report.get("metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}

    math_detected = _safe_int(metrics.get("math_detected_count"), 0)
    math_failed = _safe_int(metrics.get("math_failed_count"), 0)
    image_embedded = _safe_int(metrics.get("image_embedded_count"), 0)
    image_failed = _safe_int(metrics.get("image_failed_count"), 0)
    image_total = image_embedded + image_failed

    math_failed_ratio = (float(math_failed) / float(math_detected)) if math_detected > 0 else 0.0
    image_failed_ratio = (float(image_failed) / float(image_total)) if image_total > 0 else 0.0

    math_warning_ratio_max = _safe_float(thresholds.get("math_failed_ratio_warning_max"), 0.02)
    math_warning_count_max = _safe_int(thresholds.get("math_failed_count_warning_max"), 2)
    math_blocker_ratio = _safe_float(thresholds.get("math_failed_ratio_blocker"), 0.10)
    math_blocker_count = _safe_int(thresholds.get("math_failed_count_blocker"), 10)

    image_warning_ratio_max = _safe_float(thresholds.get("image_failed_ratio_warning_max"), 0.10)
    image_warning_count_max = _safe_int(thresholds.get("image_failed_count_warning_max"), 3)
    image_blocker_ratio = _safe_float(thresholds.get("image_failed_ratio_blocker"), 0.25)
    image_blocker_count = _safe_int(thresholds.get("image_failed_count_blocker"), 8)

    math_status = "ok"
    if math_failed > 0:
        if math_failed > math_blocker_count or math_failed_ratio > math_blocker_ratio:
            math_status = "blocker"
            _make_issue(
                issues,
                code="math_degradation_exceeded",
                severity=_severity_for(policy, "math_degradation_exceeded", "blocker"),
                message=(
                    "Math degradation exceeded prototype thresholds: "
                    f"failed={math_failed}, detected={math_detected}, ratio={math_failed_ratio:.4f}, "
                    f"blocker_count>{math_blocker_count} or blocker_ratio>{math_blocker_ratio:.4f}"
                ),
                location="failure_policy.math",
            )
        elif math_failed <= math_warning_count_max and math_failed_ratio <= math_warning_ratio_max:
            math_status = "warning_within_tolerance"
            _make_issue(
                issues,
                code="math_degradation_within_tolerance",
                severity=_severity_for(policy, "math_degradation_within_tolerance", "warning"),
                message=(
                    "Math degradation detected but within prototype tolerance: "
                    f"failed={math_failed}, detected={math_detected}, ratio={math_failed_ratio:.4f}"
                ),
                location="failure_policy.math",
            )
        else:
            math_status = "warning_above_preferred"
            _make_issue(
                issues,
                code="math_degradation_within_tolerance",
                severity=_severity_for(policy, "math_degradation_within_tolerance", "warning"),
                message=(
                    "Math degradation is above preferred tolerance but below blocker threshold: "
                    f"failed={math_failed}, detected={math_detected}, ratio={math_failed_ratio:.4f}, "
                    f"preferred_count<={math_warning_count_max}, preferred_ratio<={math_warning_ratio_max:.4f}"
                ),
                location="failure_policy.math",
            )

    image_status = "ok"
    if image_failed > 0:
        if image_failed > image_blocker_count or image_failed_ratio > image_blocker_ratio:
            image_status = "blocker"
            _make_issue(
                issues,
                code="image_degradation_exceeded",
                severity=_severity_for(policy, "image_degradation_exceeded", "blocker"),
                message=(
                    "Image degradation exceeded prototype thresholds: "
                    f"failed={image_failed}, total={image_total}, ratio={image_failed_ratio:.4f}, "
                    f"blocker_count>{image_blocker_count} or blocker_ratio>{image_blocker_ratio:.4f}"
                ),
                location="failure_policy.image",
            )
        elif image_failed <= image_warning_count_max and image_failed_ratio <= image_warning_ratio_max:
            image_status = "warning_within_tolerance"
            _make_issue(
                issues,
                code="image_degradation_within_tolerance",
                severity=_severity_for(policy, "image_degradation_within_tolerance", "warning"),
                message=(
                    "Image degradation detected but within prototype tolerance: "
                    f"failed={image_failed}, total={image_total}, ratio={image_failed_ratio:.4f}"
                ),
                location="failure_policy.image",
            )
        else:
            image_status = "warning_above_preferred"
            _make_issue(
                issues,
                code="image_degradation_within_tolerance",
                severity=_severity_for(policy, "image_degradation_within_tolerance", "warning"),
                message=(
                    "Image degradation is above preferred tolerance but below blocker threshold: "
                    f"failed={image_failed}, total={image_total}, ratio={image_failed_ratio:.4f}, "
                    f"preferred_count<={image_warning_count_max}, preferred_ratio<={image_warning_ratio_max:.4f}"
                ),
                location="failure_policy.image",
            )

    checks = {
        "schema_version": DOCX_EXPORT_FAILURE_POLICY_SCHEMA_VERSION,
        "math": {
            "status": math_status,
            "detected_count": math_detected,
            "failed_count": math_failed,
            "failed_ratio": round(math_failed_ratio, 6),
            "preferred_thresholds": {
                "count_max": math_warning_count_max,
                "ratio_max": round(math_warning_ratio_max, 6),
            },
            "blocker_thresholds": {
                "count_max": math_blocker_count,
                "ratio_max": round(math_blocker_ratio, 6),
            },
        },
        "image": {
            "status": image_status,
            "total_count": image_total,
            "failed_count": image_failed,
            "failed_ratio": round(image_failed_ratio, 6),
            "preferred_thresholds": {
                "count_max": image_warning_count_max,
                "ratio_max": round(image_warning_ratio_max, 6),
            },
            "blocker_thresholds": {
                "count_max": image_blocker_count,
                "ratio_max": round(image_blocker_ratio, 6),
            },
        },
    }
    return checks


def _check_docx_openability(
    *,
    output_docx: Path,
    issues: List[ExportIssue],
    policy: Dict[str, Any],
    check_soffice: bool,
    timeout_sec: int,
) -> Dict[str, Any]:
    def _resolve_soffice_binary() -> Optional[str]:
        direct_candidates = [
            Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
            Path("/Applications/LibreOffice.app/Contents/MacOS/soffice.bin"),
        ]
        for candidate in direct_candidates:
            if candidate.exists() and candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        wrapper = shutil.which("soffice")
        if wrapper:
            return wrapper
        return None

    soffice_path = _resolve_soffice_binary()
    result: Dict[str, Any] = {
        "zip_integrity_checked": True,
        "zip_integrity_passed": False,
        "zip_bad_member": "",
        "soffice_check_requested": bool(check_soffice),
        "soffice_check_attempted": False,
        "soffice_check_passed": None,
        "soffice_binary_found": bool(soffice_path),
        "soffice_binary_path": soffice_path or "",
        "soffice_pdf_path": "",
    }
    try:
        with zipfile.ZipFile(output_docx, "r") as zf:
            bad = zf.testzip()
            if bad is None:
                result["zip_integrity_passed"] = True
            else:
                result["zip_bad_member"] = str(bad)
                _make_issue(
                    issues,
                    code="docx_zip_integrity_failed",
                    severity=_severity_for(policy, "docx_zip_integrity_failed", "blocker"),
                    message=f"DOCX zip integrity failed; first bad member: {bad}",
                    location=str(output_docx),
                )
    except Exception as ex:  # noqa: BLE001
        _make_issue(
            issues,
            code="docx_zip_integrity_failed",
            severity=_severity_for(policy, "docx_zip_integrity_failed", "blocker"),
            message=f"DOCX zip integrity check error: {ex}",
            location=str(output_docx),
        )

    if not check_soffice:
        return result

    soffice_bin = soffice_path
    if not soffice_bin:
        _make_issue(
            issues,
            code="openability_soffice_unavailable",
            severity=_severity_for(policy, "openability_soffice_unavailable", "warning"),
            message="Openability check requested but 'soffice' binary is not available.",
            location=str(output_docx),
        )
        return result

    result["soffice_check_attempted"] = True
    with tempfile.TemporaryDirectory(prefix="docx-openability-") as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        cmd = [
            soffice_bin,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp_dir_path),
            str(output_docx),
        ]
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max(10, int(timeout_sec)),
            )
        except subprocess.TimeoutExpired:
            result["soffice_check_passed"] = False
            _make_issue(
                issues,
                code="docx_openability_failed",
                severity=_severity_for(policy, "docx_openability_failed", "blocker"),
                message=f"soffice openability check timed out after {timeout_sec}s.",
                location=str(output_docx),
            )
            return result
        except Exception as ex:  # noqa: BLE001
            result["soffice_check_passed"] = False
            _make_issue(
                issues,
                code="docx_openability_failed",
                severity=_severity_for(policy, "docx_openability_failed", "blocker"),
                message=f"soffice openability check errored: {ex}",
                location=str(output_docx),
            )
            return result

        if completed.returncode != 0:
            result["soffice_check_passed"] = False
            stderr = (completed.stderr or "").strip()
            stdout = (completed.stdout or "").strip()
            details = stderr or stdout or "unknown soffice error"
            _make_issue(
                issues,
                code="docx_openability_failed",
                severity=_severity_for(policy, "docx_openability_failed", "blocker"),
                message=f"soffice openability check failed (code {completed.returncode}): {details}",
                location=str(output_docx),
            )
            return result

        expected_pdf = tmp_dir_path / f"{output_docx.stem}.pdf"
        if expected_pdf.exists():
            result["soffice_check_passed"] = True
            result["soffice_pdf_path"] = str(expected_pdf)
        else:
            result["soffice_check_passed"] = False
            _make_issue(
                issues,
                code="docx_openability_failed",
                severity=_severity_for(policy, "docx_openability_failed", "blocker"),
                message="soffice reported success but expected PDF output was not found.",
                location=str(output_docx),
            )
    return result


class MathmlToOmmlConverter:
    def __init__(self, issues: List[ExportIssue], strict_math: bool):
        self.issues = issues
        self.strict_math = strict_math
        self.math_detected_count = 0
        self.math_converted_count = 0
        self.math_failed_count = 0

    def convert(self, mathml_fragment: str, force_display: bool = False, location: str = "") -> Optional[ET.Element]:
        self.math_detected_count += 1
        fragment = (mathml_fragment or "").strip()
        if not fragment:
            self.math_failed_count += 1
            severity = "blocker" if self.strict_math else "warning"
            _make_issue(
                self.issues,
                code="mathml_missing_in_source",
                severity=severity,
                message="Empty MathML fragment cannot be converted.",
                location=location,
            )
            return None

        try:
            root = ET.fromstring(fragment)
        except ET.ParseError as ex:
            self.math_failed_count += 1
            severity = "blocker" if self.strict_math else "warning"
            _make_issue(
                self.issues,
                code="mathml_to_omml_transform_failed",
                severity=severity,
                message=f"MathML parse failed: {ex}",
                location=location,
            )
            return None

        display_attr = (root.get("display") or "").strip().lower()
        display_mode = force_display or display_attr == "block"
        pieces = self._convert_expr(root, location=location)
        if not pieces:
            self.math_failed_count += 1
            severity = "blocker" if self.strict_math else "warning"
            _make_issue(
                self.issues,
                code="mathml_to_omml_transform_failed",
                severity=severity,
                message="No OMML tokens generated from MathML fragment.",
                location=location,
            )
            return None

        omath = ET.Element(_qn("m", "oMath"))
        for piece in pieces:
            omath.append(piece)

        self.math_converted_count += 1
        if display_mode:
            para = ET.Element(_qn("m", "oMathPara"))
            para.append(omath)
            return para
        return omath

    def _convert_expr(self, node: ET.Element, location: str = "") -> List[ET.Element]:
        name = _local_name(node.tag).lower()
        children = [child for child in list(node) if isinstance(child.tag, str)]

        if name in {"math", "mrow", "semantics", "mstyle", "none", "mtd"}:
            return self._collect_mixed_content(node, location=location)

        if name in {"mi", "mn", "mo", "mtext"}:
            text = "".join(node.itertext())
            text = _normalize_text(text)
            if not text:
                return []
            return [self._make_math_run(text)]

        if name == "mspace":
            width = (node.get("width") or "").strip()
            if width:
                return [self._make_math_run(" ")]
            return []

        if name == "mfenced":
            open_ch = node.get("open", "(")
            close_ch = node.get("close", ")")
            sep = node.get("separators", ",")
            out: List[ET.Element] = []
            if open_ch:
                out.append(self._make_math_run(open_ch))
            for idx, child in enumerate(children):
                if idx > 0 and sep:
                    out.append(self._make_math_run(sep[0]))
                out.extend(self._convert_expr(child, location=location))
            if close_ch:
                out.append(self._make_math_run(close_ch))
            return out

        if name == "mfrac" and len(children) >= 2:
            frac = ET.Element(_qn("m", "f"))
            num = ET.SubElement(frac, _qn("m", "num"))
            den = ET.SubElement(frac, _qn("m", "den"))
            self._append_container_content(num, self._convert_expr(children[0], location=location))
            self._append_container_content(den, self._convert_expr(children[1], location=location))
            return [frac]

        if name == "msup" and len(children) >= 2:
            sup = ET.Element(_qn("m", "sSup"))
            e = ET.SubElement(sup, _qn("m", "e"))
            up = ET.SubElement(sup, _qn("m", "sup"))
            self._append_container_content(e, self._convert_expr(children[0], location=location))
            self._append_container_content(up, self._convert_expr(children[1], location=location))
            return [sup]

        if name == "msub" and len(children) >= 2:
            sub = ET.Element(_qn("m", "sSub"))
            e = ET.SubElement(sub, _qn("m", "e"))
            low = ET.SubElement(sub, _qn("m", "sub"))
            self._append_container_content(e, self._convert_expr(children[0], location=location))
            self._append_container_content(low, self._convert_expr(children[1], location=location))
            return [sub]

        if name == "msubsup" and len(children) >= 3:
            sub_sup = ET.Element(_qn("m", "sSubSup"))
            e = ET.SubElement(sub_sup, _qn("m", "e"))
            low = ET.SubElement(sub_sup, _qn("m", "sub"))
            up = ET.SubElement(sub_sup, _qn("m", "sup"))
            self._append_container_content(e, self._convert_expr(children[0], location=location))
            self._append_container_content(low, self._convert_expr(children[1], location=location))
            self._append_container_content(up, self._convert_expr(children[2], location=location))
            return [sub_sup]

        if name == "msqrt":
            rad = ET.Element(_qn("m", "rad"))
            ET.SubElement(rad, _qn("m", "deg"))
            e = ET.SubElement(rad, _qn("m", "e"))
            self._append_container_content(e, self._collect_mixed_content(node, location=location))
            return [rad]

        if name == "mroot" and len(children) >= 2:
            rad = ET.Element(_qn("m", "rad"))
            deg = ET.SubElement(rad, _qn("m", "deg"))
            e = ET.SubElement(rad, _qn("m", "e"))
            self._append_container_content(e, self._convert_expr(children[0], location=location))
            self._append_container_content(deg, self._convert_expr(children[1], location=location))
            return [rad]

        if name == "munder" and len(children) >= 2:
            sub = ET.Element(_qn("m", "sSub"))
            e = ET.SubElement(sub, _qn("m", "e"))
            low = ET.SubElement(sub, _qn("m", "sub"))
            self._append_container_content(e, self._convert_expr(children[0], location=location))
            self._append_container_content(low, self._convert_expr(children[1], location=location))
            return [sub]

        if name == "mover" and len(children) >= 2:
            sup = ET.Element(_qn("m", "sSup"))
            e = ET.SubElement(sup, _qn("m", "e"))
            up = ET.SubElement(sup, _qn("m", "sup"))
            self._append_container_content(e, self._convert_expr(children[0], location=location))
            self._append_container_content(up, self._convert_expr(children[1], location=location))
            return [sup]

        if name == "munderover" and len(children) >= 3:
            sub_sup = ET.Element(_qn("m", "sSubSup"))
            e = ET.SubElement(sub_sup, _qn("m", "e"))
            low = ET.SubElement(sub_sup, _qn("m", "sub"))
            up = ET.SubElement(sub_sup, _qn("m", "sup"))
            self._append_container_content(e, self._convert_expr(children[0], location=location))
            self._append_container_content(low, self._convert_expr(children[1], location=location))
            self._append_container_content(up, self._convert_expr(children[2], location=location))
            return [sub_sup]

        if name == "mtable":
            matrix = ET.Element(_qn("m", "m"))
            for row in children:
                if _local_name(row.tag).lower() != "mtr":
                    continue
                mr = ET.SubElement(matrix, _qn("m", "mr"))
                cells = [c for c in list(row) if isinstance(c.tag, str)]
                if not cells:
                    e_cell = ET.SubElement(mr, _qn("m", "e"))
                    e_cell.append(self._make_math_run(""))
                    continue
                for cell in cells:
                    e_cell = ET.SubElement(mr, _qn("m", "e"))
                    self._append_container_content(e_cell, self._convert_expr(cell, location=location))
            return [matrix]

        if name in {"annotation", "annotation-xml"}:
            return []

        fallback = self._collect_mixed_content(node, location=location)
        _make_issue(
            self.issues,
            code="mathml_unsupported_tag_fallback",
            severity="warning",
            message=f"Unsupported MathML tag '{name}' converted by fallback flattening.",
            location=location,
        )
        return fallback

    def _collect_mixed_content(self, node: ET.Element, location: str = "") -> List[ET.Element]:
        out: List[ET.Element] = []
        if node.text:
            text = _normalize_text(node.text)
            if text:
                out.append(self._make_math_run(text))
        for child in [c for c in list(node) if isinstance(c.tag, str)]:
            out.extend(self._convert_expr(child, location=location))
            if child.tail:
                tail = _normalize_text(child.tail)
                if tail:
                    out.append(self._make_math_run(tail))
        return out

    def _make_math_run(self, text: str) -> ET.Element:
        run = ET.Element(_qn("m", "r"))
        t = ET.SubElement(run, _qn("m", "t"))
        _set_text_with_space_preserve(t, text)
        return run

    def _append_container_content(self, container: ET.Element, parts: List[ET.Element]) -> None:
        if parts:
            for part in parts:
                container.append(part)
            return
        container.append(self._make_math_run(""))


class MinimalDocxBuilder:
    def __init__(self, issues: List[ExportIssue]):
        self.issues = issues
        self.document = ET.Element(_qn("w", "document"))
        self.body = ET.SubElement(self.document, _qn("w", "body"))
        self._image_rels: List[Dict[str, Any]] = []
        self._next_rel_index = 1
        self._next_docpr_id = 1

    def add_paragraph(self, style: Optional[str] = None, center: bool = False) -> ET.Element:
        p = ET.Element(_qn("w", "p"))
        if style or center:
            ppr = ET.SubElement(p, _qn("w", "pPr"))
            if style:
                pstyle = ET.SubElement(ppr, _qn("w", "pStyle"))
                pstyle.set(_qn("w", "val"), style)
            if center:
                jc = ET.SubElement(ppr, _qn("w", "jc"))
                jc.set(_qn("w", "val"), "center")
        self.body.append(p)
        return p

    def add_text_run(self, paragraph: ET.Element, text: str, bold: bool = False) -> None:
        run = ET.SubElement(paragraph, _qn("w", "r"))
        if bold:
            rpr = ET.SubElement(run, _qn("w", "rPr"))
            ET.SubElement(rpr, _qn("w", "b"))
        t = ET.SubElement(run, _qn("w", "t"))
        _set_text_with_space_preserve(t, text)

    def add_break(self, paragraph: ET.Element) -> None:
        run = ET.SubElement(paragraph, _qn("w", "r"))
        ET.SubElement(run, _qn("w", "br"))

    def append_omml(self, paragraph: ET.Element, omml_node: ET.Element) -> None:
        paragraph.append(omml_node)

    def add_image_run(
        self,
        paragraph: ET.Element,
        image_path: Path,
        location: str = "",
        max_width_emu: int = MAX_IMAGE_WIDTH_EMU,
        max_height_emu: int = MAX_IMAGE_HEIGHT_EMU,
    ) -> bool:
        ext = image_path.suffix.lower()
        mime = SUPPORTED_IMAGE_MIME.get(ext)
        if not mime:
            _make_issue(
                self.issues,
                code="image_format_unsupported",
                severity="warning",
                message=f"Unsupported image format for DOCX embedding: {ext or '(none)'}",
                location=location,
            )
            return False

        try:
            data = image_path.read_bytes()
        except OSError as ex:
            _make_issue(
                self.issues,
                code="image_embed_failed",
                severity="warning",
                message=f"Image read failed: {image_path} ({ex})",
                location=location,
            )
            return False

        rel_id = f"rId{self._next_rel_index}"
        self._next_rel_index += 1
        media_name = f"image{len(self._image_rels) + 1}{ext}"
        size_px = _extract_image_size_px(data, ext) or (640, 360)
        cx = int(size_px[0] * EMU_PER_PX)
        cy = int(size_px[1] * EMU_PER_PX)
        cx, cy = _scale_to_fit(cx, cy, max_width_emu, max_height_emu)
        docpr_id = self._next_docpr_id
        self._next_docpr_id += 1

        self._image_rels.append(
            {
                "rel_id": rel_id,
                "target": f"media/{media_name}",
                "media_name": media_name,
                "mime": mime,
                "data": data,
            }
        )

        run = ET.SubElement(paragraph, _qn("w", "r"))
        drawing = ET.SubElement(run, _qn("w", "drawing"))
        inline = ET.SubElement(
            drawing,
            _qn("wp", "inline"),
            {"distT": "0", "distB": "0", "distL": "0", "distR": "0"},
        )
        ET.SubElement(inline, _qn("wp", "extent"), {"cx": str(cx), "cy": str(cy)})
        ET.SubElement(
            inline,
            _qn("wp", "effectExtent"),
            {"l": "0", "t": "0", "r": "0", "b": "0"},
        )
        ET.SubElement(inline, _qn("wp", "docPr"), {"id": str(docpr_id), "name": media_name})
        c_nv = ET.SubElement(inline, _qn("wp", "cNvGraphicFramePr"))
        ET.SubElement(c_nv, _qn("a", "graphicFrameLocks"), {"noChangeAspect": "1"})
        graphic = ET.SubElement(inline, _qn("a", "graphic"))
        graphic_data = ET.SubElement(
            graphic,
            _qn("a", "graphicData"),
            {"uri": "http://schemas.openxmlformats.org/drawingml/2006/picture"},
        )
        pic = ET.SubElement(graphic_data, _qn("pic", "pic"))
        nv_pic_pr = ET.SubElement(pic, _qn("pic", "nvPicPr"))
        ET.SubElement(nv_pic_pr, _qn("pic", "cNvPr"), {"id": "0", "name": media_name})
        ET.SubElement(nv_pic_pr, _qn("pic", "cNvPicPr"))
        blip_fill = ET.SubElement(pic, _qn("pic", "blipFill"))
        ET.SubElement(blip_fill, _qn("a", "blip"), {_qn("r", "embed"): rel_id})
        stretch = ET.SubElement(blip_fill, _qn("a", "stretch"))
        ET.SubElement(stretch, _qn("a", "fillRect"))
        sp_pr = ET.SubElement(pic, _qn("pic", "spPr"))
        xfrm = ET.SubElement(sp_pr, _qn("a", "xfrm"))
        ET.SubElement(xfrm, _qn("a", "off"), {"x": "0", "y": "0"})
        ET.SubElement(xfrm, _qn("a", "ext"), {"cx": str(cx), "cy": str(cy)})
        prst = ET.SubElement(sp_pr, _qn("a", "prstGeom"), {"prst": "rect"})
        ET.SubElement(prst, _qn("a", "avLst"))
        return True

    def finalize_document(self) -> None:
        sect = ET.SubElement(self.body, _qn("w", "sectPr"))
        ET.SubElement(sect, _qn("w", "pgSz"), {_qn("w", "w"): "12240", _qn("w", "h"): "15840"})
        ET.SubElement(
            sect,
            _qn("w", "pgMar"),
            {
                _qn("w", "top"): "1440",
                _qn("w", "right"): "1440",
                _qn("w", "bottom"): "1440",
                _qn("w", "left"): "1440",
                _qn("w", "header"): "708",
                _qn("w", "footer"): "708",
                _qn("w", "gutter"): "0",
            },
        )

    def write_docx(self, output_docx_path: Path) -> None:
        self.finalize_document()
        output_docx_path.parent.mkdir(parents=True, exist_ok=True)

        document_xml = ET.tostring(self.document, encoding="utf-8", xml_declaration=True)
        content_types_xml = self._build_content_types_xml()
        rels_root_xml = self._build_root_rels_xml()
        doc_rels_xml = self._build_document_rels_xml()
        app_xml = self._build_app_xml()
        core_xml = self._build_core_xml()

        with zipfile.ZipFile(output_docx_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types_xml)
            zf.writestr("_rels/.rels", rels_root_xml)
            zf.writestr("word/document.xml", document_xml)
            zf.writestr("word/_rels/document.xml.rels", doc_rels_xml)
            zf.writestr("docProps/app.xml", app_xml)
            zf.writestr("docProps/core.xml", core_xml)
            for img in self._image_rels:
                zf.writestr(f"word/{img['target']}", img["data"])

    def image_count(self) -> int:
        return len(self._image_rels)

    def _build_content_types_xml(self) -> bytes:
        root = ET.Element("Types", {"xmlns": CONTENT_TYPES_NS})
        ET.SubElement(root, "Default", {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
        ET.SubElement(root, "Default", {"Extension": "xml", "ContentType": "application/xml"})
        used_ext = set()
        for img in self._image_rels:
            ext = Path(img["media_name"]).suffix.lower().lstrip(".")
            if ext in used_ext:
                continue
            used_ext.add(ext)
            ET.SubElement(root, "Default", {"Extension": ext, "ContentType": img["mime"]})
        ET.SubElement(
            root,
            "Override",
            {
                "PartName": "/word/document.xml",
                "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
            },
        )
        ET.SubElement(
            root,
            "Override",
            {
                "PartName": "/docProps/core.xml",
                "ContentType": "application/vnd.openxmlformats-package.core-properties+xml",
            },
        )
        ET.SubElement(
            root,
            "Override",
            {
                "PartName": "/docProps/app.xml",
                "ContentType": "application/vnd.openxmlformats-officedocument.extended-properties+xml",
            },
        )
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _build_root_rels_xml(self) -> bytes:
        root = ET.Element("Relationships", {"xmlns": REL_NS})
        ET.SubElement(
            root,
            "Relationship",
            {
                "Id": "rId1",
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
                "Target": "word/document.xml",
            },
        )
        ET.SubElement(
            root,
            "Relationship",
            {
                "Id": "rId2",
                "Type": "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties",
                "Target": "docProps/core.xml",
            },
        )
        ET.SubElement(
            root,
            "Relationship",
            {
                "Id": "rId3",
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties",
                "Target": "docProps/app.xml",
            },
        )
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _build_document_rels_xml(self) -> bytes:
        root = ET.Element("Relationships", {"xmlns": REL_NS})
        for img in self._image_rels:
            ET.SubElement(
                root,
                "Relationship",
                {
                    "Id": img["rel_id"],
                    "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                    "Target": img["target"],
                },
            )
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _build_app_xml(self) -> bytes:
        root = ET.Element(
            "Properties",
            {
                "xmlns": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
                "xmlns:vt": "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes",
            },
        )
        ET.SubElement(root, "Application").text = "docx_exporter.py"
        ET.SubElement(root, "DocSecurity").text = "0"
        ET.SubElement(root, "ScaleCrop").text = "false"
        ET.SubElement(root, "SharedDoc").text = "false"
        ET.SubElement(root, "HyperlinksChanged").text = "false"
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _build_core_xml(self) -> bytes:
        root = ET.Element(
            "cp:coreProperties",
            {
                "xmlns:cp": CP_NS,
                "xmlns:dc": DC_NS,
                "xmlns:dcterms": DCTERMS_NS,
                "xmlns:dcmitype": "http://purl.org/dc/dcmitype/",
                "xmlns:xsi": XSI_NS,
            },
        )
        ET.SubElement(root, "dc:title").text = "Teacher Exam Export"
        ET.SubElement(root, "dc:creator").text = "docx_exporter.py"
        ET.SubElement(root, "cp:lastModifiedBy").text = "docx_exporter.py"
        ET.SubElement(
            root,
            "dcterms:created",
            {"xsi:type": "dcterms:W3CDTF"},
        ).text = "2026-04-08T00:00:00Z"
        ET.SubElement(
            root,
            "dcterms:modified",
            {"xsi:type": "dcterms:W3CDTF"},
        ).text = "2026-04-08T00:00:00Z"
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _tokenize_fragment(fragment_html: str) -> List[Dict[str, Any]]:
    tokens: List[Dict[str, Any]] = []
    pos = 0
    html_fragment = fragment_html or ""
    for match in TOKEN_RE.finditer(html_fragment):
        before = html_fragment[pos : match.start()]
        if before:
            text = _normalize_text(before)
            if text:
                tokens.append({"type": "text", "text": text})
        token_raw = match.group(0)
        token_lower = token_raw.lower()
        if MATH_TOKEN_RE.match(token_raw):
            tokens.append({"type": "math", "mathml": token_raw, "display": "display=\"block\"" in token_lower or "display='block'" in token_lower})
        elif IMG_TOKEN_RE.match(token_raw):
            tokens.append({"type": "image", "attrs": _parse_attrs(token_raw)})
        elif BR_TOKEN_RE.match(token_raw):
            tokens.append({"type": "br"})
        pos = match.end()
    tail = html_fragment[pos:]
    if tail:
        text = _normalize_text(tail)
        if text:
            tokens.append({"type": "text", "text": text})
    return tokens


def _extract_block_parts(block_html: str) -> Tuple[str, Dict[str, str], str]:
    raw = (block_html or "").strip()
    m = OUTER_BLOCK_RE.match(raw)
    if not m:
        return ("", {}, raw)
    tag_name = m.group(1).lower()
    attrs = _parse_attrs(m.group(2))
    inner = m.group(3)
    return (tag_name, attrs, inner)


def _render_tokens_into_paragraph(
    paragraph: ET.Element,
    tokens: List[Dict[str, Any]],
    builder: MinimalDocxBuilder,
    math_converter: MathmlToOmmlConverter,
    html_path: Path,
    asset_dir: Optional[Path],
    metrics: Dict[str, int],
    location: str,
    treat_math_as_display: bool = False,
) -> None:
    for token in tokens:
        token_type = token.get("type")
        if token_type == "text":
            builder.add_text_run(paragraph, str(token.get("text", "")))
            continue
        if token_type == "br":
            builder.add_break(paragraph)
            continue
        if token_type == "math":
            display_mode = bool(token.get("display")) or treat_math_as_display
            omml = math_converter.convert(
                str(token.get("mathml", "")),
                force_display=display_mode,
                location=location,
            )
            if omml is None:
                builder.add_text_run(paragraph, "[UNRESOLVED_MATH]")
                continue
            if _local_name(omml.tag).lower() == "omathpara":
                inner_omath = next((child for child in list(omml) if _local_name(child.tag).lower() == "omath"), None)
                if inner_omath is None:
                    builder.add_text_run(paragraph, "[UNRESOLVED_MATH]")
                    continue
                builder.append_omml(paragraph, inner_omath)
                continue
            builder.append_omml(paragraph, omml)
            continue
        if token_type == "image":
            attrs = token.get("attrs", {})
            src = str(attrs.get("src", ""))
            image_path = _resolve_image_path(src=src, html_path=html_path, asset_dir=asset_dir)
            if image_path is None:
                _make_issue(
                    builder.issues,
                    code="image_embed_failed",
                    severity="warning",
                    message=f"Image source not found: {src}",
                    location=location,
                )
                metrics["image_failed_count"] += 1
                builder.add_text_run(paragraph, "[MISSING_IMAGE]")
                continue
            embedded = builder.add_image_run(paragraph, image_path=image_path, location=location)
            if embedded:
                metrics["image_embedded_count"] += 1
            else:
                metrics["image_failed_count"] += 1
                builder.add_text_run(paragraph, "[UNSUPPORTED_IMAGE]")
            continue


def _render_table_block(
    block_inner_html: str,
    builder: MinimalDocxBuilder,
    math_converter: MathmlToOmmlConverter,
    html_path: Path,
    asset_dir: Optional[Path],
    metrics: Dict[str, int],
    location: str,
) -> None:
    rows = TABLE_ROW_RE.findall(block_inner_html or "")
    if not rows:
        para = builder.add_paragraph()
        text = _normalize_text(re.sub(r"(?is)<[^>]+>", " ", block_inner_html or ""))
        if text:
            builder.add_text_run(para, text)
        return

    for row_idx, row_html in enumerate(rows, start=1):
        para = builder.add_paragraph()
        cells = TABLE_CELL_RE.findall(row_html or "")
        if not cells:
            text = _normalize_text(re.sub(r"(?is)<[^>]+>", " ", row_html))
            if text:
                builder.add_text_run(para, text)
            continue
        for cell_idx, cell_html in enumerate(cells, start=1):
            if cell_idx > 1:
                builder.add_text_run(para, " | ")
            cell_tokens = _tokenize_fragment(cell_html)
            _render_tokens_into_paragraph(
                paragraph=para,
                tokens=cell_tokens,
                builder=builder,
                math_converter=math_converter,
                html_path=html_path,
                asset_dir=asset_dir,
                metrics=metrics,
                location=f"{location}:row{row_idx}:cell{cell_idx}",
                treat_math_as_display=False,
            )


def _build_answer_lines(answer_summary: Dict[str, Any]) -> List[str]:
    entries = answer_summary.get("entries", []) if isinstance(answer_summary, dict) else []
    if not isinstance(entries, list):
        return []
    grouped: Dict[str, Dict[str, str]] = defaultdict(dict)
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        qn = str(entry.get("question_number", "")).strip()
        mode = str(entry.get("mode", "")).strip()
        if not qn or not mode:
            continue
        if mode == "single_choice":
            value = str(entry.get("value", "")).strip()
            if value:
                grouped[qn]["single_choice"] = value
        elif mode == "boolean_group":
            sub = entry.get("subanswers", {})
            if isinstance(sub, dict) and sub:
                ordered = []
                for key in sorted(sub.keys()):
                    val = sub[key]
                    ordered.append(f"{key}:{'Đúng' if bool(val) else 'Sai'}")
                grouped[qn]["boolean_group"] = ", ".join(ordered)
        elif mode == "short_answer":
            accepted = entry.get("accepted_answers", [])
            vals: List[str] = []
            if isinstance(accepted, list):
                for ans in accepted:
                    if not isinstance(ans, dict):
                        continue
                    raw = str(ans.get("raw", "")).strip()
                    normalized = str(ans.get("normalized", "")).strip()
                    if raw and normalized and raw != normalized:
                        vals.append(f"{raw} ({normalized})")
                    elif raw:
                        vals.append(raw)
                    elif normalized:
                        vals.append(normalized)
            if vals:
                grouped[qn]["short_answer"] = " / ".join(vals)
        elif mode == "rubric":
            text = str(entry.get("value", "")).strip()
            if text:
                grouped[qn]["rubric"] = text

    def sort_key(question_number: str) -> Tuple[int, str]:
        return (int(question_number), question_number) if question_number.isdigit() else (10**9, question_number)

    lines: List[str] = []
    for qn in sorted(grouped.keys(), key=sort_key):
        data = grouped[qn]
        parts: List[str] = []
        if "single_choice" in data:
            parts.append(f"MCQ={data['single_choice']}")
        if "boolean_group" in data:
            parts.append(f"TF={data['boolean_group']}")
        if "short_answer" in data:
            parts.append(f"Short={data['short_answer']}")
        if "rubric" in data:
            parts.append(f"Rubric={data['rubric']}")
        if parts:
            lines.append(f"Câu {qn}: " + " | ".join(parts))
    return lines


def _init_report(bundle: Dict[str, Any], mode: str, output_docx_path: Path) -> Dict[str, Any]:
    source = bundle.get("source", {}) if isinstance(bundle.get("source"), dict) else {}
    source_paths = {
        "exam_bundle_path": "",
        "html_path": str(source.get("html_path", "")),
        "asset_dir": str(source.get("asset_dir", "")),
        "docx_source_path": str(source.get("docx_path", "")),
    }
    return {
        "schema_version": DOCX_EXPORT_REPORT_SCHEMA_VERSION,
        "artifact_type": "docx_export_report",
        "bundle_id": str(bundle.get("bundle_id", "")),
        "export_mode": mode,
        "source_paths": source_paths,
        "output_docx_path": str(output_docx_path),
        "verdict": "safe_to_export",
        "metrics": {
            "question_count": 0,
            "math_detected_count": 0,
            "math_converted_count": 0,
            "math_failed_count": 0,
            "image_embedded_count": 0,
            "image_failed_count": 0,
            "answer_block_count": 0,
            "rubric_block_count": 0,
        },
        "failure_policy": {},
        "policy_checks": {},
        "openability": {},
        "issues": [],
        "warnings_count": 0,
        "blockers_count": 0,
        "timings": {},
    }


def _finalize_report(report: Dict[str, Any], issues: List[ExportIssue]) -> None:
    report["issues"] = [issue.as_dict() for issue in issues]
    warning_count = sum(1 for issue in issues if issue.severity in {"warning", "error"})
    blocker_count = sum(1 for issue in issues if issue.severity == "blocker")
    report["warnings_count"] = warning_count
    report["blockers_count"] = blocker_count
    if blocker_count > 0:
        report["verdict"] = "blocked"
    elif warning_count > 0:
        report["verdict"] = "needs_review"
    else:
        report["verdict"] = "safe_to_export"


def export_exam_bundle_to_docx(
    exam_bundle_path: str | Path,
    output_docx_path: str | Path,
    mode: str = "teacher_exam",
    options: Optional[Dict[str, Any]] = None,
    report_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    options = options or {}
    strict_math = bool(options.get("strict_math", False))
    check_openability = bool(options.get("check_openability", False))
    openability_timeout_sec = _safe_int(options.get("openability_timeout_sec"), 120)
    failure_policy = _resolve_failure_policy(options)

    t0 = time.perf_counter()
    exam_bundle_file = Path(exam_bundle_path).resolve()
    output_docx = Path(output_docx_path).resolve()
    issues: List[ExportIssue] = []

    try:
        bundle = json.loads(exam_bundle_file.read_text(encoding="utf-8"))
    except OSError as ex:
        bundle = {"bundle_id": "", "source": {}}
        report = _init_report(bundle=bundle, mode=mode, output_docx_path=output_docx)
        _make_issue(
            issues,
            code="source_bundle_read_failed",
            severity="blocker",
            message=f"Cannot read exam_bundle.json: {ex}",
            location=str(exam_bundle_file),
        )
        _finalize_report(report, issues)
        if report_path:
            Path(report_path).resolve().write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    except json.JSONDecodeError as ex:
        bundle = {"bundle_id": "", "source": {}}
        report = _init_report(bundle=bundle, mode=mode, output_docx_path=output_docx)
        _make_issue(
            issues,
            code="source_bundle_parse_failed",
            severity="blocker",
            message=f"Invalid exam_bundle.json: {ex}",
            location=str(exam_bundle_file),
        )
        _finalize_report(report, issues)
        if report_path:
            Path(report_path).resolve().write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    report = _init_report(bundle=bundle, mode=mode, output_docx_path=output_docx)
    report["source_paths"]["exam_bundle_path"] = str(exam_bundle_file)
    report["failure_policy"] = failure_policy

    t1 = time.perf_counter()
    report["timings"]["load_bundle_ms"] = round((t1 - t0) * 1000.0, 3)

    if mode != "teacher_exam":
        _make_issue(
            issues,
            code="export_mode_unsupported",
            severity="blocker",
            message=f"Prototype currently supports teacher_exam only. Requested: {mode}",
            location="export_mode",
        )
        _finalize_report(report, issues)
        output_report = Path(report_path).resolve() if report_path else output_docx.with_name("docx_export_report.json")
        output_report.parent.mkdir(parents=True, exist_ok=True)
        output_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    source = bundle.get("source", {}) if isinstance(bundle.get("source"), dict) else {}
    html_path_raw = str(source.get("html_path", "")).strip()
    asset_dir_raw = str(source.get("asset_dir", "")).strip()
    if not html_path_raw:
        _make_issue(
            issues,
            code="source_html_missing",
            severity="blocker",
            message="exam_bundle.source.html_path is missing.",
            location="source.html_path",
        )
        _finalize_report(report, issues)
        output_report = Path(report_path).resolve() if report_path else output_docx.with_name("docx_export_report.json")
        output_report.parent.mkdir(parents=True, exist_ok=True)
        output_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    html_path = Path(html_path_raw).resolve()
    asset_dir = Path(asset_dir_raw).resolve() if asset_dir_raw else None
    report["source_paths"]["html_path"] = str(html_path)
    report["source_paths"]["asset_dir"] = str(asset_dir) if asset_dir else ""

    try:
        html_text = html_path.read_text(encoding="utf-8")
    except OSError as ex:
        _make_issue(
            issues,
            code="source_html_read_failed",
            severity="blocker",
            message=f"Cannot read source HTML: {ex}",
            location=str(html_path),
        )
        _finalize_report(report, issues)
        output_report = Path(report_path).resolve() if report_path else output_docx.with_name("docx_export_report.json")
        output_report.parent.mkdir(parents=True, exist_ok=True)
        output_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    parse_t0 = time.perf_counter()
    parser_module = _load_contract_parser_module()
    parsed = parser_module.parse_html_structure(html_text)
    parse_t1 = time.perf_counter()
    report["timings"]["parse_html_ms"] = round((parse_t1 - parse_t0) * 1000.0, 3)

    blocks: List[Any] = list(parsed.get("blocks", []))
    questions: List[Any] = list(parsed.get("questions", []))
    answer_cutoff = _find_answer_cutoff_index(blocks)

    if answer_cutoff is not None:
        filtered_blocks = [b for b in blocks if int(getattr(b, "block_index", 0)) < answer_cutoff]
        filtered_questions = [q for q in questions if int(getattr(q, "start_block_index", 0)) < answer_cutoff]
    else:
        filtered_blocks = blocks
        filtered_questions = questions
        missing_zone_severity = _severity_for(
            failure_policy,
            "answer_summary_zone_missing_without_questions" if len(filtered_questions) == 0 else "answer_summary_zone_missing_with_questions",
            "warning",
        )
        _make_issue(
            issues,
            code="answer_summary_zone_missing",
            severity=missing_zone_severity,
            message="Could not detect answer summary zone heading in HTML; full document content exported.",
            location=str(html_path),
        )

    report["metrics"]["question_count"] = len(filtered_questions)

    build_t0 = time.perf_counter()
    doc_builder = MinimalDocxBuilder(issues=issues)
    math_converter = MathmlToOmmlConverter(issues=issues, strict_math=strict_math)
    metrics = report["metrics"]

    title_fallback = Path(str(source.get("docx_path", ""))).stem or html_path.stem
    title = _extract_title(html_text, fallback_name=title_fallback)

    p_title = doc_builder.add_paragraph(style="Heading1")
    doc_builder.add_text_run(p_title, title)

    if filtered_questions:
        p_meta = doc_builder.add_paragraph()
        doc_builder.add_text_run(
            p_meta,
            f"Teacher exam prototype export | Questions detected: {len(filtered_questions)}",
        )
    else:
        p_meta = doc_builder.add_paragraph()
        doc_builder.add_text_run(
            p_meta,
            "Teacher exam prototype export | No question slices detected by parser.",
        )

    for block in filtered_blocks:
        block_html = getattr(block, "html", "") or ""
        block_text = (getattr(block, "text", "") or "").strip()
        block_index = int(getattr(block, "block_index", 0))
        location = f"block:{block_index}"
        tag_name, attrs, inner_html = _extract_block_parts(block_html)
        css_class = attrs.get("class", "").lower()
        is_section_heading = bool(SECTION_HEADING_RE.match(block_text))
        is_block_math = "math-block" in css_class or tag_name == "div" and "mathml" in css_class

        if tag_name == "table":
            _render_table_block(
                block_inner_html=inner_html,
                builder=doc_builder,
                math_converter=math_converter,
                html_path=html_path,
                asset_dir=asset_dir,
                metrics=metrics,
                location=location,
            )
            continue

        tokens = _tokenize_fragment(inner_html)
        has_non_image_content = any(tok.get("type") != "image" for tok in tokens)

        if tokens and not has_non_image_content:
            for image_idx, token in enumerate(tokens, start=1):
                para = doc_builder.add_paragraph(center=True)
                _render_tokens_into_paragraph(
                    paragraph=para,
                    tokens=[token],
                    builder=doc_builder,
                    math_converter=math_converter,
                    html_path=html_path,
                    asset_dir=asset_dir,
                    metrics=metrics,
                    location=f"{location}:image{image_idx}",
                    treat_math_as_display=False,
                )
            continue

        style = "Heading2" if is_section_heading else None
        paragraph = doc_builder.add_paragraph(style=style)
        if not tokens and block_text:
            doc_builder.add_text_run(paragraph, block_text)
            continue

        for tok_idx, token in enumerate(tokens, start=1):
            token_type = token.get("type")
            if token_type == "math" and (is_block_math or bool(token.get("display"))):
                display_para = doc_builder.add_paragraph(center=True)
                _render_tokens_into_paragraph(
                    paragraph=display_para,
                    tokens=[token],
                    builder=doc_builder,
                    math_converter=math_converter,
                    html_path=html_path,
                    asset_dir=asset_dir,
                    metrics=metrics,
                    location=f"{location}:math{tok_idx}",
                    treat_math_as_display=True,
                )
                continue
            if token_type == "image":
                image_para = doc_builder.add_paragraph(center=True)
                _render_tokens_into_paragraph(
                    paragraph=image_para,
                    tokens=[token],
                    builder=doc_builder,
                    math_converter=math_converter,
                    html_path=html_path,
                    asset_dir=asset_dir,
                    metrics=metrics,
                    location=f"{location}:image{tok_idx}",
                    treat_math_as_display=False,
                )
                continue
            _render_tokens_into_paragraph(
                paragraph=paragraph,
                tokens=[token],
                builder=doc_builder,
                math_converter=math_converter,
                html_path=html_path,
                asset_dir=asset_dir,
                metrics=metrics,
                location=f"{location}:token{tok_idx}",
                treat_math_as_display=False,
            )

    answer_summary = bundle.get("answer_summary", {}) if isinstance(bundle.get("answer_summary"), dict) else {}
    answer_lines = _build_answer_lines(answer_summary)
    answer_header = doc_builder.add_paragraph(style="Heading2")
    doc_builder.add_text_run(answer_header, "Teacher Answer Section")
    if answer_lines:
        for line in answer_lines:
            para = doc_builder.add_paragraph()
            doc_builder.add_text_run(para, line)
        metrics["answer_block_count"] = len(answer_lines)
    else:
        para = doc_builder.add_paragraph()
        doc_builder.add_text_run(para, "No canonical answer summary available in exam_bundle.")
        metrics["answer_block_count"] = 0
        _make_issue(
            issues,
            code="answer_summary_missing_for_teacher_export",
            severity=_severity_for(failure_policy, "answer_summary_missing_for_teacher_export", "warning"),
            message="Teacher export includes empty answer section because answer_summary.entries is missing/empty.",
            location="exam_bundle.answer_summary",
        )

    metrics["math_detected_count"] = math_converter.math_detected_count
    metrics["math_converted_count"] = math_converter.math_converted_count
    metrics["math_failed_count"] = math_converter.math_failed_count
    metrics["image_embedded_count"] = doc_builder.image_count() if metrics["image_embedded_count"] < doc_builder.image_count() else metrics["image_embedded_count"]

    if strict_math and metrics["math_failed_count"] > 0:
        _make_issue(
            issues,
            code="strict_math_failed",
            severity="blocker",
            message=f"Strict math mode enabled and {metrics['math_failed_count']} math fragment(s) failed.",
            location="math_export",
        )

    build_t1 = time.perf_counter()
    report["timings"]["build_document_ms"] = round((build_t1 - build_t0) * 1000.0, 3)

    report["policy_checks"] = _apply_failure_policy(
        report=report,
        issues=issues,
        policy=failure_policy,
    )

    _finalize_report(report, issues)

    write_t0 = time.perf_counter()
    if report["verdict"] != "blocked":
        try:
            doc_builder.write_docx(output_docx)
        except Exception as ex:  # noqa: BLE001 - report as blocker
            _make_issue(
                issues,
                code="docx_write_failed",
                severity="blocker",
                message=f"Failed to package DOCX output: {ex}",
                location=str(output_docx),
            )
            _finalize_report(report, issues)

    if report["verdict"] != "blocked":
        openability_t0 = time.perf_counter()
        report["openability"] = _check_docx_openability(
            output_docx=output_docx,
            issues=issues,
            policy=failure_policy,
            check_soffice=check_openability,
            timeout_sec=openability_timeout_sec,
        )
        openability_t1 = time.perf_counter()
        report["timings"]["openability_check_ms"] = round((openability_t1 - openability_t0) * 1000.0, 3)
        _finalize_report(report, issues)
    else:
        report["openability"] = {
            "zip_integrity_checked": False,
            "zip_integrity_passed": False,
            "zip_bad_member": "",
            "soffice_check_requested": bool(check_openability),
            "soffice_check_attempted": False,
            "soffice_check_passed": None,
            "soffice_binary_found": bool(shutil.which("soffice")),
            "soffice_binary_path": shutil.which("soffice") or "",
            "soffice_pdf_path": "",
        }
    write_t1 = time.perf_counter()
    report["timings"]["write_docx_ms"] = round((write_t1 - write_t0) * 1000.0, 3)

    report_output = Path(report_path).resolve() if report_path else output_docx.with_name("docx_export_report.json")
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_write_t0 = time.perf_counter()
    report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_write_t1 = time.perf_counter()
    report["timings"]["write_report_ms"] = round((report_write_t1 - report_write_t0) * 1000.0, 3)
    report["timings"]["total_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
    report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def export_question_pack_to_docx(
    question_bank_items_path: str | Path,
    output_docx_path: str | Path,
    mode: str = "question_pack",
    options: Optional[Dict[str, Any]] = None,
    report_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    del question_bank_items_path, options
    output_docx = Path(output_docx_path).resolve()
    report = {
        "schema_version": DOCX_EXPORT_REPORT_SCHEMA_VERSION,
        "artifact_type": "docx_export_report",
        "bundle_id": "",
        "export_mode": mode,
        "source_paths": {
            "exam_bundle_path": "",
            "html_path": "",
            "asset_dir": "",
            "docx_source_path": "",
        },
        "output_docx_path": str(output_docx),
        "verdict": "blocked",
        "metrics": {
            "question_count": 0,
            "math_detected_count": 0,
            "math_converted_count": 0,
            "math_failed_count": 0,
            "image_embedded_count": 0,
            "image_failed_count": 0,
            "answer_block_count": 0,
            "rubric_block_count": 0,
        },
        "failure_policy": _resolve_failure_policy({}),
        "policy_checks": {},
        "openability": {
            "zip_integrity_checked": False,
            "zip_integrity_passed": False,
            "zip_bad_member": "",
            "soffice_check_requested": False,
            "soffice_check_attempted": False,
            "soffice_check_passed": None,
            "soffice_binary_found": bool(shutil.which("soffice")),
            "soffice_binary_path": shutil.which("soffice") or "",
            "soffice_pdf_path": "",
        },
        "issues": [
            {
                "code": "question_pack_export_not_implemented",
                "severity": "blocker",
                "message": "Phase F prototype intentionally supports teacher_exam from exam_bundle only.",
                "exam_id": "",
                "question_id": "",
                "location": "export_question_pack_to_docx",
            }
        ],
        "warnings_count": 0,
        "blockers_count": 1,
        "timings": {},
    }
    report_output = Path(report_path).resolve() if report_path else output_docx.with_name("docx_export_report.json")
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Minimal DOCX exporter prototype (Phase F) from exam_bundle.json",
    )
    parser.add_argument("exam_bundle_path", help="Path to exam_bundle.json")
    parser.add_argument("output_docx_path", help="Path to output .docx file")
    parser.add_argument(
        "--mode",
        default="teacher_exam",
        choices=["teacher_exam", "student_exam", "question_pack", "review_copy"],
        help="Export mode (prototype supports teacher_exam only).",
    )
    parser.add_argument(
        "--report-path",
        default="",
        help="Optional path to write docx_export_report.json (default: alongside output docx).",
    )
    parser.add_argument(
        "--strict-math",
        action="store_true",
        help="Treat math conversion failures as blockers.",
    )
    parser.add_argument(
        "--check-openability",
        action="store_true",
        help="Run DOCX openability checks (zip integrity + optional soffice round-trip).",
    )
    parser.add_argument(
        "--openability-timeout-sec",
        type=int,
        default=120,
        help="Timeout for soffice openability check in seconds.",
    )
    parser.add_argument(
        "--failure-policy-json",
        default="",
        help="Optional path to JSON file overriding default DOCX export failure policy.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    failure_policy_override: Optional[Dict[str, Any]] = None
    if args.failure_policy_json:
        policy_path = Path(args.failure_policy_json).resolve()
        try:
            failure_policy_override = json.loads(policy_path.read_text(encoding="utf-8"))
        except Exception as ex:  # noqa: BLE001
            print(f"[ERROR] Failed to load failure policy JSON: {policy_path} ({ex})", file=sys.stderr)
            return 2
    report = export_exam_bundle_to_docx(
        exam_bundle_path=args.exam_bundle_path,
        output_docx_path=args.output_docx_path,
        mode=args.mode,
        options={
            "strict_math": bool(args.strict_math),
            "check_openability": bool(args.check_openability),
            "openability_timeout_sec": int(args.openability_timeout_sec),
            "failure_policy": failure_policy_override or {},
        },
        report_path=args.report_path or None,
    )
    if report.get("verdict") == "blocked":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
