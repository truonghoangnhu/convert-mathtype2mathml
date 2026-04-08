# DOCX Export Failure Policy v1

This note documents the hardened failure policy used by the teacher DOCX export prototype.

## Goal

- keep the prototype honest about real export failures
- allow small, readable degradations without treating them as fatal
- block only on structural or openability failures

## Current Default Thresholds

Math:

- warning if failed math is within a small tolerance
- blocker if failed math exceeds the blocker count or ratio threshold

Images:

- warning if failed images are within a small tolerance
- blocker if failed images exceed the blocker count or ratio threshold

Openability:

- DOCX zip integrity failure is a blocker
- `soffice` round-trip failure is a blocker when the check runs
- missing `soffice` binary is a warning, not a blocker

## Severity Rules

Mapped issues include:

- `math_degradation_within_tolerance`
- `math_degradation_exceeded`
- `image_degradation_within_tolerance`
- `image_degradation_exceeded`
- `docx_zip_integrity_failed`
- `docx_openability_failed`

## Context-Sensitive Answer Summary Missing

`answer_summary_zone_missing` is not treated uniformly.

- if local answer extraction is strong, it stays at `info` or a light warning
- if local answer extraction is weak, it can remain a warning and contribute to review

This avoids over-penalizing bundles that already have clean local answers but no explicit answer-summary zone.

## Override Path

The default policy can be overridden with:

```bash
python3 scripts/export/docx_exporter.py ... --failure-policy-json path/to/policy.json
```

Use this only for controlled tests or subject-specific tightening.

