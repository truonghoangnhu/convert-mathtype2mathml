from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol
from urllib.parse import urlparse, urlunparse

try:  # pragma: no cover - optional dependency
    import psycopg
    from psycopg.rows import dict_row as psycopg_dict_row
except Exception:  # noqa: BLE001
    psycopg = None
    psycopg_dict_row = None

SCHEMA_VERSION = "question_bank_approved_import.v1"
OUTPUT_CONTRACT_VERSION = "output_contract.v1"
DEFAULT_APPROVED_SOURCE = "review_finalize"
DEFAULT_DB_FILENAME = "question_bank_import.sqlite"
DEFAULT_JOB_LISTING_FILENAME = "question_bank_import_jobs.json"
DEFAULT_JOB_LISTING_MD_FILENAME = "question_bank_import_jobs.md"
DEFAULT_DASHBOARD_HTML_FILENAME = "question_bank_import_dashboard.html"
READINESS_APPROVED = "approved_importable"
READINESS_DRAFT = "draft_importable"
READINESS_BLOCKED = "blocked_import"
IMPORT_MODES = {"approved-only", "allow-draft"}


@dataclass
class ImportBoundaryError(Exception):
    stage: str
    code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.details:
            return f"{self.stage}:{self.code}: {self.message} ({self.details})"
        return f"{self.stage}:{self.code}: {self.message}"


class ApprovedImportAdapter(Protocol):
    db_path: Path

    def ensure_schema(self) -> None: ...

    def begin(self) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def write_import_job(self, row: Dict[str, Any]) -> None: ...

    def write_exam_bundle(self, row: Dict[str, Any]) -> None: ...

    def write_question(self, row: Dict[str, Any]) -> None: ...

    def write_answer(self, row: Dict[str, Any]) -> None: ...

    def write_rubric(self, row: Dict[str, Any]) -> None: ...

    def update_import_job_summary(self, import_job_id: str, summary_json: str) -> None: ...

    def list_jobs(
        self,
        *,
        bundle_id: Optional[str] = None,
        limit: Optional[int] = None,
        order: str = "desc",
    ) -> Dict[str, Any]: ...

    def close(self) -> None: ...


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:  # noqa: BLE001
        return default


def _safe_json_parse(value: Any, default: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        return default
    try:
        return json.loads(value)
    except Exception:  # noqa: BLE001
        return default


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _redact_db_url_for_display(database_url: str) -> str:
    # Avoid leaking credentials into reports/dashboards/error details. Keep enough
    # detail for operators to identify the target host/db.
    try:
        parsed = urlparse(str(database_url))
    except Exception:  # noqa: BLE001
        return "<redacted-db-url>"
    if not parsed.scheme:
        return "<redacted-db-url>"
    username = parsed.username or ""
    hostname = parsed.hostname or ""
    port = parsed.port
    netloc = hostname
    if username:
        netloc = f"{username}@{hostname}"
    if port is not None:
        netloc = f"{netloc}:{port}"
    return urlunparse((parsed.scheme, netloc, parsed.path or "", "", "", ""))


class SQLiteApprovedImportAdapter:
    def __init__(self, db_path: Path):
        self.db_path = db_path.resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        if getattr(self, "conn", None) is not None:
            self.conn.close()
            self.conn = None

    def begin(self) -> None:
        self._execute("BEGIN", (), "transaction", "begin_failed")

    def commit(self) -> None:
        try:
            self.conn.commit()
        except sqlite3.DatabaseError as exc:  # noqa: PERF203
            raise ImportBoundaryError("commit", "sqlite_commit_failed", str(exc), {"db_path": str(self.db_path)}) from exc

    def rollback(self) -> None:
        try:
            self.conn.rollback()
        except sqlite3.DatabaseError as exc:  # noqa: PERF203
            raise ImportBoundaryError("rollback", "sqlite_rollback_failed", str(exc), {"db_path": str(self.db_path)}) from exc

    def ensure_schema(self) -> None:
        try:
            self.conn.executescript(
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
                    document_family_confidence REAL,
                    source_priority_path_json TEXT NOT NULL,
                    parser_warning_codes_json TEXT NOT NULL,
                    answer_detection_json TEXT NOT NULL,
                    rubric_detection_json TEXT NOT NULL,
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
                    answer_detection_json TEXT NOT NULL,
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
                    rubric_detection_json TEXT NOT NULL,
                    imported_at TEXT NOT NULL,
                    approved_source TEXT NOT NULL,
                    FOREIGN KEY(item_id) REFERENCES approved_questions(item_id),
                    FOREIGN KEY(bundle_id) REFERENCES approved_exam_bundles(bundle_id),
                    FOREIGN KEY(import_job_id) REFERENCES approved_import_jobs(import_job_id)
                );
                """
            )
        except sqlite3.DatabaseError as exc:  # noqa: PERF203
            raise ImportBoundaryError("schema", "sqlite_schema_failed", str(exc), {"db_path": str(self.db_path)}) from exc

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
                    ("document_family_confidence", "REAL"),
                    ("source_priority_path_json", "TEXT"),
                    ("parser_warning_codes_json", "TEXT"),
                    ("answer_detection_json", "TEXT"),
                    ("rubric_detection_json", "TEXT"),
                ],
            "approved_question_answers": [
                ("import_mode", "TEXT"),
                ("import_readiness", "TEXT"),
                ("import_readiness_reason", "TEXT"),
                ("import_readiness_json", "TEXT"),
                ("source_publish_verdict", "TEXT"),
                ("answer_detection_json", "TEXT"),
            ],
            "approved_question_rubrics": [
                ("import_mode", "TEXT"),
                ("import_readiness", "TEXT"),
                ("import_readiness_reason", "TEXT"),
                ("import_readiness_json", "TEXT"),
                ("source_publish_verdict", "TEXT"),
                ("rubric_detection_json", "TEXT"),
            ],
        }

        try:
            for table, columns in extra_columns.items():
                existing = {row[1] for row in self.conn.execute(f"PRAGMA table_info({table})")}
                for column_name, column_type in columns:
                    if column_name not in existing:
                        self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}")
        except sqlite3.DatabaseError as exc:  # noqa: PERF203
            raise ImportBoundaryError("schema", "sqlite_schema_migrate_failed", str(exc), {"db_path": str(self.db_path)}) from exc

    def _execute(self, sql: str, params: tuple[Any, ...], stage: str, code: str) -> None:
        try:
            self.conn.execute(sql, params)
        except sqlite3.DatabaseError as exc:  # noqa: PERF203
            raise ImportBoundaryError(stage, code, str(exc), {"db_path": str(self.db_path), "sql": sql}) from exc

    def _upsert(self, table: str, row: Dict[str, Any], conflict_key: str) -> None:
        cols = list(row.keys())
        assignments = ", ".join([f"{col}=excluded.{col}" for col in cols if col != conflict_key])
        sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['?' for _ in cols])}) ON CONFLICT({conflict_key}) DO UPDATE SET {assignments}"
        try:
            self.conn.execute(sql, tuple(row[col] for col in cols))
        except sqlite3.DatabaseError as exc:  # noqa: PERF203
            raise ImportBoundaryError("write", f"sqlite_upsert_{table}_failed", str(exc), {"db_path": str(self.db_path), "table": table}) from exc

    def write_import_job(self, row: Dict[str, Any]) -> None:
        self._upsert("approved_import_jobs", row, "import_job_id")

    def write_exam_bundle(self, row: Dict[str, Any]) -> None:
        self._upsert("approved_exam_bundles", row, "bundle_id")

    def write_question(self, row: Dict[str, Any]) -> None:
        self._upsert("approved_questions", row, "item_id")

    def write_answer(self, row: Dict[str, Any]) -> None:
        self._upsert("approved_question_answers", row, "item_id")

    def write_rubric(self, row: Dict[str, Any]) -> None:
        self._upsert("approved_question_rubrics", row, "item_id")

    def update_import_job_summary(self, import_job_id: str, summary_json: str) -> None:
        self._execute(
            "UPDATE approved_import_jobs SET import_summary_json = ? WHERE import_job_id = ?",
            (summary_json, import_job_id),
            "write",
            "sqlite_update_job_summary_failed",
        )

    def list_jobs(
        self,
        *,
        bundle_id: Optional[str] = None,
        limit: Optional[int] = None,
        order: str = "desc",
    ) -> Dict[str, Any]:
        if not self.db_path.exists():
            raise FileNotFoundError(f"SQLite database does not exist: {self.db_path}")
        order_sql = "DESC" if str(order).lower() != "asc" else "ASC"
        params: List[Any] = []
        clauses = []
        if bundle_id:
            clauses.append("bundle_id = ?")
            params.append(bundle_id)
        query = (
            "SELECT import_job_id, bundle_id, subject, approved_source, import_mode, import_readiness, "
            "import_readiness_reason, import_readiness_json, source_publish_verdict, import_decision, imported_at, "
            "source_exam_bundle_path, source_question_bank_items_path, validation_ok, validation_report_json, import_summary_json "
            "FROM approved_import_jobs"
        )
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += f" ORDER BY imported_at {order_sql}, import_job_id {order_sql}"
        if limit is not None:
            query += " LIMIT ?"
            params.append(int(limit))

        warnings: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        rows: List[Dict[str, Any]] = []
        try:
            existing_columns = {row[1] for row in self.conn.execute("PRAGMA table_info(approved_import_jobs)")}
            has_import_decision = "import_decision" in existing_columns
            cursor = self.conn.execute(query, tuple(params))
            for row in cursor.fetchall():
                summary = _safe_json_parse(row["import_summary_json"], {})
                rows.append(
                    {
                        "import_job_id": row["import_job_id"],
                        "bundle_id": row["bundle_id"],
                        "subject": row["subject"],
                        "approved_source": row["approved_source"],
                        "import_mode": row["import_mode"],
                        "import_readiness": row["import_readiness"],
                        "import_readiness_reason": row["import_readiness_reason"],
                        "source_publish_verdict": row["source_publish_verdict"],
                        "import_decision": row["import_decision"] if has_import_decision else str(summary.get("import_decision", "")),
                        "imported_at": row["imported_at"],
                        "decision": str(summary.get("import_decision", "")),
                        "import_allowed": bool(summary.get("import_allowed", False)),
                        "validation_ok": bool(row["validation_ok"]),
                        "source_exam_bundle_path": row["source_exam_bundle_path"],
                        "source_question_bank_items_path": row["source_question_bank_items_path"],
                        "table_counts": summary.get("table_counts", {}),
                        "status_breakdown": summary.get("status_breakdown", {}),
                    }
                )
        except sqlite3.DatabaseError as exc:  # noqa: PERF203
            errors.append({"code": "sqlite_query_failed", "message": str(exc), "stage": "query", "db_path": str(self.db_path)})

        decision_counts = Counter(str(row.get("decision", "")) or "<empty>" for row in rows)
        readiness_counts = Counter(str(row.get("import_readiness", "")) or "<empty>" for row in rows)
        return {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "question_bank_import_job_listing",
            "db_path": str(self.db_path),
            "bundle_id_filter": bundle_id or "",
            "limit": limit if limit is not None else "",
            "order": order_sql.lower(),
            "job_count": len(rows),
            "decision_counts": dict(decision_counts),
            "readiness_counts": dict(readiness_counts),
            "jobs": rows,
            "warnings": warnings,
            "errors": errors,
            "ok": not errors,
        }


class PostgresApprovedImportAdapter:
    def __init__(self, database_url: str, *, display_name: Optional[str] = None):
        if psycopg is None:  # pragma: no cover - exercised only when dependency missing
            raise ImportBoundaryError(
                "init",
                "postgres_driver_missing",
                "psycopg is required for PostgresApprovedImportAdapter",
                {"database_url": _redact_db_url_for_display(str(database_url))},
            )
        self.database_url = str(database_url)
        self.database_url_display = _redact_db_url_for_display(self.database_url)
        self.db_path = Path(display_name or self._default_display_name(self.database_url_display))
        self.conn = psycopg.connect(self.database_url, row_factory=psycopg_dict_row)

    @staticmethod
    def _default_display_name(database_url_display: str) -> str:
        safe = database_url_display.replace("://", "__").replace("/", "__").replace("?", "__").replace("&", "__")
        return f"postgresql__{safe}"

    def close(self) -> None:
        if getattr(self, "conn", None) is not None:
            self.conn.close()
            self.conn = None

    def begin(self) -> None:
        try:
            self.conn.execute("BEGIN")
        except Exception as exc:  # noqa: BLE001
            raise ImportBoundaryError("transaction", "postgres_begin_failed", str(exc), {"database_url": self.database_url_display}) from exc

    def commit(self) -> None:
        try:
            self.conn.commit()
        except Exception as exc:  # noqa: BLE001
            raise ImportBoundaryError("commit", "postgres_commit_failed", str(exc), {"database_url": self.database_url_display}) from exc

    def rollback(self) -> None:
        try:
            self.conn.rollback()
        except Exception as exc:  # noqa: BLE001
            raise ImportBoundaryError("rollback", "postgres_rollback_failed", str(exc), {"database_url": self.database_url_display}) from exc

    def ensure_schema(self) -> None:
        try:
            self.conn.execute(
                """
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
                )
                """
            )
            self.conn.execute(
                """
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
                )
                """
            )
            self.conn.execute(
                """
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
                    document_family_confidence DOUBLE PRECISION,
                    source_priority_path_json TEXT NOT NULL,
                    parser_warning_codes_json TEXT NOT NULL,
                    answer_detection_json TEXT NOT NULL,
                    rubric_detection_json TEXT NOT NULL,
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
                )
                """
            )
            self.conn.execute(
                """
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
                    answer_detection_json TEXT NOT NULL,
                    imported_at TEXT NOT NULL,
                    approved_source TEXT NOT NULL,
                    FOREIGN KEY(item_id) REFERENCES approved_questions(item_id),
                    FOREIGN KEY(bundle_id) REFERENCES approved_exam_bundles(bundle_id),
                    FOREIGN KEY(import_job_id) REFERENCES approved_import_jobs(import_job_id)
                )
                """
            )
            self.conn.execute(
                """
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
                    rubric_detection_json TEXT NOT NULL,
                    imported_at TEXT NOT NULL,
                    approved_source TEXT NOT NULL,
                    FOREIGN KEY(item_id) REFERENCES approved_questions(item_id),
                    FOREIGN KEY(bundle_id) REFERENCES approved_exam_bundles(bundle_id),
                    FOREIGN KEY(import_job_id) REFERENCES approved_import_jobs(import_job_id)
                )
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
                    ("document_family_confidence", "DOUBLE PRECISION"),
                    ("source_priority_path_json", "TEXT"),
                    ("parser_warning_codes_json", "TEXT"),
                    ("answer_detection_json", "TEXT"),
                    ("rubric_detection_json", "TEXT"),
                ],
                "approved_question_answers": [
                    ("import_mode", "TEXT"),
                    ("import_readiness", "TEXT"),
                    ("import_readiness_reason", "TEXT"),
                    ("import_readiness_json", "TEXT"),
                    ("source_publish_verdict", "TEXT"),
                    ("answer_detection_json", "TEXT"),
                ],
                "approved_question_rubrics": [
                    ("import_mode", "TEXT"),
                    ("import_readiness", "TEXT"),
                    ("import_readiness_reason", "TEXT"),
                    ("import_readiness_json", "TEXT"),
                    ("source_publish_verdict", "TEXT"),
                    ("rubric_detection_json", "TEXT"),
                ],
            }
            for table, columns in extra_columns.items():
                for column_name, column_type in columns:
                    self.conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column_name} {column_type}")
        except Exception as exc:  # noqa: BLE001
            raise ImportBoundaryError("schema", "postgres_schema_failed", str(exc), {"database_url": self.database_url_display}) from exc

    def _execute(self, sql: str, params: tuple[Any, ...], stage: str, code: str) -> None:
        try:
            self.conn.execute(sql, params)
        except Exception as exc:  # noqa: BLE001
            raise ImportBoundaryError(stage, code, str(exc), {"database_url": self.database_url_display, "sql": sql}) from exc

    def _upsert(self, table: str, row: Dict[str, Any], conflict_key: str) -> None:
        cols = list(row.keys())
        assignments = ", ".join([f"{col}=excluded.{col}" for col in cols if col != conflict_key])
        sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s' for _ in cols])}) ON CONFLICT({conflict_key}) DO UPDATE SET {assignments}"
        try:
            self.conn.execute(sql, tuple(row[col] for col in cols))
        except Exception as exc:  # noqa: BLE001
            raise ImportBoundaryError(
                "write",
                f"postgres_upsert_{table}_failed",
                str(exc),
                {"database_url": self.database_url_display, "table": table},
            ) from exc

    def write_import_job(self, row: Dict[str, Any]) -> None:
        self._upsert("approved_import_jobs", row, "import_job_id")

    def write_exam_bundle(self, row: Dict[str, Any]) -> None:
        self._upsert("approved_exam_bundles", row, "bundle_id")

    def write_question(self, row: Dict[str, Any]) -> None:
        self._upsert("approved_questions", row, "item_id")

    def write_answer(self, row: Dict[str, Any]) -> None:
        self._upsert("approved_question_answers", row, "item_id")

    def write_rubric(self, row: Dict[str, Any]) -> None:
        self._upsert("approved_question_rubrics", row, "item_id")

    def update_import_job_summary(self, import_job_id: str, summary_json: str) -> None:
        self._execute(
            "UPDATE approved_import_jobs SET import_summary_json = %s WHERE import_job_id = %s",
            (summary_json, import_job_id),
            "write",
            "postgres_update_job_summary_failed",
        )

    def list_jobs(
        self,
        *,
        bundle_id: Optional[str] = None,
        limit: Optional[int] = None,
        order: str = "desc",
    ) -> Dict[str, Any]:
        order_sql = "DESC" if str(order).lower() != "asc" else "ASC"
        params: List[Any] = []
        clauses = []
        if bundle_id:
            clauses.append("bundle_id = %s")
            params.append(bundle_id)
        query = (
            "SELECT import_job_id, bundle_id, subject, approved_source, import_mode, import_readiness, "
            "import_readiness_reason, import_readiness_json, source_publish_verdict, import_decision, imported_at, "
            "source_exam_bundle_path, source_question_bank_items_path, validation_ok, validation_report_json, import_summary_json "
            "FROM approved_import_jobs"
        )
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += f" ORDER BY imported_at {order_sql}, import_job_id {order_sql}"
        if limit is not None:
            query += " LIMIT %s"
            params.append(int(limit))

        warnings: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        rows: List[Dict[str, Any]] = []
        try:
            self.ensure_schema()
            cursor = self.conn.execute(query, tuple(params))
            for row in cursor.fetchall():
                row = dict(row)
                summary = _safe_json_parse(row["import_summary_json"], {})
                rows.append(
                    {
                        "import_job_id": row["import_job_id"],
                        "bundle_id": row["bundle_id"],
                        "subject": row["subject"],
                        "approved_source": row["approved_source"],
                        "import_mode": row["import_mode"],
                        "import_readiness": row["import_readiness"],
                        "import_readiness_reason": row["import_readiness_reason"],
                        "source_publish_verdict": row["source_publish_verdict"],
                        "import_decision": row["import_decision"] if row["import_decision"] is not None else str(summary.get("import_decision", "")),
                        "imported_at": row["imported_at"],
                        "decision": str(summary.get("import_decision", "")),
                        "import_allowed": bool(summary.get("import_allowed", False)),
                        "validation_ok": bool(row["validation_ok"]),
                        "source_exam_bundle_path": row["source_exam_bundle_path"],
                        "source_question_bank_items_path": row["source_question_bank_items_path"],
                        "table_counts": summary.get("table_counts", {}),
                        "status_breakdown": summary.get("status_breakdown", {}),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            errors.append({"code": "postgres_query_failed", "message": str(exc), "stage": "query", "database_url": self.database_url_display})

        decision_counts = Counter(str(row.get("decision", "")) or "<empty>" for row in rows)
        readiness_counts = Counter(str(row.get("import_readiness", "")) or "<empty>" for row in rows)
        return {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "question_bank_import_job_listing",
            "db_path": str(self.db_path),
            "bundle_id_filter": bundle_id or "",
            "limit": limit if limit is not None else "",
            "order": order_sql.lower(),
            "job_count": len(rows),
            "decision_counts": dict(decision_counts),
            "readiness_counts": dict(readiness_counts),
            "jobs": rows,
            "warnings": warnings,
            "errors": errors,
            "ok": not errors,
        }


def create_approved_import_adapter(db_path: Path, *, db_url: Optional[str] = None) -> ApprovedImportAdapter:
    if db_url:
        return PostgresApprovedImportAdapter(db_url)
    return SQLiteApprovedImportAdapter(db_path)
