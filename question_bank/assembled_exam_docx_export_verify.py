from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SCHEMA_VERSION = "assembled_exam_docx_export_acceptance.v1"
ARTIFACT_TYPE = "assembled_exam_docx_export_acceptance"

ASSEMBLY_SCHEMA_VERSION = "question_bank_exam_assembly.v1"
ASSEMBLY_ARTIFACT_TYPE = "exam_assembly"
EXPORT_REPORT_SCHEMA_VERSION = "assembled_exam_docx_export_report.v1"
EXPORT_REPORT_ARTIFACT_TYPE = "assembled_exam_docx_export_report"

WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

RE_LABEL_ANSWER = re.compile(r"(?iu)^\s*đáp\s*án\s*:\s*")
RE_LABEL_RUBRIC = re.compile(r"(?iu)^\s*rubric\s*:\s*")
RE_LABEL_PROVENANCE = re.compile(r"(?iu)^\s*provenance\s*:\s*")
RE_LABEL_RECONCILIATION = re.compile(r"(?iu)^\s*reconciliation\s*:\s*")

RE_TEXT_NA = re.compile(r"(?iu)\bn/a\b")

REQUIRED_DOCX_PARTS = [
    "[Content_Types].xml",
    "_rels/.rels",
    "word/document.xml",
    "word/_rels/document.xml.rels",
    "docProps/app.xml",
    "docProps/core.xml",
]


@dataclass
class VerifyIssue:
    code: str
    severity: str
    message: str
    location: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "location": self.location,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:  # noqa: BLE001
        return default


def _text(value: Any) -> str:
    return str(value or "").strip()


def _load_json_object(path: Path, *, expected_schema: str, expected_type: str) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    schema_version = _text(payload.get("schema_version"))
    artifact_type = _text(payload.get("artifact_type"))
    if schema_version and schema_version != expected_schema:
        raise ValueError(f"{path} has unsupported schema_version={schema_version!r} (expected {expected_schema!r})")
    if artifact_type and artifact_type != expected_type:
        raise ValueError(f"{path} has unsupported artifact_type={artifact_type!r} (expected {expected_type!r})")
    return payload


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    if ":" in tag:
        return tag.split(":", 1)[1]
    return tag


def _extract_paragraph_style(paragraph: ET.Element) -> str:
    for child in paragraph:
        if _local_name(child.tag) != "pPr":
            continue
        for ppr_child in child:
            if _local_name(ppr_child.tag) != "pStyle":
                continue
            return _text(ppr_child.get(f"{{{WORD_NS['w']}}}val") or ppr_child.get("w:val"))
    return ""


def _extract_paragraph_text(paragraph: ET.Element) -> str:
    parts: List[str] = []
    for node in paragraph.iter():
        lname = _local_name(node.tag)
        if lname == "t" and node.text:
            parts.append(node.text)
        elif lname == "br":
            parts.append("\n")
    text = "".join(parts)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _read_docx_document_xml(docx_path: Path) -> bytes:
    with zipfile.ZipFile(docx_path, "r") as zf:
        return zf.read("word/document.xml")


def _docx_zip_integrity(docx_path: Path) -> Tuple[bool, str]:
    try:
        with zipfile.ZipFile(docx_path, "r") as zf:
            bad = zf.testzip()
            return (bad is None, "" if bad is None else str(bad))
    except Exception as ex:  # noqa: BLE001
        return (False, str(ex))


def _docx_has_required_parts(docx_path: Path) -> Tuple[bool, List[str]]:
    with zipfile.ZipFile(docx_path, "r") as zf:
        names = set(zf.namelist())
    missing = [part for part in REQUIRED_DOCX_PARTS if part not in names]
    return (len(missing) == 0, missing)


def _check_soffice_openability(docx_path: Path, *, timeout_sec: int) -> Dict[str, Any]:
    def _resolve_soffice_binary() -> Optional[str]:
        direct_candidates = [
            Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
            Path("/Applications/LibreOffice.app/Contents/MacOS/soffice.bin"),
        ]
        for candidate in direct_candidates:
            if candidate.exists() and candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        wrapper = shutil.which("soffice")
        return wrapper or None

    soffice_path = _resolve_soffice_binary()
    result: Dict[str, Any] = {
        "soffice_check_attempted": False,
        "soffice_check_passed": None,
        "soffice_binary_found": bool(soffice_path),
        "soffice_binary_path": soffice_path or "",
        "soffice_pdf_path": "",
        "soffice_returncode": None,
        "soffice_error": "",
    }
    if not soffice_path:
        return result

    result["soffice_check_attempted"] = True
    with tempfile.TemporaryDirectory(prefix="assembled-docx-openability-") as tmp_dir:
        outdir = Path(tmp_dir)
        cmd = [
            soffice_path,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(outdir),
            str(docx_path),
        ]
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=max(10, int(timeout_sec)))
        except subprocess.TimeoutExpired:
            result["soffice_check_passed"] = False
            result["soffice_error"] = f"timeout after {timeout_sec}s"
            return result
        except Exception as ex:  # noqa: BLE001
            result["soffice_check_passed"] = False
            result["soffice_error"] = str(ex)
            return result

        result["soffice_returncode"] = int(completed.returncode)
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            stdout = (completed.stdout or "").strip()
            result["soffice_check_passed"] = False
            result["soffice_error"] = stderr or stdout or "unknown soffice error"
            return result

        expected_pdf = outdir / f"{docx_path.stem}.pdf"
        if expected_pdf.exists():
            result["soffice_check_passed"] = True
            result["soffice_pdf_path"] = str(expected_pdf)
        else:
            result["soffice_check_passed"] = False
            result["soffice_error"] = "soffice reported success but PDF output was not found"
    return result


def _final_verdict(issues: List[VerifyIssue]) -> Tuple[str, int, int]:
    warnings = sum(1 for issue in issues if issue.severity in {"warning", "error"})
    blockers = sum(1 for issue in issues if issue.severity == "blocker")
    if blockers > 0:
        return ("blocked", warnings, blockers)
    if warnings > 0:
        return ("needs_review", warnings, blockers)
    return ("safe_to_accept", warnings, blockers)


def verify_assembled_exam_docx_export(
    *,
    assembly_artifact_path: str | Path,
    export_report_path: str | Path,
    docx_path: str | Path,
    output_report_json: Optional[str | Path] = None,
    output_report_md: Optional[str | Path] = None,
    check_soffice: bool = False,
    soffice_timeout_sec: int = 120,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    artifact_path = Path(assembly_artifact_path).resolve()
    report_path = Path(export_report_path).resolve()
    output_docx = Path(docx_path).resolve()

    issues: List[VerifyIssue] = []
    try:
        artifact = _load_json_object(
            artifact_path,
            expected_schema=ASSEMBLY_SCHEMA_VERSION,
            expected_type=ASSEMBLY_ARTIFACT_TYPE,
        )
    except Exception as ex:  # noqa: BLE001
        artifact = {}
        issues.append(VerifyIssue(code="assembly_artifact_invalid", severity="blocker", message=str(ex), location=str(artifact_path)))

    try:
        export_report = _load_json_object(
            report_path,
            expected_schema=EXPORT_REPORT_SCHEMA_VERSION,
            expected_type=EXPORT_REPORT_ARTIFACT_TYPE,
        )
    except Exception as ex:  # noqa: BLE001
        export_report = {}
        issues.append(VerifyIssue(code="export_report_invalid", severity="blocker", message=str(ex), location=str(report_path)))

    expected_item_count = 0
    if isinstance(artifact.get("items"), list):
        expected_item_count = len(artifact.get("items", []))
    reported_item_count = _safe_int((export_report.get("metrics") or {}).get("item_count"), -1)

    mode = _text(export_report.get("mode")) or ""
    export_view = _text(export_report.get("export_view")) or ""

    zip_ok, zip_bad = _docx_zip_integrity(output_docx) if output_docx.exists() else (False, "missing file")
    if not zip_ok:
        issues.append(
            VerifyIssue(
                code="docx_zip_integrity_failed",
                severity="blocker",
                message=f"DOCX zip integrity failed: {zip_bad}",
                location=str(output_docx),
            )
        )

    parts_ok, missing_parts = (False, REQUIRED_DOCX_PARTS)
    if output_docx.exists() and zip_ok:
        try:
            parts_ok, missing_parts = _docx_has_required_parts(output_docx)
        except Exception as ex:  # noqa: BLE001
            parts_ok = False
            missing_parts = REQUIRED_DOCX_PARTS
            issues.append(
                VerifyIssue(
                    code="docx_required_parts_check_failed",
                    severity="blocker",
                    message=f"Unable to check required DOCX parts: {ex}",
                    location=str(output_docx),
                )
            )
    if not parts_ok:
        issues.append(
            VerifyIssue(
                code="docx_required_parts_missing",
                severity="blocker",
                message=f"Missing required DOCX parts: {missing_parts}",
                location=str(output_docx),
            )
        )

    document_xml: bytes = b""
    paragraphs: List[Dict[str, Any]] = []
    if output_docx.exists() and zip_ok and parts_ok:
        try:
            document_xml = _read_docx_document_xml(output_docx)
            root = ET.fromstring(document_xml)
            for p in root.iter():
                if _local_name(p.tag) != "p":
                    continue
                style = _extract_paragraph_style(p)
                text = _extract_paragraph_text(p)
                if not style and not text:
                    continue
                paragraphs.append({"style": style, "text": text})
        except Exception as ex:  # noqa: BLE001
            issues.append(
                VerifyIssue(
                    code="docx_document_xml_parse_failed",
                    severity="blocker",
                    message=f"Failed to parse word/document.xml: {ex}",
                    location=str(output_docx),
                )
            )

    observed_heading2_count = sum(1 for p in paragraphs if p.get("style") == "Heading2")

    if expected_item_count > 0 and observed_heading2_count != expected_item_count:
        issues.append(
            VerifyIssue(
                code="docx_item_count_mismatch",
                severity="blocker",
                message=f"DOCX question heading count does not match artifact item count: docx={observed_heading2_count}, artifact={expected_item_count}",
                location=str(output_docx),
            )
        )

    if reported_item_count >= 0 and expected_item_count != reported_item_count:
        issues.append(
            VerifyIssue(
                code="report_item_count_mismatch",
                severity="blocker",
                message=f"Export report item_count does not match artifact item count: report={reported_item_count}, artifact={expected_item_count}",
                location=str(report_path),
            )
        )

    label_counts = {
        "answer": 0,
        "rubric": 0,
        "provenance": 0,
        "reconciliation": 0,
        "answer_non_na": 0,
        "rubric_non_na": 0,
    }
    for p in paragraphs:
        text = _text(p.get("text"))
        if not text:
            continue
        if RE_LABEL_ANSWER.match(text):
            label_counts["answer"] += 1
            if not RE_TEXT_NA.search(text):
                label_counts["answer_non_na"] += 1
        if RE_LABEL_RUBRIC.match(text):
            label_counts["rubric"] += 1
            if not RE_TEXT_NA.search(text):
                label_counts["rubric_non_na"] += 1
        if RE_LABEL_PROVENANCE.match(text):
            label_counts["provenance"] += 1
        if RE_LABEL_RECONCILIATION.match(text):
            label_counts["reconciliation"] += 1

    shown_answer_count = _safe_int((export_report.get("metrics") or {}).get("shown_answer_count"), 0)
    shown_rubric_count = _safe_int((export_report.get("metrics") or {}).get("shown_rubric_count"), 0)

    if mode == "student":
        if label_counts["answer"] > 0 or label_counts["rubric"] > 0 or label_counts["provenance"] > 0 or label_counts["reconciliation"] > 0:
            issues.append(
                VerifyIssue(
                    code="student_mode_answer_leak",
                    severity="blocker",
                    message=(
                        "Student DOCX contains teacher-only label blocks. "
                        f"answer={label_counts['answer']} rubric={label_counts['rubric']} provenance={label_counts['provenance']} reconciliation={label_counts['reconciliation']}"
                    ),
                    location=str(output_docx),
                )
            )
    elif mode == "teacher":
        if expected_item_count > 0:
            if label_counts["answer"] != expected_item_count:
                issues.append(
                    VerifyIssue(
                        code="teacher_mode_missing_answer_blocks",
                        severity="blocker",
                        message=f"Teacher DOCX must include one answer block per item: answer_blocks={label_counts['answer']}, items={expected_item_count}",
                        location=str(output_docx),
                    )
                )
            if label_counts["rubric"] != expected_item_count:
                issues.append(
                    VerifyIssue(
                        code="teacher_mode_missing_rubric_blocks",
                        severity="blocker",
                        message=f"Teacher DOCX must include one rubric block per item: rubric_blocks={label_counts['rubric']}, items={expected_item_count}",
                        location=str(output_docx),
                    )
                )
            if label_counts["provenance"] != expected_item_count:
                issues.append(
                    VerifyIssue(
                        code="teacher_mode_missing_provenance_blocks",
                        severity="blocker",
                        message=f"Teacher DOCX must include one provenance block per item: provenance_blocks={label_counts['provenance']}, items={expected_item_count}",
                        location=str(output_docx),
                    )
                )
            if label_counts["reconciliation"] != expected_item_count:
                issues.append(
                    VerifyIssue(
                        code="teacher_mode_missing_reconciliation_blocks",
                        severity="blocker",
                        message=f"Teacher DOCX must include one reconciliation block per item: reconciliation_blocks={label_counts['reconciliation']}, items={expected_item_count}",
                        location=str(output_docx),
                    )
                )
        if shown_answer_count != label_counts["answer_non_na"]:
            issues.append(
                VerifyIssue(
                    code="teacher_mode_shown_answer_count_mismatch",
                    severity="blocker",
                    message=f"Teacher DOCX shown answer count does not match export report: docx={label_counts['answer_non_na']}, report={shown_answer_count}",
                    location=str(output_docx),
                )
            )
        if shown_rubric_count != label_counts["rubric_non_na"]:
            issues.append(
                VerifyIssue(
                    code="teacher_mode_shown_rubric_count_mismatch",
                    severity="blocker",
                    message=f"Teacher DOCX shown rubric count does not match export report: docx={label_counts['rubric_non_na']}, report={shown_rubric_count}",
                    location=str(output_docx),
                )
            )
    else:
        issues.append(
            VerifyIssue(
                code="export_mode_unknown",
                severity="blocker",
                message=f"export report mode is missing or unknown: {mode!r}",
                location=str(report_path),
            )
        )

    openability = {"soffice_check_requested": bool(check_soffice)}
    if check_soffice:
        openability.update(_check_soffice_openability(output_docx, timeout_sec=int(soffice_timeout_sec)))
        if openability.get("soffice_check_attempted") and openability.get("soffice_check_passed") is False:
            # Non-blocking in this repo unless/until soffice is stable.
            issues.append(
                VerifyIssue(
                    code="docx_openability_failed",
                    severity="warning",
                    message=f"soffice openability check failed: {openability.get('soffice_error', '')}",
                    location=str(output_docx),
                )
            )

    verdict, warnings_count, blockers_count = _final_verdict(issues)
    t1 = time.perf_counter()

    acceptance: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "created_at": _now_iso(),
        "inputs": {
            "assembly_artifact_path": str(artifact_path),
            "export_report_path": str(report_path),
            "docx_path": str(output_docx),
        },
        "export": {
            "mode": mode,
            "export_view": export_view,
            "assembly_id": _text(export_report.get("assembly_id")),
            "assembly_mode": _text(export_report.get("assembly_mode")),
            "exam": export_report.get("exam", {}),
        },
        "expected": {
            "artifact_item_count": expected_item_count,
            "report_item_count": reported_item_count,
            "report_shown_answer_count": shown_answer_count,
            "report_shown_rubric_count": shown_rubric_count,
        },
        "observed": {
            "docx_heading2_count": observed_heading2_count,
            "docx_label_counts": label_counts,
            "docx_zip_integrity_ok": zip_ok,
            "docx_zip_bad_member": zip_bad,
            "required_parts_ok": parts_ok,
            "missing_required_parts": missing_parts,
        },
        "openability": openability,
        "issues": [issue.as_dict() for issue in issues],
        "warnings_count": warnings_count,
        "blockers_count": blockers_count,
        "verdict": verdict,
        "timings": {"verify_ms": round((t1 - t0) * 1000.0, 3)},
    }

    output_json = Path(output_report_json).resolve() if output_report_json else output_docx.with_name("assembled_exam_docx_export_acceptance.json")
    output_md = Path(output_report_md).resolve() if output_report_md else output_docx.with_name("assembled_exam_docx_export_acceptance.md")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(_json(acceptance) + "\n", encoding="utf-8")
    output_md.write_text(render_acceptance_markdown(acceptance), encoding="utf-8")

    acceptance["outputs"] = {"acceptance_json": str(output_json), "acceptance_md": str(output_md)}
    return acceptance


def render_acceptance_markdown(acceptance: Dict[str, Any]) -> str:
    export = acceptance.get("export", {}) if isinstance(acceptance.get("export"), dict) else {}
    expected = acceptance.get("expected", {}) if isinstance(acceptance.get("expected"), dict) else {}
    observed = acceptance.get("observed", {}) if isinstance(acceptance.get("observed"), dict) else {}
    label_counts = observed.get("docx_label_counts", {}) if isinstance(observed.get("docx_label_counts"), dict) else {}
    lines = ["# Assembled Exam DOCX Export Acceptance", ""]
    lines.append(f"- verdict: `{acceptance.get('verdict', '')}`")
    lines.append(f"- warnings: `{acceptance.get('warnings_count', 0)}` blockers: `{acceptance.get('blockers_count', 0)}`")
    lines.append(f"- mode: `{export.get('mode', '')}` view: `{export.get('export_view', '')}`")
    lines.append("")
    lines.append("## Item Count")
    lines.append(f"- artifact_item_count: `{expected.get('artifact_item_count', '')}`")
    lines.append(f"- report_item_count: `{expected.get('report_item_count', '')}`")
    lines.append(f"- docx_heading2_count: `{observed.get('docx_heading2_count', '')}`")
    lines.append("")
    lines.append("## Labels")
    for key in ["answer", "rubric", "provenance", "reconciliation", "answer_non_na", "rubric_non_na"]:
        lines.append(f"- {key}: `{label_counts.get(key, 0)}`")
    lines.append("")
    lines.append("## Integrity")
    lines.append(f"- zip_ok: `{observed.get('docx_zip_integrity_ok', False)}`")
    lines.append(f"- required_parts_ok: `{observed.get('required_parts_ok', False)}`")
    if observed.get("missing_required_parts"):
        lines.append(f"- missing_parts: `{observed.get('missing_required_parts')}`")
    lines.append("")
    if acceptance.get("issues"):
        lines.append("## Issues")
        for issue in acceptance.get("issues", []):
            if not isinstance(issue, dict):
                continue
            lines.append(f"- `{issue.get('severity','')}` `{issue.get('code','')}`: {issue.get('message','')}")
    else:
        lines.append("## Issues")
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Verify assembled-exam DOCX export outputs and emit an acceptance report.")
    parser.add_argument("--artifact", type=Path, required=True, help="Assembled exam JSON artifact")
    parser.add_argument("--export-report", type=Path, required=True, help="assembled_exam_docx_export_report.json produced by the exporter")
    parser.add_argument("--docx", type=Path, required=True, help="Exported DOCX path")
    parser.add_argument("--output-json", type=Path, default=None, help="Acceptance report JSON output path")
    parser.add_argument("--output-md", type=Path, default=None, help="Acceptance report Markdown output path")
    parser.add_argument("--check-soffice", action="store_true", help="Attempt a soffice openability check (non-blocking warnings)")
    parser.add_argument("--soffice-timeout-sec", type=int, default=120, help="Timeout for soffice openability check")
    args = parser.parse_args(argv)

    acceptance = verify_assembled_exam_docx_export(
        assembly_artifact_path=args.artifact,
        export_report_path=args.export_report,
        docx_path=args.docx,
        output_report_json=args.output_json,
        output_report_md=args.output_md,
        check_soffice=bool(args.check_soffice),
        soffice_timeout_sec=int(args.soffice_timeout_sec),
    )
    print(json.dumps(acceptance, ensure_ascii=False, sort_keys=True))
    return 0 if acceptance.get("verdict") != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())

