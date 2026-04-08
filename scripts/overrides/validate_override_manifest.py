#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

SCHEMA_VERSION = "override_manifest.v1"

SUBJECTS = {"generic", "chemistry", "physics", "math", "biology"}
OUTPUT_MODES = {"internal", "publish"}

ACTIONS = {
    "asset_visibility",
    "asset_role_override",
    "placement_override",
    "text_patch",
    "publish_exception",
    "answer_override",
}

ASSET_ROLES = {
    "equation",
    "diagram",
    "chart",
    "chemical-diagram",
    "generic-image",
    "unknown-preview",
}

PLACEMENTS = {
    "inline",
    "display",
    "context-right",
    "context-below",
    "centered",
    "table-cell",
    "unknown",
}

TEXT_TARGETS = {"html", "visible_text", "stem_html", "solution_html"}
MATCH_MODES = {"literal", "regex"}
SEVERITIES = {"info", "warning", "error", "blocker"}
VISIBILITY_VALUES = {"keep", "suppress"}

MATCH_KEYS = {
    "exam_id",
    "question_id",
    "question_number",
    "asset_id",
    "asset_src",
    "asset_src_contains",
    "prog_id",
    "source_ext",
    "fallback_type",
    "css_class_contains",
}

NON_GLOBAL_ACTIONS = {
    "asset_visibility",
    "asset_role_override",
    "placement_override",
    "text_patch",
    "answer_override",
}

ANSWER_OVERRIDE_MODES = {"single_choice", "boolean_group", "short_answer", "rubric", "none"}


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_date_yyyy_mm_dd(value: str) -> bool:
    try:
        dt.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _validate_source(source: Any, errors: List[str]) -> None:
    if source is None:
        return
    if not isinstance(source, dict):
        errors.append("source must be an object")
        return

    subject = source.get("subject")
    if subject is not None and subject not in SUBJECTS:
        errors.append(f"source.subject must be one of {sorted(SUBJECTS)}")

    output_mode = source.get("output_mode")
    if output_mode is not None and output_mode not in OUTPUT_MODES:
        errors.append(f"source.output_mode must be one of {sorted(OUTPUT_MODES)}")


def _validate_match(match_obj: Any, action: str, errors: List[str], prefix: str) -> None:
    if action in NON_GLOBAL_ACTIONS:
        if not isinstance(match_obj, dict) or not match_obj:
            errors.append(f"{prefix}.match must be a non-empty object for action {action}")
            return
    elif match_obj is None:
        return
    elif not isinstance(match_obj, dict):
        errors.append(f"{prefix}.match must be an object when provided")
        return

    if not isinstance(match_obj, dict):
        return

    unknown_keys = set(match_obj.keys()) - MATCH_KEYS
    if unknown_keys:
        errors.append(f"{prefix}.match has unknown keys: {sorted(unknown_keys)}")


def _validate_override(override: Any, seen_ids: Set[str], errors: List[str], warnings: List[str], index: int) -> None:
    prefix = f"overrides[{index}]"
    if not isinstance(override, dict):
        errors.append(f"{prefix} must be an object")
        return

    ov_id = override.get("id")
    if not _is_non_empty_string(ov_id):
        errors.append(f"{prefix}.id is required and must be a non-empty string")
    else:
        if ov_id in seen_ids:
            errors.append(f"duplicate override id: {ov_id}")
        seen_ids.add(ov_id)

    enabled = override.get("enabled", True)
    if not isinstance(enabled, bool):
        errors.append(f"{prefix}.enabled must be boolean when provided")

    action = override.get("action")
    if action not in ACTIONS:
        errors.append(f"{prefix}.action must be one of {sorted(ACTIONS)}")
        return

    _validate_match(override.get("match"), action, errors, prefix)

    value = override.get("value")
    if not isinstance(value, dict):
        errors.append(f"{prefix}.value must be an object")
        return

    if not _is_non_empty_string(override.get("reason")):
        errors.append(f"{prefix}.reason is required")

    if not _is_non_empty_string(override.get("owner")):
        errors.append(f"{prefix}.owner is required")

    expires_on = override.get("expires_on")
    ticket = override.get("ticket")

    if action == "asset_visibility":
        visibility = value.get("visibility")
        if visibility not in VISIBILITY_VALUES:
            errors.append(f"{prefix}.value.visibility must be one of {sorted(VISIBILITY_VALUES)}")

    elif action == "asset_role_override":
        role = value.get("role")
        if role not in ASSET_ROLES:
            errors.append(f"{prefix}.value.role must be one of {sorted(ASSET_ROLES)}")

    elif action == "placement_override":
        placement = value.get("placement")
        if placement not in PLACEMENTS:
            errors.append(f"{prefix}.value.placement must be one of {sorted(PLACEMENTS)}")

    elif action == "text_patch":
        target = value.get("target")
        if target not in TEXT_TARGETS:
            errors.append(f"{prefix}.value.target must be one of {sorted(TEXT_TARGETS)}")

        match_mode = value.get("match_mode")
        if match_mode not in MATCH_MODES:
            errors.append(f"{prefix}.value.match_mode must be one of {sorted(MATCH_MODES)}")

        find = value.get("find")
        if not _is_non_empty_string(find):
            errors.append(f"{prefix}.value.find is required for text_patch")
        elif match_mode == "regex":
            try:
                re.compile(find)
            except re.error as exc:
                errors.append(f"{prefix}.value.find regex is invalid: {exc}")

        if "replace" not in value or not isinstance(value.get("replace"), str):
            errors.append(f"{prefix}.value.replace must be a string for text_patch")

        if "max_replacements" in value:
            mr = value.get("max_replacements")
            if not isinstance(mr, int) or mr <= 0:
                errors.append(f"{prefix}.value.max_replacements must be a positive integer")

    elif action == "publish_exception":
        metric = value.get("metric")
        if not _is_non_empty_string(metric):
            errors.append(f"{prefix}.value.metric is required for publish_exception")

        allow_if_lte = value.get("allow_if_lte")
        if not isinstance(allow_if_lte, (int, float)):
            errors.append(f"{prefix}.value.allow_if_lte must be numeric")

        severity_override = value.get("severity_override")
        if severity_override is not None and severity_override not in SEVERITIES:
            errors.append(f"{prefix}.value.severity_override must be one of {sorted(SEVERITIES)}")

        if not _is_non_empty_string(ticket):
            errors.append(f"{prefix}.ticket is required for publish_exception")

        if not _is_non_empty_string(expires_on):
            errors.append(f"{prefix}.expires_on is required for publish_exception")
        elif not _validate_date_yyyy_mm_dd(expires_on):
            errors.append(f"{prefix}.expires_on must use YYYY-MM-DD")

    elif action == "answer_override":
        mode = value.get("mode")
        if mode not in ANSWER_OVERRIDE_MODES:
            errors.append(f"{prefix}.value.mode must be one of {sorted(ANSWER_OVERRIDE_MODES)}")
        if mode == "single_choice":
            choice_value = value.get("value")
            if not isinstance(choice_value, str) or choice_value.strip().upper() not in {"A", "B", "C", "D"}:
                errors.append(f"{prefix}.value.value must be one of A/B/C/D for single_choice answer_override")
        elif mode == "boolean_group":
            subanswers = value.get("subanswers")
            if not isinstance(subanswers, dict) or not subanswers:
                errors.append(f"{prefix}.value.subanswers must be a non-empty object for boolean_group answer_override")
            else:
                for key, bool_value in subanswers.items():
                    if str(key).lower() not in {"a", "b", "c", "d"}:
                        errors.append(f"{prefix}.value.subanswers has invalid key '{key}'")
                    if not isinstance(bool_value, bool):
                        errors.append(f"{prefix}.value.subanswers.{key} must be boolean")
        elif mode == "short_answer":
            accepted_answers = value.get("accepted_answers")
            raw_value = value.get("value")
            if accepted_answers is None and not _is_non_empty_string(raw_value):
                errors.append(f"{prefix}.value requires accepted_answers or value for short_answer answer_override")
            if accepted_answers is not None and not isinstance(accepted_answers, list):
                errors.append(f"{prefix}.value.accepted_answers must be an array when provided")
        elif mode == "rubric":
            has_text = _is_non_empty_string(value.get("rubric_text"))
            has_blocks = isinstance(value.get("blocks"), list) and len(value.get("blocks")) > 0
            if not has_text and not has_blocks:
                errors.append(f"{prefix}.value requires rubric_text or blocks for rubric answer_override")

    if _is_non_empty_string(expires_on):
        if not _validate_date_yyyy_mm_dd(expires_on):
            errors.append(f"{prefix}.expires_on must use YYYY-MM-DD")
        else:
            exp = dt.date.fromisoformat(expires_on)
            if exp < dt.date.today():
                warnings.append(f"{prefix} has expired (expires_on={expires_on})")


def validate_manifest(payload: Any) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(payload, dict):
        return {
            "ok": False,
            "errors": ["manifest root must be an object"],
            "warnings": warnings,
            "summary": {},
        }

    schema_version = payload.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    manifest_id = payload.get("manifest_id")
    if not _is_non_empty_string(manifest_id):
        errors.append("manifest_id is required")

    _validate_source(payload.get("source"), errors)

    overrides = payload.get("overrides")
    if not isinstance(overrides, list) or not overrides:
        errors.append("overrides must be a non-empty array")
        overrides = []

    seen_ids: Set[str] = set()
    for idx, override in enumerate(overrides):
        _validate_override(override, seen_ids, errors, warnings, idx)

    action_counts: Dict[str, int] = {}
    enabled_count = 0
    for ov in overrides:
        if not isinstance(ov, dict):
            continue
        action = ov.get("action")
        if isinstance(action, str):
            action_counts[action] = action_counts.get(action, 0) + 1
        if ov.get("enabled", True) is True:
            enabled_count += 1

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "schema_version": payload.get("schema_version"),
            "manifest_id": payload.get("manifest_id"),
            "override_count": len(overrides),
            "enabled_override_count": enabled_count,
            "action_counts": dict(sorted(action_counts.items(), key=lambda kv: kv[0])),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate override manifest v1")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, default=None)
    args = parser.parse_args()

    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"manifest not found: {args.manifest}", file=sys.stderr)
        raise SystemExit(2)
    except json.JSONDecodeError as exc:
        print(f"invalid JSON: {exc}", file=sys.stderr)
        raise SystemExit(2)

    result = validate_manifest(payload)

    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if result["warnings"]:
        for msg in result["warnings"]:
            print(f"warning: {msg}", file=sys.stderr)

    if result["ok"]:
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2, sort_keys=True))
        return

    for msg in result["errors"]:
        print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
