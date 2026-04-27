#!/usr/bin/env python3
from __future__ import annotations

import argparse
import binascii
import importlib.util
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
UNRESOLVED_HELPER_PATH = Path(__file__).with_name("explain_unresolved_manifest.py")

BODY_METADATA_TAGS = {
    "root",
    "mtef",
    "mtef_version",
    "platform",
    "product",
    "product_version",
    "product_subversion",
    "application_key",
    "equation_options",
    "encoding_def",
    "enc_def_index",
    "name",
    "font_def",
    "font_name",
    "eqn_prefs",
    "options",
    "sizes_count",
    "sizes",
    "unit",
    "nibbles",
    "spaces_count",
    "spaces",
    "styles_count",
    "styles",
    "font_style",
    "full",
    "end",
}


def load_unresolved_helper():
    spec = importlib.util.spec_from_file_location("explain_unresolved_manifest", UNRESOLVED_HELPER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


UNRESOLVED = load_unresolved_helper()


def main() -> int:
    parser = argparse.ArgumentParser(description="Explain empty-generated-sidecar cases by auditing transpect parser output before MathML filtering.")
    parser.add_argument("--preset", action="append", default=[], help="Preset name from the smoke preset registry.")
    parser.add_argument("--preset-config", default=str(UNRESOLVED.DEFAULT_PRESET_CONFIG), help="Preset registry JSON.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    args = parser.parse_args()

    try:
        registry = UNRESOLVED.load_preset_registry(Path(args.preset_config).resolve())
        preset_names = UNRESOLVED.select_preset_names(registry, args.preset, False)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    runtime = discover_runtime()
    reports = [analyze_preset(registry[name], runtime) for name in preset_names]
    aggregate = aggregate_reports(reports)
    if args.format == "json":
        print(json.dumps({"presets": reports, "aggregate": aggregate}, ensure_ascii=True, indent=2))
    else:
        emit_text(reports, aggregate)
    return 0


def discover_runtime() -> dict:
    mathtype_dir = REPO_ROOT / "tools" / "calabash" / "extensions" / "transpect" / "mathtype-extension"
    xmlcalabash_jar = REPO_ROOT / "tools" / "calabash" / "distro" / "xmlcalabash-1.4.1-100.jar"
    saxon_jar = REPO_ROOT / "tools" / "calabash" / "distro" / "lib" / "Saxon-HE-10.8.jar"
    if not mathtype_dir.exists() or not xmlcalabash_jar.exists() or not saxon_jar.exists():
        raise FileNotFoundError("Transpect runtime not found under tools/calabash")

    jruby_jar = latest_child(mathtype_dir / "lib", "jruby-complete-*.jar")
    ruby_ole_dir = latest_dir(mathtype_dir / "ruby", "ruby-ole-*")
    nokogiri_dir = latest_dir(mathtype_dir / "ruby", "nokogiri-*-java")
    bindata_dir = latest_dir(mathtype_dir / "ruby", "bindata-*")
    mathtype_ruby_dir = latest_dir(mathtype_dir / "ruby", "mathtype-*")

    classpath_parts = [str(xmlcalabash_jar)]
    classpath_parts.extend(str(path) for path in sorted((xmlcalabash_jar.parent / "lib").glob("*.jar")))
    classpath_parts.extend(
        [
            str(saxon_jar),
            str(mathtype_dir),
            str(jruby_jar),
            str(mathtype_dir / "ruby" / "stdlib"),
            str(ruby_ole_dir / "lib"),
            str(nokogiri_dir / "lib"),
            str(bindata_dir / "lib"),
            str(mathtype_ruby_dir / "lib"),
        ]
    )
    return {
        "classpath": ":".join(classpath_parts),
        "mathtype_dir": mathtype_dir,
    }


def latest_child(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"Missing runtime dependency under {root}: {pattern}")
    return matches[-1]


def latest_dir(root: Path, pattern: str) -> Path:
    matches = [path for path in sorted(root.glob(pattern)) if path.is_dir()]
    if not matches:
        raise FileNotFoundError(f"Missing runtime dependency under {root}: {pattern}")
    return matches[-1]


def analyze_preset(preset: dict, runtime: dict) -> dict:
    unresolved_report = UNRESOLVED.analyze_preset(preset)
    empty_cases = [
        case for case in unresolved_report["cases"]
        if case["root_cause"] == "EMPTY_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST"
    ]
    groups = []
    grouped = defaultdict(list)
    for case in empty_cases:
        grouped[(case["bin_hash"], case["preview_hash"])].append(case)

    for (bin_hash, preview_hash), cases in grouped.items():
        representative = cases[0]
        bin_stage_path = stage_path(preset["workdir"], "stage/bin-convert-src", bin_hash, ".bin")
        if not bin_stage_path.exists():
            bin_stage_path = stage_path(preset["workdir"], "stage/bin-needed-src", bin_hash, ".bin")
        preview_stage_path = stage_path(preset["workdir"], "stage/wmf-needed-src", preview_hash, ".wmf")
        if not preview_stage_path.exists():
            preview_stage_path = stage_path(preset["workdir"], "stage/wmf-src", preview_hash, ".wmf")

        bin_parser = run_jruby_converter(bin_stage_path, runtime) if bin_stage_path.exists() else {"status": "missing_input"}
        preview_parser = run_jruby_converter(preview_stage_path, runtime) if preview_stage_path.exists() else {"status": "missing_input"}
        bin_mtef_summary = summarize_mtef_xml(bin_parser.get("xml_text"))
        preview_mtef_summary = summarize_mtef_xml(preview_parser.get("xml_text"))
        payload_comparison = compare_equation_payloads(bin_parser, preview_parser)
        assessment = assess_group(
            bin_summary=bin_mtef_summary,
            preview_summary=preview_mtef_summary,
            bin_parser=bin_parser,
            preview_parser=preview_parser,
            bin_sidecar_status=representative["bin_sidecar_status"],
            preview_sidecar_status=representative["preview_sidecar_status"],
            payload_comparison=payload_comparison,
        )

        groups.append(
            {
                "bin_hash": bin_hash,
                "preview_hash": preview_hash,
                "occurrence_count": len(cases),
                "paragraph_indexes": sorted(case["paragraph_index"] for case in cases),
                "prog_id": representative["prog_id"],
                "object_kind": representative["object_kind"],
                "ole_parts": sorted({case["ole_part"] for case in cases}),
                "preview_parts": sorted({case["preview_part"] for case in cases}),
                "bin_sidecar_path": representative["bin_sidecar_path"],
                "bin_sidecar_status": representative["bin_sidecar_status"],
                "preview_sidecar_path": representative["preview_sidecar_path"],
                "preview_sidecar_status": representative["preview_sidecar_status"],
                "bin_stage_path": str(bin_stage_path) if bin_stage_path.exists() else None,
                "preview_stage_path": str(preview_stage_path) if preview_stage_path.exists() else None,
                "bin_parser": filter_parser_result(bin_parser),
                "preview_parser": filter_parser_result(preview_parser),
                "bin_mtef_summary": bin_mtef_summary,
                "preview_mtef_summary": preview_mtef_summary,
                "payload_comparison": payload_comparison,
                "assessment": assessment,
                "text_sample": representative.get("paragraph_text", ""),
            }
        )

    decision = "NO_ACTION" if not groups else choose_decision(groups)
    return {
        "preset": preset["name"],
        "subject": preset["subject"],
        "group_count": len(groups),
        "decision": decision,
        "groups": groups,
    }


def filter_parser_result(result: dict) -> dict:
    return {
        "status": result.get("status"),
        "parser_class": result.get("parser_class"),
        "version": result.get("version"),
        "application_key": result.get("application_key"),
        "equation_bytes": result.get("equation_bytes"),
        "equation_records_start_offset": result.get("equation_records_start_offset"),
        "equation_header_hex": result.get("equation_header_hex"),
        "equation_hex": result.get("equation_hex"),
        "equation_sha256": result.get("equation_sha256"),
        "checksum": result.get("checksum"),
        "top_level_records": result.get("top_level_records"),
        "eqn_prefs_counts": result.get("eqn_prefs_counts"),
        "stderr_excerpt": result.get("stderr_excerpt"),
    }


def stage_path(workdir: Path, relative_dir: str, digest: str | None, suffix: str) -> Path:
    if not digest:
        return Path("/nonexistent")
    return workdir / relative_dir / f"{digest}{suffix}"


def run_jruby_converter(input_path: Path, runtime: dict) -> dict:
    ruby_script = r"""
require "json"
require "digest"
require "mathtype"

def choice_impl(choice)
  return nil if choice.nil?
  choice.send(:current_choice)
rescue StandardError
  choice
end

def child_records_for(payload)
  return [nil, []] if payload.nil?
  fields = {
    "object_list" => (payload.respond_to?(:object_list) ? payload.object_list : nil),
    "subobject_list" => (payload.respond_to?(:subobject_list) ? payload.subobject_list : nil),
    "embellishment_list" => (payload.respond_to?(:embellishment_list) ? payload.embellishment_list : nil)
  }
  field_name, child_list = fields.find { |_name, value| value && value.respond_to?(:map) && !value.empty? }
  records = (child_list || []).map do |child|
    {
      record_type: child.record_type,
      name: Mathtype5::RECORD_NAMES[child.record_type]
    }
  end
  [field_name, records]
end

def safe_value(obj, method_name)
  return nil if obj.nil? || !obj.respond_to?(method_name)
  obj.public_send(method_name)
rescue StandardError, NotImplementedError
  nil
end

conv = Mathtype::Converter.new(ARGV[0])
equation = conv.parser.equation
parsed = Mathtype5::Equation.read(equation)
equation_records_start_offset = 5 + parsed.application_key.to_s.bytesize + 2
records = parsed.equation.each_with_index.map do |rec, idx|
  payload = rec.respond_to?(:payload) ? rec.payload : nil
  dispatch = choice_impl(payload)
  snap = dispatch && dispatch.respond_to?(:snapshot) ? dispatch.snapshot : dispatch
  preview = if snap.respond_to?(:keys)
    snap.keys.map(&:to_s)
  else
    snap.to_s
  end
  child_field, child_records = child_records_for(dispatch)
  {
    index: idx,
    record_type: rec.record_type,
    name: Mathtype5::RECORD_NAMES[rec.record_type],
    record_abs_offset: safe_value(rec, :abs_offset),
    record_num_bytes: safe_value(rec, :num_bytes),
    payload_class: dispatch&.class&.to_s,
    payload_abs_offset: safe_value(dispatch, :abs_offset),
    payload_num_bytes: safe_value(dispatch, :num_bytes),
    payload_preview: preview,
    child_list_field: child_field,
    child_records: child_records
  }
end
records.each_with_index do |rec, idx|
  nxt = records[idx + 1]
  rec[:next_record_type] = nxt && nxt[:record_type]
  rec[:next_name] = nxt && nxt[:name]
end
eqn_prefs = parsed.equation.find { |rec| rec.record_type == 18 }
prefs = eqn_prefs && eqn_prefs.payload.respond_to?(:snapshot) ? eqn_prefs.payload.snapshot : nil
payload = {
  status: "ok",
  parser_class: conv.parser.class.to_s,
  version: conv.version,
  application_key: parsed.application_key.to_s,
  equation_bytes: equation.bytesize,
  equation_records_start_offset: equation_records_start_offset,
  equation_header_hex: equation.byteslice(0, equation_records_start_offset).unpack1("H*"),
  equation_sha256: Digest::SHA256.hexdigest(equation),
  equation_hex: equation.unpack1("H*"),
  checksum: conv.parser.checksum,
  top_level_records: records,
  eqn_prefs_counts: prefs ? {
    sizes_count: prefs[:sizes_count],
    spaces_count: prefs[:spaces_count],
    styles_count: prefs[:styles_count]
  } : nil,
  xml_text: conv.to_xml
}
puts JSON.generate(payload)
"""
    cmd = [
        "java",
        "-cp",
        runtime["classpath"],
        "org.jruby.Main",
        "-e",
        ruby_script,
        str(input_path),
    ]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    stderr_excerpt = "\n".join((proc.stderr or "").splitlines()[:20]).strip()
    if proc.returncode != 0:
        return {
            "status": "error",
            "stderr_excerpt": stderr_excerpt,
            "stdout_excerpt": "\n".join((proc.stdout or "").splitlines()[:20]).strip(),
        }
    payload = json.loads(proc.stdout.strip())
    payload["stderr_excerpt"] = stderr_excerpt
    return payload


def summarize_mtef_xml(xml_text: str | None) -> dict:
    if not xml_text:
        return {
            "status": "missing",
            "tag_counts": {},
            "body_tag_counts": {},
            "metadata_only": False,
            "application_key": None,
            "equation_options": None,
            "top_level_tags": [],
            "tail_after_eqn_prefs": [],
        }
    root = ET.fromstring(xml_text)
    tag_counts = Counter(strip_ns(elem.tag) for elem in root.iter() if isinstance(elem.tag, str))
    body_tag_counts = {
        tag: count for tag, count in sorted(tag_counts.items())
        if tag not in BODY_METADATA_TAGS
    }
    mtef = root.find("mtef")
    top_level_tags = [strip_ns(child.tag) for child in list(mtef)] if mtef is not None else []
    tail_after_eqn_prefs = []
    if mtef is not None:
        children = list(mtef)
        try:
            eqn_prefs_index = next(index for index, child in enumerate(children) if strip_ns(child.tag) == "eqn_prefs")
            tail_after_eqn_prefs = [strip_ns(child.tag) for child in children[eqn_prefs_index + 1 :]]
        except StopIteration:
            tail_after_eqn_prefs = top_level_tags
    return {
        "status": "ok",
        "tag_counts": dict(sorted(tag_counts.items())),
        "body_tag_counts": body_tag_counts,
        "metadata_only": not body_tag_counts,
        "application_key": text_of(mtef, "application_key"),
        "equation_options": text_of(mtef, "equation_options"),
        "top_level_tags": top_level_tags,
        "tail_after_eqn_prefs": tail_after_eqn_prefs,
    }


def compare_equation_payloads(bin_parser: dict, preview_parser: dict) -> dict:
    bin_hex = bin_parser.get("equation_hex")
    preview_hex = preview_parser.get("equation_hex")
    if not bin_hex or not preview_hex:
        return {
            "status": "missing",
            "exact_match": False,
            "same_effective_payload": False,
            "shared_prefix_bytes": 0,
            "first_diff_offset": None,
            "bin_trailing_hex": "",
            "preview_trailing_hex": "",
        }

    bin_bytes = binascii.unhexlify(bin_hex)
    preview_bytes = binascii.unhexlify(preview_hex)
    shared_prefix = 0
    for left, right in zip(bin_bytes, preview_bytes):
        if left != right:
            break
        shared_prefix += 1
    exact_match = bin_bytes == preview_bytes
    bin_trailing = bin_bytes[shared_prefix:]
    preview_trailing = preview_bytes[shared_prefix:]
    same_effective_payload = exact_match or (
        shared_prefix == min(len(bin_bytes), len(preview_bytes))
        and (not bin_trailing or not preview_trailing)
    )
    trailing_note = None
    if same_effective_payload and preview_trailing:
        trailing_note = f"preview has trailing bytes after shared payload: {preview_trailing.hex()}"
    elif same_effective_payload and bin_trailing:
        trailing_note = f"bin has trailing bytes after shared payload: {bin_trailing.hex()}"
    return {
        "status": "ok",
        "exact_match": exact_match,
        "same_effective_payload": same_effective_payload,
        "shared_prefix_bytes": shared_prefix,
        "first_diff_offset": None if exact_match else shared_prefix,
        "bin_trailing_hex": bin_trailing.hex(),
        "preview_trailing_hex": preview_trailing.hex(),
        "trailing_note": trailing_note,
    }


def assess_group(
    *,
    bin_summary: dict,
    preview_summary: dict,
    bin_parser: dict,
    preview_parser: dict,
    bin_sidecar_status: str,
    preview_sidecar_status: str,
    payload_comparison: dict,
) -> dict:
    both_metadata_only = bin_summary.get("metadata_only") and preview_summary.get("metadata_only")
    any_body_tags = bool(bin_summary.get("body_tag_counts")) or bool(preview_summary.get("body_tag_counts"))
    both_empty_math_sidecars = bin_sidecar_status == "empty_math" and preview_sidecar_status == "empty_math"
    bin_tail = bin_summary.get("tail_after_eqn_prefs", [])
    preview_tail = preview_summary.get("tail_after_eqn_prefs", [])

    if (
        both_metadata_only
        and both_empty_math_sidecars
        and bin_tail == ["full", "end"]
        and preview_tail == ["full", "end"]
        and payload_comparison.get("same_effective_payload")
    ):
        return {
            "result": "TOP_LEVEL_FULL_END_ONLY",
            "decision": "UNSUPPORTED_OR_DEGENERATE_PAYLOAD",
            "stage": "PARSER_INPUT_PAYLOAD",
            "reason": "BIN and WMF resolve to the same effective MTEF payload, and that payload ends with top-level FULL/END after eqn_prefs with no renderable body records. Empty MathML is therefore faithful to the parsed payload, not a MathML-stage or usable-filter bug.",
        }
    if both_metadata_only:
        return {
            "result": "METADATA_ONLY_MTEF_XML",
            "stage": "PARSER_STAGE",
            "decision": "INVESTIGATE_TRANSPECT_CONVERTER",
            "reason": "Both BIN and WMF inputs parse into metadata-only MTEF XML with no line/char/template body records, so empty MathML is produced upstream before usable-sidecar filtering.",
        }
    if any_body_tags and both_empty_math_sidecars:
        return {
            "result": "BODY_PRESENT_BUT_EMPTY_MATHML",
            "stage": "MTEF_TO_MATHML_STAGE",
            "decision": "FIX_MTEF_TO_MATHML_STAGE",
            "reason": "MTEF XML contains renderable body records, but the generated MathML is still empty. That points to loss in the MTEF->MathML transform stage, not to the usable-sidecar filter.",
        }
    if any(status == "usable" for status in [bin_sidecar_status, preview_sidecar_status]):
        return {
            "result": "USABLE_MATH_EXCLUDED",
            "stage": "USABLE_SIDECAR_FILTER",
            "decision": "FIX_USABLE_SIDECAR_FILTER",
            "reason": "A usable MathML sidecar exists, so excluding it would be a usable-sidecar filter bug rather than an upstream conversion failure.",
        }
    return {
        "result": "INCONCLUSIVE",
        "stage": "CONVERTER_INVESTIGATION",
        "decision": "INVESTIGATE_TRANSPECT_CONVERTER",
        "reason": "Could not prove a downstream filtering bug; upstream conversion still needs inspection.",
    }


def choose_decision(groups: list[dict]) -> str:
    for group in groups:
        decision = group["assessment"]["decision"]
        if decision == "FIX_MTEF_TO_MATHML_STAGE":
            return decision
    for group in groups:
        decision = group["assessment"]["decision"]
        if decision == "FIX_USABLE_SIDECAR_FILTER":
            return decision
    for group in groups:
        decision = group["assessment"]["decision"]
        if decision == "UNSUPPORTED_OR_DEGENERATE_PAYLOAD":
            return decision
    for group in groups:
        decision = group["assessment"]["decision"]
        if decision == "INVESTIGATE_TRANSPECT_CONVERTER":
            return decision
    return "NO_ACTION"


def aggregate_reports(reports: list[dict]) -> dict:
    assessment_counts = Counter()
    decision_counts = Counter()
    for report in reports:
        decision_counts[report["decision"]] += 1
        for group in report["groups"]:
            assessment_counts[group["assessment"]["result"]] += 1
    return {
        "preset_count": len(reports),
        "group_count": sum(report["group_count"] for report in reports),
        "assessment_counts": dict(sorted(assessment_counts.items())),
        "decision_counts": dict(sorted(decision_counts.items())),
        "decision": choose_decision([group for report in reports for group in report["groups"]]) if reports else "NO_ACTION",
    }


def emit_text(reports: list[dict], aggregate: dict) -> None:
    for report in reports:
        print(f"{report['preset']}: groups={report['group_count']} decision={report['decision']}")
        for index, group in enumerate(report["groups"], start=1):
            print(f"  group {index}: assessment={group['assessment']['result']} decision={group['assessment']['decision']}")
            print(
                "    "
                + " ".join(
                    [
                        f"bin_hash={group['bin_hash']}",
                        f"preview_hash={group['preview_hash']}",
                        f"occurrences={group['occurrence_count']}",
                        f"prog_id={group['prog_id']}",
                    ]
                )
            )
            print(
                "    "
                + " ".join(
                    [
                        f"bin_sidecar_status={group['bin_sidecar_status']}",
                        f"preview_sidecar_status={group['preview_sidecar_status']}",
                        f"bin_parser_status={group['bin_parser']['status']}",
                        f"preview_parser_status={group['preview_parser']['status']}",
                    ]
                )
            )
            print(
                "    "
                + " ".join(
                    [
                        f"bin_metadata_only={group['bin_mtef_summary']['metadata_only']}",
                        f"preview_metadata_only={group['preview_mtef_summary']['metadata_only']}",
                        f"bin_equation_bytes={group['bin_parser'].get('equation_bytes')}",
                        f"preview_equation_bytes={group['preview_parser'].get('equation_bytes')}",
                    ]
                )
            )
            print(
                "    "
                + " ".join(
                    [
                        f"stage={group['assessment']['stage']}",
                        f"shared_prefix_bytes={group['payload_comparison'].get('shared_prefix_bytes')}",
                        f"same_effective_payload={group['payload_comparison'].get('same_effective_payload')}",
                        f"bin_tail={','.join(group['bin_mtef_summary'].get('tail_after_eqn_prefs', [])) or 'none'}",
                        f"preview_tail={','.join(group['preview_mtef_summary'].get('tail_after_eqn_prefs', [])) or 'none'}",
                    ]
                )
            )
            print(f"    reason={group['assessment']['reason']}")
            if group["payload_comparison"].get("trailing_note"):
                print(f"    payload_note={group['payload_comparison']['trailing_note']}")
            if group["bin_mtef_summary"]["body_tag_counts"]:
                print(f"    bin_body_tags={group['bin_mtef_summary']['body_tag_counts']}")
            if group["preview_mtef_summary"]["body_tag_counts"]:
                print(f"    preview_body_tags={group['preview_mtef_summary']['body_tag_counts']}")
            print(f"    bin_top_level_records={[item['name'] for item in group['bin_parser'].get('top_level_records', [])]}")
            print(f"    preview_top_level_records={[item['name'] for item in group['preview_parser'].get('top_level_records', [])]}")
            if group["text_sample"]:
                print(f"    text={group['text_sample']}")
    print("Aggregate empty-sidecar diagnostics:")
    print(
        "  "
        + " ".join(
            [
                f"preset_count={aggregate['preset_count']}",
                f"group_count={aggregate['group_count']}",
                f"decision={aggregate['decision']}",
            ]
        )
    )
    for result, count in aggregate["assessment_counts"].items():
        print(f"  - {result}={count}")


def text_of(parent: ET.Element | None, child_name: str) -> str | None:
    if parent is None:
        return None
    child = parent.find(child_name)
    return child.text if child is not None else None


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


if __name__ == "__main__":
    raise SystemExit(main())
