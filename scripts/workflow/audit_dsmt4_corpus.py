#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PRESET_CONFIG = REPO_ROOT / "scripts" / "workflow" / "docx_patch_smoke_presets.json"
UNRESOLVED_HELPER_PATH = Path(__file__).with_name("explain_unresolved_manifest.py")
EMPTY_HELPER_PATH = Path(__file__).with_name("explain_empty_generated_sidecar.py")
GENERATE_SIDECARS_SCRIPT = REPO_ROOT / "scripts" / "transpect" / "generate_sidecars.sh"
DEFAULT_EXTERNAL_AUDIT_ROOT = REPO_ROOT / "work" / "dsmt4-external-audit"

BUCKET_PRIORITY = {
    "METADATA_ONLY_PAYLOAD": 3,
    "EMPTY_GENERATED_SIDECAR": 2,
    "OTHER_PARSER_PATTERN": 1,
    "RENDERABLE_BODY_PRESENT": 0,
}

PATTERN_PRIORITY = {
    "METADATA_ONLY_FULL_END_ONLY": 6,
    "METADATA_ONLY_NO_RENDERABLE_BODY_OTHER": 5,
    "EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY": 4,
    "EMPTY_GENERATED_SIDECAR_WITH_METADATA_ONLY_MTEF": 3,
    "OTHER_PARSER_PATTERN": 2,
    "UNKNOWN_PATTERN": 1,
    "RENDERABLE_BODY_PRESENT": 0,
}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


UNRESOLVED = load_module(UNRESOLVED_HELPER_PATH, "explain_unresolved_manifest")
EMPTY = load_module(EMPTY_HELPER_PATH, "explain_empty_generated_sidecar")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the DSMT4 corpus across registry presets and optional external DOCX/workdir sources.")
    parser.add_argument("--preset", action="append", default=[], help="Preset name from the smoke preset registry.")
    parser.add_argument("--all-presets", action="store_true", help="Inspect every preset from the smoke preset registry.")
    parser.add_argument("--subject", action="append", default=[], help="Optional subject filter (math, physics, chemistry, mixed). Repeat to allow multiple subjects.")
    parser.add_argument("--preset-config", default=str(PRESET_CONFIG), help="Preset registry JSON.")
    parser.add_argument("--extra-workdir", action="append", default=[], help="Additional converted workdir to audit outside the preset registry. Repeat as needed.")
    parser.add_argument("--scan-path", action="append", default=[], help="Scan a directory recursively for extra workdirs containing tmp/state.json. Repeat as needed.")
    parser.add_argument("--external-docx", action="append", default=[], help="Audit one external DOCX directly by generating/reusing a sidecar workdir.")
    parser.add_argument("--external-dir", action="append", default=[], help="Scan a directory recursively for external .docx files to audit.")
    parser.add_argument("--prefer-underscore-first", action="store_true", help="When scanning external dirs, process files whose basename starts with '_' before other DOCX files.")
    parser.add_argument("--external-work-root", default=str(DEFAULT_EXTERNAL_AUDIT_ROOT), help="Root directory used to stage generated sidecars for --external-docx/--external-dir.")
    parser.add_argument("--format", choices=("text", "json", "tsv"), default="text", help="Output format.")
    args = parser.parse_args()

    try:
        preset_registry = load_preset_registry(Path(args.preset_config).resolve())
        registry_sources = build_registry_sources(
            preset_registry=preset_registry,
            explicit_names=args.preset,
            use_all_presets=args.all_presets,
            subject_filters=normalize_subjects(args.subject),
        )
        external_workdir_sources = build_external_workdir_sources(
            preset_registry=preset_registry,
            extra_workdirs=[Path(value).resolve() for value in args.extra_workdir],
            scan_paths=[Path(value).resolve() for value in args.scan_path],
        )
        external_docx_sources = build_external_docx_sources(
            docx_paths=[Path(value).resolve() for value in args.external_docx],
            external_dirs=[Path(value).resolve() for value in args.external_dir],
            prefer_underscore_first=args.prefer_underscore_first,
            external_work_root=Path(args.external_work_root).resolve(),
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    all_sources = [*registry_sources, *external_workdir_sources, *external_docx_sources]
    if not all_sources:
        print(
            "Choose at least one registry selection (--preset/--all-presets) or one external selection "
            "(--extra-workdir/--scan-path/--external-docx/--external-dir).",
            file=sys.stderr,
        )
        return 2

    reports = [collect_source_occurrences(source) for source in all_sources]
    runtime = EMPTY.discover_runtime() if needs_deep_audit(reports) else None
    payload_classes = classify_payload_classes(reports, runtime)
    aggregate = aggregate_payload_classes(
        payload_classes=payload_classes,
        registry_sources=registry_sources,
        external_sources=[*external_workdir_sources, *external_docx_sources],
    )
    external_source_summaries = summarize_external_sources(payload_classes, registry_sources, [*external_workdir_sources, *external_docx_sources])

    payload = {
        "sources": reports,
        "payload_classes": payload_classes,
        "aggregate": aggregate,
        "external_source_summaries": external_source_summaries,
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    elif args.format == "tsv":
        emit_tsv(payload)
    else:
        emit_text(payload)
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
            "source_group": "registry",
            "source_kind": "registry",
            "family": manifest.parent.name,
        }
    return presets


def normalize_subjects(subjects: list[str]) -> list[str]:
    return [subject.strip().lower() for subject in subjects if subject.strip()]


def build_registry_sources(
    *,
    preset_registry: dict[str, dict],
    explicit_names: list[str],
    use_all_presets: bool,
    subject_filters: list[str],
) -> list[dict]:
    if explicit_names and use_all_presets:
        raise ValueError("Choose either --preset or --all-presets, not both.")
    if not explicit_names and not use_all_presets:
        return []

    if use_all_presets:
        names = list(preset_registry)
    else:
        missing = [name for name in explicit_names if name not in preset_registry]
        if missing:
            available = ", ".join(sorted(preset_registry))
            raise ValueError(f"Unknown preset(s): {', '.join(missing)}. Available presets: {available}")
        names = []
        seen = set()
        for name in explicit_names:
            if name in seen:
                continue
            seen.add(name)
            names.append(name)

    if subject_filters:
        allowed = set(subject_filters)
        names = [name for name in names if preset_registry[name]["subject"].lower() in allowed]
        if not names:
            raise ValueError(f"No presets matched subject filter(s): {', '.join(subject_filters)}")
    return [preset_registry[name] for name in names]


def build_external_workdir_sources(
    *,
    preset_registry: dict[str, dict],
    extra_workdirs: list[Path],
    scan_paths: list[Path],
) -> list[dict]:
    registry_workdirs = {source["workdir"].resolve() for source in preset_registry.values()}
    registry_sources_by_family = defaultdict(list)
    for source in preset_registry.values():
        registry_sources_by_family[normalize_key(source["family"])].append(source)

    discovered = []
    seen = set()
    for workdir in extra_workdirs:
        resolved = workdir.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        discovered.append(resolved)

    for scan_path in scan_paths:
        if not scan_path.exists():
            raise FileNotFoundError(f"Scan path not found: {scan_path}")
        for state_path in sorted(scan_path.glob("**/tmp/state.json")):
            workdir = state_path.parent.parent.resolve()
            if workdir in seen:
                continue
            seen.add(workdir)
            discovered.append(workdir)

    external_sources = []
    for workdir in discovered:
        if workdir in registry_workdirs:
            continue
        state_path = workdir / "tmp" / "state.json"
        if not state_path.exists():
            continue
        state = UNRESOLVED.load_json_if_exists(state_path)
        dsmt4_count = sum(1 for pair in state.get("object_pairs", []) if pair.get("prog_id") == "Equation.DSMT4")
        if dsmt4_count == 0:
            continue
        input_path, inherited_subject = infer_external_input_docx(workdir, registry_sources_by_family)
        source_name = external_source_name("external-workdir", workdir)
        external_sources.append(
            {
                "name": source_name,
                "subject": inherited_subject or "external",
                "input": input_path,
                "manifest": workdir / "manifest.tsv",
                "workdir": workdir,
                "source_group": "external",
                "source_kind": "external_workdir",
                "family": workdir.name,
                "dsmt4_occurrence_hint": dsmt4_count,
                "docx_path": str(input_path) if input_path else None,
            }
        )
    external_sources.sort(key=lambda source: source["name"])
    return external_sources


def build_external_docx_sources(
    *,
    docx_paths: list[Path],
    external_dirs: list[Path],
    prefer_underscore_first: bool,
    external_work_root: Path,
) -> list[dict]:
    discovered_docx = discover_external_docx_files(docx_paths, external_dirs, prefer_underscore_first)
    sources = []
    for docx_path in discovered_docx:
        if not docx_path.exists():
            raise FileNotFoundError(f"External DOCX not found: {docx_path}")
        workdir = ensure_external_docx_workdir(docx_path, external_work_root)
        source_name = external_source_name("external-docx", docx_path)
        sources.append(
            {
                "name": source_name,
                "subject": "external",
                "input": docx_path,
                "manifest": workdir / "manifest.tsv",
                "workdir": workdir,
                "source_group": "external",
                "source_kind": "external_docx",
                "family": docx_path.stem,
                "docx_path": str(docx_path),
            }
        )
    return sources


def discover_external_docx_files(docx_paths: list[Path], external_dirs: list[Path], prefer_underscore_first: bool) -> list[Path]:
    discovered = []
    seen = set()
    for docx_path in docx_paths:
        validate_docx_path(docx_path)
        resolved = docx_path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        discovered.append(resolved)

    for directory in external_dirs:
        if not directory.exists():
            raise FileNotFoundError(f"External dir not found: {directory}")
        if not directory.is_dir():
            raise ValueError(f"External dir must be a directory: {directory}")
        candidates = [path.resolve() for path in directory.rglob("*.docx") if path.is_file()]
        for candidate in sort_docx_candidates(candidates, prefer_underscore_first):
            if candidate in seen:
                continue
            seen.add(candidate)
            discovered.append(candidate)
    return discovered


def validate_docx_path(path: Path) -> None:
    if path.suffix.lower() != ".docx":
        raise ValueError(f"External input must be a .docx file: {path}")
    if not path.exists():
        raise FileNotFoundError(f"External DOCX not found: {path}")
    if not path.is_file():
        raise ValueError(f"External input must be a file: {path}")


def sort_docx_candidates(paths: list[Path], prefer_underscore_first: bool) -> list[Path]:
    if not prefer_underscore_first:
        return sorted(paths, key=lambda path: (str(path.parent).lower(), path.name.lower()))
    return sorted(
        paths,
        key=lambda path: (
            0 if path.name.startswith("_") else 1,
            str(path.parent).lower(),
            path.name.lower(),
        ),
    )


def ensure_external_docx_workdir(docx_path: Path, external_work_root: Path) -> Path:
    external_work_root.mkdir(parents=True, exist_ok=True)
    digest = file_sha256(docx_path)
    workdir = external_work_root / f"{slugify(docx_path.stem)}--{digest[:12]}"
    metadata_path = workdir / "external-source.json"
    manifest_path = workdir / "manifest.tsv"
    state_path = workdir / "tmp" / "state.json"
    if manifest_path.exists() and state_path.exists():
        if not metadata_path.exists():
            metadata_path.write_text(
                json.dumps(
                    {
                        "source_docx": str(docx_path),
                        "source_sha256": digest,
                    },
                    ensure_ascii=True,
                    indent=2,
                ),
                encoding="utf-8",
            )
        return workdir

    runtime = discover_transpect_generation_paths()
    workdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(GENERATE_SIDECARS_SCRIPT),
        str(docx_path),
        str(workdir),
        str(runtime["mathtype_dir"]),
        str(runtime["xmlcalabash_jar"]),
        str(runtime["saxon_jar"]),
    ]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        stderr_excerpt = "\n".join(proc.stderr.splitlines()[:40]).strip()
        stdout_excerpt = "\n".join(proc.stdout.splitlines()[:40]).strip()
        detail = stderr_excerpt or stdout_excerpt or "unknown error"
        raise RuntimeError(f"Sidecar generation failed for {docx_path}: {detail}")
    metadata_path.write_text(
        json.dumps(
            {
                "source_docx": str(docx_path),
                "source_sha256": digest,
                "workdir": str(workdir),
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return workdir


def discover_transpect_generation_paths() -> dict[str, Path]:
    mathtype_dir = REPO_ROOT / "tools" / "calabash" / "extensions" / "transpect" / "mathtype-extension"
    xmlcalabash_jar = REPO_ROOT / "tools" / "calabash" / "distro" / "xmlcalabash-1.4.1-100.jar"
    saxon_jar = REPO_ROOT / "tools" / "calabash" / "distro" / "lib" / "Saxon-HE-10.8.jar"
    missing = [path for path in [GENERATE_SIDECARS_SCRIPT, mathtype_dir, xmlcalabash_jar, saxon_jar] if not path.exists()]
    if missing:
        raise FileNotFoundError("Transpect sidecar runtime not found: " + ", ".join(str(path) for path in missing))
    return {
        "mathtype_dir": mathtype_dir,
        "xmlcalabash_jar": xmlcalabash_jar,
        "saxon_jar": saxon_jar,
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return slug or "docx"


def infer_external_input_docx(workdir: Path, registry_sources_by_family: dict[str, list[dict]]) -> tuple[Path | None, str | None]:
    family_key = normalize_key(base_family_name(workdir.name))
    candidates = registry_sources_by_family.get(family_key, [])
    if len(candidates) == 1:
        return candidates[0]["input"], candidates[0]["subject"]
    docx_candidates = []
    for docx_path in sorted((REPO_ROOT / "in").glob("*.docx")):
        if normalize_key(docx_path.stem) == family_key:
            docx_candidates.append(docx_path.resolve())
    if len(docx_candidates) == 1:
        return docx_candidates[0], None
    return None, None


def external_source_name(kind: str, path: Path) -> str:
    try:
        relative = path.relative_to(REPO_ROOT)
        return f"{kind}:{relative.as_posix()}"
    except ValueError:
        return f"{kind}:{path}"


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def base_family_name(value: str) -> str:
    return re.sub(r"--[0-9a-f]{12,}$", "", value)


def collect_source_occurrences(source: dict) -> dict:
    state = UNRESOLVED.load_json_if_exists(source["workdir"] / "tmp" / "state.json")
    occurrences = []
    if source.get("input") and Path(source["input"]).exists():
        occurrences = UNRESOLVED.load_occurrences(Path(source["input"]))
    occurrences_by_pair = defaultdict(list)
    for occurrence in occurrences:
        if occurrence.get("prog_id") != "Equation.DSMT4":
            continue
        occurrences_by_pair[(occurrence.get("ole_part"), occurrence.get("preview_part"))].append(occurrence)

    classes = {}
    for pair in state.get("object_pairs", []):
        if pair.get("prog_id") != "Equation.DSMT4":
            continue
        ole_part = pair.get("ole_part")
        preview_part = pair.get("preview_part")
        bin_hash = state.get("bin_part_to_hash", {}).get(ole_part)
        preview_hash = state.get("wmf_part_to_hash", {}).get(preview_part)
        if not bin_hash or not preview_hash:
            continue
        class_key = f"{bin_hash}|{preview_hash}"
        class_entry = classes.setdefault(
            class_key,
            {
                "class_key": class_key,
                "bin_hash": bin_hash,
                "preview_hash": preview_hash,
                "prog_id": pair.get("prog_id"),
                "source_names": set(),
                "source_groups": set(),
                "source_kinds": set(),
                "subjects": set(),
                "occurrence_count": 0,
                "ole_parts": set(),
                "preview_parts": set(),
                "paragraph_indexes": defaultdict(list),
                "text_samples": [],
                "workdir": str(source["workdir"]),
                "source_family": source["family"],
            },
        )
        class_entry["source_names"].add(source["name"])
        class_entry["source_groups"].add(source["source_group"])
        class_entry["source_kinds"].add(source["source_kind"])
        class_entry["subjects"].add(source["subject"])
        class_entry["ole_parts"].add(ole_part)
        class_entry["preview_parts"].add(preview_part)
        matched_occurrences = occurrences_by_pair.get((ole_part, preview_part), [])
        if matched_occurrences:
            class_entry["occurrence_count"] += len(matched_occurrences)
            for occurrence in matched_occurrences:
                class_entry["paragraph_indexes"][source["name"]].append(occurrence["paragraph_index"])
                if occurrence.get("paragraph_text") and len(class_entry["text_samples"]) < 3:
                    class_entry["text_samples"].append(occurrence["paragraph_text"])
        else:
            class_entry["occurrence_count"] += 1

    serialized_classes = []
    for class_entry in classes.values():
        serialized_classes.append(
            {
                "class_key": class_entry["class_key"],
                "bin_hash": class_entry["bin_hash"],
                "preview_hash": class_entry["preview_hash"],
                "prog_id": class_entry["prog_id"],
                "source_names": sorted(class_entry["source_names"]),
                "preset_names": sorted(class_entry["source_names"]),
                "source_groups": sorted(class_entry["source_groups"]),
                "source_kinds": sorted(class_entry["source_kinds"]),
                "subjects": sorted(class_entry["subjects"]),
                "occurrence_count": class_entry["occurrence_count"],
                "ole_parts": sorted(class_entry["ole_parts"]),
                "preview_parts": sorted(class_entry["preview_parts"]),
                "paragraph_indexes": {name: sorted(indexes) for name, indexes in sorted(class_entry["paragraph_indexes"].items())},
                "text_samples": class_entry["text_samples"],
                "workdir": class_entry["workdir"],
                "source_family": class_entry["source_family"],
                "source_families": [class_entry["source_family"]],
                "source_group": source["source_group"],
                "source_kind": source["source_kind"],
            }
        )

    return {
        "source_name": source["name"],
        "preset": source["name"],
        "subject": source["subject"],
        "source_group": source["source_group"],
        "source_kind": source["source_kind"],
        "family": source["family"],
        "input": str(source["input"]) if source.get("input") else None,
        "docx_path": source.get("docx_path"),
        "workdir": str(source["workdir"]),
        "dsmt4_occurrences": sum(entry["occurrence_count"] for entry in serialized_classes),
        "payload_class_count": len(serialized_classes),
        "payload_classes": serialized_classes,
    }


def needs_deep_audit(reports: list[dict]) -> bool:
    for report in reports:
        for payload_class in report["payload_classes"]:
            if not class_has_usable_sidecar(payload_class):
                return True
    return False


def class_has_usable_sidecar(payload_class: dict) -> bool:
    workdir = Path(payload_class["workdir"])
    bin_status = UNRESOLVED.mathml_status(workdir / "mathml" / "bin" / f"{payload_class['bin_hash']}.bin.mathml")
    preview_status = UNRESOLVED.mathml_status(workdir / "mathml" / "wmf" / f"{payload_class['preview_hash']}.wmf.mathml")
    return bin_status == "usable" or preview_status == "usable"


def classify_payload_classes(reports: list[dict], runtime: dict | None) -> list[dict]:
    payload_classes = []
    for report in reports:
        for payload_class in report["payload_classes"]:
            payload_classes.append(classify_single_payload_class(payload_class, runtime))
    payload_classes.sort(
        key=lambda entry: (
            -BUCKET_PRIORITY.get(entry["bucket"], -1),
            -entry["occurrence_count"],
            entry["source_group"],
            entry["source_kind"],
            ",".join(entry["source_names"]),
            entry["bin_hash"],
            entry["preview_hash"],
        )
    )
    return payload_classes


def classify_single_payload_class(payload_class: dict, runtime: dict | None) -> dict:
    workdir = Path(payload_class["workdir"])
    bin_sidecar_path = workdir / "mathml" / "bin" / f"{payload_class['bin_hash']}.bin.mathml"
    preview_sidecar_path = workdir / "mathml" / "wmf" / f"{payload_class['preview_hash']}.wmf.mathml"
    bin_sidecar_status = UNRESOLVED.mathml_status(bin_sidecar_path)
    preview_sidecar_status = UNRESOLVED.mathml_status(preview_sidecar_path)

    result = dict(payload_class)
    result.update(
        {
            "bin_sidecar_status": bin_sidecar_status,
            "preview_sidecar_status": preview_sidecar_status,
            "bin_sidecar_path": str(bin_sidecar_path),
            "preview_sidecar_path": str(preview_sidecar_path),
        }
    )

    if bin_sidecar_status == "usable" or preview_sidecar_status == "usable":
        pattern_signature = {
            "pattern_class": "RENDERABLE_BODY_PRESENT",
            "stage": "GENERATED_SIDECAR",
            "bin_sidecar_status": bin_sidecar_status,
            "preview_sidecar_status": preview_sidecar_status,
        }
        result.update(
            {
                "bucket": "RENDERABLE_BODY_PRESENT",
                "pattern_class": "RENDERABLE_BODY_PRESENT",
                "pattern_stage": "GENERATED_SIDECAR",
                "pattern_signature": pattern_signature,
                "pattern_signature_key": build_signature_key(pattern_signature),
                "assessment": {
                    "result": "USABLE_GENERATED_MATHML",
                    "decision": "NO_ACTION",
                    "stage": "GENERATED_SIDECAR",
                    "reason": "At least one generated sidecar is usable, which is enough evidence that the payload class renders successfully upstream.",
                },
                "deep_audit": None,
            }
        )
        return result

    if runtime is None:
        raise RuntimeError("Deep audit required but runtime was not initialized.")

    bin_stage_path = EMPTY.stage_path(workdir, "stage/bin-convert-src", payload_class["bin_hash"], ".bin")
    if not bin_stage_path.exists():
        bin_stage_path = EMPTY.stage_path(workdir, "stage/bin-needed-src", payload_class["bin_hash"], ".bin")
    preview_stage_path = EMPTY.stage_path(workdir, "stage/wmf-needed-src", payload_class["preview_hash"], ".wmf")
    if not preview_stage_path.exists():
        preview_stage_path = EMPTY.stage_path(workdir, "stage/wmf-src", payload_class["preview_hash"], ".wmf")

    bin_parser = EMPTY.run_jruby_converter(bin_stage_path, runtime) if bin_stage_path.exists() else {"status": "missing_input"}
    preview_parser = EMPTY.run_jruby_converter(preview_stage_path, runtime) if preview_stage_path.exists() else {"status": "missing_input"}
    bin_summary = EMPTY.summarize_mtef_xml(bin_parser.get("xml_text"))
    preview_summary = EMPTY.summarize_mtef_xml(preview_parser.get("xml_text"))
    payload_comparison = EMPTY.compare_equation_payloads(bin_parser, preview_parser)
    assessment = EMPTY.assess_group(
        bin_summary=bin_summary,
        preview_summary=preview_summary,
        bin_parser=bin_parser,
        preview_parser=preview_parser,
        bin_sidecar_status=bin_sidecar_status,
        preview_sidecar_status=preview_sidecar_status,
        payload_comparison=payload_comparison,
    )

    if assessment["result"] in {"TOP_LEVEL_FULL_END_ONLY", "METADATA_ONLY_MTEF_XML"}:
        bucket = "METADATA_ONLY_PAYLOAD"
    elif assessment["decision"] == "FIX_MTEF_TO_MATHML_STAGE" or bin_sidecar_status == "empty_math" or preview_sidecar_status == "empty_math":
        bucket = "EMPTY_GENERATED_SIDECAR"
    else:
        bucket = "OTHER_PARSER_PATTERN"

    pattern_class = classify_pattern_class(
        assessment=assessment,
        bin_summary=bin_summary,
        preview_summary=preview_summary,
        bin_parser=bin_parser,
        preview_parser=preview_parser,
        bin_sidecar_status=bin_sidecar_status,
        preview_sidecar_status=preview_sidecar_status,
    )
    pattern_signature = build_pattern_signature(
        pattern_class=pattern_class,
        assessment=assessment,
        bin_summary=bin_summary,
        preview_summary=preview_summary,
        bin_parser=bin_parser,
        preview_parser=preview_parser,
        payload_comparison=payload_comparison,
        bin_sidecar_status=bin_sidecar_status,
        preview_sidecar_status=preview_sidecar_status,
    )

    result.update(
        {
            "bucket": bucket,
            "pattern_class": pattern_class,
            "pattern_stage": assessment.get("stage"),
            "pattern_signature": pattern_signature,
            "pattern_signature_key": build_signature_key(pattern_signature),
            "assessment": assessment,
            "deep_audit": {
                "bin_stage_path": str(bin_stage_path) if bin_stage_path.exists() else None,
                "preview_stage_path": str(preview_stage_path) if preview_stage_path.exists() else None,
                "bin_parser": EMPTY.filter_parser_result(bin_parser),
                "preview_parser": EMPTY.filter_parser_result(preview_parser),
                "bin_mtef_summary": bin_summary,
                "preview_mtef_summary": preview_summary,
                "payload_comparison": payload_comparison,
            },
        }
    )
    return result


def classify_pattern_class(
    *,
    assessment: dict,
    bin_summary: dict,
    preview_summary: dict,
    bin_parser: dict,
    preview_parser: dict,
    bin_sidecar_status: str,
    preview_sidecar_status: str,
) -> str:
    result = assessment.get("result")
    if result == "TOP_LEVEL_FULL_END_ONLY":
        return "METADATA_ONLY_FULL_END_ONLY"
    if result == "METADATA_ONLY_MTEF_XML":
        return "METADATA_ONLY_NO_RENDERABLE_BODY_OTHER"
    if result == "BODY_PRESENT_BUT_EMPTY_MATHML":
        return "EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY"
    if result == "USABLE_MATH_EXCLUDED":
        return "EMPTY_GENERATED_SIDECAR_WITH_METADATA_ONLY_MTEF"

    parser_statuses = {bin_parser.get("status"), preview_parser.get("status")}
    if "error" in parser_statuses or "missing_input" in parser_statuses:
        return "UNKNOWN_PATTERN"
    if bin_summary.get("metadata_only") and preview_summary.get("metadata_only"):
        return "EMPTY_GENERATED_SIDECAR_WITH_METADATA_ONLY_MTEF"
    if bin_sidecar_status == "empty_math" or preview_sidecar_status == "empty_math":
        return "EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY"
    return "OTHER_PARSER_PATTERN"


def parser_record_names(parser: dict) -> list[str]:
    return [record.get("name", "unknown") for record in parser.get("top_level_records") or []]


def parser_xml_tags(summary: dict) -> list[str]:
    return list(summary.get("top_level_tags") or [])


def build_pattern_signature(
    *,
    pattern_class: str,
    assessment: dict,
    bin_summary: dict,
    preview_summary: dict,
    bin_parser: dict,
    preview_parser: dict,
    payload_comparison: dict,
    bin_sidecar_status: str,
    preview_sidecar_status: str,
) -> dict:
    return {
        "pattern_class": pattern_class,
        "stage": assessment.get("stage"),
        "assessment_result": assessment.get("result"),
        "assessment_decision": assessment.get("decision"),
        "same_effective_payload": payload_comparison.get("same_effective_payload"),
        "bin_sidecar_status": bin_sidecar_status,
        "preview_sidecar_status": preview_sidecar_status,
        "bin_parser_class": bin_parser.get("parser_class"),
        "preview_parser_class": preview_parser.get("parser_class"),
        "bin_equation_bytes": bin_parser.get("equation_bytes"),
        "preview_equation_bytes": preview_parser.get("equation_bytes"),
        "bin_checksum": bin_parser.get("checksum"),
        "preview_checksum": preview_parser.get("checksum"),
        "bin_top_level_record_sequence": parser_record_names(bin_parser),
        "preview_top_level_record_sequence": parser_record_names(preview_parser),
        "bin_tail_after_eqn_prefs": list(bin_summary.get("tail_after_eqn_prefs") or []),
        "preview_tail_after_eqn_prefs": list(preview_summary.get("tail_after_eqn_prefs") or []),
        "bin_top_level_mtef_xml_tags": parser_xml_tags(bin_summary),
        "preview_top_level_mtef_xml_tags": parser_xml_tags(preview_summary),
    }


def build_signature_key(signature: dict) -> str:
    return json.dumps(signature, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def aggregate_payload_classes(payload_classes: list[dict], registry_sources: list[dict], external_sources: list[dict]) -> dict:
    registry_entries = [entry for entry in payload_classes if entry["source_group"] == "registry"]
    external_entries = [entry for entry in payload_classes if entry["source_group"] == "external"]

    registry_class_keys = {entry["class_key"] for entry in registry_entries}
    external_class_keys = {entry["class_key"] for entry in external_entries}
    combined_classes = collapse_payload_classes(payload_classes)

    metadata_only_patterns = Counter()
    pattern_class_counts = Counter()
    pattern_occurrence_counts = Counter()
    pattern_source_families = defaultdict(set)
    pattern_signature_groups = {}
    same_effective_payload_classes = 0
    deep_audited_classes = 0
    bucket_class_counts = Counter()
    bucket_occurrence_counts = Counter()
    bucket_source_names = defaultdict(set)
    bucket_registry_names = defaultdict(set)
    bucket_external_names = defaultdict(set)
    payload_classes_reused_by_occurrence = 0
    payload_classes_shared_across_sources = 0

    for payload_class in combined_classes.values():
        bucket = payload_class["bucket"]
        bucket_class_counts[bucket] += 1
        bucket_occurrence_counts[bucket] += payload_class["occurrence_count"]
        bucket_source_names[bucket].update(payload_class["source_names"])
        bucket_registry_names[bucket].update(payload_class["registry_source_names"])
        bucket_external_names[bucket].update(payload_class["external_source_names"])
        if payload_class["occurrence_count"] > 1:
            payload_classes_reused_by_occurrence += 1
        if len(payload_class["source_names"]) > 1:
            payload_classes_shared_across_sources += 1
        payload_comparison = (payload_class.get("deep_audit") or {}).get("payload_comparison", {})
        if payload_comparison.get("same_effective_payload"):
            same_effective_payload_classes += 1
        if payload_class.get("deep_audit"):
            deep_audited_classes += 1
        if bucket == "METADATA_ONLY_PAYLOAD":
            metadata_only_patterns[metadata_only_pattern(payload_class)] += 1
        pattern_class = payload_class.get("pattern_class", "UNKNOWN_PATTERN")
        pattern_class_counts[pattern_class] += 1
        pattern_occurrence_counts[pattern_class] += payload_class["occurrence_count"]
        pattern_source_families[pattern_class].update(payload_class.get("source_families", []))
        signature_key = payload_class.get("pattern_signature_key")
        if signature_key:
            signature_group = pattern_signature_groups.setdefault(
                signature_key,
                {
                    "pattern_signature_key": signature_key,
                    "pattern_class": pattern_class,
                    "pattern_stage": payload_class.get("pattern_stage"),
                    "signature": payload_class.get("pattern_signature"),
                    "payload_class_count": 0,
                    "occurrence_count": 0,
                    "source_families": set(),
                    "class_keys": [],
                },
            )
            signature_group["payload_class_count"] += 1
            signature_group["occurrence_count"] += payload_class["occurrence_count"]
            signature_group["source_families"].update(payload_class.get("source_families", []))
            if len(signature_group["class_keys"]) < 5:
                signature_group["class_keys"].append(payload_class["class_key"])

    external_docx_sources = [source for source in external_sources if source["source_kind"] == "external_docx"]
    aggregate = {
        "dsmt4_registry_sources_total": len(registry_sources),
        "dsmt4_external_sources_total": len(external_sources),
        "external_files_scanned": len(external_docx_sources),
        "dsmt4_registry_occurrences_total": sum(entry["occurrence_count"] for entry in registry_entries),
        "dsmt4_external_occurrences_total": sum(entry["occurrence_count"] for entry in external_entries),
        "external_dsmt4_occurrences_total": sum(entry["occurrence_count"] for entry in external_entries),
        "dsmt4_occurrences_total": sum(entry["occurrence_count"] for entry in payload_classes),
        "dsmt4_registry_payload_classes_total": len(registry_class_keys),
        "dsmt4_external_payload_classes_total": len(external_class_keys),
        "external_dsmt4_payload_classes_total": len(external_class_keys),
        "dsmt4_external_new_payload_classes_total": len(external_class_keys - registry_class_keys),
        "external_new_payload_classes_total": len(external_class_keys - registry_class_keys),
        "dsmt4_external_existing_payload_classes_total": len(external_class_keys & registry_class_keys),
        "dsmt4_payload_classes_total": len(combined_classes),
        "dsmt4_payload_classes_reused_by_occurrence": payload_classes_reused_by_occurrence,
        "dsmt4_payload_classes_shared_across_sources": payload_classes_shared_across_sources,
        "dsmt4_renderable_classes": bucket_class_counts["RENDERABLE_BODY_PRESENT"],
        "dsmt4_renderable_occurrences": bucket_occurrence_counts["RENDERABLE_BODY_PRESENT"],
        "dsmt4_renderable_sources": len(bucket_source_names["RENDERABLE_BODY_PRESENT"]),
        "dsmt4_external_renderable_classes": count_bucket_for_keys(combined_classes, external_class_keys, "RENDERABLE_BODY_PRESENT"),
        "external_metadata_only_classes_total": count_bucket_for_keys(combined_classes, external_class_keys, "METADATA_ONLY_PAYLOAD"),
        "dsmt4_metadata_only_classes": bucket_class_counts["METADATA_ONLY_PAYLOAD"],
        "dsmt4_metadata_only_occurrences": bucket_occurrence_counts["METADATA_ONLY_PAYLOAD"],
        "dsmt4_metadata_only_sources": len(bucket_source_names["METADATA_ONLY_PAYLOAD"]),
        "dsmt4_metadata_only_registry_presets": len(bucket_registry_names["METADATA_ONLY_PAYLOAD"]),
        "dsmt4_external_metadata_only_classes": count_bucket_for_keys(combined_classes, external_class_keys, "METADATA_ONLY_PAYLOAD"),
        "dsmt4_metadata_only_classes_total_combined": bucket_class_counts["METADATA_ONLY_PAYLOAD"],
        "dsmt4_metadata_only_presets_total_combined": len(bucket_registry_names["METADATA_ONLY_PAYLOAD"]),
        "dsmt4_metadata_only_sources_total_combined": len(bucket_source_names["METADATA_ONLY_PAYLOAD"]),
        "dsmt4_empty_generated_sidecar_classes": bucket_class_counts["EMPTY_GENERATED_SIDECAR"],
        "dsmt4_empty_generated_sidecar_occurrences": bucket_occurrence_counts["EMPTY_GENERATED_SIDECAR"],
        "dsmt4_other_parser_pattern_classes": bucket_class_counts["OTHER_PARSER_PATTERN"],
        "dsmt4_other_parser_pattern_occurrences": bucket_occurrence_counts["OTHER_PARSER_PATTERN"],
        "dsmt4_same_effective_payload_classes": same_effective_payload_classes,
        "dsmt4_deep_audited_classes": deep_audited_classes,
        "dsmt4_pattern_classes_total": len(combined_classes),
        "dsmt4_pattern_occurrences_total": sum(entry["occurrence_count"] for entry in combined_classes.values()),
        "dsmt4_pattern_taxonomy_total": len(pattern_class_counts),
        "metadata_only_patterns": dict(sorted(metadata_only_patterns.items())),
    }
    for pattern_name in sorted(pattern_class_counts):
        slug = pattern_name.lower()
        aggregate[f"dsmt4_pattern_{slug}_classes"] = pattern_class_counts[pattern_name]
        aggregate[f"dsmt4_pattern_{slug}_occurrences"] = pattern_occurrence_counts[pattern_name]
        aggregate[f"dsmt4_pattern_{slug}_source_families"] = len(pattern_source_families[pattern_name])
    aggregate["top_pattern_classes"] = rank_pattern_entries(
        pattern_class_counts=pattern_class_counts,
        pattern_occurrence_counts=pattern_occurrence_counts,
        pattern_source_families=pattern_source_families,
        only_degenerate=False,
    )
    aggregate["top_degenerate_pattern_classes"] = rank_pattern_entries(
        pattern_class_counts=pattern_class_counts,
        pattern_occurrence_counts=pattern_occurrence_counts,
        pattern_source_families=pattern_source_families,
        only_degenerate=True,
    )
    aggregate["top_pattern_signatures"] = rank_signature_groups(pattern_signature_groups, only_degenerate=False)
    aggregate["top_degenerate_pattern_signatures"] = rank_signature_groups(pattern_signature_groups, only_degenerate=True)
    aggregate["decision"] = decide_corpus_label(aggregate)
    aggregate["decision_reason"] = explain_decision(aggregate)
    return aggregate


def collapse_payload_classes(payload_classes: list[dict]) -> dict[str, dict]:
    combined = {}
    for entry in payload_classes:
        class_key = entry["class_key"]
        source_names = list(entry.get("source_names") or entry.get("preset_names") or [])
        source_group = entry.get("source_group", "registry")
        source_kind = entry.get("source_kind", "registry")
        source_groups = list(entry.get("source_groups") or [source_group])
        source_kinds = list(entry.get("source_kinds") or [source_kind])
        paragraph_indexes = {name: list(indexes) for name, indexes in entry.get("paragraph_indexes", {}).items()}
        text_samples = list(entry.get("text_samples", []))

        current = combined.get(class_key)
        if current is None:
            combined[class_key] = {
                **entry,
                "source_names": source_names,
                "preset_names": list(entry.get("preset_names") or source_names),
                "source_groups": source_groups,
                "source_kinds": source_kinds,
                "registry_source_names": list(entry.get("registry_source_names") or (source_names if source_group == "registry" else [])),
                "external_source_names": list(entry.get("external_source_names") or (source_names if source_group == "external" else [])),
                "source_families": list(entry.get("source_families") or [entry.get("source_family")]),
                "paragraph_indexes": paragraph_indexes,
                "text_samples": text_samples,
                "occurrence_count": entry["occurrence_count"],
            }
            continue

        current["occurrence_count"] += entry["occurrence_count"]
        current["source_names"] = sorted(set(current["source_names"]) | set(source_names))
        current["preset_names"] = sorted(set(current["preset_names"]) | set(entry.get("preset_names") or source_names))
        current["source_groups"] = sorted(set(current["source_groups"]) | set(source_groups))
        current["source_kinds"] = sorted(set(current["source_kinds"]) | set(source_kinds))
        current["source_families"] = sorted(
            family for family in (set(current.get("source_families", [])) | {entry.get("source_family")}) if family
        )
        if source_group == "registry":
            current["registry_source_names"] = sorted(set(current["registry_source_names"]) | set(source_names))
        else:
            current["external_source_names"] = sorted(set(current["external_source_names"]) | set(source_names))
        for source_name, indexes in paragraph_indexes.items():
            current["paragraph_indexes"].setdefault(source_name, [])
            current["paragraph_indexes"][source_name] = sorted(set(current["paragraph_indexes"][source_name]) | set(indexes))
        for sample in text_samples:
            if sample and sample not in current["text_samples"] and len(current["text_samples"]) < 3:
                current["text_samples"].append(sample)
        if (
            BUCKET_PRIORITY[entry["bucket"]] > BUCKET_PRIORITY[current["bucket"]]
            or (
                BUCKET_PRIORITY[entry["bucket"]] == BUCKET_PRIORITY[current["bucket"]]
                and PATTERN_PRIORITY.get(entry.get("pattern_class"), -1) > PATTERN_PRIORITY.get(current.get("pattern_class"), -1)
            )
        ):
            current["bucket"] = entry["bucket"]
            current["assessment"] = entry["assessment"]
            current["deep_audit"] = entry["deep_audit"]
            current["source_group"] = source_group
            current["source_kind"] = source_kind
            current["workdir"] = entry.get("workdir")
            current["source_family"] = entry.get("source_family")
            current["subjects"] = entry.get("subjects", [])
            current["ole_parts"] = entry.get("ole_parts", [])
            current["preview_parts"] = entry.get("preview_parts", [])
            current["bin_sidecar_status"] = entry.get("bin_sidecar_status")
            current["preview_sidecar_status"] = entry.get("preview_sidecar_status")
            current["bin_sidecar_path"] = entry.get("bin_sidecar_path")
            current["preview_sidecar_path"] = entry.get("preview_sidecar_path")
            current["pattern_class"] = entry.get("pattern_class")
            current["pattern_stage"] = entry.get("pattern_stage")
            current["pattern_signature"] = entry.get("pattern_signature")
            current["pattern_signature_key"] = entry.get("pattern_signature_key")
    return combined


def count_bucket_for_keys(combined_classes: dict[str, dict], class_keys: set[str], bucket: str) -> int:
    return sum(1 for class_key in class_keys if combined_classes.get(class_key, {}).get("bucket") == bucket)


def metadata_only_pattern(payload_class: dict) -> str:
    deep_audit = payload_class.get("deep_audit") or {}
    bin_tail = deep_audit.get("bin_mtef_summary", {}).get("tail_after_eqn_prefs", [])
    preview_tail = deep_audit.get("preview_mtef_summary", {}).get("tail_after_eqn_prefs", [])
    if bin_tail == ["full", "end"] and preview_tail == ["full", "end"]:
        return "FULL_END_ONLY_AFTER_EQN_PREFS"
    return "OTHER_METADATA_ONLY_PATTERN"


def rank_pattern_entries(
    *,
    pattern_class_counts: Counter,
    pattern_occurrence_counts: Counter,
    pattern_source_families: dict[str, set],
    only_degenerate: bool,
) -> list[dict]:
    names = list(pattern_class_counts)
    if only_degenerate:
        names = [name for name in names if name != "RENDERABLE_BODY_PRESENT"]
    ordered = sorted(
        names,
        key=lambda name: (
            -pattern_class_counts[name],
            -pattern_occurrence_counts[name],
            -len(pattern_source_families[name]),
            -PATTERN_PRIORITY.get(name, -1),
            name,
        ),
    )
    return [
        {
            "pattern_class": name,
            "payload_class_count": pattern_class_counts[name],
            "occurrence_count": pattern_occurrence_counts[name],
            "source_family_count": len(pattern_source_families[name]),
        }
        for name in ordered[:10]
    ]


def rank_signature_groups(pattern_signature_groups: dict[str, dict], only_degenerate: bool) -> list[dict]:
    groups = list(pattern_signature_groups.values())
    if only_degenerate:
        groups = [group for group in groups if group["pattern_class"] != "RENDERABLE_BODY_PRESENT"]
    groups.sort(
        key=lambda group: (
            -group["payload_class_count"],
            -group["occurrence_count"],
            -len(group["source_families"]),
            -PATTERN_PRIORITY.get(group["pattern_class"], -1),
            group["pattern_signature_key"],
        )
    )
    ranked = []
    for group in groups[:10]:
        ranked.append(
            {
                "pattern_class": group["pattern_class"],
                "pattern_stage": group["pattern_stage"],
                "payload_class_count": group["payload_class_count"],
                "occurrence_count": group["occurrence_count"],
                "source_family_count": len(group["source_families"]),
                "pattern_signature_key": group["pattern_signature_key"],
                "signature": group["signature"],
                "example_class_keys": group["class_keys"],
            }
        )
    return ranked


def decide_corpus_label(aggregate: dict) -> str:
    if aggregate["dsmt4_metadata_only_classes_total_combined"] >= 2 or aggregate["dsmt4_metadata_only_sources_total_combined"] >= 2:
        return "CONFIRMED_UNSUPPORTED_OR_DEGENERATE_PAYLOAD_CLASS"
    if aggregate["dsmt4_metadata_only_classes_total_combined"] >= 1:
        return "INSUFFICIENT_EVIDENCE_NEED_MORE_CORPUS"
    if aggregate["dsmt4_empty_generated_sidecar_classes"] >= 1:
        return "INVESTIGATE_MTEF_TO_MATHML_STAGE"
    if aggregate["dsmt4_other_parser_pattern_classes"] >= 1:
        return "INVESTIGATE_PARSER_STAGE"
    return "INSUFFICIENT_EVIDENCE_NEED_MORE_CORPUS"


def explain_decision(aggregate: dict) -> str:
    if aggregate["decision"] == "CONFIRMED_UNSUPPORTED_OR_DEGENERATE_PAYLOAD_CLASS":
        return "The same metadata-only parser-stage pattern appears in multiple independent payload classes or source families, so this is no longer just a single reused outlier."
    if aggregate["decision"] == "INSUFFICIENT_EVIDENCE_NEED_MORE_CORPUS":
        if aggregate["dsmt4_metadata_only_classes_total_combined"] >= 1:
            return "A metadata-only DSMT4 pattern exists, but it still appears in only one payload class and one source in the combined corpus, so the evidence is too narrow to confirm a broader unsupported class."
        return "No repeated non-renderable DSMT4 payload class is visible in the combined corpus."
    if aggregate["decision"] == "INVESTIGATE_MTEF_TO_MATHML_STAGE":
        return "Some DSMT4 payload classes still generate empty sidecars even though the parser-stage evidence is not metadata-only, which points to the MTEF->MathML stage."
    return "Some DSMT4 payload classes still fail before a clear metadata-only classification, so parser-stage inspection needs more work."


def summarize_external_sources(payload_classes: list[dict], registry_sources: list[dict], external_sources: list[dict]) -> list[dict]:
    registry_class_keys = {entry["class_key"] for entry in payload_classes if entry["source_group"] == "registry"}
    classes_by_source = defaultdict(list)
    for entry in payload_classes:
        if entry["source_group"] != "external":
            continue
        for source_name in entry["source_names"]:
            classes_by_source[source_name].append(entry)

    summaries = []
    seen_class_keys = set(registry_class_keys)
    for source in external_sources:
        entries = classes_by_source.get(source["name"], [])
        class_keys = {entry["class_key"] for entry in entries}
        metadata_only_entries = [entry for entry in entries if entry["bucket"] == "METADATA_ONLY_PAYLOAD"]
        new_class_keys = class_keys - seen_class_keys
        full_end_only_present = any(metadata_only_pattern(entry) == "FULL_END_ONLY_AFTER_EQN_PREFS" for entry in metadata_only_entries)
        pattern_class_counts = Counter()
        pattern_occurrence_counts = Counter()
        for entry in entries:
            pattern_name = entry.get("pattern_class", "UNKNOWN_PATTERN")
            pattern_class_counts[pattern_name] += 1
            pattern_occurrence_counts[pattern_name] += entry["occurrence_count"]
        summaries.append(
            {
                "source_name": source["name"],
                "source_kind": source["source_kind"],
                "docx_path": source.get("docx_path"),
                "workdir": str(source["workdir"]),
                "dsmt4_occurrences": sum(entry["occurrence_count"] for entry in entries),
                "dsmt4_payload_classes": len(class_keys),
                "dsmt4_new_payload_classes_so_far": len(new_class_keys),
                "dsmt4_metadata_only_classes": len({entry["class_key"] for entry in metadata_only_entries}),
                "full_end_only_present": full_end_only_present,
                "top_pattern_classes": [
                    {
                        "pattern_class": name,
                        "payload_class_count": pattern_class_counts[name],
                        "occurrence_count": pattern_occurrence_counts[name],
                    }
                    for name in sorted(
                        pattern_class_counts,
                        key=lambda name: (-pattern_class_counts[name], -pattern_occurrence_counts[name], -PATTERN_PRIORITY.get(name, -1), name),
                    )[:5]
                ],
            }
        )
        seen_class_keys.update(class_keys)
    return summaries


def emit_text(payload: dict) -> None:
    aggregate = payload["aggregate"]
    payload_classes = payload["payload_classes"]
    external_source_summaries = payload["external_source_summaries"]

    print("DSMT4 corpus aggregate:")
    for key in [
        "dsmt4_registry_sources_total",
        "dsmt4_external_sources_total",
        "external_files_scanned",
        "dsmt4_registry_occurrences_total",
        "dsmt4_external_occurrences_total",
        "external_dsmt4_occurrences_total",
        "dsmt4_occurrences_total",
        "dsmt4_registry_payload_classes_total",
        "dsmt4_external_payload_classes_total",
        "external_dsmt4_payload_classes_total",
        "dsmt4_external_new_payload_classes_total",
        "external_new_payload_classes_total",
        "dsmt4_external_existing_payload_classes_total",
        "dsmt4_payload_classes_total",
        "dsmt4_payload_classes_reused_by_occurrence",
        "dsmt4_payload_classes_shared_across_sources",
        "dsmt4_renderable_classes",
        "dsmt4_renderable_occurrences",
        "dsmt4_renderable_sources",
        "dsmt4_external_renderable_classes",
        "dsmt4_metadata_only_classes",
        "dsmt4_metadata_only_occurrences",
        "dsmt4_metadata_only_sources",
        "dsmt4_metadata_only_registry_presets",
        "dsmt4_external_metadata_only_classes",
        "external_metadata_only_classes_total",
        "dsmt4_metadata_only_classes_total_combined",
        "dsmt4_metadata_only_presets_total_combined",
        "dsmt4_metadata_only_sources_total_combined",
        "dsmt4_empty_generated_sidecar_classes",
        "dsmt4_empty_generated_sidecar_occurrences",
        "dsmt4_other_parser_pattern_classes",
        "dsmt4_other_parser_pattern_occurrences",
        "dsmt4_same_effective_payload_classes",
        "dsmt4_deep_audited_classes",
        "dsmt4_pattern_classes_total",
        "dsmt4_pattern_occurrences_total",
        "dsmt4_pattern_taxonomy_total",
    ]:
        print(f"- {key}={aggregate[key]}")
    for key in sorted(key for key in aggregate if key.startswith("dsmt4_pattern_") and key not in {"dsmt4_pattern_classes_total", "dsmt4_pattern_occurrences_total", "dsmt4_pattern_taxonomy_total"}):
        if isinstance(aggregate[key], (str, int, float, bool)):
            print(f"- {key}={aggregate[key]}")
    if aggregate["metadata_only_patterns"]:
        print("Metadata-only patterns:")
        for name, count in aggregate["metadata_only_patterns"].items():
            print(f"- {name}={count}")
    if aggregate["top_pattern_classes"]:
        print("Top pattern classes:")
        for entry in aggregate["top_pattern_classes"]:
            print(
                f"- {entry['pattern_class']}: payload_classes={entry['payload_class_count']} "
                f"occurrences={entry['occurrence_count']} source_families={entry['source_family_count']}"
            )
    if aggregate["top_degenerate_pattern_classes"]:
        print("Top degenerate pattern classes:")
        for entry in aggregate["top_degenerate_pattern_classes"]:
            print(
                f"- {entry['pattern_class']}: payload_classes={entry['payload_class_count']} "
                f"occurrences={entry['occurrence_count']} source_families={entry['source_family_count']}"
            )
    if aggregate["top_degenerate_pattern_signatures"]:
        print("Top degenerate pattern signatures:")
        for entry in aggregate["top_degenerate_pattern_signatures"]:
            print(
                f"- {entry['pattern_class']}: payload_classes={entry['payload_class_count']} "
                f"occurrences={entry['occurrence_count']} source_families={entry['source_family_count']}"
            )
            print(f"  signature={entry['pattern_signature_key']}")
    print(f"Decision: {aggregate['decision']}")
    print(f"Reason: {aggregate['decision_reason']}")

    if external_source_summaries:
        print("External source summaries:")
        for summary in external_source_summaries:
            docx_label = summary["docx_path"] or "none"
            print(
                f"- {summary['source_name']}: source_kind={summary['source_kind']} docx={docx_label} "
                f"dsmt4_occurrences={summary['dsmt4_occurrences']} dsmt4_payload_classes={summary['dsmt4_payload_classes']} "
                f"dsmt4_new_payload_classes_so_far={summary['dsmt4_new_payload_classes_so_far']} "
                f"dsmt4_metadata_only_classes={summary['dsmt4_metadata_only_classes']} "
                f"full_end_only_present={summary['full_end_only_present']}"
            )
            if summary["top_pattern_classes"]:
                patterns = ", ".join(
                    f"{entry['pattern_class']}:{entry['payload_class_count']}c/{entry['occurrence_count']}o"
                    for entry in summary["top_pattern_classes"]
                )
                print(f"  top_pattern_classes={patterns}")

    interesting_classes = [entry for entry in payload_classes if entry["bucket"] != "RENDERABLE_BODY_PRESENT"]
    if interesting_classes:
        print("Non-renderable DSMT4 payload classes:")
        for index, payload_class in enumerate(interesting_classes, start=1):
            paragraphs = ",".join(str(i) for indexes in payload_class["paragraph_indexes"].values() for i in indexes) or "unknown"
            print(
                f"- class {index}: bucket={payload_class['bucket']} sources={','.join(payload_class['source_names'])} "
                f"source_kind={payload_class['source_kind']} occurrences={payload_class['occurrence_count']} "
                f"pattern_class={payload_class.get('pattern_class')} paragraphs={paragraphs}"
            )
            print(
                f"  bin_hash={payload_class['bin_hash']} preview_hash={payload_class['preview_hash']} "
                f"bin_sidecar_status={payload_class['bin_sidecar_status']} preview_sidecar_status={payload_class['preview_sidecar_status']}"
            )
            assessment = payload_class.get("assessment", {})
            print(
                f"  assessment={assessment.get('result')} decision={assessment.get('decision')} "
                f"stage={assessment.get('stage')}"
            )
            deep_audit = payload_class.get("deep_audit") or {}
            if deep_audit:
                print(
                    f"  same_effective_payload={deep_audit['payload_comparison'].get('same_effective_payload')} "
                    f"shared_prefix_bytes={deep_audit['payload_comparison'].get('shared_prefix_bytes')}"
                )
                print(
                    f"  bin_tail={','.join(deep_audit['bin_mtef_summary'].get('tail_after_eqn_prefs', [])) or 'none'} "
                    f"preview_tail={','.join(deep_audit['preview_mtef_summary'].get('tail_after_eqn_prefs', [])) or 'none'}"
                )
                print(f"  pattern_signature={payload_class.get('pattern_signature_key')}")


def emit_tsv(payload: dict) -> None:
    aggregate = payload["aggregate"]
    payload_classes = payload["payload_classes"]
    external_source_summaries = payload["external_source_summaries"]

    print("# aggregate")
    print("key\tvalue")
    for key, value in aggregate.items():
        if isinstance(value, (dict, list)):
            continue
        print(f"{key}\t{value}")
    if aggregate["metadata_only_patterns"]:
        print("\n# metadata_only_patterns")
        print("pattern\tclass_count")
        for name, count in aggregate["metadata_only_patterns"].items():
            print(f"{name}\t{count}")
    if external_source_summaries:
        print("\n# external_source_summaries")
        print("source_name\tsource_kind\tdocx_path\tdsmt4_occurrences\tdsmt4_payload_classes\tdsmt4_new_payload_classes_so_far\tdsmt4_metadata_only_classes\tfull_end_only_present\ttop_pattern_classes")
        for summary in external_source_summaries:
            print(
                "\t".join(
                    [
                        summary["source_name"],
                        summary["source_kind"],
                        str(summary["docx_path"] or ""),
                        str(summary["dsmt4_occurrences"]),
                        str(summary["dsmt4_payload_classes"]),
                        str(summary["dsmt4_new_payload_classes_so_far"]),
                        str(summary["dsmt4_metadata_only_classes"]),
                        str(summary["full_end_only_present"]),
                        ",".join(
                            f"{entry['pattern_class']}:{entry['payload_class_count']}c/{entry['occurrence_count']}o"
                            for entry in summary.get("top_pattern_classes", [])
                        ),
                    ]
                )
            )
    if aggregate["top_pattern_classes"]:
        print("\n# top_pattern_classes")
        print("pattern_class\tpayload_class_count\toccurrence_count\tsource_family_count")
        for entry in aggregate["top_pattern_classes"]:
            print(
                "\t".join(
                    [
                        entry["pattern_class"],
                        str(entry["payload_class_count"]),
                        str(entry["occurrence_count"]),
                        str(entry["source_family_count"]),
                    ]
                )
            )
    if aggregate["top_degenerate_pattern_signatures"]:
        print("\n# top_degenerate_pattern_signatures")
        print("pattern_class\tpattern_stage\tpayload_class_count\toccurrence_count\tsource_family_count\tpattern_signature_key")
        for entry in aggregate["top_degenerate_pattern_signatures"]:
            print(
                "\t".join(
                    [
                        entry["pattern_class"],
                        str(entry["pattern_stage"] or ""),
                        str(entry["payload_class_count"]),
                        str(entry["occurrence_count"]),
                        str(entry["source_family_count"]),
                        entry["pattern_signature_key"],
                    ]
                )
            )
    print("\n# payload_classes")
    print(
        "\t".join(
            [
                "bucket",
                "pattern_class",
                "source_group",
                "source_kind",
                "source_names",
                "occurrence_count",
                "bin_hash",
                "preview_hash",
                "bin_sidecar_status",
                "preview_sidecar_status",
                "assessment_result",
                "assessment_decision",
                "assessment_stage",
            ]
        )
    )
    for payload_class in payload_classes:
        assessment = payload_class.get("assessment", {})
        print(
            "\t".join(
                [
                    payload_class["bucket"],
                    str(payload_class.get("pattern_class", "")),
                    payload_class["source_group"],
                    payload_class["source_kind"],
                    ",".join(payload_class["source_names"]),
                    str(payload_class["occurrence_count"]),
                    payload_class["bin_hash"],
                    payload_class["preview_hash"],
                    payload_class["bin_sidecar_status"],
                    payload_class["preview_sidecar_status"],
                    str(assessment.get("result", "")),
                    str(assessment.get("decision", "")),
                    str(assessment.get("stage", "")),
                ]
            )
        )


if __name__ == "__main__":
    raise SystemExit(main())
