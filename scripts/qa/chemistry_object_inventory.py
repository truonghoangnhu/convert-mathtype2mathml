#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


@dataclass(frozen=True)
class InventoryItem:
    family: str
    behavior: str
    remediation: str
    count: int
    examples: List[Dict[str, str]]


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def infer_family(obj: Dict) -> str:
    placeholder_family = (obj.get("placeholder_family") or "").strip().lower()
    if placeholder_family:
        return placeholder_family
    fallback_type = (obj.get("fallback_type") or "").strip().lower()
    classification = (obj.get("classification") or "").strip().lower()
    prog_id = (obj.get("prog_id") or "").strip().lower()
    if "chemdraw" in prog_id:
        return "chemdraw"
    if "chemsketch" in prog_id:
        return "chemsketch"
    if "chemwindow" in prog_id:
        return "chemwindow"
    if classification == "chemical-diagram":
        return "chemical-diagram"
    if fallback_type == "unsupported-inline-metafile":
        return "inline-metafile"
    if fallback_type == "unsupported-web-image-inline":
        return "unsupported-web-image-inline"
    if fallback_type == "placeholder-gif-inline-image":
        return "placeholder-gif-inline-image"
    return classification or "unknown"


def infer_behavior(obj: Dict, family: str) -> str:
    scope = (obj.get("scope") or "").strip().lower()
    render_success = bool(obj.get("render_success"))
    render_output_type = (obj.get("render_output_type") or "").strip().lower()
    fallback_type = (obj.get("fallback_type") or "").strip().lower()
    if render_success and render_output_type in {"svg", "png", "gif", "jpg", "jpeg", "webp"}:
        return "rendered asset already present"
    if family in {"chemdraw", "chemsketch", "chemwindow", "chemical-diagram"}:
        return "visible unresolved chemical-diagram placeholder"
    if family == "inline-metafile":
        return "hidden QA-only unsupported inline-image placeholder" if scope == "html-placeholder" else "inline metafile placeholder"
    if fallback_type == "unsupported-web-image-inline":
        return "unsupported inline web image placeholder"
    if fallback_type == "placeholder-gif-inline-image":
        return "placeholder GIF fallback"
    if scope == "html-placeholder":
        return "visible unresolved placeholder"
    return "unresolved placeholder"


def infer_remediation(family: str, obj: Dict) -> str:
    render_attempted = bool(obj.get("render_attempted"))
    render_source_used = (obj.get("render_source_used") or "").strip().lower()
    fallback_type = (obj.get("fallback_type") or "").strip().lower()
    if family in {"chemdraw", "chemsketch"}:
        if not render_attempted:
            return "inspect embedded OLE source or add explicit manual cleanup metadata"
        if "preview-image" in render_source_used:
            return "improve preview extraction/rasterization or preserve explicit unresolved metadata"
        return "inspect ChemDraw/ChemSketch binary source and keep unresolved when no faithful render exists"
    if family == "chemwindow":
        return "best-effort preview rendering already applies; unresolved cases need source inspection"
    if family == "chemical-diagram":
        return "keep as unresolved chemical-diagram with explicit provenance until a faithful render exists"
    if family == "inline-metafile":
        return "classify as unsupported inline metafile and keep unresolved unless a web-safe preview is available"
    if fallback_type == "unsupported-web-image-inline":
        return "retain unsupported inline image metadata for manual cleanup"
    return "manual review"


def inventory_from_report(report: Dict) -> List[InventoryItem]:
    buckets: Dict[str, List[Dict]] = defaultdict(list)
    for obj in report.get("unresolved_objects", []):
        family = infer_family(obj)
        buckets[family].append(obj)

    items: List[InventoryItem] = []
    for family, objects in sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        examples = []
        for obj in objects[:5]:
            examples.append(
                {
                    "exam": obj.get("exam", ""),
                    "location": obj.get("location", ""),
                    "classification": obj.get("classification", ""),
                    "fallback_type": obj.get("fallback_type", ""),
                    "prog_id": obj.get("prog_id", ""),
                    "render_source_used": obj.get("render_source_used", ""),
                    "render_output_type": obj.get("render_output_type", ""),
                    "placeholder_family": obj.get("placeholder_family", ""),
                    "unresolved_reason": obj.get("unresolved_reason", ""),
                }
            )
        behavior = infer_behavior(objects[0], family)
        remediation = infer_remediation(family, objects[0])
        items.append(
            InventoryItem(
                family=family,
                behavior=behavior,
                remediation=remediation,
                count=len(objects),
                examples=examples,
            )
        )
    return items


def summarize_reports(report_paths: Sequence[Path]) -> Dict:
    reports: List[Dict] = []
    for path in report_paths:
        if not path.exists():
            raise FileNotFoundError(path)
        reports.append(load_json(path))

    items_by_family: Dict[str, Counter] = defaultdict(Counter)
    example_by_family: Dict[str, List[Dict]] = defaultdict(list)
    totals = Counter()
    sources: List[Dict[str, str]] = []

    for path, report in zip(report_paths, reports):
        sources.append(
            {
                "qa_json": str(path),
                "subject": report.get("subject", ""),
                "html": report.get("html", ""),
                "publish_verdict": report.get("publish_verdict", ""),
            }
        )
        for obj in report.get("unresolved_objects", []):
            family = infer_family(obj)
            items_by_family[family]["count"] += 1
            if not example_by_family[family] or len(example_by_family[family]) < 5:
                example_by_family[family].append(
                    {
                        "exam": obj.get("exam", ""),
                        "location": obj.get("location", ""),
                        "classification": obj.get("classification", ""),
                        "fallback_type": obj.get("fallback_type", ""),
                        "prog_id": obj.get("prog_id", ""),
                        "render_source_used": obj.get("render_source_used", ""),
                        "render_output_type": obj.get("render_output_type", ""),
                        "placeholder_family": obj.get("placeholder_family", ""),
                        "unresolved_reason": obj.get("unresolved_reason", ""),
                    }
                )
            totals["unresolved_objects"] += 1
            if (obj.get("classification") or "").strip().lower() == "chemical-diagram":
                totals["chemical_diagram_objects"] += 1
            if (obj.get("fallback_type") or "").strip().lower() == "unsupported-placeholder":
                totals["unsupported_placeholder_objects"] += 1
            if (obj.get("fallback_type") or "").strip().lower() == "unsupported-inline-metafile":
                totals["inline_metafile_objects"] += 1

    families: List[Dict] = []
    for family, counter in sorted(items_by_family.items(), key=lambda kv: (-kv[1]["count"], kv[0])):
        sample_obj = None
        for report in reports:
            for obj in report.get("unresolved_objects", []):
                if infer_family(obj) == family:
                    sample_obj = obj
                    break
            if sample_obj is not None:
                break
        if sample_obj is None:
            continue
        items = inventory_from_report({"unresolved_objects": [sample_obj] * counter["count"]})
        inventory_item = items[0]
        families.append(
            {
                "family": inventory_item.family,
                "count": counter["count"],
                "current_output_behavior": inventory_item.behavior,
                "likely_remediation_path": inventory_item.remediation,
                "examples": example_by_family[family],
            }
        )

    return {
        "schema_version": "chemistry.object.inventory.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "totals": dict(totals),
        "families": families,
    }


def to_markdown(summary: Dict) -> str:
    lines: List[str] = []
    lines.append("# Chemistry Object Inventory")
    lines.append("")
    lines.append(f"- Schema version: `{summary['schema_version']}`")
    lines.append(f"- Generated at: `{summary['generated_at']}`")
    lines.append(f"- Source reports: {len(summary.get('sources', []))}")
    lines.append("")
    lines.append("## Totals")
    lines.append("")
    totals = summary.get("totals", {})
    for key in sorted(totals):
        lines.append(f"- {key}: {totals[key]}")
    lines.append("")
    lines.append("## Families")
    lines.append("")
    lines.append("| family | count | current output behavior | likely remediation path |")
    lines.append("|---|---:|---|---|")
    for item in summary.get("families", []):
        lines.append(
            "| `{family}` | {count} | {behavior} | {remediation} |".format(
                family=item["family"],
                count=item["count"],
                behavior=item["current_output_behavior"],
                remediation=item["likely_remediation_path"],
            )
        )
    lines.append("")
    for item in summary.get("families", []):
        lines.append(f"### {item['family']}")
        lines.append("")
        lines.append(f"- Count: {item['count']}")
        lines.append(f"- Current output behavior: {item['current_output_behavior']}")
        lines.append(f"- Likely remediation path: {item['likely_remediation_path']}")
        if item.get("examples"):
            lines.append("")
            lines.append("| exam | location | classification | fallback | prog_id | reason |")
            lines.append("|---|---|---|---|---|---|")
            for ex in item["examples"][:5]:
                lines.append(
                    "| `{exam}` | `{location}` | `{classification}` | `{fallback_type}` | `{prog_id}` | `{unresolved_reason}` |".format(
                        exam=ex.get("exam", ""),
                        location=ex.get("location", ""),
                        classification=ex.get("classification", ""),
                        fallback_type=ex.get("fallback_type", ""),
                        prog_id=ex.get("prog_id", ""),
                        unresolved_reason=ex.get("unresolved_reason", ""),
                    )
                )
        lines.append("")
    return "\n".join(lines) + "\n"


def write_outputs(summary: Dict, output_dir: Path, stem: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{stem}.chemistry_inventory.json"
    md_path = output_dir / f"{stem}.chemistry_inventory.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(summary), encoding="utf-8")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize unresolved chemistry objects from QA reports.")
    parser.add_argument("--qa-json", dest="qa_json", action="append", type=Path, required=True, help="QA JSON report(s) to inspect.")
    parser.add_argument("--output-dir", type=Path, default=Path("out/chemistry-object-inventory"))
    parser.add_argument("--stem", default="chemistry_object_inventory")
    args = parser.parse_args()

    summary = summarize_reports([path.resolve() for path in args.qa_json])
    json_path, md_path = write_outputs(summary, args.output_dir.resolve(), args.stem)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
