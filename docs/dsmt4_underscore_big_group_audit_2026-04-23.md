# DSMT4 underscore-group audit

Scope:
- audit/taxonomy/reporting only
- no product logic changes
- no patch engine changes
- no Java matching-path changes
- no usable-sidecar filter changes
- no converter logic changes

Audit command:

```bash
python3 - <<'PY'
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path('/Users/truonghoangnhu/Desktop/transpect-branch-project')
MODULE_PATH = REPO_ROOT / 'scripts' / 'workflow' / 'audit_dsmt4_corpus.py'
spec = importlib.util.spec_from_file_location('audit_dsmt4_corpus', MODULE_PATH)
AUDIT = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(AUDIT)

docx_paths = [
    REPO_ROOT / 'in' / '_10_TOAN_2025_test.docx',
    REPO_ROOT / 'in' / '_30_Toan_2025.docx',
    REPO_ROOT / 'in' / '_10_Li_2025.docx',
    REPO_ROOT / 'in' / '_30_Li_2025.docx',
    REPO_ROOT / 'in' / '_30_Dethithu_Hoa_2025.docx',
    REPO_ROOT / 'in' / '_30_Hoa_2025.docx',
    REPO_ROOT / 'in' / '_25_de_Vat_Ly_Very_Big.docx',
    REPO_ROOT / 'in' / '_Hoa_2026_Big.docx',
    REPO_ROOT / 'in' / '_Ly_2026_Big.docx',
    REPO_ROOT / 'in' / '_Toan_2026_Big.docx',
]

sources = AUDIT.build_external_docx_sources(
    docx_paths=docx_paths,
    external_dirs=[],
    prefer_underscore_first=False,
    external_work_root=Path(AUDIT.DEFAULT_EXTERNAL_AUDIT_ROOT),
)
reports = [AUDIT.collect_source_occurrences(source) for source in sources]
runtime = AUDIT.EMPTY.discover_runtime() if AUDIT.needs_deep_audit(reports) else None
payload_classes = AUDIT.classify_payload_classes(reports, runtime)
aggregate = AUDIT.aggregate_payload_classes(payload_classes, [], sources)
external_summaries = AUDIT.summarize_external_sources(payload_classes, [], sources)

source_pattern_counts = defaultdict(Counter)
source_pattern_occurrences = defaultdict(Counter)
for entry in payload_classes:
    if entry.get('source_group') != 'external':
        continue
    for source_name in entry.get('source_names', []):
        source_pattern_counts[source_name][entry.get('pattern_class', 'UNKNOWN_PATTERN')] += 1
        source_pattern_occurrences[source_name][entry.get('pattern_class', 'UNKNOWN_PATTERN')] += entry.get('occurrence_count', 0)

summary = {
    'files': [
        {
            'source_name': s['source_name'],
            'docx_path': s['docx_path'],
            'workdir': s['workdir'],
            'dsmt4_occurrences': s['dsmt4_occurrences'],
            'dsmt4_payload_classes': s['dsmt4_payload_classes'],
            'dsmt4_new_payload_classes_so_far': s['dsmt4_new_payload_classes_so_far'],
            'dsmt4_metadata_only_classes': s['dsmt4_metadata_only_classes'],
            'full_end_only_present': s['full_end_only_present'],
        }
        for s in external_summaries
    ],
    'repeat_family_files': {
        family: [
            s['source_name']
            for s in external_summaries
            if source_pattern_counts[s['source_name']].get(family, 0) > 0
        ]
        for family in [
            'METADATA_ONLY_FULL_END_ONLY',
            'METADATA_ONLY_NO_RENDERABLE_BODY_OTHER',
            'EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY',
        ]
    },
    'novel_degenerate_families': [],
    'top_file_deep_audit': max(
        external_summaries,
        key=lambda s: (s['dsmt4_occurrences'], s['dsmt4_payload_classes'], s['dsmt4_metadata_only_classes'], s['dsmt4_new_payload_classes_so_far']),
    ),
    'aggregate': {
        'decision': aggregate['decision'],
        'decision_reason': aggregate['decision_reason'],
        'top_degenerate_pattern_classes': aggregate['top_degenerate_pattern_classes'],
        'top_degenerate_pattern_signatures': aggregate['top_degenerate_pattern_signatures'],
        'metadata_only_patterns': aggregate['metadata_only_patterns'],
    },
}
print(json.dumps(summary, ensure_ascii=True, indent=2))
PY
```

## Per-file summary

| File | dsmt4_occurrences | dsmt4_payload_classes | dsmt4_new_payload_classes_so_far | dsmt4_metadata_only_classes | full_end_only_present |
| --- | ---: | ---: | ---: | ---: | --- |
| `_10_TOAN_2025_test.docx` | 3839 | 2811 | 2811 | 0 | false |
| `_30_Toan_2025.docx` | 265 | 205 | 205 | 0 | false |
| `_10_Li_2025.docx` | 256 | 201 | 201 | 1 | true |
| `_30_Li_2025.docx` | 1051 | 918 | 826 | 2 | true |
| `_30_Dethithu_Hoa_2025.docx` | 674 | 383 | 383 | 0 | false |
| `_30_Hoa_2025.docx` | 674 | 383 | 0 | 0 | false |
| `_25_de_Vat_Ly_Very_Big.docx` | 330 | 294 | 294 | 2 | true |
| `_Hoa_2026_Big.docx` | 723 | 371 | 366 | 2 | true |
| `_Ly_2026_Big.docx` | 3706 | 1968 | 1968 | 1 | true |
| `_Toan_2026_Big.docx` | 4904 | 3572 | 3514 | 3 | true |

## Repeated families

- `METADATA_ONLY_FULL_END_ONLY`: `_10_Li_2025.docx`, `_30_Li_2025.docx`, `_Ly_2026_Big.docx`, `_Toan_2026_Big.docx`
- `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER`: `_30_Li_2025.docx`, `_25_de_Vat_Ly_Very_Big.docx`, `_Hoa_2026_Big.docx`, `_Toan_2026_Big.docx`
- `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY`: none in this 10-file group

## Conclusions

- top file worth deep-auditing next: `_Toan_2026_Big.docx`
- source family with the highest follow-up value in this set: `toan-2026-big`
- family to follow up next: `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER`, then `METADATA_ONLY_FULL_END_ONLY`
- no novel degenerate family was found in this underscore group
- the aggregate corpus decision for this set is `CONFIRMED_UNSUPPORTED_OR_DEGENERATE_PAYLOAD_CLASS`

## Re-run

```bash
# Use the "Audit command" block above.
```
