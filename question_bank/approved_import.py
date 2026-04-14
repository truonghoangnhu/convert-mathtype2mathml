#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html as html_lib
import json
import hashlib
import sqlite3
import os
from urllib.parse import urlparse, urlunparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .import_boundary import SQLiteApprovedImportAdapter, create_approved_import_adapter
from .import_service import ApprovedImportService

SCHEMA_VERSION = "question_bank_approved_import.v1"
DEFAULT_APPROVED_SOURCE = "review_finalize"
DEFAULT_DB_FILENAME = "question_bank_import.sqlite"
DEFAULT_VALIDATION_REPORT_FILENAME = "question_bank_import_validation.json"
DEFAULT_IMPORT_SUMMARY_FILENAME = "question_bank_import_summary.json"
DEFAULT_IMPORT_SUMMARY_MD_FILENAME = "question_bank_import_summary.md"
DEFAULT_BATCH_SUMMARY_FILENAME = "question_bank_batch_import_summary.json"
DEFAULT_BATCH_SUMMARY_MD_FILENAME = "question_bank_batch_import_summary.md"
DEFAULT_JOB_LISTING_FILENAME = "question_bank_import_jobs.json"
DEFAULT_JOB_LISTING_MD_FILENAME = "question_bank_import_jobs.md"
DEFAULT_DASHBOARD_HTML_FILENAME = "question_bank_import_dashboard.html"

OUTPUT_CONTRACT_VERSION = "output_contract.v1"
EXPECTED_TYPES = {
    "exam_bundle": "exam_bundle",
    "question_bank_items": "question_bank_items",
}
EXPECTED_KEYS = {
    "exam_bundle": [
        "schema_version",
        "artifact_type",
        "bundle_id",
        "subject",
        "output_mode",
        "summary",
        "exams",
        "answer_summary",
        "answer_qa_summary",
        "question_item_count",
    ],
    "question_bank_items": [
        "schema_version",
        "artifact_type",
        "bundle_id",
        "subject",
        "output_mode",
        "item_count",
        "items",
    ],
}
ALLOWED_OUTPUT_MODES = {"publish"}
ALLOWED_ANSWER_MODES = {"single_choice", "boolean_group", "short_answer", "rubric", "none"}
ALLOWED_RECONCILIATION_STATUSES = {
    "resolved",
    "resolved_with_fill",
    "resolved_normalized_equivalent",
    "conflict",
    "needs_review",
    "blocked",
}

READINESS_APPROVED = "approved_importable"
READINESS_DRAFT = "draft_importable"
READINESS_BLOCKED = "blocked_import"
IMPORT_MODES = {"approved-only", "allow-draft"}

REQUIRED_ITEM_KEYS = [
    "item_id",
    "exam_id",
    "question_number",
    "question_type",
    "answer_key",
    "answer_sources",
    "reconciliation",
    "rubric",
    "qa_flags",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _load_json_object(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:  # noqa: BLE001
        return default


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _display_db_path_from_url(db_url: str) -> Path:
    try:
        parsed = urlparse(str(db_url))
    except Exception:  # noqa: BLE001
        safe = "<redacted-db-url>"
    else:
        username = parsed.username or ""
        hostname = parsed.hostname or ""
        port = parsed.port
        netloc = hostname
        if username:
            netloc = f"{username}@{hostname}"
        if port is not None:
            netloc = f"{netloc}:{port}"
        redacted = urlunparse((parsed.scheme, netloc, parsed.path or "", "", "", "")) if parsed.scheme else "<redacted-db-url>"
        safe = redacted
    safe = safe.replace("://", "__").replace("/", "__").replace("?", "__").replace("&", "__")
    return Path(f"postgresql__{safe}")


def _record(checks: List[Dict[str, Any]], code: str, ok: bool, message: str, severity: str = "error") -> None:
    checks.append({"code": code, "ok": bool(ok), "severity": severity, "message": message})


def _nested_dict(payload: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def determine_import_readiness(exam_bundle: Dict[str, Any], validation: Dict[str, Any]) -> Dict[str, Any]:
    summary = _nested_dict(exam_bundle, "summary")
    answer_qa = _nested_dict(exam_bundle, "answer_qa_summary")
    output_mode = str(exam_bundle.get("output_mode", "") or "")
    publish_verdict = str(summary.get("publish_verdict", "") or "")
    question_count = _safe_int(exam_bundle.get("question_item_count"), 0)
    validation_error_count = len(validation.get("errors", [])) if isinstance(validation.get("errors"), list) else 0
    validation_warning_count = len(validation.get("warnings", [])) if isinstance(validation.get("warnings"), list) else 0
    blocker_count = _safe_int(answer_qa.get("blocker_count"), 0)
    canonical_missing = _safe_int(answer_qa.get("canonical_answer_missing_count"), 0)
    unresolved = _safe_int(answer_qa.get("unresolved_reconciliation_count"), 0)
    conflict_count = _safe_int(answer_qa.get("conflict_count"), 0)
    issue_count = _safe_int(answer_qa.get("issue_count"), 0)
    hard_issue_count = blocker_count + canonical_missing + unresolved + conflict_count

    evidence = {
        "output_mode": output_mode,
        "publish_verdict": publish_verdict,
        "validation_error_count": validation_error_count,
        "validation_warning_count": validation_warning_count,
        "blocker_count": blocker_count,
        "canonical_answer_missing_count": canonical_missing,
        "unresolved_reconciliation_count": unresolved,
        "conflict_count": conflict_count,
        "issue_count": issue_count,
        "hard_issue_count": hard_issue_count,
        "question_count": question_count,
        "publish_summary": {
            "document_family": summary.get("document_family", ""),
            "document_family_confidence": summary.get("document_family_confidence", None),
        },
    }

    if validation_error_count > 0:
        return {
            "state": READINESS_BLOCKED,
            "reason": "validation failed; artifact is not structurally importable",
            "evidence": evidence,
            "can_import_default": False,
            "can_import_allow_draft": False,
        }

    if output_mode != "publish":
        return {
            "state": READINESS_BLOCKED,
            "reason": f"output_mode is {output_mode or '<empty>'}; final import requires publish output",
            "evidence": evidence,
            "can_import_default": False,
            "can_import_allow_draft": False,
        }

    if question_count <= 0:
        return {
            "state": READINESS_BLOCKED,
            "reason": "final bundle contains zero questions",
            "evidence": evidence,
            "can_import_default": False,
            "can_import_allow_draft": False,
        }

    if not publish_verdict:
        return {
            "state": READINESS_BLOCKED,
            "reason": "missing publish_verdict in final exam bundle",
            "evidence": evidence,
            "can_import_default": False,
            "can_import_allow_draft": False,
        }

    if publish_verdict == "blocked":
        return {
            "state": READINESS_BLOCKED,
            "reason": "final exam bundle is explicitly blocked",
            "evidence": evidence,
            "can_import_default": False,
            "can_import_allow_draft": False,
        }

    if publish_verdict == "safe_to_publish":
        if hard_issue_count == 0:
            return {
                "state": READINESS_APPROVED,
                "reason": "publish-ready and no hard QA blockers remain",
                "evidence": evidence,
                "can_import_default": True,
                "can_import_allow_draft": True,
            }
        return {
            "state": READINESS_BLOCKED,
            "reason": "publish-ready verdict conflicts with remaining hard QA blockers",
            "evidence": evidence,
            "can_import_default": False,
            "can_import_allow_draft": False,
        }

    if publish_verdict == "needs_review":
        return {
            "state": READINESS_DRAFT,
            "reason": "final artifact is structurally valid but still marked needs_review",
            "evidence": evidence,
            "can_import_default": False,
            "can_import_allow_draft": True,
        }

    return {
        "state": READINESS_BLOCKED,
        "reason": f"unrecognized publish_verdict: {publish_verdict}",
        "evidence": evidence,
        "can_import_default": False,
        "can_import_allow_draft": False,
    }


def validate_approved_artifacts(
    exam_bundle: Dict[str, Any],
    question_bank_items: Dict[str, Any],
    *,
    exam_bundle_path: Path,
    question_bank_items_path: Path,
    approved_source: str,
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    def error(code: str, message: str) -> None:
        errors.append({"code": code, "message": message})

    def warning(code: str, message: str) -> None:
        warnings.append({"code": code, "message": message})

    def check(code: str, ok: bool, message: str, severity: str = "error") -> None:
        _record(checks, code, ok, message, severity)
        if ok:
            return
        if severity == "warning":
            warning(code, message)
        else:
            error(code, message)

    bundle_id = str(exam_bundle.get("bundle_id", "") or "")
    subject = str(exam_bundle.get("subject", "") or "")
    output_mode = str(exam_bundle.get("output_mode", "") or "")
    qb_bundle_id = str(question_bank_items.get("bundle_id", "") or "")
    qb_subject = str(question_bank_items.get("subject", "") or "")
    qb_output_mode = str(question_bank_items.get("output_mode", "") or "")

    check("exam_bundle_schema_version", exam_bundle.get("schema_version") == OUTPUT_CONTRACT_VERSION, f"exam_bundle.schema_version must be {OUTPUT_CONTRACT_VERSION}")
    check("question_bank_items_schema_version", question_bank_items.get("schema_version") == OUTPUT_CONTRACT_VERSION, f"question_bank_items.schema_version must be {OUTPUT_CONTRACT_VERSION}")
    check("exam_bundle_artifact_type", exam_bundle.get("artifact_type") == EXPECTED_TYPES["exam_bundle"], f"exam_bundle.artifact_type must be {EXPECTED_TYPES['exam_bundle']}")
    check("question_bank_items_artifact_type", question_bank_items.get("artifact_type") == EXPECTED_TYPES["question_bank_items"], f"question_bank_items.artifact_type must be {EXPECTED_TYPES['question_bank_items']}")
    check("bundle_id_present", _non_empty(bundle_id), "bundle_id must be a non-empty string")
    check("subject_present", _non_empty(subject), "subject must be a non-empty string")
    check("output_mode_present", _non_empty(output_mode), "output_mode must be a non-empty string")
    check("question_bank_bundle_id_present", _non_empty(qb_bundle_id), "question_bank_items.bundle_id must be a non-empty string")
    check("question_bank_subject_present", _non_empty(qb_subject), "question_bank_items.subject must be a non-empty string")
    check("question_bank_output_mode_present", _non_empty(qb_output_mode), "question_bank_items.output_mode must be a non-empty string")
    check("bundle_id_match", bundle_id == qb_bundle_id, "bundle_id must match across approved artifacts")
    check("subject_match", subject == qb_subject, "subject must match across approved artifacts")
    check("output_mode_match", output_mode == qb_output_mode, "output_mode must match across approved artifacts")

    check("exam_bundle_required_keys", all(key in exam_bundle for key in EXPECTED_KEYS["exam_bundle"]), "exam_bundle is missing required top-level keys")
    check("question_bank_items_required_keys", all(key in question_bank_items for key in EXPECTED_KEYS["question_bank_items"]), "question_bank_items is missing required top-level keys")

    if output_mode and output_mode not in ALLOWED_OUTPUT_MODES:
        warning("output_mode_not_publish", f"output_mode is {output_mode}; importer is intended for publish artifacts")

    items = question_bank_items.get("items") if isinstance(question_bank_items.get("items"), list) else []
    exams = exam_bundle.get("exams") if isinstance(exam_bundle.get("exams"), list) else []

    exam_question_count = _safe_int(exam_bundle.get("question_item_count"), -1)
    qb_item_count = _safe_int(question_bank_items.get("item_count"), -1)
    summed_exam_questions = 0
    for idx, exam in enumerate(exams):
        if isinstance(exam, dict):
            summed_exam_questions += _safe_int(exam.get("question_count"), 0)
        else:
            error("exam_entry_invalid", f"exams[{idx}] must be an object")

    check("items_length_match", len(items) == qb_item_count, "question_bank_items.item_count must equal the number of items")
    check("exam_question_count_match", exam_question_count == len(items), "exam_bundle.question_item_count must equal the number of approved items")
    check("exam_question_total_match", summed_exam_questions == len(items), "sum of exams[].question_count must equal the number of approved items")

    item_ids: List[str] = []
    question_type_counts: Counter[str] = Counter()
    answer_mode_counts: Counter[str] = Counter()
    reconciliation_counts: Counter[str] = Counter()
    rubric_mode_counts: Counter[str] = Counter()
    unresolved_like_count = 0
    rubric_present_count = 0

    for idx, item in enumerate(items):
        prefix = f"items[{idx}]"
        if not isinstance(item, dict):
            error("item_not_object", f"{prefix} must be an object")
            continue

        for key in REQUIRED_ITEM_KEYS:
            if key not in item:
                error("item_missing_required_key", f"{prefix} missing required key '{key}'")

        item_id = str(item.get("item_id", "") or "")
        if not _non_empty(item_id):
            error("item_id_missing", f"{prefix}.item_id must be a non-empty string")
        else:
            item_ids.append(item_id)

        question_type = str(item.get("question_type", "") or "")
        if _non_empty(question_type):
            question_type_counts[question_type] += 1
        else:
            error("question_type_missing", f"{prefix}.question_type must be a non-empty string")

        answer_key = item.get("answer_key") if isinstance(item.get("answer_key"), dict) else None
        if answer_key is None:
            error("answer_key_invalid", f"{prefix}.answer_key must be an object")
            answer_mode = ""
        else:
            answer_mode = str(answer_key.get("mode", "") or "")
            answer_mode_counts[answer_mode or "<empty>"] += 1
            if not _non_empty(answer_mode):
                error("answer_key_mode_missing", f"{prefix}.answer_key.mode must be a non-empty string")
            elif answer_mode not in ALLOWED_ANSWER_MODES:
                error("answer_key_mode_invalid", f"{prefix}.answer_key.mode must be one of {sorted(ALLOWED_ANSWER_MODES)}")

        answer_sources = item.get("answer_sources") if isinstance(item.get("answer_sources"), list) else None
        if answer_sources is None:
            error("answer_sources_invalid", f"{prefix}.answer_sources must be an array")
        elif answer_mode != "none" and answer_mode and not answer_sources:
            warning("answer_sources_empty", f"{prefix} has no answer sources despite answer_key.mode={answer_mode}")

        reconciliation = item.get("reconciliation") if isinstance(item.get("reconciliation"), dict) else None
        if reconciliation is None:
            error("reconciliation_invalid", f"{prefix}.reconciliation must be an object")
            reconciliation_status = ""
        else:
            reconciliation_status = str(reconciliation.get("status", "") or "")
            if not _non_empty(reconciliation_status):
                error("reconciliation_status_missing", f"{prefix}.reconciliation.status must be a non-empty string")
            elif reconciliation_status not in ALLOWED_RECONCILIATION_STATUSES:
                error("reconciliation_status_invalid", f"{prefix}.reconciliation.status must be one of {sorted(ALLOWED_RECONCILIATION_STATUSES)}")
            reconciliation_counts[reconciliation_status or "<empty>"] += 1
            if reconciliation_status in {"conflict", "needs_review", "blocked"}:
                unresolved_like_count += 1

        rubric = item.get("rubric")
        if not isinstance(rubric, (dict, list)):
            error("rubric_invalid", f"{prefix}.rubric must be an object or array")
            rubric_mode = ""
        else:
            rubric_mode = str((rubric.get("mode", "") if isinstance(rubric, dict) else "") or "")
            rubric_mode_counts[rubric_mode or "<empty>"] += 1
            if rubric not in ({}, [], None):
                rubric_present_count += 1

        qa_flags = item.get("qa_flags")
        if not isinstance(qa_flags, list):
            error("qa_flags_invalid", f"{prefix}.qa_flags must be an array")

    if item_ids:
        check("item_id_unique", len(set(item_ids)) == len(item_ids), "question_bank_items.item_id values must be unique")
    else:
        error("item_ids_missing", "no valid item_ids found in question_bank_items.items")

    publish_verdict = str(_nested_dict(exam_bundle, "summary").get("publish_verdict", "") or "")
    if publish_verdict and publish_verdict not in {"safe_to_publish", "needs_review", "blocked"}:
        warning("publish_verdict_unexpected", f"unexpected publish_verdict value: {publish_verdict}")
    elif publish_verdict != "safe_to_publish":
        warning("publish_verdict_not_safe", f"publish_verdict is {publish_verdict or '<empty>'}; importer still accepts the final approved artifacts")

    counts = {
        "exam_question_count": exam_question_count,
        "question_bank_item_count": qb_item_count,
        "items_length": len(items),
        "exam_count": len(exams),
        "summed_exam_question_count": summed_exam_questions,
        "unique_item_count": len(set(item_ids)),
        "unresolved_like_count": unresolved_like_count,
        "rubric_present_count": rubric_present_count,
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "question_bank_approved_import_validation",
        "bundle_id": bundle_id,
        "subject": subject,
        "output_mode": output_mode,
        "approved_source": approved_source,
        "imported_at": _now_iso(),
        "paths": {
            "exam_bundle": str(exam_bundle_path),
            "question_bank_items": str(question_bank_items_path),
        },
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "bundle_id": bundle_id,
            "subject": subject,
            "approved_source": approved_source,
            "counts": counts,
            "question_type_counts": dict(question_type_counts),
            "answer_mode_counts": dict(answer_mode_counts),
            "reconciliation_status_counts": dict(reconciliation_counts),
            "rubric_mode_counts": dict(rubric_mode_counts),
        },
        "ok": not errors,
    }


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS approved_import_jobs (
            import_job_id TEXT PRIMARY KEY,
            bundle_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            approved_source TEXT NOT NULL,
            import_mode TEXT NOT NULL,
            import_readiness TEXT NOT NULL,
            import_readiness_reason TEXT NOT NULL,
            import_readiness_json TEXT NOT NULL,
            source_publish_verdict TEXT NOT NULL,
            import_decision TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            source_exam_bundle_path TEXT NOT NULL,
            source_question_bank_items_path TEXT NOT NULL,
            validation_ok INTEGER NOT NULL,
            validation_report_json TEXT NOT NULL,
            import_summary_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS approved_exam_bundles (
            bundle_id TEXT PRIMARY KEY,
            import_job_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            approved_source TEXT NOT NULL,
            import_mode TEXT NOT NULL,
            import_readiness TEXT NOT NULL,
            import_readiness_reason TEXT NOT NULL,
            import_readiness_json TEXT NOT NULL,
            source_publish_verdict TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            output_mode TEXT NOT NULL,
            question_item_count INTEGER NOT NULL,
            summary_json TEXT NOT NULL,
            answer_summary_json TEXT NOT NULL,
            answer_qa_summary_json TEXT NOT NULL,
            source_json TEXT NOT NULL,
            FOREIGN KEY(import_job_id) REFERENCES approved_import_jobs(import_job_id)
        );

        CREATE TABLE IF NOT EXISTS approved_questions (
            item_id TEXT PRIMARY KEY,
            bundle_id TEXT NOT NULL,
            import_job_id TEXT NOT NULL,
            exam_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            question_number INTEGER NOT NULL,
            question_type TEXT NOT NULL,
            placement TEXT NOT NULL,
            prompt_preview TEXT NOT NULL,
            document_family TEXT NOT NULL,
            import_mode TEXT NOT NULL,
            import_readiness TEXT NOT NULL,
            import_readiness_reason TEXT NOT NULL,
            import_readiness_json TEXT NOT NULL,
            source_publish_verdict TEXT NOT NULL,
            qa_flags_json TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            approved_source TEXT NOT NULL,
            FOREIGN KEY(bundle_id) REFERENCES approved_exam_bundles(bundle_id),
            FOREIGN KEY(import_job_id) REFERENCES approved_import_jobs(import_job_id)
        );

        CREATE TABLE IF NOT EXISTS approved_question_answers (
            item_id TEXT PRIMARY KEY,
            bundle_id TEXT NOT NULL,
            import_job_id TEXT NOT NULL,
            answer_mode TEXT NOT NULL,
            import_mode TEXT NOT NULL,
            import_readiness TEXT NOT NULL,
            import_readiness_reason TEXT NOT NULL,
            import_readiness_json TEXT NOT NULL,
            source_publish_verdict TEXT NOT NULL,
            answer_key_json TEXT NOT NULL,
            answer_sources_json TEXT NOT NULL,
            reconciliation_json TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            approved_source TEXT NOT NULL,
            FOREIGN KEY(item_id) REFERENCES approved_questions(item_id),
            FOREIGN KEY(bundle_id) REFERENCES approved_exam_bundles(bundle_id),
            FOREIGN KEY(import_job_id) REFERENCES approved_import_jobs(import_job_id)
        );

        CREATE TABLE IF NOT EXISTS approved_question_rubrics (
            item_id TEXT PRIMARY KEY,
            bundle_id TEXT NOT NULL,
            import_job_id TEXT NOT NULL,
            rubric_mode TEXT NOT NULL,
            import_mode TEXT NOT NULL,
            import_readiness TEXT NOT NULL,
            import_readiness_reason TEXT NOT NULL,
            import_readiness_json TEXT NOT NULL,
            source_publish_verdict TEXT NOT NULL,
            rubric_text TEXT NOT NULL,
            rubric_json TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            approved_source TEXT NOT NULL,
            FOREIGN KEY(item_id) REFERENCES approved_questions(item_id),
            FOREIGN KEY(bundle_id) REFERENCES approved_exam_bundles(bundle_id),
            FOREIGN KEY(import_job_id) REFERENCES approved_import_jobs(import_job_id)
        );
        """
    )

    extra_columns = {
        "approved_import_jobs": [
            ("import_mode", "TEXT"),
            ("import_readiness", "TEXT"),
            ("import_readiness_reason", "TEXT"),
            ("import_readiness_json", "TEXT"),
            ("source_publish_verdict", "TEXT"),
            ("import_decision", "TEXT"),
        ],
        "approved_exam_bundles": [
            ("import_mode", "TEXT"),
            ("import_readiness", "TEXT"),
            ("import_readiness_reason", "TEXT"),
            ("import_readiness_json", "TEXT"),
            ("source_publish_verdict", "TEXT"),
        ],
        "approved_questions": [
            ("import_mode", "TEXT"),
            ("import_readiness", "TEXT"),
            ("import_readiness_reason", "TEXT"),
            ("import_readiness_json", "TEXT"),
            ("source_publish_verdict", "TEXT"),
        ],
        "approved_question_answers": [
            ("import_mode", "TEXT"),
            ("import_readiness", "TEXT"),
            ("import_readiness_reason", "TEXT"),
            ("import_readiness_json", "TEXT"),
            ("source_publish_verdict", "TEXT"),
        ],
        "approved_question_rubrics": [
            ("import_mode", "TEXT"),
            ("import_readiness", "TEXT"),
            ("import_readiness_reason", "TEXT"),
            ("import_readiness_json", "TEXT"),
            ("source_publish_verdict", "TEXT"),
        ],
    }

    for table, columns in extra_columns.items():
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for column_name, column_type in columns:
            if column_name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}")


def _upsert(conn: sqlite3.Connection, table: str, row: Dict[str, Any], conflict_key: str) -> None:
    cols = list(row.keys())
    assignments = ", ".join([f"{col}=excluded.{col}" for col in cols if col != conflict_key])
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['?' for _ in cols])}) ON CONFLICT({conflict_key}) DO UPDATE SET {assignments}"
    conn.execute(sql, tuple(row[col] for col in cols))


def _import_job_id(bundle_id: str, approved_source: str, import_mode: str) -> str:
    seed = "|".join([bundle_id or "bundle", approved_source or DEFAULT_APPROVED_SOURCE, import_mode or "approved-only"])
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    prefix = (bundle_id or "bundle")[:12]
    return f"qbimp_{prefix}_{digest}"


def _count_non_empty_rubrics(items: List[Dict[str, Any]]) -> int:
    count = 0
    for item in items:
        rubric = item.get("rubric")
        if isinstance(rubric, dict) and rubric:
            count += 1
        elif isinstance(rubric, list) and rubric:
            count += 1
    return count


def discover_finalized_bundle_pairs(root_dir: Path) -> List[Dict[str, Path]]:
    root_dir = root_dir.resolve()
    if not root_dir.exists():
        raise FileNotFoundError(f"batch root does not exist: {root_dir}")
    if not root_dir.is_dir():
        raise NotADirectoryError(f"batch root must be a directory: {root_dir}")

    bundle_dirs: Dict[Path, Dict[str, Path]] = {}

    def register_bundle_dir(bundle_dir: Path) -> None:
        bundle_dir = bundle_dir.resolve()
        exam_bundle_path = bundle_dir / "final_exam_bundle.json"
        question_bank_items_path = bundle_dir / "final_question_bank_items.json"
        if exam_bundle_path.is_file() and question_bank_items_path.is_file():
            bundle_dirs[bundle_dir] = {
                "bundle_dir": bundle_dir,
                "exam_bundle_path": exam_bundle_path,
                "question_bank_items_path": question_bank_items_path,
            }

    register_bundle_dir(root_dir)
    for exam_bundle_path in sorted(root_dir.rglob("final_exam_bundle.json")):
        register_bundle_dir(exam_bundle_path.parent)

    return [bundle_dirs[bundle_dir] for bundle_dir in sorted(bundle_dirs)]


def _bundle_artifact_paths(bundle_dir: Path) -> Dict[str, Path]:
    bundle_dir = bundle_dir.resolve()
    return {
        "validation_report_json": bundle_dir / DEFAULT_VALIDATION_REPORT_FILENAME,
        "import_summary_json": bundle_dir / DEFAULT_IMPORT_SUMMARY_FILENAME,
        "import_summary_md": bundle_dir / DEFAULT_IMPORT_SUMMARY_MD_FILENAME,
    }


def _safe_json_parse(value: Any, default: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        return default
    try:
        return json.loads(value)
    except Exception:  # noqa: BLE001
        return default


def _escape(value: Any) -> str:
    return html_lib.escape("" if value is None else str(value), quote=True)


def render_batch_summary_md(batch_summary: Dict[str, Any]) -> str:
    lines = ["# Question Bank Batch Import Summary", ""]
    for key in ["batch_id", "batch_root", "db_path", "import_mode", "approved_source", "started_at", "finished_at"]:
        value = batch_summary.get(key, "")
        if value:
            lines.append(f"- `{key}`: `{value}`")
    lines.append(f"- `bundle_count`: `{batch_summary.get('bundle_count', 0)}`")
    lines.append(f"- `imported_count`: `{batch_summary.get('imported_count', 0)}`")
    lines.append(f"- `skipped_count`: `{batch_summary.get('skipped_count', 0)}`")
    lines.append(f"- `blocked_count`: `{batch_summary.get('blocked_count', 0)}`")
    lines.append(f"- `error_count`: `{batch_summary.get('error_count', 0)}`")
    if batch_summary.get("decision_counts"):
        lines.append("")
        lines.append("## Decision Counts")
        for key, value in sorted((batch_summary.get("decision_counts") or {}).items()):
            lines.append(f"- `{key}`: `{value}`")
    if batch_summary.get("readiness_counts"):
        lines.append("")
        lines.append("## Readiness Counts")
        for key, value in sorted((batch_summary.get("readiness_counts") or {}).items()):
            lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## Bundles")
    lines.append("| bundle_id | subject | import_mode | import_readiness | source_publish_verdict | decision | imported_at |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for bundle in batch_summary.get("bundles", []):
        lines.append(
            "| {bundle_id} | {subject} | {import_mode} | {import_readiness} | {source_publish_verdict} | {decision} | {imported_at} |".format(
                bundle_id=str(bundle.get("bundle_id", "")),
                subject=str(bundle.get("subject", "")),
                import_mode=str(bundle.get("import_mode", "")),
                import_readiness=str(bundle.get("import_readiness", "")),
                source_publish_verdict=str(bundle.get("source_publish_verdict", "")),
                decision=str(bundle.get("decision", "")),
                imported_at=str(bundle.get("imported_at", "")),
            )
        )
    if batch_summary.get("warnings"):
        lines.append("")
        lines.append("## Warnings")
        for warning in batch_summary.get("warnings", []):
            if isinstance(warning, dict):
                lines.append(f"- `{warning.get('code', '')}`: {warning.get('message', '')}")
            else:
                lines.append(f"- {warning}")
    if batch_summary.get("errors"):
        lines.append("")
        lines.append("## Errors")
        for error in batch_summary.get("errors", []):
            if isinstance(error, dict):
                lines.append(f"- `{error.get('code', '')}`: {error.get('message', '')}")
            else:
                lines.append(f"- {error}")
    return "\n".join(lines) + "\n"


def render_import_job_listing_md(job_listing: Dict[str, Any]) -> str:
    lines = ["# Question Bank Import Jobs", ""]
    for key in ["db_path", "bundle_id_filter", "limit", "order", "job_count"]:
        value = job_listing.get(key, "")
        if value not in ("", None):
            lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("| import_job_id | bundle_id | subject | import_mode | import_readiness | source_publish_verdict | decision | imported_at |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for job in job_listing.get("jobs", []):
        lines.append(
            "| {import_job_id} | {bundle_id} | {subject} | {import_mode} | {import_readiness} | {source_publish_verdict} | {decision} | {imported_at} |".format(
                import_job_id=str(job.get("import_job_id", "")),
                bundle_id=str(job.get("bundle_id", "")),
                subject=str(job.get("subject", "")),
                import_mode=str(job.get("import_mode", "")),
                import_readiness=str(job.get("import_readiness", "")),
                source_publish_verdict=str(job.get("source_publish_verdict", "")),
                decision=str(job.get("decision", "")),
                imported_at=str(job.get("imported_at", "")),
            )
        )
    if job_listing.get("warnings"):
        lines.append("")
        lines.append("## Warnings")
        for warning in job_listing.get("warnings", []):
            if isinstance(warning, dict):
                lines.append(f"- `{warning.get('code', '')}`: {warning.get('message', '')}")
            else:
                lines.append(f"- {warning}")
    if job_listing.get("errors"):
        lines.append("")
        lines.append("## Errors")
        for error in job_listing.get("errors", []):
            if isinstance(error, dict):
                lines.append(f"- `{error.get('code', '')}`: {error.get('message', '')}")
            else:
                lines.append(f"- {error}")
    return "\n".join(lines) + "\n"


def discover_latest_batch_summary(search_root: Path) -> Optional[Path]:
    search_root = search_root.resolve()
    if not search_root.exists() or not search_root.is_dir():
        return None
    candidates = []
    for pattern in ("question_bank_batch_import_summary*.json",):
        candidates.extend([path for path in search_root.rglob(pattern) if path.is_file()])
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime, str(path)))


def load_batch_summary(batch_summary_path: Path) -> Dict[str, Any]:
    payload = _load_json_object(batch_summary_path)
    if payload.get("artifact_type") == "question_bank_batch_import_summary":
        payload.setdefault("batch_kind", "import")
        return payload
    if "files" in payload and "batch_name" in payload and "generated_at" in payload:
        files = payload.get("files") if isinstance(payload.get("files"), list) else []
        bundles: List[Dict[str, Any]] = []
        imported_count = 0
        skipped_count = 0
        blocked_count = 0
        error_count = 0
        for file_entry in files:
            if not isinstance(file_entry, dict):
                continue
            source_relative = str(file_entry.get("source_relative", "") or "")
            contract_manifest_relative = str(file_entry.get("contract_manifest_relative", "") or "")
            bundle_id = ""
            if contract_manifest_relative:
                bundle_id = Path(contract_manifest_relative).parent.name
            if not bundle_id and source_relative:
                bundle_id = Path(source_relative).stem
            subject = str(file_entry.get("subject", "") or "")
            question_count = _safe_int(file_entry.get("question_count"), 0)
            operational_verdict = str(file_entry.get("operational_publish_verdict", "") or "")
            operational_reason = str(file_entry.get("operational_publish_reason", "") or "")
            status = str(file_entry.get("status", "") or "")
            if status != "ok":
                error_count += 1
            if operational_verdict == "blocked" or question_count <= 0:
                blocked_count += 1
                readiness = READINESS_BLOCKED
                decision = "blocked"
            else:
                readiness = READINESS_DRAFT if operational_verdict == "safe_to_publish" else "operational_ready"
                decision = operational_verdict or "ready"
                if operational_verdict == "safe_to_publish":
                    imported_count += 1
                else:
                    skipped_count += 1
            bundles.append(
                {
                    "bundle_id": bundle_id,
                    "subject": subject,
                    "import_mode": str(payload.get("output_mode", "") or ""),
                    "import_readiness": readiness,
                    "source_publish_verdict": operational_verdict,
                    "decision": decision,
                    "imported_at": str(payload.get("generated_at", "") or ""),
                    "question_count": question_count,
                    "operational_publish_reason": operational_reason,
                    "status": status,
                }
            )
        return {
            "schema_version": "question_bank_operational_batch_summary.v1",
            "artifact_type": "question_bank_operational_batch_summary",
            "batch_kind": "operational",
            "batch_id": str(payload.get("batch_name", "") or ""),
            "batch_root": str(payload.get("output_dir", "") or ""),
            "import_mode": str(payload.get("output_mode", "") or ""),
            "approved_source": "parse_batch",
            "started_at": "",
            "finished_at": str(payload.get("generated_at", "") or ""),
            "bundle_count": len(bundles),
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "blocked_count": blocked_count,
            "error_count": error_count,
            "decision_counts": Counter(bundle.get("decision", "") for bundle in bundles),
            "readiness_counts": Counter(bundle.get("import_readiness", "") for bundle in bundles),
            "bundles": bundles,
            "warnings": [],
            "errors": [],
        }
    raise ValueError(f"{batch_summary_path} is not a batch import summary")


def _dashboard_cards(job_listing: Dict[str, Any], batch_summary: Optional[Dict[str, Any]], latest_batch_path: Optional[Path]) -> str:
    readiness_counts = Counter(str(job.get("import_readiness", "")) or "<empty>" for job in job_listing.get("jobs", []))
    pieces = [
        ("DB Jobs", job_listing.get("job_count", 0)),
        ("Approved", readiness_counts.get(READINESS_APPROVED, 0)),
        ("Draft", readiness_counts.get(READINESS_DRAFT, 0)),
        ("Blocked", readiness_counts.get(READINESS_BLOCKED, 0)),
    ]
    if batch_summary:
        pieces.extend(
            [
                ("Batch bundles", batch_summary.get("bundle_count", 0)),
                ("Imported", batch_summary.get("imported_count", 0)),
                ("Skipped", batch_summary.get("skipped_count", 0)),
                ("Batch blocked", batch_summary.get("blocked_count", 0)),
            ]
        )
    cards = []
    for label, value in pieces:
        cards.append(
            f"<div class='card'><div class='card-label'>{_escape(label)}</div><div class='card-value'>{_escape(value)}</div></div>"
        )
    latest_source = _escape(str(latest_batch_path) if latest_batch_path else "not found")
    cards.append(
        f"<div class='card card-wide'><div class='card-label'>Latest batch summary</div><div class='card-value card-path'>{latest_source}</div></div>"
    )
    return "".join(cards)


def _render_bundle_rows(bundles: List[Dict[str, Any]]) -> str:
    rows: List[str] = []
    for bundle in sorted(bundles, key=lambda item: str(item.get("imported_at", "")), reverse=True):
        readiness = str(bundle.get("import_readiness", ""))
        rows.append(
            "<tr data-readiness='{readiness}' data-subject='{subject}' data-bundle='{bundle_id}'>"
            "<td>{bundle_id}</td><td>{subject}</td><td>{import_mode}</td><td>{import_readiness}</td>"
            "<td>{source_publish_verdict}</td><td>{decision}</td><td>{imported_at}</td></tr>".format(
                readiness=_escape(readiness),
                subject=_escape(bundle.get("subject", "")),
                bundle_id=_escape(bundle.get("bundle_id", "")),
                import_mode=_escape(bundle.get("import_mode", "")),
                import_readiness=_escape(readiness),
                source_publish_verdict=_escape(bundle.get("source_publish_verdict", "")),
                decision=_escape(bundle.get("decision", "")),
                imported_at=_escape(bundle.get("imported_at", "")),
            )
        )
    return "\n".join(rows)


def _render_jobs_rows(jobs: List[Dict[str, Any]]) -> str:
    rows: List[str] = []
    for job in jobs:
        readiness = str(job.get("import_readiness", ""))
        rows.append(
            "<tr data-readiness='{readiness}' data-subject='{subject}' data-bundle='{bundle_id}'>"
            "<td>{bundle_id}</td><td>{subject}</td><td>{import_mode}</td><td>{import_readiness}</td>"
            "<td>{import_decision}</td><td>{source_publish_verdict}</td><td>{imported_at}</td></tr>".format(
                readiness=_escape(readiness),
                subject=_escape(job.get("subject", "")),
                bundle_id=_escape(job.get("bundle_id", "")),
                import_mode=_escape(job.get("import_mode", "")),
                import_readiness=_escape(readiness),
                import_decision=_escape(job.get("decision", job.get("import_decision", ""))),
                source_publish_verdict=_escape(job.get("source_publish_verdict", "")),
                imported_at=_escape(job.get("imported_at", "")),
            )
        )
    return "\n".join(rows)


def render_import_dashboard_html(
    *,
    db_path: Path,
    job_listing: Dict[str, Any],
    batch_summary: Optional[Dict[str, Any]] = None,
    batch_summary_path: Optional[Path] = None,
    title: str = "Question Bank Import Dashboard",
) -> str:
    latest_batch_title = "Latest Batch Summary"
    batch_rows = ""
    batch_meta = "<div class='empty'>No batch summary found.</div>"
    if batch_summary:
        if batch_summary.get("batch_kind") == "operational":
            latest_batch_title = "Operational Batch Summary"
        bundles = list(batch_summary.get("bundles", [])) if isinstance(batch_summary.get("bundles"), list) else []
        batch_rows = _render_bundle_rows(bundles)
        batch_meta = (
            "<div class='meta-grid'>"
            f"<div><span class='meta-label'>Batch ID</span><span class='meta-value'>{_escape(batch_summary.get('batch_id', ''))}</span></div>"
            f"<div><span class='meta-label'>Batch root</span><span class='meta-value'>{_escape(batch_summary.get('batch_root', ''))}</span></div>"
            f"<div><span class='meta-label'>Import mode</span><span class='meta-value'>{_escape(batch_summary.get('import_mode', ''))}</span></div>"
            f"<div><span class='meta-label'>Approved source</span><span class='meta-value'>{_escape(batch_summary.get('approved_source', ''))}</span></div>"
            f"<div><span class='meta-label'>Started at</span><span class='meta-value'>{_escape(batch_summary.get('started_at', ''))}</span></div>"
            f"<div><span class='meta-label'>Finished at</span><span class='meta-value'>{_escape(batch_summary.get('finished_at', ''))}</span></div>"
            "</div>"
            "<div class='summary-strip'>"
            f"<span class='pill'>Bundles: {_escape(batch_summary.get('bundle_count', 0))}</span>"
            f"<span class='pill'>Imported: {_escape(batch_summary.get('imported_count', 0))}</span>"
            f"<span class='pill'>Skipped: {_escape(batch_summary.get('skipped_count', 0))}</span>"
            f"<span class='pill'>Blocked: {_escape(batch_summary.get('blocked_count', 0))}</span>"
            f"<span class='pill'>Errors: {_escape(batch_summary.get('error_count', 0))}</span>"
            "</div>"
        )
    latest_batch_path_text = _escape(str(batch_summary_path) if batch_summary_path else "not found")
    readiness_controls = "".join(
        f"<button class='filter-btn' data-readiness-filter='{value}'>{label}</button>"
        for value, label in [
            ("all", "All"),
            (READINESS_APPROVED, "Approved"),
            (READINESS_DRAFT, "Draft"),
            (READINESS_BLOCKED, "Blocked"),
        ]
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape(title)}</title>
  <style>
    :root {{
      --bg: #0f172a;
      --panel: #111827;
      --panel-2: #1f2937;
      --text: #e5e7eb;
      --muted: #94a3b8;
      --line: #334155;
      --accent: #38bdf8;
      --good: #22c55e;
      --warn: #f59e0b;
      --bad: #ef4444;
    }}
    body {{
      margin: 0;
      background: linear-gradient(180deg, #0b1120 0%, #111827 100%);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .wrap {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1, h2, h3 {{
      margin: 0 0 12px 0;
      font-weight: 700;
    }}
    p, .meta-value, th, td, button, input {{
      font-size: 14px;
    }}
    .subtle {{
      color: var(--muted);
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin: 20px 0 24px;
    }}
    .card {{
      background: rgba(17, 24, 39, 0.9);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px 16px;
    }}
    .card-wide {{
      grid-column: span 2;
    }}
    .card-label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .08em;
      margin-bottom: 8px;
    }}
    .card-value {{
      font-size: 22px;
      font-weight: 700;
      word-break: break-word;
    }}
    .card-path {{
      font-size: 14px;
      line-height: 1.4;
      font-weight: 500;
    }}
    .panel {{
      background: rgba(15, 23, 42, 0.88);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      margin-bottom: 18px;
      overflow: hidden;
    }}
    .panel-header {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-bottom: 10px;
    }}
    .meta-grid > div {{
      background: rgba(17, 24, 39, 0.7);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px 12px;
    }}
    .meta-label {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      margin-bottom: 4px;
    }}
    .meta-value {{
      word-break: break-word;
    }}
    .summary-strip {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 12px 0 4px;
    }}
    .pill {{
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.35);
      color: #bfdbfe;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
    }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    .filter-btn {{
      border: 1px solid var(--line);
      background: var(--panel-2);
      color: var(--text);
      border-radius: 999px;
      padding: 7px 12px;
      cursor: pointer;
    }}
    .filter-btn.active {{
      background: var(--accent);
      color: #04111f;
      border-color: transparent;
      font-weight: 700;
    }}
    .search {{
      min-width: 240px;
      background: #0b1220;
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 8px 10px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
    }}
    th, td {{
      padding: 10px 10px;
      border-bottom: 1px solid rgba(51, 65, 85, 0.8);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      color: #cbd5e1;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .06em;
    }}
    tbody tr:hover {{
      background: rgba(30, 41, 59, 0.65);
    }}
    .empty {{
      padding: 14px 0;
      color: var(--muted);
    }}
    .section-title {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .badge {{
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 12px;
      border: 1px solid var(--line);
      color: var(--muted);
    }}
    @media (max-width: 760px) {{
      .card-wide {{
        grid-column: span 1;
      }}
      .panel-header {{
        align-items: stretch;
      }}
      .search {{
        width: 100%;
        min-width: 0;
      }}
      table, thead, tbody, th, td, tr {{
        display: block;
      }}
      thead {{
        display: none;
      }}
      tbody tr {{
        margin-bottom: 12px;
        border: 1px solid var(--line);
        border-radius: 12px;
        overflow: hidden;
      }}
      td {{
        border-bottom: 1px solid rgba(51, 65, 85, 0.5);
      }}
      td::before {{
        content: attr(data-label) ": ";
        color: var(--muted);
        font-weight: 700;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>{_escape(title)}</h1>
    <div class="subtle">Read-only view of the approved-import SQLite boundary.</div>
    <div class="cards">
      {_dashboard_cards(job_listing, batch_summary, batch_summary_path)}
    </div>

    <div class="panel">
      <div class="panel-header">
        <div class="section-title">
          <h2>Filters</h2>
          <span class="badge">approval state</span>
        </div>
        <div class="controls">
          {readiness_controls}
          <input id="search" class="search" type="search" placeholder="Search bundle_id or subject" />
        </div>
      </div>
      <div class="subtle">Filters apply to both the batch summary table and the import-job table.</div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <div class="section-title">
          <h2>{_escape(latest_batch_title)}</h2>
          <span class="badge">{latest_batch_path_text}</span>
        </div>
      </div>
      {batch_meta}
      <div style="overflow:auto;">
        <table>
          <thead>
            <tr>
              <th>bundle_id</th>
              <th>subject</th>
              <th>import_mode</th>
              <th>import_readiness</th>
              <th>source_publish_verdict</th>
              <th>decision</th>
              <th>imported_at</th>
            </tr>
          </thead>
          <tbody id="batch-rows">
            {batch_rows or '<tr><td colspan="7" class="empty">No batch summary rows available.</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <div class="section-title">
          <h2>Import Jobs</h2>
          <span class="badge">{_escape(job_listing.get('job_count', 0))} rows</span>
        </div>
      </div>
      <div style="overflow:auto;">
        <table>
          <thead>
            <tr>
              <th>bundle_id</th>
              <th>subject</th>
              <th>import_mode</th>
              <th>import_readiness</th>
              <th>import_decision</th>
              <th>source_publish_verdict</th>
              <th>imported_at</th>
            </tr>
          </thead>
          <tbody id="job-rows">
            {_render_jobs_rows(job_listing.get('jobs', [])) or '<tr><td colspan="7" class="empty">No import jobs in SQLite yet.</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    const filterButtons = Array.from(document.querySelectorAll('[data-readiness-filter]'));
    const searchInput = document.getElementById('search');
    let activeReadiness = 'all';

    function matchesFilter(row) {{
      const readiness = row.getAttribute('data-readiness') || '';
      const subject = (row.getAttribute('data-subject') || '').toLowerCase();
      const bundle = (row.getAttribute('data-bundle') || '').toLowerCase();
      const query = (searchInput.value || '').trim().toLowerCase();
      const readinessOk = activeReadiness === 'all' || readiness === activeReadiness;
      const searchOk = !query || subject.includes(query) || bundle.includes(query);
      return readinessOk && searchOk;
    }}

    function applyFilters() {{
      document.querySelectorAll('#batch-rows tr, #job-rows tr').forEach((row) => {{
        row.style.display = matchesFilter(row) ? '' : 'none';
      }});
    }}

    filterButtons.forEach((button) => {{
      button.addEventListener('click', () => {{
        activeReadiness = button.getAttribute('data-readiness-filter') || 'all';
        filterButtons.forEach((btn) => btn.classList.toggle('active', btn === button));
        applyFilters();
      }});
    }});

    searchInput.addEventListener('input', applyFilters);
    const defaultButton = filterButtons.find((button) => (button.getAttribute('data-readiness-filter') || '') === 'all');
    if (defaultButton) {{
      defaultButton.classList.add('active');
    }}
    applyFilters();
  </script>
</body>
</html>
"""
    return html


def write_import_dashboard(
    db_path: Path,
    output_html_path: Path,
    *,
    db_url: Optional[str] = None,
    batch_summary_json_path: Optional[Path] = None,
    batch_root: Optional[Path] = None,
    title: str = "Question Bank Import Dashboard",
    job_limit: Optional[int] = None,
) -> Dict[str, Any]:
    db_path = db_path.resolve()
    output_html_path = output_html_path.resolve()
    if batch_summary_json_path:
        batch_summary = load_batch_summary(batch_summary_json_path.resolve())
        discovered_path = batch_summary_json_path.resolve()
    else:
        if db_url and batch_root is None:
            discovered_path = None
            batch_summary = None
        else:
            search_root = (batch_root or db_path.parent).resolve()
            discovered_path = discover_latest_batch_summary(search_root)
            batch_summary = load_batch_summary(discovered_path) if discovered_path else None
    job_listing = list_import_jobs(db_path, db_url=db_url, limit=job_limit, order="desc")
    html_text = render_import_dashboard_html(
        db_path=db_path,
        job_listing=job_listing,
        batch_summary=batch_summary,
        batch_summary_path=discovered_path,
        title=title,
    )
    output_html_path.parent.mkdir(parents=True, exist_ok=True)
    output_html_path.write_text(html_text, encoding="utf-8")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "question_bank_import_dashboard",
        "db_path": str(db_path),
        "output_html_path": str(output_html_path),
        "batch_summary_path": str(discovered_path) if discovered_path else "",
        "job_count": job_listing.get("job_count", 0),
        "ok": True,
    }


def list_import_jobs(
    db_path: Path,
    *,
    db_url: Optional[str] = None,
    bundle_id: Optional[str] = None,
    limit: Optional[int] = None,
    order: str = "desc",
) -> Dict[str, Any]:
    adapter = create_approved_import_adapter(db_path, db_url=db_url)
    try:
        return adapter.list_jobs(bundle_id=bundle_id, limit=limit, order=order)
    finally:
        adapter.close()


def batch_import_approved_artifacts(
    batch_root: Path,
    db_path: Path,
    *,
    db_url: Optional[str] = None,
    import_mode: str = "approved-only",
    approved_source: str = DEFAULT_APPROVED_SOURCE,
    imported_at: Optional[str] = None,
    report_json_path: Optional[Path] = None,
    summary_json_path: Optional[Path] = None,
    summary_md_path: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    batch_root = batch_root.resolve()
    imported_at = imported_at or _now_iso()
    batch_id = f"batch_{batch_root.name}_{imported_at.replace(':', '').replace('-', '').replace('T', '_').replace('Z', '')}"
    discovered = discover_finalized_bundle_pairs(batch_root)
    batch_started_at = _now_iso()
    warnings: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    bundle_records: List[Dict[str, Any]] = []
    decision_counts: Counter[str] = Counter()
    readiness_counts: Counter[str] = Counter()

    if not discovered:
        errors.append({"code": "no_finalized_bundles_found", "message": f"no finalized bundle pairs found under {batch_root}"})
    else:
        # Safety-only visibility: item_id collisions across bundles will silently overwrite rows in the
        # current SQLite boundary (approved_questions primary key is item_id). We do not change import
        # semantics here; we only surface a deterministic warning so operators can namespace item_id
        # values before import when importing multiple bundles into one DB.
        try:
            item_to_bundles: Dict[str, List[str]] = {}
            for pair in discovered:
                bundle_dir = Path(pair.get("bundle_dir"))
                qb_path = Path(pair.get("question_bank_items_path"))
                qb = _load_json_object(qb_path)
                items = qb.get("items") if isinstance(qb.get("items"), list) else []
                bundle_name = bundle_dir.name
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    item_id = str(it.get("item_id", "") or "").strip()
                    if not item_id:
                        continue
                    item_to_bundles.setdefault(item_id, [])
                    if bundle_name not in item_to_bundles[item_id]:
                        item_to_bundles[item_id].append(bundle_name)

            collisions = {k: v for k, v in item_to_bundles.items() if len(v) > 1}
            if collisions:
                examples = []
                for item_id in sorted(collisions)[:10]:
                    examples.append({"item_id": item_id, "bundle_names": sorted(collisions[item_id])})
                warnings.append(
                    {
                        "code": "item_id_collision_across_bundles",
                        "message": "Detected duplicate item_id values across bundles in this batch; without pre-import namespacing, later bundles will overwrite earlier bundles in the SQLite boundary DB.",
                        "details": {
                            "collision_item_id_count": len(collisions),
                            "example_collisions": examples,
                            "recommended_policy": "Namespace item_id before batch import, e.g. '{bundle_name}::{item_id}' or '{bundle_id}::{item_id}'.",
                        },
                    }
                )
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                {
                    "code": "item_id_collision_scan_failed",
                    "message": "Failed to scan batch for item_id collisions; import will proceed, but collision safety is unknown.",
                    "details": {"error": str(exc)},
                }
            )

    db_path = db_path.resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    for bundle_pair in discovered:
        bundle_dir = bundle_pair["bundle_dir"]
        bundle_outputs = _bundle_artifact_paths(bundle_dir)
        record: Dict[str, Any] = {
            "bundle_dir": str(bundle_dir),
            "exam_bundle_path": str(bundle_pair["exam_bundle_path"]),
            "question_bank_items_path": str(bundle_pair["question_bank_items_path"]),
            "report_json_path": str(bundle_outputs["validation_report_json"]),
            "summary_json_path": str(bundle_outputs["import_summary_json"]),
            "summary_md_path": str(bundle_outputs["import_summary_md"]),
        }
        try:
            result = import_approved_artifacts(
                bundle_pair["exam_bundle_path"],
                bundle_pair["question_bank_items_path"],
                db_path,
                db_url=db_url,
                import_mode=import_mode,
                approved_source=approved_source,
                imported_at=None,
                report_json_path=bundle_outputs["validation_report_json"],
                summary_json_path=bundle_outputs["import_summary_json"],
                summary_md_path=bundle_outputs["import_summary_md"],
                dry_run=dry_run,
            )
            validation = result["validation"]
            summary = result["summary"]
            bundle_record = {
                **record,
                "bundle_id": summary.get("bundle_id", validation.get("bundle_id", "")),
                "subject": summary.get("subject", validation.get("subject", "")),
                "import_mode": summary.get("import_mode", import_mode),
                "import_readiness": summary.get("import_readiness", {}).get("state", ""),
                "source_publish_verdict": summary.get("source_publish_verdict", ""),
                "decision": summary.get("import_decision", ""),
                "imported_at": summary.get("imported_at", ""),
                "imported": bool(result.get("imported", False)),
                "validation_ok": bool(validation.get("ok", False)),
                "validation_error_count": len(validation.get("errors", [])),
                "validation_warning_count": len(validation.get("warnings", [])),
                "error_count": 0,
                "warning_count": len(validation.get("warnings", [])),
            }
        except Exception as exc:  # noqa: BLE001
            errors.append(
                {
                    "code": "bundle_import_failed",
                    "message": str(exc),
                    "bundle_dir": str(bundle_dir),
                }
            )
            bundle_record = {
                **record,
                "bundle_id": "",
                "subject": "",
                "import_mode": import_mode,
                "import_readiness": READINESS_BLOCKED,
                "source_publish_verdict": "",
                "decision": "error",
                "imported_at": imported_at,
                "imported": False,
                "validation_ok": False,
                "validation_error_count": 1,
                "validation_warning_count": 0,
                "error_count": 1,
                "warning_count": 0,
            }

        decision = str(bundle_record.get("decision", "") or "")
        import_readiness = str(bundle_record.get("import_readiness", "") or "")
        decision_counts[decision or "<empty>"] += 1
        readiness_counts[import_readiness or "<empty>"] += 1
        bundle_records.append(bundle_record)

    finished_at = _now_iso()
    imported_count = sum(1 for record in bundle_records if record.get("imported"))
    skipped_count = sum(1 for record in bundle_records if record.get("decision") in {"skipped_by_mode", "dry_run"})
    blocked_count = sum(1 for record in bundle_records if record.get("decision") == "blocked")
    error_count = sum(1 for record in bundle_records if record.get("decision") == "error")
    batch_summary: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "question_bank_batch_import_summary",
        "batch_id": batch_id,
        "batch_root": str(batch_root),
        "db_path": str(db_path),
        "import_mode": import_mode,
        "approved_source": approved_source,
        "started_at": batch_started_at,
        "finished_at": finished_at,
        "bundle_count": len(bundle_records),
        "imported_count": imported_count,
        "skipped_count": skipped_count,
        "blocked_count": blocked_count,
        "error_count": error_count + len(errors),
        "decision_counts": dict(decision_counts),
        "readiness_counts": dict(readiness_counts),
        "bundles": bundle_records,
        "warnings": warnings,
        "errors": errors,
        "ok": not errors and len(bundle_records) > 0,
    }

    if report_json_path:
        report_json_path = report_json_path.resolve()
        report_json_path.parent.mkdir(parents=True, exist_ok=True)
        report_json_path.write_text(_json(batch_summary) + "\n", encoding="utf-8")
    if summary_json_path:
        summary_json_path = summary_json_path.resolve()
        summary_json_path.parent.mkdir(parents=True, exist_ok=True)
        summary_json_path.write_text(_json(batch_summary) + "\n", encoding="utf-8")
    if summary_md_path:
        summary_md_path = summary_md_path.resolve()
        summary_md_path.parent.mkdir(parents=True, exist_ok=True)
        summary_md_path.write_text(render_batch_summary_md(batch_summary), encoding="utf-8")

    return batch_summary


def import_approved_artifacts(
    exam_bundle_path: Path,
    question_bank_items_path: Path,
    db_path: Path,
    *,
    db_url: Optional[str] = None,
    import_mode: str = "approved-only",
    approved_source: str = DEFAULT_APPROVED_SOURCE,
    imported_at: Optional[str] = None,
    report_json_path: Optional[Path] = None,
    summary_json_path: Optional[Path] = None,
    summary_md_path: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    if import_mode not in IMPORT_MODES:
        raise ValueError(f"import_mode must be one of {sorted(IMPORT_MODES)}")

    imported_at = imported_at or _now_iso()
    exam_bundle = _load_json_object(exam_bundle_path)
    question_bank_items = _load_json_object(question_bank_items_path)
    validation = validate_approved_artifacts(
        exam_bundle,
        question_bank_items,
        exam_bundle_path=exam_bundle_path,
        question_bank_items_path=question_bank_items_path,
        approved_source=approved_source,
    )
    readiness = determine_import_readiness(exam_bundle, validation)
    import_allowed = bool(readiness["can_import_default"] if import_mode == "approved-only" else readiness["can_import_allow_draft"])
    if dry_run:
        import_decision = "dry_run"
    elif not validation.get("ok", False):
        import_decision = "blocked"
    elif readiness["state"] == READINESS_DRAFT and import_mode != "allow-draft":
        import_decision = "skipped_by_mode"
    elif readiness["state"] == READINESS_BLOCKED:
        import_decision = "blocked"
    elif import_allowed:
        import_decision = "imported"
    else:
        import_decision = "blocked"

    validation["import_policy"] = {
        "mode": import_mode,
        "default_mode": "approved-only",
        "allow_draft": import_mode == "allow-draft",
    }
    validation["import_readiness"] = readiness
    validation["import_allowed"] = import_allowed
    validation["import_decision"] = import_decision

    db_path = db_path.resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    import_job_id = _import_job_id(str(validation.get("bundle_id", "")), approved_source, import_mode)

    items = question_bank_items.get("items") if isinstance(question_bank_items.get("items"), list) else []

    summary: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "question_bank_approved_import_summary",
        "bundle_id": validation.get("bundle_id", ""),
        "subject": validation.get("subject", ""),
        "approved_source": approved_source,
        "import_mode": import_mode,
        "import_readiness": readiness,
        "import_allowed": import_allowed,
        "import_decision": import_decision,
        "source_publish_verdict": readiness["evidence"]["publish_verdict"],
        "imported_at": imported_at,
        "import_job_id": import_job_id,
        "db_path": str(db_path),
        "validation_ok": bool(validation.get("ok", False)),
        "validation_error_count": len(validation.get("errors", [])),
        "validation_warning_count": len(validation.get("warnings", [])),
        "warnings": list(validation.get("warnings", [])),
        "errors": list(validation.get("errors", [])),
        "import_boundary": {
            "adapter": "PostgresApprovedImportAdapter" if db_url else "SQLiteApprovedImportAdapter",
            "validation_first": True,
            "dry_run": dry_run,
            "mode": import_mode,
            "approved_source": approved_source,
        },
        "table_counts": {
            "approved_import_jobs": 0,
            "approved_exam_bundles": 0,
            "approved_questions": 0,
            "approved_question_answers": 0,
            "approved_question_rubrics": 0,
        },
        "status_breakdown": {},
        "metrics": {
            "question_count": len(items),
            "non_empty_rubric_count": _count_non_empty_rubrics(items),
            "answer_source_total": sum(len(item.get("answer_sources", [])) for item in items if isinstance(item, dict)),
        },
        "validation_report_path": str(report_json_path) if report_json_path else "",
    }

    if report_json_path:
        report_json_path.parent.mkdir(parents=True, exist_ok=True)
        report_json_path.write_text(_json(validation) + "\n", encoding="utf-8")

    if not validation.get("ok", False) or readiness["state"] == READINESS_BLOCKED:
        summary["import_boundary"]["decision"] = import_decision
        summary["import_boundary"]["persisted"] = False
        if summary_json_path:
            summary_json_path.parent.mkdir(parents=True, exist_ok=True)
            summary_json_path.write_text(_json(summary) + "\n", encoding="utf-8")
        if summary_md_path:
            summary_md_path.parent.mkdir(parents=True, exist_ok=True)
            summary_md_path.write_text(render_summary_md(summary), encoding="utf-8")
        return {"validation": validation, "summary": summary, "db_path": str(db_path), "imported": False}

    if readiness["state"] == READINESS_DRAFT and import_mode != "allow-draft":
        summary["import_boundary"]["decision"] = import_decision
        summary["import_boundary"]["persisted"] = False
        if summary_json_path:
            summary_json_path.parent.mkdir(parents=True, exist_ok=True)
            summary_json_path.write_text(_json(summary) + "\n", encoding="utf-8")
        if summary_md_path:
            summary_md_path.parent.mkdir(parents=True, exist_ok=True)
            summary_md_path.write_text(render_summary_md(summary), encoding="utf-8")
        return {"validation": validation, "summary": summary, "db_path": str(db_path), "imported": False}

    boundary_service = ApprovedImportService(create_approved_import_adapter(db_path, db_url=db_url))
    try:
        boundary_result = boundary_service.persist_import(
            exam_bundle=exam_bundle,
            question_bank_items=question_bank_items,
            validation=validation,
            readiness=readiness,
            summary=summary,
            import_mode=import_mode,
            approved_source=approved_source,
            imported_at=imported_at,
            dry_run=dry_run,
            exam_bundle_path=exam_bundle_path,
            question_bank_items_path=question_bank_items_path,
        )
    finally:
        boundary_service.close()

    summary = boundary_result["summary"]
    db_path = Path(boundary_result.get("db_path", str(db_path)))
    imported = bool(boundary_result.get("imported", False))

    if summary_json_path:
        summary_json_path.parent.mkdir(parents=True, exist_ok=True)
        summary_json_path.write_text(_json(summary) + "\n", encoding="utf-8")
    if summary_md_path:
        summary_md_path.parent.mkdir(parents=True, exist_ok=True)
        summary_md_path.write_text(render_summary_md(summary), encoding="utf-8")

    return {"validation": validation, "summary": summary, "db_path": str(db_path), "imported": imported}


def render_summary_md(summary: Dict[str, Any]) -> str:
    lines = ["# Question Bank Approved Import Summary", ""]
    for key in ["bundle_id", "subject", "approved_source", "imported_at", "import_job_id", "db_path"]:
        value = summary.get(key, "")
        if value:
            lines.append(f"- `{key}`: `{value}`")
    if summary.get("import_mode"):
        lines.append(f"- `import_mode`: `{summary.get('import_mode')}`")
    if summary.get("import_boundary") and isinstance(summary.get("import_boundary"), dict):
        lines.append(f"- `import_boundary.adapter`: `{summary['import_boundary'].get('adapter', '')}`")
        lines.append(f"- `import_boundary.validation_first`: `{summary['import_boundary'].get('validation_first', False)}`")
        lines.append(f"- `import_boundary.dry_run`: `{summary['import_boundary'].get('dry_run', False)}`")
        lines.append(f"- `import_boundary.mode`: `{summary['import_boundary'].get('mode', '')}`")
        lines.append(f"- `import_boundary.approved_source`: `{summary['import_boundary'].get('approved_source', '')}`")
        lines.append(f"- `import_boundary.decision`: `{summary['import_boundary'].get('decision', '')}`")
        lines.append(f"- `import_boundary.persisted`: `{summary['import_boundary'].get('persisted', False)}`")
    if summary.get("import_readiness") and isinstance(summary.get("import_readiness"), dict):
        lines.append(f"- `import_readiness.state`: `{summary['import_readiness'].get('state', '')}`")
        lines.append(f"- `import_readiness.reason`: `{summary['import_readiness'].get('reason', '')}`")
    lines.append(f"- `import_allowed`: `{summary.get('import_allowed', False)}`")
    lines.append(f"- `import_decision`: `{summary.get('import_decision', '')}`")
    lines.append(f"- `source_publish_verdict`: `{summary.get('source_publish_verdict', '')}`")
    lines.append(f"- `validation_ok`: `{summary.get('validation_ok', False)}`")
    lines.append(f"- `validation_error_count`: `{summary.get('validation_error_count', 0)}`")
    lines.append(f"- `validation_warning_count`: `{summary.get('validation_warning_count', 0)}`")
    lines.append("")
    lines.append("## Table Counts")
    for key, value in (summary.get("table_counts") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    if summary.get("metrics"):
        lines.append("")
        lines.append("## Metrics")
        for key, value in (summary.get("metrics") or {}).items():
            lines.append(f"- `{key}`: `{value}`")
    if summary.get("warnings"):
        lines.append("")
        lines.append("## Warnings")
        for warning in summary.get("warnings", []):
            if isinstance(warning, dict):
                lines.append(f"- `{warning.get('code', '')}`: {warning.get('message', '')}")
            else:
                lines.append(f"- {warning}")
    if summary.get("errors"):
        lines.append("")
        lines.append("## Errors")
        for error in summary.get("errors", []):
            if isinstance(error, dict):
                lines.append(f"- `{error.get('code', '')}`: {error.get('message', '')}")
            else:
                lines.append(f"- {error}")
    return "\n".join(lines) + "\n"


def _resolve_input_paths(args: argparse.Namespace) -> Tuple[Path, Path]:
    if args.bundle_dir:
        bundle_dir = args.bundle_dir.resolve()
        exam_bundle_path = args.exam_bundle or (bundle_dir / "final_exam_bundle.json")
        question_bank_items_path = args.question_bank_items or (bundle_dir / "final_question_bank_items.json")
    else:
        exam_bundle_path = args.exam_bundle
        question_bank_items_path = args.question_bank_items
        if exam_bundle_path is None or question_bank_items_path is None:
            raise SystemExit("provide either --bundle-dir or both --exam-bundle and --question-bank-items")
    return exam_bundle_path.resolve(), question_bank_items_path.resolve()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Import approved final artifacts into a question_bank SQLite store.")
    parser.add_argument("--bundle-dir", type=Path, default=None, help="Directory containing final_exam_bundle.json and final_question_bank_items.json")
    parser.add_argument("--exam-bundle", type=Path, default=None, help="Path to final_exam_bundle.json")
    parser.add_argument("--question-bank-items", type=Path, default=None, help="Path to final_question_bank_items.json")
    parser.add_argument("--batch-root", type=Path, default=None, help="Directory tree containing finalized bundle directories")
    parser.add_argument("--db", type=Path, default=None, help="SQLite database path for the question bank import store")
    parser.add_argument("--db-url", type=str, default=None, help="Postgres database URL for the question bank import store")
    parser.add_argument("--mode", type=str, default="approved-only", choices=sorted(IMPORT_MODES), help="Import readiness mode: approved-only or allow-draft")
    parser.add_argument("--approved-source", type=str, default=DEFAULT_APPROVED_SOURCE, help="Approved source label recorded in provenance")
    parser.add_argument("--imported-at", type=str, default=None, help="Override imported_at timestamp in UTC ISO-8601")
    parser.add_argument("--report-json", type=Path, default=None, help="Validation report JSON path")
    parser.add_argument("--summary-json", type=Path, default=None, help="Import summary JSON path")
    parser.add_argument("--summary-md", type=Path, default=None, help="Import summary markdown path")
    parser.add_argument("--batch-report-json", type=Path, default=None, help="Batch import summary JSON path")
    parser.add_argument("--batch-summary-md", type=Path, default=None, help="Batch import summary markdown path")
    parser.add_argument("--batch-summary-json", type=Path, default=None, help="Existing batch summary JSON path for the dashboard")
    parser.add_argument("--list-jobs", action="store_true", help="List approved import jobs from the SQLite store")
    parser.add_argument("--job-bundle-id", type=str, default=None, help="Filter job listing by bundle_id")
    parser.add_argument("--job-limit", type=int, default=None, help="Limit job listing rows")
    parser.add_argument("--job-order", type=str, default="desc", choices=["asc", "desc"], help="Order for job listing rows")
    parser.add_argument("--jobs-json", type=Path, default=None, help="Job listing JSON path")
    parser.add_argument("--jobs-md", type=Path, default=None, help="Job listing markdown path")
    parser.add_argument("--dashboard-html", type=Path, default=None, help="Generate a read-only HTML dashboard from the SQLite boundary")
    parser.add_argument("--dashboard-title", type=str, default="Question Bank Import Dashboard", help="Dashboard title")
    parser.add_argument("--dry-run", action="store_true", help="Validate and report without writing the database")
    args = parser.parse_args(argv)

    # Operational default: allow DB URL to be provided via environment variables so
    # production runs don't require flags.
    if not args.db_url:
        args.db_url = os.environ.get("QB_DB_URL") or os.environ.get("DATABASE_URL") or None

    if args.dashboard_html:
        if args.batch_root:
            base_dir = args.batch_root.resolve()
        elif args.bundle_dir:
            base_dir = args.bundle_dir.resolve()
        elif args.exam_bundle is not None:
            base_dir = args.exam_bundle.resolve().parent
        else:
            base_dir = Path.cwd()
        db_path = _display_db_path_from_url(args.db_url) if args.db_url else (args.db or (base_dir / DEFAULT_DB_FILENAME)).resolve()
        dashboard_html = args.dashboard_html.resolve()
        result = write_import_dashboard(
            db_path,
            dashboard_html,
            db_url=args.db_url,
            batch_summary_json_path=args.batch_summary_json,
            batch_root=args.batch_root,
            title=args.dashboard_title,
            job_limit=args.job_limit,
        )
        print(_json(result))
        return 0

    if args.list_jobs:
        if args.batch_root:
            base_dir = args.batch_root.resolve()
        elif args.bundle_dir:
            base_dir = args.bundle_dir.resolve()
        elif args.exam_bundle is not None:
            base_dir = args.exam_bundle.resolve().parent
        else:
            base_dir = Path.cwd()
        db_path = _display_db_path_from_url(args.db_url) if args.db_url else (args.db or (base_dir / DEFAULT_DB_FILENAME)).resolve()
        jobs_json = (args.jobs_json or (db_path.parent / DEFAULT_JOB_LISTING_FILENAME)).resolve()
        jobs_md = (args.jobs_md or (db_path.parent / DEFAULT_JOB_LISTING_MD_FILENAME)).resolve()
        listing = list_import_jobs(
            db_path,
            db_url=args.db_url,
            bundle_id=args.job_bundle_id,
            limit=args.job_limit,
            order=args.job_order,
        )
        if jobs_json:
            jobs_json.parent.mkdir(parents=True, exist_ok=True)
            jobs_json.write_text(_json(listing) + "\n", encoding="utf-8")
        if jobs_md:
            jobs_md.parent.mkdir(parents=True, exist_ok=True)
            jobs_md.write_text(render_import_job_listing_md(listing), encoding="utf-8")
        print(
            _json(
                {
                    "jobs_json": str(jobs_json),
                    "jobs_md": str(jobs_md),
                    "db_path": str(db_path),
                    "job_count": listing.get("job_count", 0),
                    "bundle_id_filter": args.job_bundle_id or "",
                    "ok": bool(listing.get("ok", False)),
                }
            )
        )
        return 0 if listing.get("ok", False) else 1

    if args.batch_root:
        batch_root = args.batch_root.resolve()
        db_path = _display_db_path_from_url(args.db_url) if args.db_url else (args.db or (batch_root / DEFAULT_DB_FILENAME)).resolve()
        batch_report_json = (args.batch_report_json or (batch_root / DEFAULT_BATCH_SUMMARY_FILENAME)).resolve()
        batch_summary_md = (args.batch_summary_md or (batch_root / DEFAULT_BATCH_SUMMARY_MD_FILENAME)).resolve()
        result = batch_import_approved_artifacts(
            batch_root,
            db_path,
            db_url=args.db_url,
            import_mode=args.mode,
            approved_source=args.approved_source,
            imported_at=args.imported_at,
            report_json_path=batch_report_json,
            summary_json_path=batch_report_json,
            summary_md_path=batch_summary_md,
            dry_run=args.dry_run,
        )
        print(
            _json(
                {
                    "batch_report": str(batch_report_json),
                    "summary_markdown": str(batch_summary_md),
                    "db_path": str(db_path),
                    "batch_root": str(batch_root),
                    "bundle_count": result.get("bundle_count", 0),
                    "imported_count": result.get("imported_count", 0),
                    "skipped_count": result.get("skipped_count", 0),
                    "blocked_count": result.get("blocked_count", 0),
                    "error_count": result.get("error_count", 0),
                    "ok": bool(result.get("ok", False)),
                }
            )
        )
        return 0 if result.get("ok", False) else 1

    exam_bundle_path, question_bank_items_path = _resolve_input_paths(args)
    base_dir = args.bundle_dir.resolve() if args.bundle_dir else exam_bundle_path.parent
    db_path = _display_db_path_from_url(args.db_url) if args.db_url else (args.db or (base_dir / DEFAULT_DB_FILENAME)).resolve()
    report_json = (args.report_json or (base_dir / DEFAULT_VALIDATION_REPORT_FILENAME)).resolve()
    summary_json = (args.summary_json or (base_dir / DEFAULT_IMPORT_SUMMARY_FILENAME)).resolve()
    summary_md = (args.summary_md or (base_dir / DEFAULT_IMPORT_SUMMARY_MD_FILENAME)).resolve()

    result = import_approved_artifacts(
        exam_bundle_path,
        question_bank_items_path,
        db_path,
        db_url=args.db_url,
        import_mode=args.mode,
        approved_source=args.approved_source,
        imported_at=args.imported_at,
        report_json_path=report_json,
        summary_json_path=summary_json,
        summary_md_path=summary_md,
        dry_run=args.dry_run,
    )

    validation = result["validation"]
    print(
        _json(
            {
                "validation_report": str(report_json),
                "import_summary": str(summary_json),
                "summary_markdown": str(summary_md),
                "db_path": str(db_path),
                "imported": bool(result.get("imported", False)),
                "ok": bool(validation.get("ok", False)),
                "import_mode": args.mode,
                "import_readiness": validation.get("import_readiness", {}),
                "import_allowed": validation.get("import_allowed", False),
                "import_decision": validation.get("import_decision", ""),
            }
        )
    )

    if args.dry_run:
        return 0 if validation.get("ok", False) else 1
    return 0 if result.get("imported", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
