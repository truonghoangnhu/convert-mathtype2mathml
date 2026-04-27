# DSMT4 `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` deep-audit

Scope:
- audit/taxonomy/reporting only
- no patch engine changes
- no Java matching-path changes
- no usable-sidecar filter changes
- no converter logic changes
- no production fix branch

Selection priority used here:
1. `in/_Toan_2026_Big.docx`
2. `in/_30_Li_2025.docx`
3. `in/_Hoa_2026_Big.docx`
4. `in/_25_de_Vat_Ly_Very_Big.docx`

## Deep-audit table

| source file | occurrences | payload classes | source families | stage | bytes pairs | main signature/pattern | assessment / decision label | relation to `METADATA_ONLY_FULL_END_ONLY` | recommendation |
| --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |
| `external-docx:in/_Hoa_2026_Big.docx` | 3 | 2 | `_Hoa_2026_Big` | `PARSER_STAGE` | `193/194` | `encoding_def,font_def,font_def,font_def,font_def,eqn_prefs,full,end` | `METADATA_ONLY_MTEF_XML / INVESTIGATE_TRANSPECT_CONVERTER` | No same-source `FULL_END_ONLY` class, but still matches the broader canonical metadata-only `full -> end` shape | Keep taxonomy-only |
| `external-docx:in/_25_de_Vat_Ly_Very_Big.docx` | 2 | 2 | `_25_de_Vat_Ly_Very_Big` | `PARSER_STAGE` | `192/193`, `193/194` | `encoding_def,font_def,font_def,font_def,font_def,eqn_prefs,full,end` | `METADATA_ONLY_MTEF_XML / INVESTIGATE_TRANSPECT_CONVERTER` | No same-source `FULL_END_ONLY` class, but still matches the broader canonical metadata-only `full -> end` shape | Keep taxonomy-only |
| `external-docx:in/_Toan_2026_Big.docx` | 2 | 2 | `_Toan_2026_Big` | `PARSER_STAGE` | `193/194`, `198/199` | `encoding_def,font_def,font_def,font_def,font_def,eqn_prefs,full,end` | `METADATA_ONLY_MTEF_XML / INVESTIGATE_TRANSPECT_CONVERTER` | Same-source near-variant of `FULL_END_ONLY`; one class matches the canonical `193/194` shape directly and one stays close via `198/199` | Keep taxonomy-only |
| `external-docx:in/_30_Li_2025.docx` | 1 | 1 | `_30_Li_2025` | `PARSER_STAGE` | `193/194` | `encoding_def,font_def,font_def,font_def,font_def,eqn_prefs,full,end` | `METADATA_ONLY_MTEF_XML / INVESTIGATE_TRANSPECT_CONVERTER` | Same-source adjacent line to `FULL_END_ONLY`; same `full -> end` tail, but local `FULL_END_ONLY` variant has a different pre-tail record shape (`212/213` plus extra `encoding_def`) | Keep taxonomy-only |

## Signature summary

- total occurrences: `8`
- total payload classes: `7`
- source families: `4`
- canonical structural signature: **yes**
- dominant structural signature:
  - stage `PARSER_STAGE`
  - assessment `METADATA_ONLY_MTEF_XML`
  - decision `INVESTIGATE_TRANSPECT_CONVERTER`
  - parser pair `Mathtype::OleFileParser / Mathtype::WmfFileParser`
  - `same_effective_payload=true`
  - record sequence `encoding_def,font_def,font_def,font_def,font_def,eqn_prefs,full,end`
  - tail `full,end`
  - sidecar status `bin=missing`, `preview=empty_math`

Exact signature groups:
- dominant bytes pair: `193/194`
- dominant exact signature by repeated checksum pair: `35F3/35FD` in `_Hoa_2026_Big` and `_Toan_2026_Big`
- smaller exact variants:
  - `192/193`
  - `198/199`

## Conclusion

- This family now has a canonical structural signature of its own.
- Even so, the current evidence says it is **not** a truly separate line yet; it is best described as a **near-`METADATA_ONLY_FULL_END_ONLY` classification variant**.
- The strongest reason is that every selected payload class still collapses to the same metadata-only `full -> end` shape, with no renderable body evidence and no stable structural split away from the dominant `FULL_END_ONLY` line.
- The current difference is mainly where taxonomy draws the boundary:
  - `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` lands at `PARSER_STAGE / METADATA_ONLY_MTEF_XML`
  - `METADATA_ONLY_FULL_END_ONLY` lands at `PARSER_INPUT_PAYLOAD / TOP_LEVEL_FULL_END_ONLY`

## Decision

- decision label: `KEEP_TAXONOMY_ONLY_NEAR_FULL_END_ONLY`
- open another standalone investigation branch after this: `No`
- if reopened later, target stage: `PARSER_STAGE_VS_PARSER_INPUT_BOUNDARY`
- reopen gate:
  - only if a later audit finds a stable structural split from `FULL_END_ONLY`
  - or a later probe exposes new parser-stage/body evidence

## Re-run

```bash
python3 scripts/workflow/explain_dsmt4_metadata_only_no_renderable_body_other_family.py \
  --external-docx in/_Toan_2026_Big.docx \
  --external-docx in/_30_Li_2025.docx \
  --external-docx in/_Hoa_2026_Big.docx \
  --external-docx in/_25_de_Vat_Ly_Very_Big.docx
```

```bash
python3 scripts/workflow/explain_dsmt4_metadata_only_no_renderable_body_other_family.py \
  --external-docx in/_Toan_2026_Big.docx \
  --external-docx in/_30_Li_2025.docx \
  --external-docx in/_Hoa_2026_Big.docx \
  --external-docx in/_25_de_Vat_Ly_Very_Big.docx \
  --format json
```
