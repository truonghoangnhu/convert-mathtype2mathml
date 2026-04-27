# EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY investigation

Scope:
- converter-stage investigation only
- diagnostics/reporting/tooling only
- no patch engine changes
- no Java matching-path changes
- no usable-sidecar filter changes
- no default converter-behavior changes

Source under investigation:
- `in/10_Toan_HCM_2026.docx`

How the report was produced:
- `python3 scripts/workflow/explain_empty_generated_sidecar_with_renderable_body.py --external-docx in/10_Toan_HCM_2026.docx --format json`
- `python3 scripts/workflow/audit_dsmt4_corpus.py --external-docx in/10_Toan_HCM_2026.docx --format json`

## Report

| Field | Value |
| --- | --- |
| source file | `external-docx:in/10_Toan_HCM_2026.docx` |
| occurrences | `1` |
| payload classes | `1` |
| source parts | `oleObject3009.bin` + `image2537.wmf` |
| parser pair | `Mathtype::OleFileParser` / `Mathtype::WmfFileParser` |
| equation_bytes | `216 / 217` |
| sidecar status | `bin=missing`, `preview=empty_math` |
| main signature/pattern | `mt_comment, encoding_def, font_def x4, eqn_prefs, full, end` |
| tail after eqn_prefs | `full, end` |
| same effective payload | `true` |
| stage-level diagnosis | `CLASSIFICATION_BOUNDARY_AROUND_MT_COMMENT` |
| decision label | `INVESTIGATE_TRANSPECT_CONVERTER` |
| recommended next step | verify whether `mt_comment/comment_*` tags are being over-read as renderable-body evidence before opening any converter fix branch |

## Findings

1. The sidecar falls into `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY` because the broader taxonomy currently routes any `BODY_PRESENT_BUT_EMPTY_MATHML` result, and also some `empty_math` sidecar cases, into that family.
2. For this source, the helper's deeper diagnosis shows that "renderable body" is not real renderable math body. It is comment-only surface area coming from `mt_comment/comment_*` artifacts.
3. The `mt_comment` prefix is the classification boundary marker in this case. It appears before `encoding_def`, but the payload still terminates as `eqn_prefs -> full -> end` with no `line`, `char`, `tmpl`, or other renderable math records.
4. The strongest current root cause is the classification boundary around `mt_comment`, not the patch engine, not Java matching, and not the usable-sidecar filter.
5. This remains a converter-stage investigation line only because the family was originally opened on that stage, but the actual evidence here does not yet justify a production converter fix.

## Final call for this family

- final label: `INVESTIGATE_TRANSPECT_CONVERTER`
- production-fix branch after this: `No`, not yet
- if reopened later, target stage: `CONVERTER_CLASSIFICATION_BOUNDARY`
- fix-branch gate: only reopen if a later probe finds stable renderable math body evidence before MathML generation
