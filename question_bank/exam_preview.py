from __future__ import annotations

import argparse
import html as html_lib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "question_bank_exam_preview.v1"
ARTIFACT_TYPE = "exam_preview"
DEFAULT_OUTPUT_JSON = "exam_preview.json"
DEFAULT_OUTPUT_MD = "exam_preview.md"
DEFAULT_OUTPUT_HTML = "exam_preview.html"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _escape(value: Any) -> str:
    return html_lib.escape("" if value is None else str(value), quote=False)


def _load_json_object(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _first_nonempty(mapping: Dict[str, Any], keys: List[str]) -> str:
    for key in keys:
        value = mapping.get(key)
        text = "" if value is None else str(value).strip()
        if text:
            return text
    return ""


def _format_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Đúng" if value else "Sai"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).strip()
    return text


def _format_block(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, str):
        text = value.strip()
        return text or "n/a"
    return _json(value)


def _render_textual_rows(value: Any, *, prefix: str) -> List[str]:
    lines: List[str] = []
    if isinstance(value, dict):
        for key in sorted(value.keys(), key=lambda entry: str(entry)):
            row_value = value.get(key)
            lines.append(f"- {prefix} {key}: {_format_scalar(row_value)}")
    elif isinstance(value, list):
        for idx, row in enumerate(value, start=1):
            if isinstance(row, dict):
                label = row.get("label") or row.get("key") or row.get("id") or idx
                row_value = row.get("value")
                if row_value is None and len(row) == 1:
                    only_key = next(iter(row.keys()))
                    row_value = row.get(only_key)
                    label = only_key
                lines.append(f"- {prefix} {label}: {_format_scalar(row_value)}")
            else:
                lines.append(f"- {prefix} {idx}: {_format_scalar(row)}")
    return lines


def _item_label(item: Dict[str, Any]) -> str:
    question_number = item.get("question_number", "")
    question_type = item.get("question_type", "")
    item_id = item.get("item_id", "")
    return f"Câu {question_number} [{question_type}] {item_id}".strip()


def _render_question_content(item: Dict[str, Any]) -> str:
    text = _first_nonempty(
        item,
        [
            "prompt_preview",
            "question_content",
            "stem",
            "stem_preview",
            "content_preview",
            "content_text",
        ],
    )
    return text or "n/a"


def _render_choice_block(item: Dict[str, Any]) -> str:
    for key in ["choices", "options"]:
        value = item.get(key)
        if isinstance(value, list) and value:
            lines = [f"{key}:"]
            for idx, choice in enumerate(value, start=1):
                if isinstance(choice, dict):
                    label = choice.get("label") or choice.get("key") or choice.get("id") or idx
                    text = choice.get("text") or choice.get("value") or choice.get("content") or choice.get("label") or ""
                    lines.append(f"  - {label}: {_format_scalar(text)}")
                else:
                    lines.append(f"  - {idx}: {_format_scalar(choice)}")
            return "\n".join(lines)
    boolean_rows = item.get("boolean_rows")
    if boolean_rows is not None:
        lines = ["boolean_rows:"]
        lines.extend(_render_textual_rows(boolean_rows, prefix="row"))
        return "\n".join(lines)
    rows = item.get("rows")
    if rows is not None:
        lines = ["rows:"]
        lines.extend(_render_textual_rows(rows, prefix="row"))
        return "\n".join(lines)
    return ""


def _render_answer_block(item: Dict[str, Any], *, mode: str = "student") -> str:
    if mode != "teacher":
        return "withheld in student preview"
    answer_key = item.get("answer_key", {}) if isinstance(item.get("answer_key"), dict) else {}
    answer_mode = str(answer_key.get("mode", "") or "")
    value = answer_key.get("value", "")
    if answer_mode == "boolean_group":
        if isinstance(value, dict):
            lines = ["Đáp án:"]
            for key in sorted(value.keys(), key=lambda entry: str(entry)):
                lines.append(f"- {key}: {_format_scalar(value.get(key))}")
            return "\n".join(lines)
        if isinstance(value, list):
            lines = ["Đáp án:"]
            lines.extend(_render_textual_rows(value, prefix="row"))
            return "\n".join(lines)
    if answer_mode in {"single_choice", "short_answer"}:
        return f"Đáp án: {_format_scalar(value) or 'n/a'}"
    if answer_mode == "essay":
        return "Essay answer is not rendered in the preview; see rubric instead."
    if answer_mode:
        return f"answer_key.mode={answer_mode}: {_format_block(value)}"
    if value not in {"", None, []}:
        return f"Đáp án: {_format_block(value)}"
    return "n/a"


def _render_rubric_block(item: Dict[str, Any], *, mode: str = "student") -> str:
    if mode != "teacher":
        return "withheld in student preview"
    rubric = item.get("rubric", {}) if isinstance(item.get("rubric"), dict) else {}
    rubric_text = str(rubric.get("rubric_text", "") or "").strip()
    if rubric_text:
        return rubric_text
    rubric_json = rubric.get("rubric_json", {})
    if isinstance(rubric_json, dict):
        return str(rubric_json.get("rubric_text", "") or "").strip()
    if rubric_json:
        return _format_block(rubric_json)
    return "n/a"


def _render_provenance_lines(item: Dict[str, Any]) -> List[str]:
    lines = [
        f"- bundle_id: `{item.get('bundle_id', '')}`",
        f"- source_item_id: `{item.get('item_id', '')}`",
        f"- source import provenance: `{item.get('approved_source', '')}` / `{item.get('import_mode', '')}` / `{item.get('import_readiness', '')}`",
        f"- reconciliation: `{(item.get('reconciliation') or {}).get('status', '')}`",
    ]
    question_type = item.get("question_type", "")
    document_family = item.get("document_family", "")
    if question_type:
        lines.append(f"- question_type: `{question_type}`")
    if document_family:
        lines.append(f"- document_family: `{document_family}`")
    if item.get("qa_flags"):
        lines.append(f"- qa_flags: `{_json(item.get('qa_flags'))}`")
    return lines


def render_exam_preview_markdown(artifact: Dict[str, Any], *, mode: str = "student") -> str:
    exam = artifact.get("exam", {}) if isinstance(artifact.get("exam"), dict) else {}
    selection = artifact.get("selection", {}) if isinstance(artifact.get("selection"), dict) else {}
    lines = ["# Exam Preview", ""]
    lines.append(f"- `assembly_id`: `{artifact.get('assembly_id', '')}`")
    lines.append(f"- `assembly_mode`: `{artifact.get('assembly_mode', '')}`")
    lines.append(f"- `exam.exam_id`: `{exam.get('exam_id', '')}`")
    lines.append(f"- `exam.title`: `{exam.get('title', '')}`")
    lines.append(f"- `exam.subject`: `{exam.get('subject', '')}`")
    lines.append(f"- `preview_mode`: `{mode}`")
    if artifact.get("summary") and isinstance(artifact.get("summary"), dict):
        summary = artifact["summary"]
        if summary.get("seed"):
            lines.append(f"- `seed`: `{summary.get('seed', '')}`")
        if summary.get("required_count") is not None:
            lines.append(f"- `required_count`: `{summary.get('required_count', '')}`")
        lines.append(f"- `item_count`: `{summary.get('item_count', '')}`")
        lines.append(f"- `bundle_count`: `{summary.get('bundle_count', '')}`")
    lines.append("")
    lines.append("## Ordered Questions")
    lines.append(f"- count: `{len(artifact.get('items', []))}`")
    lines.append("")
    for item in artifact.get("items", []):
        if not isinstance(item, dict):
            continue
        lines.append(f"### {_item_label(item)}")
        lines.extend(_render_provenance_lines(item))
        lines.append("- question content:")
        question_content = _render_question_content(item)
        for line in question_content.splitlines() or ["n/a"]:
            lines.append(f"  - {line}")
        choice_block = _render_choice_block(item)
        if choice_block:
            lines.append("- structured content:")
            for line in choice_block.splitlines():
                lines.append(f"  - {line}")
        answer_block = _render_answer_block(item, mode=mode)
        lines.append(f"- answer visibility: `{'visible' if mode == 'teacher' else 'hidden'}`")
        lines.append("- answer:")
        for line in answer_block.splitlines() or ["n/a"]:
            lines.append(f"  - {line}")
        rubric_block = _render_rubric_block(item, mode=mode)
        lines.append(f"- rubric visibility: `{'visible' if mode == 'teacher' else 'hidden'}`")
        lines.append("- rubric:")
        for line in rubric_block.splitlines() or ["n/a"]:
            lines.append(f"  - {line}")
        answer_sources = item.get("answer_sources", [])
        if isinstance(answer_sources, list) and answer_sources:
            lines.append("- answer_sources:")
            for source in answer_sources:
                if isinstance(source, dict):
                    lines.append(
                        f"  - `{source.get('source_type', '')}` / `{source.get('strength', '')}`"
                    )
                else:
                    lines.append(f"  - `{_format_scalar(source)}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_exam_preview_html(artifact: Dict[str, Any], *, mode: str = "student") -> str:
    exam = artifact.get("exam", {}) if isinstance(artifact.get("exam"), dict) else {}
    items = artifact.get("items", []) if isinstance(artifact.get("items"), list) else []
    rows: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        question_content = _escape(_render_question_content(item))
        choice_block = _escape(_render_choice_block(item))
        answer_text = _escape(_render_answer_block(item, mode=mode))
        rubric_text = _escape(_render_rubric_block(item, mode=mode))
        provenance_bits = []
        provenance_bits.append(f"<span>bundle_id: {_escape(item.get('bundle_id', ''))}</span>")
        provenance_bits.append(f"<span>item_id: {_escape(item.get('item_id', ''))}</span>")
        provenance_bits.append(
            f"<span>provenance: {_escape(item.get('approved_source', ''))} / {_escape(item.get('import_mode', ''))} / {_escape(item.get('import_readiness', ''))}</span>"
        )
        provenance_bits.append(f"<span>reconciliation: {_escape((item.get('reconciliation') or {}).get('status', ''))}</span>")
        question_type = _escape(item.get("question_type", ""))
        document_family = _escape(item.get("document_family", ""))
        if question_type:
            provenance_bits.append(f"<span>question_type: {question_type}</span>")
        if document_family:
            provenance_bits.append(f"<span>document_family: {document_family}</span>")
        section_parts = [
            "<section class='question'>",
            f"<h3>{_escape(_item_label(item))}</h3>",
            f"<div class='meta'>{''.join(provenance_bits)}</div>",
            f"<div class='block'><strong>Question content</strong><div class='content'>{question_content}</div></div>",
        ]
        if choice_block:
            section_parts.append(f"<div class='block'><strong>Structured content</strong><pre>{choice_block}</pre></div>")
        visibility = "visible" if mode == "teacher" else "hidden"
        section_parts.append(
            f"<div class='block'><strong>Answer visibility</strong><span class='badge {visibility}'>{visibility}</span></div>"
        )
        section_parts.append(f"<div class='block'><strong>Answer</strong><pre>{answer_text}</pre></div>")
        section_parts.append(
            f"<div class='block'><strong>Rubric visibility</strong><span class='badge {visibility}'>{visibility}</span></div>"
        )
        section_parts.append(f"<div class='block'><strong>Rubric</strong><pre>{rubric_text}</pre></div>")
        answer_sources = item.get("answer_sources", [])
        if isinstance(answer_sources, list) and answer_sources:
            source_lines = []
            for source in answer_sources:
                if isinstance(source, dict):
                    source_lines.append(f"- {source.get('source_type', '')} / {source.get('strength', '')}")
                else:
                    source_lines.append(f"- {_format_scalar(source)}")
            section_parts.append(
                f"<div class='block'><strong>Answer sources</strong><pre>{_escape(chr(10).join(source_lines))}</pre></div>"
            )
        section_parts.append("</section>")
        rows.append("".join(section_parts))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape(exam.get('title', 'Exam Preview'))}</title>
  <style>
    body {{ font-family: Inter, system-ui, sans-serif; margin: 0; padding: 24px; background: #0b1020; color: #e5e7eb; }}
    .wrap {{ max-width: 1100px; margin: 0 auto; }}
    .panel {{ background: #111827; border: 1px solid #334155; border-radius: 12px; padding: 18px; margin-bottom: 18px; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }}
    .meta span {{ background: rgba(56,189,248,.12); border: 1px solid rgba(56,189,248,.3); border-radius: 999px; padding: 4px 8px; font-size: 12px; }}
    .question {{ background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 14px; }}
    .question h3 {{ margin: 0 0 8px 0; }}
    .block {{ margin-top: 12px; }}
    .content, pre {{ white-space: pre-wrap; margin: 8px 0 0 0; }}
    pre {{ padding: 12px; border-radius: 8px; background: rgba(15,23,42,.7); border: 1px solid #334155; color: #e5e7eb; }}
    .content {{ color: #dbeafe; }}
    .empty {{ color: #94a3b8; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; margin-left: 8px; font-size: 12px; }}
    .badge.visible {{ background: rgba(16,185,129,.14); border: 1px solid rgba(16,185,129,.35); color: #bbf7d0; }}
    .badge.hidden {{ background: rgba(148,163,184,.14); border: 1px solid rgba(148,163,184,.35); color: #cbd5e1; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <h1>{_escape(exam.get('title', 'Exam Preview'))}</h1>
      <div class="meta">
        <span>assembly_id: {_escape(artifact.get('assembly_id', ''))}</span>
        <span>assembly_mode: {_escape(artifact.get('assembly_mode', ''))}</span>
        <span>exam_id: {_escape(exam.get('exam_id', ''))}</span>
        <span>subject: {_escape(exam.get('subject', ''))}</span>
        <span>mode: {_escape(mode)}</span>
      </div>
      <div class="empty">Preview-only rendering of assembled exam artifacts. Student mode hides answers and rubrics; teacher mode shows them.</div>
    </div>
    {''.join(rows) if rows else '<div class=\"panel empty\">No items to preview.</div>'}
  </div>
</body>
</html>
"""


def write_exam_preview(
    artifact_path: Path,
    *,
    output_json_path: Optional[Path] = None,
    output_md_path: Optional[Path] = None,
    output_html_path: Optional[Path] = None,
    mode: str = "student",
) -> Dict[str, Any]:
    artifact_path = artifact_path.resolve()
    artifact = _load_json_object(artifact_path)
    visible_answer_count = 0
    visible_rubric_count = 0
    for item in artifact.get("items", []):
        if not isinstance(item, dict):
            continue
        if mode == "teacher" and _render_answer_block(item, mode=mode) not in {"", "n/a"}:
            visible_answer_count += 1
        if mode == "teacher" and _render_rubric_block(item, mode=mode) not in {"", "n/a"}:
            visible_rubric_count += 1
    preview = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "source_artifact_path": str(artifact_path),
        "preview_mode": mode,
        "assembly_id": artifact.get("assembly_id", ""),
        "assembly_mode": artifact.get("assembly_mode", ""),
        "exam": artifact.get("exam", {}),
        "item_count": len(artifact.get("items", [])) if isinstance(artifact.get("items"), list) else 0,
        "visible_answer_count": visible_answer_count,
        "visible_rubric_count": visible_rubric_count,
        "ok": True,
    }
    if output_json_path:
        output_json_path = output_json_path.resolve()
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        preview["output_json_path"] = str(output_json_path)
    if output_md_path:
        output_md_path = output_md_path.resolve()
        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        output_md_path.write_text(render_exam_preview_markdown(artifact, mode=mode), encoding="utf-8")
        preview["output_md_path"] = str(output_md_path)
    if output_html_path:
        output_html_path = output_html_path.resolve()
        output_html_path.parent.mkdir(parents=True, exist_ok=True)
        output_html_path.write_text(render_exam_preview_html(artifact, mode=mode), encoding="utf-8")
        preview["output_html_path"] = str(output_html_path)
    if output_json_path:
        output_json_path.write_text(_json(preview) + "\n", encoding="utf-8")
    return preview


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Render a minimal preview for an assembled exam artifact.")
    parser.add_argument("--artifact", type=Path, default=None, help="Path to an assembled exam JSON artifact")
    parser.add_argument("--assembly-id", type=str, default=None, help="Resolve a persisted assembly record by assembly_id")
    parser.add_argument("--db", type=Path, default=None, help="SQLite approved-import boundary DB (when using --assembly-id)")
    parser.add_argument("--db-url", type=str, default=None, help="Postgres URL (when using --assembly-id; or QB_DB_URL/DATABASE_URL)")
    parser.add_argument("--mode", type=str, default="student", choices=["student", "teacher"], help="Preview mode")
    parser.add_argument("--output-json", type=Path, default=None, help="Output JSON preview summary path")
    parser.add_argument("--output-md", type=Path, default=None, help="Output markdown preview path")
    parser.add_argument("--output-html", type=Path, default=None, help="Output HTML preview path")
    args = parser.parse_args(argv)

    if bool(args.artifact) == bool(args.assembly_id):
        raise SystemExit("provide exactly one of --artifact or --assembly-id")

    if args.assembly_id:
        from .exam_assembly import resolve_persisted_assembly_artifact_path

        resolved = resolve_persisted_assembly_artifact_path(
            assembly_id=str(args.assembly_id),
            db_path=(args.db.resolve() if args.db else None),
            db_url=args.db_url,
        )
        artifact_path = resolved
    else:
        artifact_path = args.artifact.resolve()

    output_json = (args.output_json or artifact_path.parent / DEFAULT_OUTPUT_JSON).resolve()
    output_md = (args.output_md or artifact_path.parent / DEFAULT_OUTPUT_MD).resolve()
    output_html = (args.output_html or artifact_path.parent / DEFAULT_OUTPUT_HTML).resolve()

    result = write_exam_preview(
        artifact_path,
        output_json_path=output_json,
        output_md_path=output_md,
        output_html_path=output_html,
        mode=args.mode,
    )
    print(_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
