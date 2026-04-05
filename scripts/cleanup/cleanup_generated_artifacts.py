#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set


RUN_DIR_PATTERN = re.compile(r".*-\d{8}-\d{6}$")
HTML_REF_PATTERN = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
CSS_URL_PATTERN = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""", re.IGNORECASE)


@dataclass
class Candidate:
    path: Path
    reason: str
    size_bytes: int
    kind: str


def path_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def list_run_dirs_for_cleanup(
    root: Path,
    *,
    keep_latest: int,
    min_age_hours: float,
    protected_names: Set[str],
) -> List[Candidate]:
    if not root.exists():
        return []
    run_dirs = [p for p in root.iterdir() if p.is_dir() and RUN_DIR_PATTERN.match(p.name)]
    run_dirs.sort(key=lambda p: p.stat().st_mtime_ns, reverse=True)
    now = time.time()
    keep_set: Set[str] = set(protected_names)
    for directory in run_dirs[: max(0, keep_latest)]:
        keep_set.add(directory.name)

    candidates: List[Candidate] = []
    for directory in run_dirs:
        if directory.name in keep_set:
            continue
        age_hours = max(0.0, (now - directory.stat().st_mtime) / 3600.0)
        if age_hours < min_age_hours:
            continue
        candidates.append(
            Candidate(
                path=directory,
                reason=f"old generated run dir ({age_hours:.1f}h)",
                size_bytes=path_size(directory),
                kind="directory",
            )
        )
    return candidates


def collect_html_asset_refs(html_path: Path, asset_dir: Path) -> Set[str]:
    text = html_path.read_text(encoding="utf-8", errors="ignore")
    refs: Set[str] = set()
    for pattern in (HTML_REF_PATTERN, CSS_URL_PATTERN):
        for match in pattern.finditer(text):
            value = match.group(1).strip()
            if not value:
                continue
            value = value.split("#", 1)[0].split("?", 1)[0]
            if not value:
                continue
            if value.startswith(("http://", "https://", "data:", "mailto:")):
                continue
            if value.startswith(asset_dir.name + "/"):
                refs.add(value[len(asset_dir.name) + 1 :].replace("\\", "/"))
    return refs


def list_orphan_assets(out_root: Path) -> List[Candidate]:
    candidates: List[Candidate] = []
    if not out_root.exists():
        return candidates
    for html_path in out_root.rglob("*-transpect.html"):
        if not html_path.is_file():
            continue
        asset_dir = html_path.with_name(html_path.stem + "_files")
        if not asset_dir.exists() or not asset_dir.is_dir():
            continue
        referenced = collect_html_asset_refs(html_path, asset_dir)
        for asset in asset_dir.rglob("*"):
            if not asset.is_file():
                continue
            rel = asset.relative_to(asset_dir).as_posix()
            if rel in referenced:
                continue
            candidates.append(
                Candidate(
                    path=asset,
                    reason=f"orphan asset (not referenced by {html_path.name})",
                    size_bytes=path_size(asset),
                    kind="file",
                )
            )
    return candidates


def remove_candidate(candidate: Candidate) -> bool:
    try:
        if candidate.kind == "directory":
            shutil.rmtree(candidate.path)
        else:
            candidate.path.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Safe cleanup for generated batch artifacts.")
    parser.add_argument("--work-root", type=Path, default=repo_root / "work")
    parser.add_argument("--out-root", type=Path, default=repo_root / "out")
    parser.add_argument("--keep-work-runs", type=int, default=6)
    parser.add_argument("--keep-out-runs", type=int, default=12)
    parser.add_argument("--min-age-hours", type=float, default=24.0)
    parser.add_argument("--prune-work-runs", action="store_true")
    parser.add_argument("--prune-out-runs", action="store_true")
    parser.add_argument("--prune-orphan-assets", action="store_true")
    parser.add_argument("--protected-name", action="append", default=[])
    parser.add_argument("--report-json", type=Path, default=None)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    protected_names = set(args.protected_name)
    all_candidates: List[Candidate] = []

    if args.prune_work_runs:
        all_candidates.extend(
            list_run_dirs_for_cleanup(
                args.work_root.resolve(),
                keep_latest=max(0, args.keep_work_runs),
                min_age_hours=args.min_age_hours,
                protected_names=protected_names,
            )
        )
    if args.prune_out_runs:
        all_candidates.extend(
            list_run_dirs_for_cleanup(
                args.out_root.resolve(),
                keep_latest=max(0, args.keep_out_runs),
                min_age_hours=args.min_age_hours,
                protected_names=protected_names,
            )
        )
    if args.prune_orphan_assets:
        all_candidates.extend(list_orphan_assets(args.out_root.resolve()))

    # Avoid duplicate removals where a file is inside a candidate directory.
    all_candidates.sort(key=lambda c: len(c.path.parts))
    deduped: List[Candidate] = []
    covered: List[Path] = []
    for candidate in all_candidates:
        if any(parent == candidate.path or parent in candidate.path.parents for parent in covered):
            continue
        deduped.append(candidate)
        if candidate.kind == "directory":
            covered.append(candidate.path)

    removed: List[Dict] = []
    failed: List[Dict] = []
    for candidate in deduped:
        item = {
            "path": str(candidate.path),
            "reason": candidate.reason,
            "size_bytes": candidate.size_bytes,
            "kind": candidate.kind,
        }
        if args.apply:
            ok = remove_candidate(candidate)
            if ok:
                removed.append(item)
            else:
                failed.append(item)
        else:
            removed.append(item)

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "apply" if args.apply else "dry-run",
        "work_root": str(args.work_root.resolve()),
        "out_root": str(args.out_root.resolve()),
        "rules": {
            "prune_work_runs": args.prune_work_runs,
            "prune_out_runs": args.prune_out_runs,
            "prune_orphan_assets": args.prune_orphan_assets,
            "keep_work_runs": args.keep_work_runs,
            "keep_out_runs": args.keep_out_runs,
            "min_age_hours": args.min_age_hours,
            "protected_name": sorted(protected_names),
        },
        "candidates_count": len(deduped),
        "candidates_total_bytes": sum(item["size_bytes"] for item in removed) if removed else 0,
        "removed_or_listed": removed,
        "failed_to_remove": failed,
    }

    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

