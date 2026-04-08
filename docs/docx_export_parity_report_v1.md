# DOCX Export Parity Report v1

This report compares exported teacher DOCX output against the source `exam_bundle.json` and its source HTML.

## Purpose

- verify the exported DOCX still matches the canonical exam structure
- catch regressions in question counts, math presence, images, answer sections, and solution cues
- keep the review deterministic and sample-based

## Report Shape

Top-level fields:

- `schema_version`
- `artifact_type`
- `exam_bundle_path`
- `exported_docx_path`
- `policy`
- `source_metrics`
- `docx_metrics`
- `checks`
- `findings`
- `warnings_count`
- `blockers_count`
- `verdict`

## Metrics

Source-side metrics include:

- question count
- question order
- exam title
- section titles
- MathML count
- image count
- answer summary presence
- solution cue presence

DOCX-side metrics include:

- exam title
- question count before the answer appendix
- question order before the answer appendix
- section titles before the answer appendix
- OMML count
- drawing count
- minimum drawing extent heuristic
- answer heading presence
- answer line count
- solution cue presence

## Example

The clean baseline example is generated at:

- `out/docx-export-smoke/omml-clean-parity.json`
- `out/docx-export-regression-20260408-132014/cases/omml_clean_sample/docx_export_parity_report.md`

Example excerpt:

```json
{
  "schema_version": "docx_export_parity_report.v1",
  "artifact_type": "docx_export_parity_report",
  "verdict": "parity_ok",
  "source_metrics": {
    "exam_title": "Example title",
    "question_count": 0,
    "question_numbers": [],
    "math_count": 2,
    "image_count": 0
  },
  "docx_metrics": {
    "docx_title": "Example title",
    "question_count": 0,
    "question_numbers": [],
    "math_count": 2,
    "drawing_count": 0,
    "has_answer_heading": true,
    "answer_line_count": 0
  },
  "findings": []
}
```

## Status Rules

- `parity_ok`: no blockers and no meaningful review items
- `needs_review`: only warnings or info-level deviations
- `blocked`: at least one blocker

## Markdown Companion

When requested via `--md-out`, the parity checker also writes a compact markdown summary alongside the JSON report.
