#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_keys(payload: Dict[str, Any], required: List[str], prefix: str, errors: List[str]) -> None:
    for key in required:
        if key not in payload:
            errors.append(f"{prefix}: missing required key '{key}'")


def validate_contract_dir(contract_dir: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    required_artifacts = config.get("required_artifacts", {})
    expected_schema_versions = config.get("expected_schema_versions", {})
    expected_artifact_types = config.get("expected_artifact_types", {})
    required_top_level_keys = config.get("required_top_level_keys", {})

    artifact_payloads: Dict[str, Dict[str, Any]] = {}
    for artifact_name, filename in required_artifacts.items():
        path = contract_dir / str(filename)
        if not path.exists():
            errors.append(f"missing required artifact file: {filename}")
            continue
        try:
            payload = _load_json(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"invalid JSON in {filename}: {exc}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"artifact {filename} must contain a JSON object")
            continue
        artifact_payloads[artifact_name] = payload

    for artifact_name, payload in artifact_payloads.items():
        expected_schema = expected_schema_versions.get(artifact_name)
        if expected_schema and payload.get("schema_version") != expected_schema:
            errors.append(
                f"{artifact_name}: schema_version mismatch (expected {expected_schema}, got {payload.get('schema_version')})"
            )
        expected_type = expected_artifact_types.get(artifact_name)
        if expected_type and payload.get("artifact_type") != expected_type:
            errors.append(
                f"{artifact_name}: artifact_type mismatch (expected {expected_type}, got {payload.get('artifact_type')})"
            )

        req_keys = required_top_level_keys.get(artifact_name, [])
        if isinstance(req_keys, list):
            _require_keys(payload, [str(k) for k in req_keys], artifact_name, errors)

    bundle_ids = {
        str(payload.get("bundle_id"))
        for payload in artifact_payloads.values()
        if payload.get("bundle_id") is not None
    }
    if len(bundle_ids) > 1:
        errors.append(f"bundle_id mismatch across artifacts: {sorted(bundle_ids)}")

    manifest = artifact_payloads.get("manifest")
    if isinstance(manifest, dict):
        manifest_artifacts = manifest.get("artifacts", {})
        if not isinstance(manifest_artifacts, dict):
            errors.append("manifest: artifacts must be an object")
        else:
            for name in config.get("manifest_required_artifacts", []):
                if name not in manifest_artifacts:
                    errors.append(f"manifest: artifacts missing key '{name}'")

        enums = manifest.get("enums", {})
        if not isinstance(enums, dict):
            errors.append("manifest: enums must be an object")
        else:
            required_enums = config.get("manifest_required_enum_values", {})
            if isinstance(required_enums, dict):
                for enum_key, required_values in required_enums.items():
                    actual = enums.get(enum_key)
                    if not isinstance(actual, list):
                        errors.append(f"manifest: enum '{enum_key}' must be a list")
                        continue
                    actual_set = {str(v) for v in actual}
                    missing = [str(v) for v in required_values if str(v) not in actual_set]
                    if missing:
                        errors.append(f"manifest: enum '{enum_key}' missing required values: {missing}")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "contract_dir": str(contract_dir),
            "artifact_count_checked": len(artifact_payloads),
            "required_artifact_count": len(required_artifacts),
            "bundle_id": next(iter(bundle_ids)) if bundle_ids else "",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check output contract compatibility and detect schema drift.")
    parser.add_argument("--contract-dir", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().with_name("contract_compatibility_v1.json"),
    )
    parser.add_argument("--summary-json", type=Path, default=None)
    args = parser.parse_args()

    try:
        config = _load_json(args.config.resolve())
    except Exception as exc:  # noqa: BLE001
        print(f"failed to read compatibility config: {exc}", file=sys.stderr)
        raise SystemExit(2)

    result = validate_contract_dir(args.contract_dir.resolve(), config)

    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if result["warnings"]:
        for warning in result["warnings"]:
            print(f"warning: {warning}", file=sys.stderr)

    if result["ok"]:
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2, sort_keys=True))
        return

    for error in result["errors"]:
        print(f"error: {error}", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
