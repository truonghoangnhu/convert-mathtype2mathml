# DSMT4 Taxonomy Lines Report

This report freezes the current taxonomy-only comparison for three degenerate DSMT4 lines.

Scope:

- docs/reporting/artifact only
- no DOCX patch engine changes
- no Java matching path changes
- no usable-sidecar filter changes
- no converter logic changes

## Taxonomy-Only Comparison

| family | source files | occurrences | payload classes | source families | stage | main signature/pattern | repeats? | relation to dominant `METADATA_ONLY_FULL_END_ONLY` line | recommendation |
|---|---|---:|---:|---:|---|---|---|---|---|
| `METADATA_ONLY_FULL_END_ONLY` | `in/10_Toan_HCM_2026.docx`, `in/_Toan_2026_Big.docx`, `in/_Ly_2026_Big.docx` | 10 | 6 | 4 | `PARSER_INPUT_PAYLOAD` | canonical shape `encoding_def,font_def,font_def,font_def,font_def,eqn_prefs,full,end`; same-effective payload; dominant signature repeatedly includes bytes `193/194` | Yes, across multiple source families | This is the dominant unsupported subtype line | Follow-up target, but still investigation-only; do not open a production fix |
| `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` | `in/_Toan_2026_Big.docx` | 2 | 2 | 1 | `PARSER_STAGE` | metadata-only MTEF XML; same-effective payload; tail still `full,end`; two signatures currently visible: `198/199` and `193/194` | No, not yet across source families | Very close to the dominant line in `full -> end` shape, but taxonomy differs because it lands in `METADATA_ONLY_MTEF_XML` / `INVESTIGATE_TRANSPECT_CONVERTER` instead of `TOP_LEVEL_FULL_END_ONLY` | Keep in taxonomy for now; prefer corpus/spec expansion before any dedicated follow-up |
| `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY` | `in/10_Toan_HCM_2026.docx` | 1 | 1 | 1 | `CONVERTER_INVESTIGATION` | `mt_comment` prefix before `encoding_def`; same-effective payload; bytes `216/217`; tail still `full,end`; decision currently `INCONCLUSIVE` + `INVESTIGATE_TRANSPECT_CONVERTER` | No | Not the dominant line; only partially similar because it still ends at `full -> end`, but it differs clearly by `mt_comment` prefix and converter-stage placement | Best converter-stage follow-up target among the three lines |

## Combined Conclusion

- Dominant unsupported subtype line:
  - `METADATA_ONLY_FULL_END_ONLY`
- Converter-stage follow-up tốt nhất:
  - `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY`
- Line chỉ nên giữ trong taxonomy lúc này:
  - `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER`
- Priority follow-up:
  1. `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY`
  2. `METADATA_ONLY_FULL_END_ONLY`
  3. `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER`
- Non-goal:
  - do not open a production fix yet

## Regenerate

Per-file cache audits:

```bash
python3 scripts/workflow/audit_dsmt4_corpus.py \
  --all-presets \
  --extra-workdir work/dsmt4-external-audit/10-toan-hcm-2026--5c97b34e92a9 \
  --format json > /tmp/audit_10toanhcm.json
```

```bash
python3 scripts/workflow/audit_dsmt4_corpus.py \
  --all-presets \
  --extra-workdir work/dsmt4-external-audit/toan-2026-big--3457e9e43ced \
  --format json > /tmp/audit_toan2026.json
```

```bash
python3 scripts/workflow/audit_dsmt4_corpus.py \
  --all-presets \
  --extra-workdir work/dsmt4-external-audit/ly-2026-big--74bc115a3fe8 \
  --format json > /tmp/audit_ly2026.json
```

Combined top-3 taxonomy:

```bash
python3 scripts/workflow/audit_dsmt4_corpus.py \
  --all-presets \
  --extra-workdir work/dsmt4-external-audit/toan-2026-big--3457e9e43ced \
  --extra-workdir work/dsmt4-external-audit/10-toan-hcm-2026--5c97b34e92a9 \
  --extra-workdir work/dsmt4-external-audit/ly-2026-big--74bc115a3fe8 \
  --format json > /tmp/audit_top3_combined.json
```
