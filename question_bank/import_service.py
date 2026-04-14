from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from .import_boundary import ImportBoundaryError, ApprovedImportAdapter, DEFAULT_APPROVED_SOURCE, READINESS_BLOCKED, READINESS_DRAFT, _json, _now_iso, _safe_int


class ApprovedImportService:
    def __init__(self, adapter: ApprovedImportAdapter):
        self.adapter = adapter

    def close(self) -> None:
        self.adapter.close()

    def list_jobs(self, *, bundle_id: Optional[str] = None, limit: Optional[int] = None, order: str = "desc") -> Dict[str, Any]:
        return self.adapter.list_jobs(bundle_id=bundle_id, limit=limit, order=order)

    def persist_import(
        self,
        *,
        exam_bundle: Dict[str, Any],
        question_bank_items: Dict[str, Any],
        validation: Dict[str, Any],
        readiness: Dict[str, Any],
        summary: Dict[str, Any],
        import_mode: str,
        approved_source: str = DEFAULT_APPROVED_SOURCE,
        imported_at: str,
        dry_run: bool = False,
        exam_bundle_path: Path,
        question_bank_items_path: Path,
    ) -> Dict[str, Any]:
        items = question_bank_items.get("items") if isinstance(question_bank_items.get("items"), list) else []
        summary = dict(summary)
        summary.setdefault("import_boundary", {})
        summary["import_boundary"].update(
            {
                "adapter": self.adapter.__class__.__name__,
                "validation_first": True,
                "dry_run": dry_run,
            }
        )

        if dry_run:
            summary["import_boundary"]["decision"] = "dry_run"
            summary["import_boundary"]["persisted"] = False
            return {"summary": summary, "imported": False, "db_path": str(self.adapter.db_path)}

        if not validation.get("ok", False) or readiness.get("state") == READINESS_BLOCKED:
            summary["import_boundary"]["decision"] = summary.get("import_decision", "blocked")
            summary["import_boundary"]["persisted"] = False
            return {"summary": summary, "imported": False, "db_path": str(self.adapter.db_path)}

        if readiness.get("state") == READINESS_DRAFT and import_mode != "allow-draft":
            summary["import_boundary"]["decision"] = "skipped_by_mode"
            summary["import_boundary"]["persisted"] = False
            return {"summary": summary, "imported": False, "db_path": str(self.adapter.db_path)}

        reconciliation_counts: Counter[str] = Counter()
        question_type_counts: Counter[str] = Counter()
        answer_mode_counts: Counter[str] = Counter()
        rubric_mode_counts: Counter[str] = Counter()

        import_job_id = str(summary.get("import_job_id", "") or "")
        if not import_job_id:
            raise ImportBoundaryError("summary", "missing_import_job_id", "import summary is missing import_job_id")

        try:
            self.adapter.ensure_schema()
            self.adapter.begin()
            self.adapter.write_import_job(
                {
                    "import_job_id": import_job_id,
                    "bundle_id": str(validation.get("bundle_id", "")),
                    "subject": str(validation.get("subject", "")),
                    "approved_source": approved_source,
                    "import_mode": import_mode,
                    "import_readiness": readiness["state"],
                    "import_readiness_reason": readiness["reason"],
                    "import_readiness_json": _json(readiness),
                    "source_publish_verdict": readiness["evidence"]["publish_verdict"],
                    "import_decision": str(summary.get("import_decision", "")),
                    "imported_at": imported_at,
                    "source_exam_bundle_path": str(exam_bundle_path),
                    "source_question_bank_items_path": str(question_bank_items_path),
                    "validation_ok": 1,
                    "validation_report_json": _json(validation),
                    "import_summary_json": _json(summary),
                }
            )

            self.adapter.write_exam_bundle(
                {
                    "bundle_id": str(validation.get("bundle_id", "")),
                    "import_job_id": import_job_id,
                    "subject": str(validation.get("subject", "")),
                    "approved_source": approved_source,
                    "import_mode": import_mode,
                    "import_readiness": readiness["state"],
                    "import_readiness_reason": readiness["reason"],
                    "import_readiness_json": _json(readiness),
                    "source_publish_verdict": readiness["evidence"]["publish_verdict"],
                    "imported_at": imported_at,
                    "schema_version": str(exam_bundle.get("schema_version", "")),
                    "artifact_type": str(exam_bundle.get("artifact_type", "")),
                    "output_mode": str(exam_bundle.get("output_mode", "")),
                    "question_item_count": _safe_int(exam_bundle.get("question_item_count"), 0),
                    "summary_json": _json(exam_bundle.get("summary", {})),
                    "answer_summary_json": _json(exam_bundle.get("answer_summary", {})),
                    "answer_qa_summary_json": _json(exam_bundle.get("answer_qa_summary", {})),
                    "source_json": _json(exam_bundle.get("source", {})),
                }
            )

            for item in items:
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("item_id", "") or "")
                answer_key = item.get("answer_key") if isinstance(item.get("answer_key"), dict) else {}
                reconciliation = item.get("reconciliation") if isinstance(item.get("reconciliation"), dict) else {}
                answer_detection = item.get("answer_detection") if isinstance(item.get("answer_detection"), dict) else {}
                rubric_detection = item.get("rubric_detection") if isinstance(item.get("rubric_detection"), dict) else {}
                rubric = item.get("rubric")
                answer_mode = str(answer_key.get("mode", "") or "")
                reconciliation_status = str(reconciliation.get("status", "") or "")
                rubric_mode = str(rubric.get("mode", "") if isinstance(rubric, dict) else "" or "")
                rubric_text = ""
                if isinstance(rubric, dict):
                    rubric_text = str(rubric.get("rubric_text", "") or "")
                reconciliation_counts[reconciliation_status or "<empty>"] += 1
                question_type_counts[str(item.get("question_type", "") or "") or "<empty>"] += 1
                answer_mode_counts[answer_mode or "<empty>"] += 1
                rubric_mode_counts[rubric_mode or "<empty>"] += 1

                self.adapter.write_question(
                    {
                        "item_id": item_id,
                        "bundle_id": str(validation.get("bundle_id", "")),
                        "import_job_id": import_job_id,
                        "exam_id": str(item.get("exam_id", "") or ""),
                        "subject": str(validation.get("subject", "")),
                        "question_number": _safe_int(item.get("question_number"), 0),
                        "question_type": str(item.get("question_type", "") or ""),
                        "placement": str(item.get("placement", "") or ""),
                        "prompt_preview": str(item.get("prompt_preview", "") or ""),
                        "document_family": str(item.get("document_family", validation.get("summary", {}).get("document_family", "")) or ""),
                        "document_family_confidence": item.get("document_family_confidence", validation.get("summary", {}).get("document_family_confidence", None)),
                        "source_priority_path_json": _json(item.get("source_priority_path", [])),
                        "parser_warning_codes_json": _json(item.get("parser_warning_codes", [])),
                        "answer_detection_json": _json(answer_detection),
                        "rubric_detection_json": _json(rubric_detection),
                        "import_mode": import_mode,
                        "import_readiness": readiness["state"],
                        "import_readiness_reason": readiness["reason"],
                        "import_readiness_json": _json(readiness),
                        "source_publish_verdict": readiness["evidence"]["publish_verdict"],
                        "qa_flags_json": _json(item.get("qa_flags", [])),
                        "imported_at": imported_at,
                        "approved_source": approved_source,
                    }
                )

                self.adapter.write_answer(
                    {
                        "item_id": item_id,
                        "bundle_id": str(validation.get("bundle_id", "")),
                        "import_job_id": import_job_id,
                        "answer_mode": answer_mode,
                        "import_mode": import_mode,
                        "import_readiness": readiness["state"],
                        "import_readiness_reason": readiness["reason"],
                        "import_readiness_json": _json(readiness),
                        "source_publish_verdict": readiness["evidence"]["publish_verdict"],
                        "answer_key_json": _json(item.get("answer_key", {})),
                        "answer_sources_json": _json(item.get("answer_sources", [])),
                        "reconciliation_json": _json(item.get("reconciliation", {})),
                        "answer_detection_json": _json(answer_detection),
                        "imported_at": imported_at,
                        "approved_source": approved_source,
                    }
                )

                self.adapter.write_rubric(
                    {
                        "item_id": item_id,
                        "bundle_id": str(validation.get("bundle_id", "")),
                        "import_job_id": import_job_id,
                        "rubric_mode": rubric_mode,
                        "import_mode": import_mode,
                        "import_readiness": readiness["state"],
                        "import_readiness_reason": readiness["reason"],
                        "import_readiness_json": _json(readiness),
                        "source_publish_verdict": readiness["evidence"]["publish_verdict"],
                        "rubric_text": rubric_text,
                        "rubric_json": _json(rubric if isinstance(rubric, (dict, list)) else {}),
                        "rubric_detection_json": _json(rubric_detection),
                        "imported_at": imported_at,
                        "approved_source": approved_source,
                    }
                )

            summary["table_counts"] = {
                "approved_import_jobs": 1,
                "approved_exam_bundles": 1,
                "approved_questions": len(items),
                "approved_question_answers": len(items),
                "approved_question_rubrics": len(items),
            }
            summary["status_breakdown"] = {
                "reconciliation": dict(reconciliation_counts),
                "question_type": dict(question_type_counts),
                "answer_mode": dict(answer_mode_counts),
                "rubric_mode": dict(rubric_mode_counts),
                "import_readiness": readiness["state"],
                "import_mode": import_mode,
                "publish_verdict": readiness["evidence"]["publish_verdict"],
            }
            summary["import_boundary"].update(
                {
                    "adapter": self.adapter.__class__.__name__,
                    "validation_first": True,
                    "dry_run": False,
                    "decision": str(summary.get("import_decision", "")),
                    "persisted": True,
                }
            )
            self.adapter.update_import_job_summary(import_job_id, _json(summary))
            self.adapter.commit()
        except ImportBoundaryError as exc:
            try:
                self.adapter.rollback()
            except Exception:  # noqa: BLE001
                pass
            summary.setdefault("errors", [])
            summary["errors"].append(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "stage": exc.stage,
                    "details": exc.details,
                }
            )
            summary["error_count"] = _safe_int(summary.get("error_count"), 0) + 1
            summary.setdefault("import_boundary", {})
            summary["import_boundary"].update(
                {
                    "adapter": self.adapter.__class__.__name__,
                    "validation_first": True,
                    "dry_run": dry_run,
                    "persisted": False,
                    "error": {
                        "stage": exc.stage,
                        "code": exc.code,
                        "message": exc.message,
                    },
                }
            )
            return {"summary": summary, "imported": False, "db_path": str(self.adapter.db_path), "error": summary["errors"][-1]}
        finally:
            pass

        return {"summary": summary, "imported": True, "db_path": str(self.adapter.db_path)}
