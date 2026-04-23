# DSMT4 Full `in/*` Corpus Audit

Scope:

- audit/taxonomy/reporting only
- reused existing cache/workdir from `work/dsmt4-external-audit/*` for all `28` DOCX files
- no patch engine changes
- no Java matching-path changes
- no usable-sidecar filter changes
- no parser/converter default-behavior changes
- no production fix branch

Inventory order used for this audit:

- filenames starting with `_` first
- then descending DOCX size
- cache/workdir reuse throughout

## Per-file summary

| file | size | dsmt4_occurrences | dsmt4_payload_classes | dsmt4_new_payload_classes_so_far | dsmt4_metadata_only_classes | full_end_only_present |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `_30_Toan_2025.docx` | `15229525` | 265 | 205 | 205 | 0 | false |
| `_30_Li_2025.docx` | `13607551` | 1051 | 918 | 918 | 2 | true |
| `_Ly_2026_Big.docx` | `12908339` | 3706 | 1968 | 1968 | 1 | true |
| `_10_TOAN_2025_test.docx` | `8884492` | 3839 | 2811 | 2811 | 0 | false |
| `_Toan_2026_Big.docx` | `8519760` | 4904 | 3572 | 3514 | 3 | true |
| `_30_Dethithu_Hoa_2025.docx` | `8424845` | 674 | 383 | 383 | 0 | false |
| `_30_Hoa_2025.docx` | `8424845` | 674 | 383 | 0 | 0 | false |
| `_10_Li_2025.docx` | `6510656` | 256 | 201 | 109 | 1 | true |
| `_Hoa_2026_Big.docx` | `5064437` | 723 | 371 | 366 | 2 | true |
| `_25_de_Vat_Ly_Very_Big.docx` | `4149912` | 330 | 294 | 294 | 2 | true |
| `10_VatLi_2026.docx` | `12600747` | 564 | 510 | 508 | 2 | true |
| `10_Toan_HCM_2026.docx` | `8974193` | 4369 | 3539 | 3539 | 1 | true |
| `20_HoaHoc_2026.docx` | `4842031` | 804 | 484 | 468 | 3 | true |
| `Toan_Phi.docx` | `2586091` | 829 | 821 | 821 | 0 | false |
| `Toan_deso_22_small.docx` | `1622298` | 489 | 304 | 230 | 0 | false |
| `Vat_Ly_Le_Khiet.docx` | `1468149` | 281 | 281 | 281 | 0 | false |
| `Toan_deso_12_small.docx` | `1227711` | 320 | 242 | 235 | 0 | false |
| `Toan_deso_11_TB.docx` | `1112768` | 485 | 312 | 312 | 1 | true |
| `0101_Nghe_An.docx` | `741317` | 288 | 288 | 288 | 0 | false |
| `0102_Quang_Ninh.docx` | `603812` | 174 | 170 | 170 | 0 | false |
| `Hoa_Ha_Noi_L1.docx` | `499699` | 267 | 170 | 170 | 0 | false |
| `Hoa_Bac-Ninh_L1.docx` | `478441` | 103 | 54 | 53 | 0 | false |
| `De_L1_Quang_Ngai.docx` | `472289` | 122 | 118 | 118 | 0 | false |
| `Toan_de_1202.docx` | `416485` | 120 | 120 | 120 | 0 | false |
| `34_thuvienvatly.docx` | `366016` | 17 | 17 | 17 | 0 | false |
| `Hoa_Ha_Tinh_L1.docx` | `359053` | 90 | 90 | 89 | 0 | false |
| `Vat_Ly_207_nam_2021.docx` | `358228` | 16 | 16 | 16 | 0 | false |
| `Pham Nghia.docx` | `43949` | 11 | 11 | 11 | 0 | false |

## Existing Family Repeats

- `METADATA_ONLY_FULL_END_ONLY`: `10_Toan_HCM_2026.docx`, `10_VatLi_2026.docx`, `20_HoaHoc_2026.docx`, `Toan_deso_11_TB.docx`, `_10_Li_2025.docx`, `_30_Li_2025.docx`, `_Ly_2026_Big.docx`, `_Toan_2026_Big.docx`
- `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER`: `10_VatLi_2026.docx`, `20_HoaHoc_2026.docx`, `_25_de_Vat_Ly_Very_Big.docx`, `_30_Li_2025.docx`, `_Hoa_2026_Big.docx`, `_Toan_2026_Big.docx`
- `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY`: `10_Toan_HCM_2026.docx`

## Combined Taxonomy Summary

| field | value |
| --- | --- |
| files audited from cache/workdir | 28 |
| dsmt4_external_occurrences_total | 25771 |
| dsmt4_external_payload_classes_total | 18014 |
| dsmt4_external_new_payload_classes_total | 18014 |
| dsmt4_external_metadata_only_classes | 17 |
| dsmt4_empty_generated_sidecar_classes | 1 |
| dsmt4_other_parser_pattern_classes | 0 |
| decision | `CONFIRMED_UNSUPPORTED_OR_DEGENERATE_PAYLOAD_CLASS` |

Top degenerate pattern classes across the full corpus:

| family | payload classes | occurrences | source families |
| --- | ---: | ---: | ---: |
| `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` | 10 | 11 | 6 |
| `METADATA_ONLY_FULL_END_ONLY` | 7 | 11 | 8 |
| `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY` | 1 | 1 | 1 |

Top degenerate signatures across the full corpus:

| family | stage | payload classes | occurrences | source families | bytes pair | main signature/pattern |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `METADATA_ONLY_FULL_END_ONLY` | `PARSER_INPUT_PAYLOAD` | 3 | 5 | 3 | `193/194` | `encoding_def, font_def, font_def, font_def, font_def, eqn_prefs, full, end` |
| `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` | `PARSER_STAGE` | 3 | 4 | 2 | `193/194` | `encoding_def, font_def, font_def, font_def, font_def, eqn_prefs, full, end` |
| `METADATA_ONLY_FULL_END_ONLY` | `PARSER_INPUT_PAYLOAD` | 1 | 2 | 2 | `212/213` | `encoding_def, font_def, encoding_def, font_def, font_def, font_def, font_def, eqn_prefs, full, end` |
| `METADATA_ONLY_FULL_END_ONLY` | `PARSER_INPUT_PAYLOAD` | 1 | 2 | 1 | `212/213` | `encoding_def, font_def, font_def, font_def, font_def, font_def, eqn_prefs, full, end` |
| `METADATA_ONLY_FULL_END_ONLY` | `PARSER_INPUT_PAYLOAD` | 1 | 1 | 1 | `192/193` | `encoding_def, font_def, font_def, font_def, font_def, eqn_prefs, full, end` |
| `METADATA_ONLY_FULL_END_ONLY` | `PARSER_INPUT_PAYLOAD` | 1 | 1 | 1 | `193/194` | `encoding_def, font_def, font_def, font_def, font_def, eqn_prefs, full, end` |
| `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` | `PARSER_STAGE` | 1 | 1 | 1 | `187/188` | `encoding_def, font_def, font_def, font_def, font_def, eqn_prefs, full, end` |
| `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` | `PARSER_STAGE` | 1 | 1 | 1 | `191/192` | `encoding_def, font_def, font_def, font_def, font_def, eqn_prefs, full, end` |
| `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` | `PARSER_STAGE` | 1 | 1 | 1 | `192/193` | `encoding_def, font_def, font_def, font_def, font_def, eqn_prefs, full, end` |
| `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` | `PARSER_STAGE` | 1 | 1 | 1 | `193/194` | `encoding_def, font_def, font_def, font_def, font_def, eqn_prefs, full, end` |

## New Degenerate Families

- No new degenerate family appeared beyond the current three-line taxonomy.

## Current Readout

- `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` is now the broadest repeating degenerate family by corpus spread: `10` payload classes / `11` occurrences / `6` source families. This strengthens coverage only; it does not change the current conclusion that this line is still a taxonomy-only near-`FULL_END_ONLY` variant.
- `METADATA_ONLY_FULL_END_ONLY` remains the dominant unsupported-subtype line in the current taxonomy baseline, with repeated full-corpus footprint of `7` payload classes / `11` occurrences / `8` source families.
- `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY` still appears in exactly one source only: `10_Toan_HCM_2026.docx`.
- No second source family was found for `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY`.

## Top 5 Deep-Audit Next

- `_Toan_2026_Big.docx`
- `20_HoaHoc_2026.docx`
- `_30_Li_2025.docx`
- `10_VatLi_2026.docx`
- `10_Toan_HCM_2026.docx`

Rationale:

- `_Toan_2026_Big.docx`: largest already-known mixed degenerate source with both metadata-only lines and highest novelty.
- `20_HoaHoc_2026.docx`: non-underscore source where both metadata-only lines co-occur and `dsmt4_metadata_only_classes=3`.
- `_30_Li_2025.docx`: large underscore source with both metadata-only lines and the cleanest source-local split history.
- `10_VatLi_2026.docx`: new non-underscore mixed source where both metadata-only lines repeat strongly.
- `10_Toan_HCM_2026.docx`: only source that still carries the converter/classification-boundary family.

## Recommended Next Step

- Keep taxonomy frozen at the current three lines.
- If one follow-up is needed, prefer `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY` because it still has only one source family and remains the narrowest unresolved classification-boundary line.
- If the goal is corpus strengthening instead, deep-audit the non-underscore mixed sources `20_HoaHoc_2026.docx` and `10_VatLi_2026.docx` before opening any new branch.

## Re-run

Priority-ordered cached full audit was produced with this local module call:

```bash
python3 - <<'PY'
from pathlib import Path
import json, importlib.util
repo = Path('.')
script_path = repo / 'scripts' / 'workflow' / 'audit_dsmt4_corpus.py'
spec = importlib.util.spec_from_file_location('audit_dsmt4_corpus', script_path)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)
preset_registry = mod.load_preset_registry(mod.PRESET_CONFIG)
ordered = sorted((repo / 'in').glob('*.docx'), key=lambda p: (not p.name.startswith('_'), -p.stat().st_size, p.name.lower()))
sources = []
for p in ordered:
    workdir = mod.ensure_external_docx_workdir(p.resolve(), repo / 'work' / 'dsmt4-external-audit')
    sources.extend(mod.build_external_workdir_sources(preset_registry=preset_registry, extra_workdirs=[workdir.resolve()], scan_paths=[]))
reports = [mod.collect_source_occurrences(source) for source in sources]
runtime = mod.EMPTY.discover_runtime() if mod.needs_deep_audit(reports) else None
payload_classes = mod.classify_payload_classes(reports, runtime)
aggregate = mod.aggregate_payload_classes(payload_classes, registry_sources=[], external_sources=sources)
external_source_summaries = mod.summarize_external_sources(payload_classes, registry_sources=[], external_sources=sources)
print(json.dumps({'aggregate': aggregate, 'external_source_summaries': external_source_summaries}, ensure_ascii=False, indent=2))
PY
```

A simple cache-only inventory check:

```bash
find in -maxdepth 1 -type f -name '*.docx' | sort
find work/dsmt4-external-audit -maxdepth 1 -mindepth 1 -type d | sort
```
