from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sqlite3
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .import_boundary import READINESS_APPROVED

try:  # pragma: no cover - optional dependency
    import psycopg
    from psycopg.rows import dict_row as psycopg_dict_row
except Exception:  # noqa: BLE001
    psycopg = None
    psycopg_dict_row = None

SCHEMA_VERSION = "question_bank_exam_assembly.v1"
ARTIFACT_TYPE = "exam_assembly"
DEFAULT_OUTPUT_JSON = "fixed_exam_assembly.json"
DEFAULT_OUTPUT_MD = "fixed_exam_assembly.md"
DEFAULT_RANDOM_OUTPUT_JSON = "random_exam_assembly.json"
DEFAULT_RANDOM_OUTPUT_MD = "random_exam_assembly.md"
DEFAULT_TITLE = "Fixed Exam Assembly"
DEFAULT_RANDOM_TITLE = "Random Exam Assembly"

ASSEMBLY_STORE_SCHEMA_VERSION = "question_bank_exam_assembly_store.v1"
ASSEMBLY_STORE_TABLE = "qb_exam_assemblies"


@dataclass
class AssemblyError(Exception):
    stage: str
    code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.details:
            return f"{self.stage}:{self.code}: {self.message} ({self.details})"
        return f"{self.stage}:{self.code}: {self.message}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _safe_json_parse(value: Any, default: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        return default
    try:
        return json.loads(value)
    except Exception:  # noqa: BLE001
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:  # noqa: BLE001
        return default


def _empty_to_default(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _normalize_question_types(question_types: Optional[List[str]]) -> List[str]:
    if not question_types:
        return []
    normalized: List[str] = []
    for entry in question_types:
        if not entry:
            continue
        for piece in str(entry).split(","):
            value = piece.strip()
            if value and value not in normalized:
                normalized.append(value)
    return normalized


def _redact_db_url_for_display(database_url: str) -> str:
    text = str(database_url or "")
    if "://" not in text:
        return "<redacted-db-url>"
    scheme, rest = text.split("://", 1)
    if not scheme:
        return "<redacted-db-url>"
    rest = rest.split("?", 1)[0].split("#", 1)[0]
    if "@" in rest:
        userinfo, hostpart = rest.split("@", 1)
        user = userinfo.split(":", 1)[0]
        rest = f"{user}@{hostpart}"
    return f"{scheme}://{rest}"


def _stable_selection_hash(ordered_item_ids: List[str]) -> str:
    digest = hashlib.sha256(("\n".join(ordered_item_ids)).encode("utf-8")).hexdigest()[:16]
    return f"sel_{digest}"


def _is_unknown_subject(subject: str) -> bool:
    value = str(subject or "").strip().lower()
    return value in {"", "generic", "unknown"}


def _resolve_db_url(db_url: Optional[str]) -> Optional[str]:
    if db_url:
        return str(db_url)
    return os.environ.get("QB_DB_URL") or os.environ.get("DATABASE_URL") or None


def resolve_persisted_assembly_artifact_path(
    *,
    assembly_id: str,
    db_path: Optional[Path] = None,
    db_url: Optional[str] = None,
) -> Path:
    """
    Resolve a persisted qb_exam_assemblies record to the on-disk JSON artifact path.

    This is the QB-C bridge: it lets preview/export operate from an assembly_id (DB record),
    without requiring the operator to manually pass the artifact path.
    """
    resolved_url = _resolve_db_url(db_url)
    service = FixedExamAssemblyService(db_path=(None if resolved_url else db_path), db_url=resolved_url)
    try:
        payload = service.get_assembly_record(str(assembly_id))
        record = payload.get("record", {}) if isinstance(payload.get("record"), dict) else {}
        artifact_path_text = _empty_to_default(record.get("artifact_json_path"))
        if not artifact_path_text:
            raise AssemblyError(
                "resolve_artifact",
                "missing_artifact_json_path",
                "assembly record is missing artifact_json_path",
                {"assembly_id": str(assembly_id)},
            )
        artifact_path = Path(artifact_path_text).expanduser()
        if not artifact_path.exists():
            raise AssemblyError(
                "resolve_artifact",
                "artifact_json_path_missing",
                "assembly artifact JSON path does not exist on disk",
                {"assembly_id": str(assembly_id), "artifact_json_path": str(artifact_path)},
            )
        return artifact_path.resolve()
    finally:
        service.close()


class FixedExamAssemblyService:
    def __init__(self, *, db_path: Optional[Path] = None, db_url: Optional[str] = None):
        if db_url:
            if psycopg is None:  # pragma: no cover
                raise AssemblyError("init", "postgres_driver_missing", "psycopg is required for Postgres assembly reads")
            self.db_url = str(db_url)
            self.backend = "postgres"
            self.param = "%s"
            display = _redact_db_url_for_display(self.db_url)
            self.db_path = Path(f"postgresql__{display.replace('://','__').replace('/','__')}")
            self.conn = psycopg.connect(self.db_url, row_factory=psycopg_dict_row)
        else:
            if db_path is None:
                raise AssemblyError("init", "missing_db_path", "db_path is required when db_url is not provided")
            self.db_url = None
            self.backend = "sqlite"
            self.param = "?"
            self.db_path = db_path.resolve()
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
        self._approved_questions_columns = self._detect_columns("approved_questions")

    def close(self) -> None:
        if getattr(self, "conn", None) is not None:
            self.conn.close()
            self.conn = None

    def _format_sql(self, sql: str) -> str:
        if self.param == "?":
            return sql
        return sql.replace("?", self.param)

    def _execute(self, sql: str, params: tuple[Any, ...]) -> Any:
        try:
            return self.conn.execute(self._format_sql(sql), params)
        except Exception as exc:  # noqa: BLE001
            raise AssemblyError("db", "query_failed", str(exc), {"backend": self.backend}) from exc

    def _detect_columns(self, table: str) -> set[str]:
        cols: set[str] = set()
        try:
            if self.backend == "sqlite":
                rows = self._execute(f"PRAGMA table_info({table})", ()).fetchall()
                for row in rows:
                    try:
                        cols.add(str(dict(row).get("name", "")).strip())
                    except Exception:  # noqa: BLE001
                        continue
            else:
                # Postgres: constrain to current schema; tolerate permissions/edge cases.
                rows = self._execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
                    (str(table),),
                ).fetchall()
                for row in rows:
                    try:
                        cols.add(str(dict(row).get("column_name", "")).strip())
                    except Exception:  # noqa: BLE001
                        continue
        except Exception:  # noqa: BLE001
            return set()
        return {c for c in cols if c}

    def _fetch_bundle_row(self, bundle_id: str) -> Dict[str, Any]:
        row = self._execute(
            """
            SELECT bundle_id, import_job_id, subject, approved_source, import_mode, import_readiness,
                   import_readiness_reason, source_publish_verdict, imported_at, schema_version,
                   artifact_type, output_mode, question_item_count, summary_json, answer_summary_json,
                   answer_qa_summary_json, source_json
            FROM approved_exam_bundles
            WHERE bundle_id = ?
            """,
            (bundle_id,),
        ).fetchone()
        if row is None:
            raise AssemblyError(
                "load_bundle",
                "bundle_not_found",
                f"approved bundle not found: {bundle_id}",
                {"bundle_id": bundle_id},
            )
        return dict(row) if row is not None else {}

    def _fetch_bundle_rows(self, bundle_ids: List[str]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for bundle_id in bundle_ids:
            bundle_row = self._fetch_bundle_row(bundle_id)
            rows.append(
                {
                    "bundle_id": bundle_row.get("bundle_id", ""),
                    "import_job_id": bundle_row.get("import_job_id", ""),
                    "subject": bundle_row.get("subject", ""),
                    "approved_source": bundle_row.get("approved_source", ""),
                    "import_mode": bundle_row.get("import_mode", ""),
                    "import_readiness": bundle_row.get("import_readiness", ""),
                    "import_readiness_reason": bundle_row.get("import_readiness_reason", ""),
                    "source_publish_verdict": bundle_row.get("source_publish_verdict", ""),
                    "imported_at": bundle_row.get("imported_at", ""),
                    "question_item_count": _safe_int(bundle_row.get("question_item_count"), 0),
                    "summary": _safe_json_parse(bundle_row.get("summary_json"), {}),
                    "answer_summary": _safe_json_parse(bundle_row.get("answer_summary_json"), {}),
                    "answer_qa_summary": _safe_json_parse(bundle_row.get("answer_qa_summary_json"), {}),
                    "source": _safe_json_parse(bundle_row.get("source_json"), {}),
                }
            )
        return rows

    def _build_assembly_artifact(
        self,
        *,
        assembly_mode: str,
        assembly_id: str,
        exam_record: Dict[str, Any],
        selection: Dict[str, Any],
        validation: Dict[str, Any],
        items: List[Dict[str, Any]],
        bundle_rows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        artifact: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": ARTIFACT_TYPE,
            "assembly_mode": assembly_mode,
            "assembly_id": assembly_id,
            "created_at": _now_iso(),
            "source_db_path": str(self.db_path),
            "exam": exam_record,
            "selection": selection,
            "validation": validation,
            "source_bundles": bundle_rows,
            "items": items,
            "summary": {
                "item_count": len(items),
                "bundle_count": len(bundle_rows),
                "subject": exam_record.get("subject", ""),
                "approved_only": True,
                "validation_ok": bool(validation.get("ok", False)),
                "answer_count": sum(1 for item in items if _empty_to_default(item.get("answer_key", {}).get("mode")) != "none"),
                "rubric_count": sum(
                    1
                    for item in items
                    if _empty_to_default(item.get("rubric", {}).get("rubric_text"))
                    or _empty_to_default(item.get("rubric", {}).get("mode")) not in {"", "none"}
                ),
            },
        }
        if "seed" in selection:
            artifact["summary"]["seed"] = selection.get("seed", "")
        if "required_count" in selection:
            artifact["summary"]["required_count"] = selection.get("required_count", 0)
        if "filters" in selection:
            artifact["summary"]["filters"] = selection.get("filters", {})
        return artifact

    def _query_eligible_pool(
        self,
        *,
        subject: Optional[str] = None,
        question_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        clauses = [f"import_readiness = {self.param}"]
        params: List[Any] = [READINESS_APPROVED]
        if subject:
            clauses.append(f"subject = {self.param}")
            params.append(subject)
        normalized_types = _normalize_question_types(question_types)
        if normalized_types:
            placeholders = ", ".join([self.param] * len(normalized_types))
            clauses.append(f"question_type IN ({placeholders})")
            params.extend(normalized_types)
        query = (
            "SELECT item_id, bundle_id, subject, question_number, question_type "
            "FROM approved_questions WHERE "
            + " AND ".join(clauses)
            + " ORDER BY bundle_id ASC, question_number ASC, item_id ASC"
        )
        rows = [dict(row) for row in self._execute(query, tuple(params)).fetchall()]
        return rows

    def _fetch_item_row(self, item_id: str) -> Dict[str, Any]:
        # approved_questions schema has evolved; tolerate optional columns by substituting defaults.
        doc_fam_conf_sql = (
            "q.document_family_confidence"
            if "document_family_confidence" in self._approved_questions_columns
            else "NULL AS document_family_confidence"
        )
        source_priority_sql = (
            "q.source_priority_path_json"
            if "source_priority_path_json" in self._approved_questions_columns
            else "'' AS source_priority_path_json"
        )
        parser_warn_sql = (
            "q.parser_warning_codes_json"
            if "parser_warning_codes_json" in self._approved_questions_columns
            else "'' AS parser_warning_codes_json"
        )
        row = self._execute(
            f"""
            SELECT
                q.item_id,
                q.bundle_id,
                q.import_job_id,
                q.exam_id,
                q.subject,
                q.question_number,
                q.question_type,
                q.placement,
                q.prompt_preview,
                q.document_family,
                {doc_fam_conf_sql},
                {source_priority_sql},
                {parser_warn_sql},
                q.import_mode,
                q.import_readiness,
                q.import_readiness_reason,
                q.import_readiness_json,
                q.source_publish_verdict,
                q.qa_flags_json,
                q.imported_at,
                q.approved_source,
                a.answer_mode,
                a.answer_key_json,
                a.answer_sources_json,
                a.reconciliation_json,
                a.import_mode AS answer_import_mode,
                a.import_readiness AS answer_import_readiness,
                a.import_readiness_reason AS answer_import_readiness_reason,
                a.import_readiness_json AS answer_import_readiness_json,
                a.source_publish_verdict AS answer_source_publish_verdict,
                a.imported_at AS answer_imported_at,
                a.approved_source AS answer_approved_source,
                r.rubric_mode,
                r.rubric_text,
                r.rubric_json,
                r.import_mode AS rubric_import_mode,
                r.import_readiness AS rubric_import_readiness,
                r.import_readiness_reason AS rubric_import_readiness_reason,
                r.import_readiness_json AS rubric_import_readiness_json,
                r.source_publish_verdict AS rubric_source_publish_verdict,
                r.imported_at AS rubric_imported_at,
                r.approved_source AS rubric_approved_source
            FROM approved_questions q
            LEFT JOIN approved_question_answers a ON a.item_id = q.item_id
            LEFT JOIN approved_question_rubrics r ON r.item_id = q.item_id
            WHERE q.item_id = ?
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            raise AssemblyError(
                "load_item",
                "item_not_found",
                f"approved item not found: {item_id}",
                {"item_id": item_id},
            )
        return dict(row) if row is not None else {}

    def _validate_item(self, item: Dict[str, Any], requested_item_id: str) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        if _empty_to_default(item.get("item_id")) != requested_item_id:
            issues.append(
                {
                    "stage": "validation",
                    "code": "item_id_mismatch",
                    "severity": "blocker",
                    "item_id": requested_item_id,
                    "message": f"loaded item_id {item.get('item_id', '')} does not match requested id",
                }
            )
        if _empty_to_default(item.get("import_readiness")) != READINESS_APPROVED:
            issues.append(
                {
                    "stage": "validation",
                    "code": "item_not_approved_importable",
                    "severity": "blocker",
                    "item_id": requested_item_id,
                    "message": f"item is not approved-importable: {item.get('import_readiness', '')}",
                }
            )
        if not _empty_to_default(item.get("bundle_id")):
            issues.append(
                {
                    "stage": "validation",
                    "code": "missing_bundle_id",
                    "severity": "blocker",
                    "item_id": requested_item_id,
                    "message": "missing bundle_id for selected item",
                }
            )
        if _safe_int(item.get("question_number"), 0) <= 0:
            issues.append(
                {
                    "stage": "validation",
                    "code": "invalid_question_number",
                    "severity": "blocker",
                    "item_id": requested_item_id,
                    "message": f"invalid question_number: {item.get('question_number')}",
                }
            )
        if not _empty_to_default(item.get("question_type")):
            issues.append(
                {
                    "stage": "validation",
                    "code": "missing_question_type",
                    "severity": "blocker",
                    "item_id": requested_item_id,
                    "message": "missing question_type for selected item",
                }
            )
        if not _empty_to_default(item.get("prompt_preview")):
            issues.append(
                {
                    "stage": "validation",
                    "code": "missing_prompt_preview",
                    "severity": "blocker",
                    "item_id": requested_item_id,
                    "message": "missing prompt preview for selected item",
                }
            )
        answer_key = _safe_json_parse(item.get("answer_key_json"), {})
        reconciliation = _safe_json_parse(item.get("reconciliation_json"), {})
        rubric = _safe_json_parse(item.get("rubric_json"), {})
        if not isinstance(answer_key, dict):
            issues.append(
                {
                    "stage": "validation",
                    "code": "answer_key_unparseable",
                    "severity": "blocker",
                    "item_id": requested_item_id,
                    "message": "answer_key_json is not a JSON object",
                }
            )
        if not isinstance(reconciliation, dict):
            issues.append(
                {
                    "stage": "validation",
                    "code": "reconciliation_unparseable",
                    "severity": "blocker",
                    "item_id": requested_item_id,
                    "message": "reconciliation_json is not a JSON object",
                }
            )
        if not isinstance(rubric, dict):
            issues.append(
                {
                    "stage": "validation",
                    "code": "rubric_unparseable",
                    "severity": "blocker",
                    "item_id": requested_item_id,
                    "message": "rubric_json is not a JSON object",
                }
            )
        return issues

    def _build_item(self, row: Dict[str, Any], selection_index: int) -> Dict[str, Any]:
        return {
            "selection_index": selection_index,
            "item_id": row["item_id"],
            "bundle_id": row["bundle_id"],
            "import_job_id": row.get("import_job_id", ""),
            "exam_id": row.get("exam_id", ""),
            "subject": row.get("subject", ""),
            "question_number": _safe_int(row.get("question_number"), 0),
            "question_type": row.get("question_type", ""),
            "placement": row.get("placement", ""),
            "prompt_preview": row.get("prompt_preview", ""),
            "document_family": row.get("document_family", ""),
            "document_family_confidence": row.get("document_family_confidence", None),
            "source_priority_path": _safe_json_parse(row.get("source_priority_path_json"), []),
            "parser_warning_codes": _safe_json_parse(row.get("parser_warning_codes_json"), []),
            "qa_flags": _safe_json_parse(row.get("qa_flags_json"), []),
            "import_mode": row.get("import_mode", ""),
            "import_readiness": row.get("import_readiness", ""),
            "import_readiness_reason": row.get("import_readiness_reason", ""),
            "import_readiness_json": _safe_json_parse(row.get("import_readiness_json"), {}),
            "source_publish_verdict": row.get("source_publish_verdict", ""),
            "imported_at": row.get("imported_at", ""),
            "approved_source": row.get("approved_source", ""),
            "answer_key": _safe_json_parse(row.get("answer_key_json"), {}),
            "answer_sources": _safe_json_parse(row.get("answer_sources_json"), []),
            "reconciliation": _safe_json_parse(row.get("reconciliation_json"), {}),
            "rubric": {
                "mode": row.get("rubric_mode", ""),
                "rubric_text": row.get("rubric_text", ""),
                "rubric_json": _safe_json_parse(row.get("rubric_json"), {}),
                "import_mode": row.get("rubric_import_mode", ""),
                "import_readiness": row.get("rubric_import_readiness", ""),
                "import_readiness_reason": row.get("rubric_import_readiness_reason", ""),
                "source_publish_verdict": row.get("rubric_source_publish_verdict", ""),
                "approved_source": row.get("rubric_approved_source", ""),
                "imported_at": row.get("rubric_imported_at", ""),
            },
        }

    def _ensure_assembly_store_schema(self) -> None:
        self._execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ASSEMBLY_STORE_TABLE} (
                assembly_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                assembly_mode TEXT NOT NULL,
                subject TEXT NOT NULL,
                approved_only INTEGER NOT NULL,
                selection_item_count INTEGER NOT NULL,
                selection_hash TEXT NOT NULL,
                requested_item_ids_json TEXT NOT NULL,
                ordered_item_ids_json TEXT NOT NULL,
                duplicate_item_ids_json TEXT NOT NULL,
                missing_item_ids_json TEXT NOT NULL,
                source_snapshot_json TEXT NOT NULL,
                artifact_json_path TEXT NOT NULL,
                artifact_md_path TEXT NOT NULL,
                validation_ok INTEGER NOT NULL,
                warnings_json TEXT NOT NULL,
                errors_json TEXT NOT NULL,
                schema_version TEXT NOT NULL
            )
            """,
            (),
        )

    def _persist_assembly_record(self, artifact: Dict[str, Any], *, output_json_path: Path, output_md_path: Path) -> None:
        self._ensure_assembly_store_schema()
        selection = artifact.get("selection", {}) if isinstance(artifact.get("selection"), dict) else {}
        validation = artifact.get("validation", {}) if isinstance(artifact.get("validation"), dict) else {}
        source_snapshot = {
            "source_db_path": artifact.get("source_db_path", ""),
            "source_bundles": artifact.get("source_bundles", []),
        }
        if "seed" in selection:
            source_snapshot["random"] = {
                "seed": selection.get("seed", ""),
                "required_count": selection.get("required_count", 0),
                "filters": selection.get("filters", {}),
                "pool_count": selection.get("pool_count", 0),
            }
        requested_item_ids = selection.get("requested_item_ids", []) if isinstance(selection.get("requested_item_ids"), list) else []
        ordered_item_ids = selection.get("ordered_item_ids", []) if isinstance(selection.get("ordered_item_ids"), list) else []
        duplicates = selection.get("duplicate_item_ids", []) if isinstance(selection.get("duplicate_item_ids"), list) else []
        missing = selection.get("missing_item_ids", []) if isinstance(selection.get("missing_item_ids"), list) else []
        selection_hash = _stable_selection_hash([str(v) for v in ordered_item_ids])
        row = {
            "assembly_id": artifact.get("assembly_id", ""),
            "created_at": artifact.get("created_at", _now_iso()),
            "assembly_mode": artifact.get("assembly_mode", ""),
            "subject": artifact.get("exam", {}).get("subject", "") if isinstance(artifact.get("exam"), dict) else "",
            "approved_only": 1,
            "selection_item_count": _safe_int(artifact.get("summary", {}).get("item_count"), 0) if isinstance(artifact.get("summary"), dict) else 0,
            "selection_hash": selection_hash,
            "requested_item_ids_json": _json(requested_item_ids),
            "ordered_item_ids_json": _json(ordered_item_ids),
            "duplicate_item_ids_json": _json(duplicates),
            "missing_item_ids_json": _json(missing),
            "source_snapshot_json": _json(source_snapshot),
            "artifact_json_path": str(output_json_path),
            "artifact_md_path": str(output_md_path),
            "validation_ok": 1 if bool(validation.get("ok", False)) else 0,
            "warnings_json": _json(validation.get("warnings", [])),
            "errors_json": _json(validation.get("errors", [])),
            "schema_version": ASSEMBLY_STORE_SCHEMA_VERSION,
        }
        cols = list(row.keys())
        placeholders = ", ".join([self.param] * len(cols))
        assignments = ", ".join([f"{col}=excluded.{col}" for col in cols if col != "assembly_id"])
        sql = (
            f"INSERT INTO {ASSEMBLY_STORE_TABLE} ({', '.join(cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT(assembly_id) DO UPDATE SET {assignments}"
        )
        self._execute(sql, tuple(row[col] for col in cols))
        self.conn.commit()

    def list_assembly_records(
        self,
        *,
        limit: int = 50,
        order: str = "desc",
        assembly_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._ensure_assembly_store_schema()
        order_sql = "DESC" if str(order).lower() != "asc" else "ASC"
        params: List[Any] = []
        clauses: List[str] = []
        if assembly_mode:
            clauses.append(f"assembly_mode = {self.param}")
            params.append(str(assembly_mode))
        where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        query = (
            "SELECT assembly_id, created_at, assembly_mode, subject, approved_only, selection_item_count, selection_hash, "
            "artifact_json_path, artifact_md_path, validation_ok, source_snapshot_json "
            f"FROM {ASSEMBLY_STORE_TABLE}{where_sql} "
            f"ORDER BY created_at {order_sql}, assembly_id {order_sql} "
            f"LIMIT {self.param}"
        )
        params.append(int(limit))
        rows = [dict(row) for row in self._execute(query, tuple(params)).fetchall()]
        records: List[Dict[str, Any]] = []
        for row in rows:
            snapshot = _safe_json_parse(row.get("source_snapshot_json"), {})
            record = {
                "assembly_id": row.get("assembly_id", ""),
                "created_at": row.get("created_at", ""),
                "assembly_mode": row.get("assembly_mode", ""),
                "subject": row.get("subject", ""),
                "selection_item_count": _safe_int(row.get("selection_item_count"), 0),
                "selection_hash": row.get("selection_hash", ""),
                "artifact_json_path": row.get("artifact_json_path", ""),
                "artifact_md_path": row.get("artifact_md_path", ""),
                "validation_ok": bool(_safe_int(row.get("validation_ok"), 0)),
            }
            if isinstance(snapshot, dict) and isinstance(snapshot.get("random"), dict):
                record["random"] = snapshot.get("random", {})
            records.append(record)
        return {
            "schema_version": ASSEMBLY_STORE_SCHEMA_VERSION,
            "artifact_type": "question_bank_exam_assembly_record_listing",
            "backend": self.backend,
            "db_path": str(self.db_path),
            "limit": int(limit),
            "order": order_sql.lower(),
            "assembly_mode_filter": str(assembly_mode or ""),
            "record_count": len(records),
            "records": records,
            "ok": True,
        }

    def get_assembly_record(self, assembly_id: str) -> Dict[str, Any]:
        self._ensure_assembly_store_schema()
        row = self._execute(
            f"SELECT * FROM {ASSEMBLY_STORE_TABLE} WHERE assembly_id = {self.param}",
            (str(assembly_id),),
        ).fetchone()
        if row is None:
            raise AssemblyError("load_assembly_record", "assembly_not_found", "assembly_id not found", {"assembly_id": assembly_id})
        payload = dict(row)
        # Parse JSON fields for operator readability.
        for key in [
            "requested_item_ids_json",
            "ordered_item_ids_json",
            "duplicate_item_ids_json",
            "missing_item_ids_json",
            "source_snapshot_json",
            "warnings_json",
            "errors_json",
        ]:
            payload[key] = _safe_json_parse(payload.get(key), [])
        return {
            "schema_version": ASSEMBLY_STORE_SCHEMA_VERSION,
            "artifact_type": "question_bank_exam_assembly_record",
            "backend": self.backend,
            "db_path": str(self.db_path),
            "record": payload,
            "ok": True,
        }

    def assemble_fixed_exam(
        self,
        *,
        item_ids: List[str],
        assembly_id: Optional[str] = None,
        exam_id: Optional[str] = None,
        title: str = DEFAULT_TITLE,
        subject: Optional[str] = None,
        notes: str = "",
        output_json_path: Optional[Path] = None,
        output_md_path: Optional[Path] = None,
        persist: bool = True,
    ) -> Dict[str, Any]:
        if not item_ids:
            raise AssemblyError("selection", "no_item_ids", "no item ids were provided")

        requested_item_ids = [str(item_id).strip() for item_id in item_ids if str(item_id).strip()]
        if not requested_item_ids:
            raise AssemblyError("selection", "no_item_ids", "no non-empty item ids were provided")

        duplicates = [item_id for item_id, count in Counter(requested_item_ids).items() if count > 1]

        validation_errors: List[Dict[str, Any]] = []
        validation_warnings: List[Dict[str, Any]] = []
        seen_bundle_ids: List[str] = []
        seen_subjects: List[str] = []
        seen_exam_ids: List[str] = []
        items: List[Dict[str, Any]] = []
        missing_item_ids: List[str] = []

        if duplicates:
            validation_errors.append(
                {
                    "stage": "validation",
                    "code": "duplicate_item_ids",
                    "severity": "blocker",
                    "message": "duplicate item ids are not allowed in fixed assembly",
                    "details": {"duplicate_item_ids": duplicates},
                }
            )

        for idx, item_id in enumerate(requested_item_ids):
            try:
                row = self._fetch_item_row(item_id)
            except AssemblyError as exc:
                missing_item_ids.append(item_id)
                validation_errors.append(
                    {
                        "stage": exc.stage,
                        "code": exc.code,
                        "severity": "blocker",
                        "item_id": item_id,
                        "message": exc.message,
                        "details": exc.details,
                    }
                )
                continue

            bundle_id = _empty_to_default(row.get("bundle_id"))
            if bundle_id and bundle_id not in seen_bundle_ids:
                seen_bundle_ids.append(bundle_id)
            subject_value = _empty_to_default(row.get("subject"))
            if subject_value and subject_value not in seen_subjects:
                seen_subjects.append(subject_value)
            exam_id_value = _empty_to_default(row.get("exam_id"))
            if exam_id_value and exam_id_value not in seen_exam_ids:
                seen_exam_ids.append(exam_id_value)

            validation_issues = self._validate_item(row, item_id)
            for issue in validation_issues:
                if issue.get("severity") == "warning":
                    validation_warnings.append(issue)
                else:
                    validation_errors.append(issue)

            items.append(self._build_item(row, selection_index=idx))

        known_subjects = [s for s in seen_subjects if not _is_unknown_subject(s)]
        inferred_subject = subject or (known_subjects[0] if len(known_subjects) == 1 else "")
        if len(known_subjects) > 1:
            validation_errors.append(
                {
                    "stage": "validation",
                    "code": "mixed_subject_selection",
                    "severity": "blocker",
                    "message": "selected items span multiple subjects",
                    "details": {"subjects": known_subjects},
                }
            )
        if subject and inferred_subject and subject != inferred_subject:
            validation_errors.append(
                {
                    "stage": "validation",
                    "code": "subject_mismatch",
                    "severity": "blocker",
                    "message": f"assembly subject {subject} does not match selected subject {inferred_subject}",
                    "details": {"requested_subject": subject, "selected_subject": inferred_subject},
                }
            )
        if not inferred_subject:
            validation_errors.append(
                {
                    "stage": "validation",
                    "code": "missing_subject",
                    "severity": "blocker",
                    "message": "unable to infer a single subject from selected items",
                }
            )

        if len(items) != len(requested_item_ids):
            validation_errors.append(
                {
                    "stage": "validation",
                    "code": "missing_selected_items",
                    "severity": "blocker",
                    "message": "one or more selected item ids could not be loaded",
                    "details": {"missing_item_ids": missing_item_ids},
                }
            )

        bundle_rows = self._fetch_bundle_rows(seen_bundle_ids)

        valid = not validation_errors
        assembly_id = assembly_id or f"assembly_{uuid.uuid4().hex}"
        exam_record = {
            "exam_id": exam_id or assembly_id,
            "title": title,
            "subject": inferred_subject,
            "notes": notes,
        }
        validation = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": ARTIFACT_TYPE,
            "ok": valid,
            "errors": validation_errors,
            "warnings": validation_warnings,
            "item_count": len(items),
            "requested_item_count": len(requested_item_ids),
            "selected_item_count": len(items),
            "bundle_count": len(bundle_rows),
            "duplicate_item_ids": duplicates,
            "missing_item_ids": missing_item_ids,
            "subject": inferred_subject,
            "approved_only": True,
        }
        artifact = self._build_assembly_artifact(
            assembly_mode="fixed",
            assembly_id=assembly_id,
            exam_record=exam_record,
            selection={
                "requested_item_ids": requested_item_ids,
                "ordered_item_ids": [item["item_id"] for item in items],
                "missing_item_ids": missing_item_ids,
                "duplicate_item_ids": duplicates,
                "approved_only": True,
            },
            validation=validation,
            items=items,
            bundle_rows=bundle_rows,
        )

        if subject and not artifact["exam"]["subject"]:
            artifact["exam"]["subject"] = subject

        if not valid:
            raise AssemblyError(
                "validation",
                "assembly_validation_failed",
                "fixed exam assembly validation failed",
                {
                    "errors": validation_errors,
                    "warnings": validation_warnings,
                    "assembly_id": assembly_id,
                },
            )

        if output_json_path:
            output_json_path = output_json_path.resolve()
            output_json_path.parent.mkdir(parents=True, exist_ok=True)
            output_json_path.write_text(_json(artifact) + "\n", encoding="utf-8")
        if output_md_path:
            output_md_path = output_md_path.resolve()
            output_md_path.parent.mkdir(parents=True, exist_ok=True)
            output_md_path.write_text(render_fixed_exam_assembly_md(artifact), encoding="utf-8")
        if persist:
            if output_json_path is None or output_md_path is None:
                raise AssemblyError("persist", "missing_output_paths", "persist requires output_json_path and output_md_path")
            self._persist_assembly_record(artifact, output_json_path=output_json_path, output_md_path=output_md_path)
        return artifact


class RandomExamAssemblyService(FixedExamAssemblyService):
    def assemble_random_exam(
        self,
        *,
        required_count: int,
        seed: str,
        subject: Optional[str] = None,
        question_types: Optional[List[str]] = None,
        assembly_id: Optional[str] = None,
        exam_id: Optional[str] = None,
        title: str = DEFAULT_RANDOM_TITLE,
        notes: str = "",
        output_json_path: Optional[Path] = None,
        output_md_path: Optional[Path] = None,
        persist: bool = True,
    ) -> Dict[str, Any]:
        if required_count <= 0:
            raise AssemblyError(
                "selection",
                "invalid_required_count",
                "required_count must be greater than zero",
                {"required_count": required_count},
            )
        seed_text = _empty_to_default(seed)
        if not seed_text:
            raise AssemblyError("selection", "missing_seed", "seed is required for deterministic random assembly")

        normalized_question_types = _normalize_question_types(question_types)
        pool_rows = self._query_eligible_pool(subject=subject, question_types=normalized_question_types)
        pool_subjects = sorted({_empty_to_default(row.get("subject")) for row in pool_rows if _empty_to_default(row.get("subject"))})
        known_pool_subjects = [s for s in pool_subjects if not _is_unknown_subject(s)]

        validation_errors: List[Dict[str, Any]] = []
        validation_warnings: List[Dict[str, Any]] = []

        if not pool_rows:
            validation_errors.append(
                {
                    "stage": "validation",
                    "code": "pool_empty",
                    "severity": "blocker",
                    "message": "eligible approved-importable pool is empty for the requested filters",
                    "details": {"subject": subject or "", "question_types": normalized_question_types},
                }
            )
        if len(pool_rows) < required_count:
            validation_errors.append(
                {
                    "stage": "validation",
                    "code": "pool_too_small",
                    "severity": "blocker",
                    "message": "eligible pool is smaller than the requested required_count",
                    "details": {"pool_count": len(pool_rows), "required_count": required_count},
                }
            )
        if not subject and not known_pool_subjects:
            validation_errors.append(
                {
                    "stage": "validation",
                    "code": "missing_subject_pool",
                    "severity": "blocker",
                    "message": "random assembly requires a subject filter when the eligible pool has no known subject",
                    "details": {"subjects": pool_subjects},
                }
            )
        if not subject and len(known_pool_subjects) > 1:
            validation_errors.append(
                {
                    "stage": "validation",
                    "code": "ambiguous_subject_pool",
                    "severity": "blocker",
                    "message": "random assembly requires a subject filter when the eligible pool spans multiple subjects",
                    "details": {"subjects": known_pool_subjects},
                }
            )

        selected_pool_rows: List[Dict[str, Any]] = []
        if not validation_errors:
            rng = random.Random(seed_text)
            selected_pool_rows = rng.sample(pool_rows, required_count)

        selected_ids = [row["item_id"] for row in selected_pool_rows]
        items: List[Dict[str, Any]] = []
        seen_bundle_ids: List[str] = []
        seen_subjects: List[str] = []
        missing_item_ids: List[str] = []

        for idx, item_id in enumerate(selected_ids):
            try:
                row = self._fetch_item_row(item_id)
            except AssemblyError as exc:
                missing_item_ids.append(item_id)
                validation_errors.append(
                    {
                        "stage": exc.stage,
                        "code": exc.code,
                        "severity": "blocker",
                        "item_id": item_id,
                        "message": exc.message,
                        "details": exc.details,
                    }
                )
                continue

            bundle_id = _empty_to_default(row.get("bundle_id"))
            if bundle_id and bundle_id not in seen_bundle_ids:
                seen_bundle_ids.append(bundle_id)
            subject_value = _empty_to_default(row.get("subject"))
            if subject_value and subject_value not in seen_subjects:
                seen_subjects.append(subject_value)

            validation_issues = self._validate_item(row, item_id)
            for issue in validation_issues:
                if issue.get("severity") == "warning":
                    validation_warnings.append(issue)
                else:
                    validation_errors.append(issue)

            items.append(self._build_item(row, selection_index=idx))

        known_subjects = [s for s in seen_subjects if not _is_unknown_subject(s)]
        inferred_subject = subject or (known_subjects[0] if len(known_subjects) == 1 else "")
        if len(known_subjects) > 1:
            validation_errors.append(
                {
                    "stage": "validation",
                    "code": "mixed_subject_selection",
                    "severity": "blocker",
                    "message": "selected random items span multiple subjects",
                    "details": {"subjects": known_subjects},
                }
            )
        if subject and inferred_subject and subject != inferred_subject:
            validation_errors.append(
                {
                    "stage": "validation",
                    "code": "subject_mismatch",
                    "severity": "blocker",
                    "message": f"assembly subject {subject} does not match selected subject {inferred_subject}",
                    "details": {"requested_subject": subject, "selected_subject": inferred_subject},
                }
            )
        if not inferred_subject:
            validation_errors.append(
                {
                    "stage": "validation",
                    "code": "missing_subject",
                    "severity": "blocker",
                    "message": "unable to infer a single subject from selected random items",
                }
            )

        if len(items) != len(selected_ids):
            validation_errors.append(
                {
                    "stage": "validation",
                    "code": "missing_selected_items",
                    "severity": "blocker",
                    "message": "one or more randomly selected item ids could not be loaded",
                    "details": {"missing_item_ids": missing_item_ids},
                }
            )

        bundle_rows = self._fetch_bundle_rows(seen_bundle_ids)
        valid = not validation_errors
        assembly_id = assembly_id or f"assembly_{uuid.uuid4().hex}"
        exam_record = {
            "exam_id": exam_id or assembly_id,
            "title": title,
            "subject": inferred_subject,
            "notes": notes,
        }
        validation = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": ARTIFACT_TYPE,
            "ok": valid,
            "errors": validation_errors,
            "warnings": validation_warnings,
            "item_count": len(items),
            "required_count": required_count,
            "selected_item_count": len(items),
            "pool_count": len(pool_rows),
            "subject": inferred_subject,
            "question_types": normalized_question_types,
            "approved_only": True,
            "seed": seed_text,
        }
        artifact = self._build_assembly_artifact(
            assembly_mode="random",
            assembly_id=assembly_id,
            exam_record=exam_record,
            selection={
                "seed": seed_text,
                "required_count": required_count,
                "requested_item_ids": [],
                "selected_item_ids": selected_ids,
                "ordered_item_ids": [item["item_id"] for item in items],
                "missing_item_ids": missing_item_ids,
                "duplicate_item_ids": [],
                "approved_only": True,
                "pool_count": len(pool_rows),
                "filters": {"subject": subject or "", "question_types": normalized_question_types},
            },
            validation=validation,
            items=items,
            bundle_rows=bundle_rows,
        )

        if not valid:
            raise AssemblyError(
                "validation",
                "assembly_validation_failed",
                "random exam assembly validation failed",
                {
                    "errors": validation_errors,
                    "warnings": validation_warnings,
                    "assembly_id": assembly_id,
                    "seed": seed_text,
                },
            )

        if output_json_path:
            output_json_path = output_json_path.resolve()
            output_json_path.parent.mkdir(parents=True, exist_ok=True)
            output_json_path.write_text(_json(artifact) + "\n", encoding="utf-8")
        if output_md_path:
            output_md_path = output_md_path.resolve()
            output_md_path.parent.mkdir(parents=True, exist_ok=True)
            output_md_path.write_text(render_random_exam_assembly_md(artifact), encoding="utf-8")
        if persist:
            if output_json_path is None or output_md_path is None:
                raise AssemblyError("persist", "missing_output_paths", "persist requires output_json_path and output_md_path")
            self._persist_assembly_record(artifact, output_json_path=output_json_path, output_md_path=output_md_path)
        return artifact


def render_exam_assembly_md(artifact: Dict[str, Any]) -> str:
    mode = str(artifact.get("assembly_mode", "") or "")
    if mode == "random":
        heading = "Random Exam Assembly"
    elif mode == "fixed":
        heading = "Fixed Exam Assembly"
    else:
        heading = "Exam Assembly"
    lines = [f"# {heading}", ""]
    lines.append(f"- `assembly_id`: `{artifact.get('assembly_id', '')}`")
    lines.append(f"- `assembly_mode`: `{artifact.get('assembly_mode', '')}`")
    lines.append(f"- `source_db_path`: `{artifact.get('source_db_path', '')}`")
    exam = artifact.get("exam", {}) if isinstance(artifact.get("exam"), dict) else {}
    for key in ["exam_id", "title", "subject"]:
        value = exam.get(key, "")
        if value:
            lines.append(f"- `exam.{key}`: `{value}`")
    selection = artifact.get("selection", {}) if isinstance(artifact.get("selection"), dict) else {}
    lines.append("")
    lines.append("## Selection")
    if mode == "random":
        lines.append(f"- required_count: `{selection.get('required_count', 0)}`")
        lines.append(f"- seed: `{selection.get('seed', '')}`")
        filters = selection.get("filters", {}) if isinstance(selection.get("filters"), dict) else {}
        if filters:
            lines.append(f"- filters: `{_json(filters)}`")
        lines.append(f"- pool_count: `{selection.get('pool_count', 0)}`")
        lines.append(f"- selected: `{len(selection.get('ordered_item_ids', []))}`")
    else:
        lines.append(f"- requested: `{len(selection.get('requested_item_ids', []))}`")
        lines.append(f"- selected: `{len(selection.get('ordered_item_ids', []))}`")
    if selection.get("duplicate_item_ids"):
        lines.append(f"- duplicate_item_ids: `{selection.get('duplicate_item_ids')}`")
    if selection.get("missing_item_ids"):
        lines.append(f"- missing_item_ids: `{selection.get('missing_item_ids')}`")
    lines.append("")
    lines.append("## Summary")
    summary = artifact.get("summary", {}) if isinstance(artifact.get("summary"), dict) else {}
    for key in ["item_count", "bundle_count", "subject", "approved_only", "validation_ok", "answer_count", "rubric_count"]:
        lines.append(f"- `{key}`: `{summary.get(key, '')}`")
    lines.append("")
    lines.append("## Source Bundles")
    for bundle in artifact.get("source_bundles", []):
        if not isinstance(bundle, dict):
            continue
        lines.append(f"- `{bundle.get('bundle_id', '')}`: `{bundle.get('subject', '')}` / `{bundle.get('import_readiness', '')}` / `{bundle.get('source_publish_verdict', '')}`")
    lines.append("")
    lines.append("## Validation")
    validation = artifact.get("validation", {}) if isinstance(artifact.get("validation"), dict) else {}
    lines.append(f"- ok: `{validation.get('ok', False)}`")
    if validation.get("errors"):
        lines.append("- errors:")
        for error in validation.get("errors", []):
            if isinstance(error, dict):
                lines.append(f"  - `{error.get('code', '')}`: {error.get('message', '')}")
    if validation.get("warnings"):
        lines.append("- warnings:")
        for warning in validation.get("warnings", []):
            if isinstance(warning, dict):
                lines.append(f"  - `{warning.get('code', '')}`: {warning.get('message', '')}")
    lines.append("")
    lines.append("## Items")
    for item in artifact.get("items", []):
        if not isinstance(item, dict):
            continue
        lines.append(f"- `{item.get('selection_index', '')}` `{item.get('item_id', '')}` / `{item.get('bundle_id', '')}` / `{item.get('question_number', '')}` / `{item.get('question_type', '')}`")
    return "\n".join(lines) + "\n"


def render_fixed_exam_assembly_md(artifact: Dict[str, Any]) -> str:
    return render_exam_assembly_md(artifact)


def render_random_exam_assembly_md(artifact: Dict[str, Any]) -> str:
    return render_exam_assembly_md(artifact)


def assemble_fixed_exam(
    *,
    db_path: Optional[Path] = None,
    db_url: Optional[str] = None,
    item_ids: List[str],
    assembly_id: Optional[str] = None,
    exam_id: Optional[str] = None,
    title: str = DEFAULT_TITLE,
    subject: Optional[str] = None,
    notes: str = "",
    output_json_path: Optional[Path] = None,
    output_md_path: Optional[Path] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    service = FixedExamAssemblyService(db_path=db_path, db_url=db_url)
    try:
        return service.assemble_fixed_exam(
            item_ids=item_ids,
            assembly_id=assembly_id,
            exam_id=exam_id,
            title=title,
            subject=subject,
            notes=notes,
            output_json_path=output_json_path,
            output_md_path=output_md_path,
            persist=persist,
        )
    finally:
        service.close()


def assemble_random_exam(
    *,
    db_path: Optional[Path] = None,
    db_url: Optional[str] = None,
    required_count: int,
    seed: str,
    subject: Optional[str] = None,
    question_types: Optional[List[str]] = None,
    assembly_id: Optional[str] = None,
    exam_id: Optional[str] = None,
    title: str = DEFAULT_RANDOM_TITLE,
    notes: str = "",
    output_json_path: Optional[Path] = None,
    output_md_path: Optional[Path] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    service = RandomExamAssemblyService(db_path=db_path, db_url=db_url)
    try:
        return service.assemble_random_exam(
            required_count=required_count,
            seed=seed,
            subject=subject,
            question_types=question_types,
            assembly_id=assembly_id,
            exam_id=exam_id,
            title=title,
            notes=notes,
            output_json_path=output_json_path,
            output_md_path=output_md_path,
            persist=persist,
        )
    finally:
        service.close()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Assemble fixed or random exams from approved-import boundary items.")
    parser.add_argument("--db", type=Path, default=None, help="SQLite database path for the approved-import boundary")
    parser.add_argument("--db-url", type=str, default=None, help="Postgres database URL for the approved-import boundary")
    parser.add_argument("--mode", type=str, default="fixed", choices=["fixed", "random"], help="Assembly mode: fixed or random")
    parser.add_argument("--item-id", action="append", default=[], help="Ordered approved item_id to include in the assembly")
    parser.add_argument("--required-count", type=int, default=None, help="Required item count for random assembly")
    parser.add_argument("--seed", type=str, default=None, help="Deterministic random seed for random assembly")
    parser.add_argument("--question-type", action="append", default=[], help="Optional question_type filter for random assembly; may be repeated or comma-separated")
    parser.add_argument("--assembly-id", type=str, default=None, help="Optional assembly identifier")
    parser.add_argument("--exam-id", type=str, default=None, help="Optional exam identifier to record in the artifact")
    parser.add_argument("--title", type=str, default=None, help="Assembly title")
    parser.add_argument("--subject", type=str, default=None, help="Optional subject override; must match selected items when provided")
    parser.add_argument("--notes", type=str, default="", help="Optional assembly note")
    parser.add_argument("--persist", action="store_true", help="Persist a minimal assembly record (hybrid model)")
    parser.add_argument("--no-persist", action="store_true", help="Disable persistence of the assembly record")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory for default artifact paths")
    parser.add_argument("--output-json", type=Path, default=None, help="Output JSON artifact path")
    parser.add_argument("--output-md", type=Path, default=None, help="Output markdown summary path")
    parser.add_argument("--list-assembly-records", action="store_true", help="List persisted assembly records from qb_exam_assemblies")
    parser.add_argument("--record-assembly-id", type=str, default=None, help="Fetch a single assembly record by assembly_id")
    parser.add_argument("--record-limit", type=int, default=50, help="Limit for record listing")
    parser.add_argument("--record-order", type=str, default="desc", choices=["asc", "desc"], help="Order for record listing")
    parser.add_argument("--record-mode", type=str, default=None, choices=[None, "fixed", "random"], help="Optional assembly_mode filter for record listing")
    parser.add_argument("--records-json", type=Path, default=None, help="Output JSON path for record listing/detail")
    parser.add_argument("--records-md", type=Path, default=None, help="Output markdown path for record listing/detail")
    args = parser.parse_args(argv)

    if not args.db_url:
        args.db_url = os.environ.get("QB_DB_URL") or os.environ.get("DATABASE_URL") or None
    if args.db_url:
        db_path = None
    else:
        if args.db is None:
            raise SystemExit("provide --db-url (or QB_DB_URL/DATABASE_URL) or --db for SQLite")
        db_path = args.db.resolve()

    if args.list_assembly_records or args.record_assembly_id:
        service = FixedExamAssemblyService(db_path=db_path, db_url=args.db_url)
        try:
            if args.record_assembly_id:
                payload = service.get_assembly_record(args.record_assembly_id)
            else:
                payload = service.list_assembly_records(limit=int(args.record_limit), order=args.record_order, assembly_mode=args.record_mode)
        finally:
            service.close()
        records_json = (args.records_json or (Path.cwd() / "assembly_records.json")).resolve()
        records_md = (args.records_md or (Path.cwd() / "assembly_records.md")).resolve()
        records_json.parent.mkdir(parents=True, exist_ok=True)
        records_json.write_text(_json(payload) + "\n", encoding="utf-8")
        records_md.parent.mkdir(parents=True, exist_ok=True)
        # Minimal markdown: list view only.
        if payload.get("artifact_type") == "question_bank_exam_assembly_record_listing":
            lines = ["# Assembly Records", ""]
            lines.append(f"- backend: `{payload.get('backend','')}`")
            lines.append(f"- db_path: `{payload.get('db_path','')}`")
            lines.append(f"- record_count: `{payload.get('record_count',0)}`")
            lines.append("")
            lines.append("| created_at | assembly_id | mode | subject | item_count | selection_hash |")
            lines.append("| --- | --- | --- | --- | --- | --- |")
            for r in payload.get("records", []):
                if not isinstance(r, dict):
                    continue
                lines.append(
                    "| {created_at} | {assembly_id} | {mode} | {subject} | {n} | {h} |".format(
                        created_at=str(r.get("created_at","")),
                        assembly_id=str(r.get("assembly_id","")),
                        mode=str(r.get("assembly_mode","")),
                        subject=str(r.get("subject","")),
                        n=str(r.get("selection_item_count","")),
                        h=str(r.get("selection_hash","")),
                    )
                )
            records_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            record = payload.get("record", {}) if isinstance(payload.get("record"), dict) else {}
            lines = ["# Assembly Record", ""]
            lines.append(f"- assembly_id: `{record.get('assembly_id','')}`")
            lines.append(f"- assembly_mode: `{record.get('assembly_mode','')}`")
            lines.append(f"- created_at: `{record.get('created_at','')}`")
            lines.append(f"- subject: `{record.get('subject','')}`")
            lines.append(f"- selection_item_count: `{record.get('selection_item_count','')}`")
            lines.append(f"- selection_hash: `{record.get('selection_hash','')}`")
            lines.append(f"- artifact_json_path: `{record.get('artifact_json_path','')}`")
            lines.append(f"- artifact_md_path: `{record.get('artifact_md_path','')}`")
            records_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(_json({"records_json": str(records_json), "records_md": str(records_md), "ok": True}))
        return 0

    if args.mode == "random" and args.item_id:
        raise SystemExit("random mode does not accept --item-id; use --required-count, --seed, and optional filters")

    title = args.title or (DEFAULT_TITLE if args.mode == "fixed" else DEFAULT_RANDOM_TITLE)
    output_json_default = DEFAULT_OUTPUT_JSON if args.mode == "fixed" else DEFAULT_RANDOM_OUTPUT_JSON
    output_md_default = DEFAULT_OUTPUT_MD if args.mode == "fixed" else DEFAULT_RANDOM_OUTPUT_MD
    output_root = (args.output_dir.resolve() if args.output_dir else (db_path.parent if db_path is not None else Path.cwd())).resolve()
    output_json = (args.output_json or (output_root / output_json_default)).resolve()
    output_md = (args.output_md or (output_root / output_md_default)).resolve()
    persist = bool(args.persist) and not bool(args.no_persist)
    if args.db_url and not args.no_persist and not args.persist:
        persist = True

    try:
        if args.mode == "fixed":
            artifact = assemble_fixed_exam(
                db_path=db_path,
                db_url=args.db_url,
                item_ids=args.item_id,
                assembly_id=args.assembly_id,
                exam_id=args.exam_id,
                title=title,
                subject=args.subject,
                notes=args.notes,
                output_json_path=output_json,
                output_md_path=output_md,
                persist=persist,
            )
        else:
            if args.required_count is None:
                raise SystemExit("--required-count is required when --mode random")
            if args.seed is None:
                raise SystemExit("--seed is required when --mode random")
            artifact = assemble_random_exam(
                db_path=db_path,
                db_url=args.db_url,
                required_count=args.required_count,
                seed=args.seed,
                subject=args.subject,
                question_types=args.question_type,
                assembly_id=args.assembly_id,
                exam_id=args.exam_id,
                title=title,
                notes=args.notes,
                output_json_path=output_json,
                output_md_path=output_md,
                persist=persist,
            )
    except AssemblyError as exc:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": ARTIFACT_TYPE,
            "assembly_mode": args.mode,
            "assembly_id": args.assembly_id or "",
            "created_at": _now_iso(),
            "source_db_path": str(db_path),
            "exam": {
                "exam_id": args.exam_id or "",
                "title": title,
                "subject": args.subject or "",
                "notes": args.notes,
            },
            "selection": {
                "requested_item_ids": args.item_id if args.mode == "fixed" else [],
                "ordered_item_ids": [],
                "missing_item_ids": [],
                "duplicate_item_ids": [],
                "approved_only": True,
                "seed": args.seed or "",
                "required_count": args.required_count or 0,
                "filters": {
                    "subject": args.subject or "",
                    "question_types": _normalize_question_types(args.question_type),
                },
            },
            "validation": {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": ARTIFACT_TYPE,
                "ok": False,
                "errors": [
                    {
                        "stage": exc.stage,
                        "code": exc.code,
                        "message": exc.message,
                        "details": exc.details,
                        "severity": "blocker",
                    }
                ],
                "warnings": [],
                "approved_only": True,
            },
            "source_bundles": [],
            "items": [],
            "summary": {
                "item_count": 0,
                "bundle_count": 0,
                "subject": args.subject or "",
                "approved_only": True,
                "validation_ok": False,
                "answer_count": 0,
                "rubric_count": 0,
                "seed": args.seed or "",
                "required_count": args.required_count or 0,
                "filters": {
                    "subject": args.subject or "",
                    "question_types": _normalize_question_types(args.question_type),
                },
            },
            "ok": False,
        }
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(_json(payload) + "\n", encoding="utf-8")
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_fixed_exam_assembly_md(payload), encoding="utf-8")
        print(_json({"ok": False, "error": payload["validation"]["errors"][0], "output_json": str(output_json), "output_md": str(output_md)}))
        return 1

    print(
        _json(
            {
                "ok": True,
                "assembly_id": artifact.get("assembly_id", ""),
                "mode": artifact.get("assembly_mode", args.mode),
                "output_json": str(output_json),
                "output_md": str(output_md),
                "item_count": len(artifact.get("items", [])),
                "bundle_count": len(artifact.get("source_bundles", [])),
                "subject": artifact.get("exam", {}).get("subject", ""),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
