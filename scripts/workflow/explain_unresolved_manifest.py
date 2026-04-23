#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from zipfile import ZipFile


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRESET_CONFIG = REPO_ROOT / "scripts" / "workflow" / "docx_patch_smoke_presets.json"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "v": "urn:schemas-microsoft-com:vml",
    "o": "urn:schemas-microsoft-com:office:office",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

ROOT_CAUSE_ORDER = [
    "NON_EQUATION_OBJECT_SUPPRESSED_FROM_MANIFEST",
    "EMPTY_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST",
    "UNUSABLE_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST",
    "USABLE_GENERATED_SIDECAR_MISSING_FROM_MANIFEST",
    "MANIFEST_ENTRY_POINTS_TO_MISSING_SIDECAR",
    "MANIFEST_ENTRY_POINTS_TO_UNUSABLE_SIDECAR",
    "LEAF_FALLBACK_AMBIGUOUS",
    "NO_GENERATED_BIN_SIDECAR",
    "MANIFEST_MISSING_ENTRY",
]

DECISION_ORDER = [
    "FIX_MATCHING_BUG",
    "INVESTIGATE_TRANSPECT_OUTPUT",
    "CORPUS_DATA_ISSUE",
    "NO_ACTION",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Explain unresolved manifest cases for one or more patch smoke presets.")
    parser.add_argument("--preset", action="append", default=[], help="Preset name from the smoke preset registry. Repeat to inspect multiple presets.")
    parser.add_argument("--all-presets", action="store_true", help="Inspect every preset from the preset registry.")
    parser.add_argument("--preset-config", default=str(DEFAULT_PRESET_CONFIG), help="Preset registry JSON.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    args = parser.parse_args()

    try:
        preset_registry = load_preset_registry(Path(args.preset_config).resolve())
        preset_names = select_preset_names(preset_registry, args.preset, args.all_presets)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    reports = [analyze_preset(preset_registry[name]) for name in preset_names]
    aggregate = aggregate_reports(reports)

    if args.format == "json":
        print(json.dumps({"presets": reports, "aggregate": aggregate}, ensure_ascii=True, indent=2))
    else:
        emit_text(reports, aggregate)
    return 0


def load_preset_registry(config_path: Path) -> dict[str, dict]:
    if not config_path.exists():
        raise FileNotFoundError(f"Preset config not found: {config_path}")
    data = json.loads(config_path.read_text(encoding="utf-8"))
    presets = {}
    for raw_preset in data.get("presets", []):
        name = raw_preset["name"]
        if name in presets:
            raise ValueError(f"Duplicate preset name in config: {name}")
        manifest = (REPO_ROOT / raw_preset["manifest"]).resolve()
        presets[name] = {
            "name": name,
            "subject": raw_preset.get("subject", "unknown"),
            "input": (REPO_ROOT / raw_preset["input"]).resolve(),
            "manifest": manifest,
            "workdir": manifest.parent,
        }
    return presets


def select_preset_names(preset_registry: dict[str, dict], explicit_names: list[str], all_presets: bool) -> list[str]:
    if explicit_names and all_presets:
        raise ValueError("Choose either --preset or --all-presets, not both.")
    if not explicit_names and not all_presets:
        raise ValueError("Choose at least one --preset or use --all-presets.")
    if all_presets:
        return list(preset_registry)
    missing = [name for name in explicit_names if name not in preset_registry]
    if missing:
        available = ", ".join(sorted(preset_registry))
        raise ValueError(f"Unknown preset(s): {', '.join(missing)}. Available presets: {available}")
    seen = set()
    ordered = []
    for name in explicit_names:
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def analyze_preset(preset: dict) -> dict:
    manifest_index = load_manifest_index(preset["manifest"])
    state = load_json_if_exists(preset["workdir"] / "tmp" / "state.json")
    lineage_report = load_json_if_exists(preset["workdir"] / "manifest.lineage-report.json")
    occurrences = load_occurrences(preset["input"])
    unresolved_cases = []
    for occurrence in occurrences:
        ole_diag = diagnose_manifest_part(occurrence.get("ole_part"), manifest_index)
        preview_diag = diagnose_manifest_part(occurrence.get("preview_part"), manifest_index)
        if ole_diag["resolved"] or preview_diag["resolved"]:
            continue
        case = enrich_unresolved_case(
            preset=preset,
            occurrence=occurrence,
            manifest_index=manifest_index,
            state=state,
            lineage_report=lineage_report,
            ole_diag=ole_diag,
            preview_diag=preview_diag,
            occurrences=occurrences,
        )
        unresolved_cases.append(case)

    root_cause_counts = Counter(case["root_cause"] for case in unresolved_cases)
    decision = decide_label(unresolved_cases)
    return {
        "preset": preset["name"],
        "subject": preset["subject"],
        "input": str(preset["input"]),
        "manifest": str(preset["manifest"]),
        "workdir": str(preset["workdir"]),
        "unresolved_case_count": len(unresolved_cases),
        "root_cause_counts": order_counter(root_cause_counts, ROOT_CAUSE_ORDER),
        "decision": decision,
        "cases": unresolved_cases,
        "lineage_report": summarize_lineage_report(lineage_report),
    }


def load_manifest_index(manifest_path: Path) -> dict:
    entries = []
    by_part = {}
    by_leaf = {}
    if manifest_path.exists():
        for raw_line in manifest_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "\t" not in line:
                continue
            part_name, rel_path = line.split("\t", 1)
            normalized = normalize_part_name(part_name)
            abs_path = (manifest_path.parent / rel_path).resolve()
            entry = {
                "part": normalized,
                "leaf": leaf_name(normalized),
                "rel_path": rel_path,
                "abs_path": str(abs_path),
                "sidecar_exists": abs_path.exists(),
                "sidecar_status": mathml_status(abs_path),
            }
            entry["sidecar_usable"] = entry["sidecar_status"] == "usable"
            entries.append(entry)
            by_part[normalized] = entry
            by_leaf.setdefault(entry["leaf"], []).append(entry)
    return {"entries": entries, "by_part": by_part, "by_leaf": by_leaf}


def load_json_if_exists(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_occurrences(docx_path: Path) -> list[dict]:
    occurrences = []
    with ZipFile(docx_path) as zf:
        document_root = ET.fromstring(zf.read("word/document.xml"))
        rels_root = ET.fromstring(zf.read("word/_rels/document.xml.rels"))
        rel_by_id = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels_root}
        paragraph_index = -1
        for paragraph in document_root.findall(".//w:p", NS):
            paragraph_index += 1
            paragraph_text = clean_excerpt("".join(text.text or "" for text in paragraph.findall(".//w:t", NS)))
            runs = paragraph.findall("./w:r", NS)
            for run_index, run in enumerate(runs):
                objects = run.findall(".//w:object", NS)
                for object_index, obj in enumerate(objects):
                    ole_object = obj.find(".//o:OLEObject", NS)
                    image_data = obj.find(".//v:imagedata", NS)
                    ole_rel_id = attribute_by_name(ole_object, NS["r"], "id")
                    preview_rel_id = attribute_by_name(image_data, NS["r"], "id")
                    ole_target = normalize_part_name(resolve_target(rel_by_id.get(ole_rel_id)))
                    preview_target = normalize_part_name(resolve_target(rel_by_id.get(preview_rel_id)))
                    source_type = detect_source_type(ole_target, preview_target)
                    occurrences.append(
                        {
                            "paragraph_index": paragraph_index,
                            "run_index": run_index,
                            "object_index": object_index,
                            "paragraph_text": paragraph_text,
                            "source_type": source_type,
                            "prog_id": attribute_by_name(ole_object, None, "ProgID"),
                            "ole_part": ole_target,
                            "preview_part": preview_target,
                            "ole_rel_id": ole_rel_id,
                            "preview_rel_id": preview_rel_id,
                        }
                    )
    return occurrences


def enrich_unresolved_case(
    preset: dict,
    occurrence: dict,
    manifest_index: dict,
    state: dict,
    lineage_report: dict,
    ole_diag: dict,
    preview_diag: dict,
    occurrences: list[dict],
) -> dict:
    state_pair = find_state_pair(state, occurrence.get("ole_part"), occurrence.get("preview_part"))
    object_kind = state_pair.get("object_kind") or "unknown"
    prog_id = state_pair.get("prog_id") or occurrence.get("prog_id") or "unknown"
    bin_hash = None
    preview_hash = None
    if occurrence.get("ole_part"):
        bin_hash = state.get("bin_part_to_hash", {}).get(occurrence["ole_part"])
    if occurrence.get("preview_part"):
        preview_hash = state.get("wmf_part_to_hash", {}).get(occurrence["preview_part"])

    bin_sidecar_path = None
    bin_sidecar_exists = False
    bin_sidecar_usable = False
    bin_sidecar_status = "missing"
    if bin_hash:
        candidate = preset["workdir"] / "mathml" / "bin" / f"{bin_hash}.bin.mathml"
        bin_sidecar_path = str(candidate)
        bin_sidecar_exists = candidate.exists()
        bin_sidecar_status = mathml_status(candidate)
        bin_sidecar_usable = bin_sidecar_status == "usable"

    preview_sidecar_path = None
    preview_sidecar_exists = False
    preview_sidecar_usable = False
    preview_sidecar_status = "missing"
    if preview_hash:
        candidate = preset["workdir"] / "mathml" / "wmf" / f"{preview_hash}.wmf.mathml"
        preview_sidecar_path = str(candidate)
        preview_sidecar_exists = candidate.exists()
        preview_sidecar_status = mathml_status(candidate)
        preview_sidecar_usable = preview_sidecar_status == "usable"

    ole_sha256 = hash_zip_part(preset["input"], occurrence.get("ole_part"))
    preview_sha256 = hash_zip_part(preset["input"], occurrence.get("preview_part"))
    preview_use_count = sum(1 for item in occurrences if item.get("preview_part") == occurrence.get("preview_part"))
    ole_hash_reuse_count = 0
    if ole_sha256:
        ole_hash_reuse_count = sum(
            1 for item in occurrences if hash_zip_part(preset["input"], item.get("ole_part")) == ole_sha256
        )

    case = {
        "paragraph_index": occurrence["paragraph_index"],
        "run_index": occurrence["run_index"],
        "object_index": occurrence["object_index"],
        "source_type": occurrence["source_type"],
        "paragraph_text": occurrence["paragraph_text"],
        "prog_id": prog_id,
        "object_kind": object_kind,
        "ole_part": occurrence.get("ole_part"),
        "preview_part": occurrence.get("preview_part"),
        "ole_rel_id": occurrence.get("ole_rel_id"),
        "preview_rel_id": occurrence.get("preview_rel_id"),
        "ole_manifest": ole_diag,
        "preview_manifest": preview_diag,
        "ole_sha256": ole_sha256,
        "preview_sha256": preview_sha256,
        "ole_hash_reuse_count": ole_hash_reuse_count,
        "preview_use_count": preview_use_count,
        "bin_hash": bin_hash,
        "preview_hash": preview_hash,
        "bin_staged": has_stage_file(preset["workdir"] / "stage" / "bin-src", bin_hash, ".bin"),
        "bin_needed": occurrence.get("ole_part") in state.get("bins_needed", []),
        "bin_queued_for_convert": has_stage_file(preset["workdir"] / "stage" / "bin-convert-src", bin_hash, ".bin"),
        "bin_sidecar_path": bin_sidecar_path,
        "bin_sidecar_exists": bin_sidecar_exists,
        "bin_sidecar_usable": bin_sidecar_usable,
        "bin_sidecar_status": bin_sidecar_status,
        "preview_suppressed_non_equation": occurrence.get("preview_part") in state.get("suppressed_non_equation_preview_parts", []),
        "preview_sidecar_path": preview_sidecar_path,
        "preview_sidecar_exists": preview_sidecar_exists,
        "preview_sidecar_usable": preview_sidecar_usable,
        "preview_sidecar_status": preview_sidecar_status,
        "lineage_pair_marked_unresolved": is_lineage_pair_unresolved(lineage_report, occurrence.get("ole_part"), occurrence.get("preview_part")),
    }
    case["root_cause"] = classify_root_cause(case)
    case["decision"] = decision_for_root_cause(case["root_cause"])
    return case


def summarize_lineage_report(lineage_report: dict) -> dict:
    if not lineage_report:
        return {}
    return {
        "manifest_entry_count": lineage_report.get("manifest_entry_count"),
        "wmf_manifest_entries": lineage_report.get("wmf_manifest_entries"),
        "bin_manifest_entries": lineage_report.get("bin_manifest_entries"),
        "dsmt4_total": lineage_report.get("dsmt4_total"),
        "dsmt4_manifest_mapped": lineage_report.get("dsmt4_manifest_mapped"),
        "dsmt4_unresolved_after_generation": lineage_report.get("dsmt4_unresolved_after_generation"),
    }


def classify_root_cause(case: dict) -> str:
    if case["object_kind"] not in {"equation", "unknown", "", None}:
        return "NON_EQUATION_OBJECT_SUPPRESSED_FROM_MANIFEST"
    if has_manifest_entry_problem(case["ole_manifest"]) or has_manifest_entry_problem(case["preview_manifest"]):
        if has_missing_sidecar(case["ole_manifest"]) or has_missing_sidecar(case["preview_manifest"]):
            return "MANIFEST_ENTRY_POINTS_TO_MISSING_SIDECAR"
        return "MANIFEST_ENTRY_POINTS_TO_UNUSABLE_SIDECAR"
    if case["ole_manifest"]["ambiguous_leaf"] or case["preview_manifest"]["ambiguous_leaf"]:
        return "LEAF_FALLBACK_AMBIGUOUS"
    generated_statuses = {case["bin_sidecar_status"], case["preview_sidecar_status"]}
    if "usable" in generated_statuses:
        return "USABLE_GENERATED_SIDECAR_MISSING_FROM_MANIFEST"
    if "empty_math" in generated_statuses:
        return "EMPTY_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST"
    if any(status not in {"missing", "usable", "empty_math"} for status in generated_statuses):
        return "UNUSABLE_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST"
    if case["bin_needed"]:
        return "NO_GENERATED_BIN_SIDECAR"
    return "MANIFEST_MISSING_ENTRY"


def has_manifest_entry_problem(diag: dict) -> bool:
    return diag["exact_manifest_hit"] and not diag["resolved"]


def has_missing_sidecar(diag: dict) -> bool:
    return diag["exact_manifest_hit"] and not diag["exact_sidecar_exists"]


def decision_for_root_cause(root_cause: str) -> str:
    if root_cause in {
        "EMPTY_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST",
        "UNUSABLE_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST",
        "USABLE_GENERATED_SIDECAR_MISSING_FROM_MANIFEST",
        "MANIFEST_ENTRY_POINTS_TO_MISSING_SIDECAR",
        "MANIFEST_ENTRY_POINTS_TO_UNUSABLE_SIDECAR",
        "NO_GENERATED_BIN_SIDECAR",
    }:
        return "INVESTIGATE_TRANSPECT_OUTPUT"
    if root_cause in {"NON_EQUATION_OBJECT_SUPPRESSED_FROM_MANIFEST", "MANIFEST_MISSING_ENTRY", "LEAF_FALLBACK_AMBIGUOUS"}:
        return "CORPUS_DATA_ISSUE"
    return "FIX_MATCHING_BUG"


def decide_label(cases: list[dict]) -> str:
    if not cases:
        return "NO_ACTION"
    case_decisions = {case["decision"] for case in cases}
    for label in DECISION_ORDER:
        if label in case_decisions:
            return label
    return "NO_ACTION"


def aggregate_reports(reports: list[dict]) -> dict:
    root_cause_counts = Counter()
    decision_counts = Counter()
    total_cases = 0
    for report in reports:
        total_cases += report["unresolved_case_count"]
        decision_counts[report["decision"]] += 1
        root_cause_counts.update(report["root_cause_counts"])
    aggregate_cases = []
    for report in reports:
        aggregate_cases.extend(report["cases"])
    return {
        "preset_count": len(reports),
        "unresolved_case_count": total_cases,
        "root_cause_counts": order_counter(root_cause_counts, ROOT_CAUSE_ORDER),
        "decision_counts": order_counter(decision_counts, DECISION_ORDER),
        "decision": decide_label(aggregate_cases),
    }


def emit_text(reports: list[dict], aggregate: dict) -> None:
    for report in reports:
        print(f"{report['preset']}: unresolved_cases={report['unresolved_case_count']} decision={report['decision']}")
        lineage = report["lineage_report"]
        if lineage:
            print(
                "  lineage: "
                + " ".join(
                    f"{key}={value}"
                    for key, value in lineage.items()
                    if value is not None
                )
            )
        print("  root causes:")
        if not report["root_cause_counts"]:
            print("  - none")
        else:
            for root_cause, count in report["root_cause_counts"].items():
                print(f"  - {root_cause}={count}")
        for index, case in enumerate(report["cases"], start=1):
            print(f"  case {index}: root_cause={case['root_cause']} decision={case['decision']}")
            print(
                "    "
                + " ".join(
                    [
                        f"paragraph={case['paragraph_index']}",
                        f"run={case['run_index']}",
                        f"source_type={case['source_type']}",
                        f"prog_id={case['prog_id']}",
                        f"object_kind={case['object_kind']}",
                    ]
                )
            )
            print(
                "    "
                + " ".join(
                    [
                        f"ole_part={case['ole_part']}",
                        f"preview_part={case['preview_part']}",
                    ]
                )
            )
            print(
                "    "
                + " ".join(
                    [
                        f"ole_manifest_resolved={case['ole_manifest']['resolved']}",
                        f"ole_exact_hit={case['ole_manifest']['exact_manifest_hit']}",
                        f"ole_leaf_matches={case['ole_manifest']['leaf_match_count']}",
                        f"preview_manifest_resolved={case['preview_manifest']['resolved']}",
                        f"preview_exact_hit={case['preview_manifest']['exact_manifest_hit']}",
                        f"preview_leaf_matches={case['preview_manifest']['leaf_match_count']}",
                    ]
                )
            )
            print(
                "    "
                + " ".join(
                    [
                        f"bin_staged={case['bin_staged']}",
                        f"bin_needed={case['bin_needed']}",
                        f"bin_queued_for_convert={case['bin_queued_for_convert']}",
                        f"bin_sidecar_exists={case['bin_sidecar_exists']}",
                        f"bin_sidecar_usable={case['bin_sidecar_usable']}",
                        f"bin_sidecar_status={case['bin_sidecar_status']}",
                        f"preview_sidecar_status={case['preview_sidecar_status']}",
                        f"preview_suppressed_non_equation={case['preview_suppressed_non_equation']}",
                        f"lineage_pair_marked_unresolved={case['lineage_pair_marked_unresolved']}",
                    ]
                )
            )
            print(
                "    "
                + " ".join(
                    [
                        f"ole_hash_reuse_count={case['ole_hash_reuse_count']}",
                        f"preview_use_count={case['preview_use_count']}",
                    ]
                )
            )
            if case["paragraph_text"]:
                print(f"    text={case['paragraph_text']}")

    print("Aggregate unresolved diagnostics:")
    print(
        "  "
        + " ".join(
            [
                f"preset_count={aggregate['preset_count']}",
                f"unresolved_case_count={aggregate['unresolved_case_count']}",
                f"decision={aggregate['decision']}",
            ]
        )
    )
    print("  root causes:")
    if not aggregate["root_cause_counts"]:
        print("  - none")
    else:
        for root_cause, count in aggregate["root_cause_counts"].items():
            print(f"  - {root_cause}={count}")


def diagnose_manifest_part(part_name: str | None, manifest_index: dict) -> dict:
    if not part_name:
        return {
            "part": None,
            "leaf": "",
            "exact_manifest_hit": False,
            "exact_sidecar_exists": False,
            "exact_sidecar_usable": False,
            "exact_sidecar_status": "missing",
            "leaf_match_count": 0,
            "leaf_match_parts": [],
            "ambiguous_leaf": False,
            "resolved": False,
        }

    normalized = normalize_part_name(part_name)
    exact = manifest_index["by_part"].get(normalized)
    leaf_matches = manifest_index["by_leaf"].get(leaf_name(normalized), [])
    resolved = False
    if exact and exact["sidecar_usable"]:
        resolved = True
    elif not exact and len(leaf_matches) == 1 and leaf_matches[0]["sidecar_usable"]:
        resolved = True
    return {
        "part": normalized,
        "leaf": leaf_name(normalized),
        "exact_manifest_hit": exact is not None,
        "exact_sidecar_exists": exact["sidecar_exists"] if exact else False,
        "exact_sidecar_usable": exact["sidecar_usable"] if exact else False,
        "exact_sidecar_status": exact["sidecar_status"] if exact else "missing",
        "leaf_match_count": len(leaf_matches),
        "leaf_match_parts": [entry["part"] for entry in leaf_matches[:5]],
        "ambiguous_leaf": len(leaf_matches) > 1,
        "resolved": resolved,
    }


def find_state_pair(state: dict, ole_part: str | None, preview_part: str | None) -> dict:
    for pair in state.get("object_pairs", []):
        if pair.get("ole_part") == ole_part and pair.get("preview_part") == preview_part:
            return pair
    return {}


def is_lineage_pair_unresolved(lineage_report: dict, ole_part: str | None, preview_part: str | None) -> bool:
    for pair in lineage_report.get("dsmt4_unresolved_pairs", []):
        if pair.get("ole_part") == ole_part and pair.get("preview_part") == preview_part:
            return True
    return False


def has_stage_file(stage_dir: Path, digest: str | None, suffix: str) -> bool:
    if not digest:
        return False
    return (stage_dir / f"{digest}{suffix}").exists()


def hash_zip_part(docx_path: Path, part_name: str | None) -> str | None:
    normalized = normalize_part_name(part_name)
    if not normalized:
        return None
    zip_name = normalized.lstrip("/")
    with ZipFile(docx_path) as zf:
        if zip_name not in zf.namelist():
            return None
        return hashlib.sha256(zf.read(zip_name)).hexdigest()


def is_usable_mathml(path: Path) -> bool:
    return mathml_status(path) == "usable"


def mathml_status(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return "missing"
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if "<math" not in text:
        return "not_math_markup"
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return "parse_error"
    if strip_ns(root.tag) != "math":
        return "non_math_root"
    children = [child for child in list(root) if isinstance(child.tag, str)]
    if children:
        return "usable"
    if (root.text or "").strip():
        return "usable"
    return "empty_math"


def resolve_target(target: str | None) -> str | None:
    if not target:
        return None
    cleaned = target.replace("\\", "/")
    if cleaned.startswith("../"):
        cleaned = cleaned[3:]
    if not cleaned.startswith("/"):
        cleaned = "/word/" + cleaned if not cleaned.startswith("word/") else "/" + cleaned
    return cleaned


def normalize_part_name(part_name: str | None) -> str | None:
    if part_name is None:
        return None
    value = str(part_name).strip().replace("\\", "/")
    if not value:
        return None
    if "?" in value:
        value = value.split("?", 1)[0]
    if not value.startswith("/"):
        value = "/" + value
    return value


def leaf_name(part_name: str | None) -> str:
    normalized = normalize_part_name(part_name)
    if not normalized:
        return ""
    return normalized.rsplit("/", 1)[-1]


def detect_source_type(ole_part: str | None, preview_part: str | None) -> str:
    if extension_of(ole_part) == ".bin":
        return "OLE_BIN"
    if extension_of(preview_part) in {".wmf", ".emf"}:
        return "WMF_PREVIEW"
    return "UNKNOWN"


def extension_of(part_name: str | None) -> str:
    value = (part_name or "").lower()
    match = re.search(r"(\.[a-z0-9]+)$", value)
    return match.group(1) if match else ""


def attribute_by_name(element: ET.Element | None, namespace: str | None, local_name: str) -> str | None:
    if element is None:
        return None
    for key, value in element.attrib.items():
        if namespace:
            expected = f"{{{namespace}}}{local_name}"
            if key == expected:
                return value
        elif key == local_name or key.endswith("}" + local_name):
            return value
    return None


def clean_excerpt(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:180]


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


def order_counter(counter: Counter, preferred_order: list[str]) -> dict[str, int]:
    ordered = {}
    for key in preferred_order:
        if counter.get(key, 0):
            ordered[key] = counter[key]
    for key in sorted(counter):
        if key not in ordered and counter[key]:
            ordered[key] = counter[key]
    return ordered


if __name__ == "__main__":
    raise SystemExit(main())
