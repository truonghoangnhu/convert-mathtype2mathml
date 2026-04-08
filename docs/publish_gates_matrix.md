# Publish Gates Matrix

Publish gates classify QA findings into four severities:

- `info`
- `warning`
- `error`
- `blocker`

Final verdict logic:

- any `blocker` -> `blocked`
- else any `error` or `warning` -> `needs_review`
- else -> `safe_to_publish`

## Baseline Mapping

### Blocker

- unresolved objects remain
- preview/fallback images remain
- Word field-code leakage remains
- image-field text contamination remains
- unsupported web image formats remain
- web-safe asset policy violations remain
- chemical diagram placeholders/render-fail/blank remain
- answer reconciliation conflicts remain (`answer_source_conflict`, `summary_vs_*_conflict`, `boolean_subanswer_conflict`, `short_answer_value_conflict`, `rubric_source_conflict`)
- canonical answer missing remains (`canonical_answer_missing`)
- in publish mode only:
  - debug attribute leakage
  - internal namespace leakage

### Error

- visible text corruption remains
- chemistry inline/arrow/unit/glyph issues remain
- physics unit/text issues remain
- mixed text + MathML layout issues remain
- math glyph/unreadable symbol issues remain
- Downs reaction notation issues remain

### Warning

- table whitespace/layout polish residuals
- too-small table inline images
- essay figure placement residuals
- oversized-whitespace inline images
- suspicious image crops
- blank generic inline images
- placeholder-like GIF assets
- oversized chemical diagram display cases
- nonessential standalone image candidates remain
- answer resolved from weak secondary source only (`answer_resolved_from_summary_only`, `answer_resolved_from_solution_only`)
- answer summary extraction ambiguity remains (`answer_summary_zone_ambiguous`, `answer_summary_table_shape_unexpected`)
- missing answer summary zone while local extraction remains weak/incomplete (`answer_summary_zone_missing`)

### Info

- non-publish debug leakage in internal mode (tracked, does not block internal outputs)
- redundant-but-consistent answer source confirmation (`answer_summary_redundant_but_consistent`)
- missing answer summary zone with strong local extraction (`answer_summary_zone_missing`, tuned to info)
