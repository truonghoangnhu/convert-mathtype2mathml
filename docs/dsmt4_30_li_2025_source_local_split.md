# DSMT4 Source-Local Split for `in/_30_Li_2025.docx`

This artifact is a source-local taxonomy comparison for `in/_30_Li_2025.docx`.
It explains why `METADATA_ONLY_FULL_END_ONLY` and `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER`
look structurally close inside the same source, but should not be merged at the current
investigation state.

| family | occurrences | payload classes | stage | bytes pairs | main signature/pattern | assessment | source-family scope | current recommendation |
|---|---:|---:|---|---|---|---|---|---|
| `METADATA_ONLY_FULL_END_ONLY` | 1 | 1 | `PARSER_INPUT_PAYLOAD` | `212/213` | `encoding_def,font_def,encoding_def,font_def,font_def,font_def,font_def,eqn_prefs,full,end`; same-effective payload; both sides `empty_math` | `TOP_LEVEL_FULL_END_ONLY` / `UNSUPPORTED_OR_DEGENERATE_PAYLOAD` | `_30_Li_2025` only | Keep as the dominant unsupported subtype line; do not split into a new branch here |
| `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` | 1 | 1 | `PARSER_STAGE` | `193/194` | `encoding_def,font_def,font_def,font_def,font_def,eqn_prefs,full,end`; same-effective payload; `bin=missing`, `preview=empty_math` | `METADATA_ONLY_MTEF_XML` / `INVESTIGATE_TRANSPECT_CONVERTER` | `_30_Li_2025` only | Keep taxonomy-only for now; do not elevate to a standalone investigation candidate yet |

## Shared Shape

- Both lines are metadata-only.
- Both lines preserve the same top-level tail: `eqn_prefs -> full -> end`.
- Both lines have `same_effective_payload=true`.
- Neither line exposes renderable body evidence in this source-local comparison.

## Divergence by Stage/Assessment

- `METADATA_ONLY_FULL_END_ONLY` is classified at `PARSER_INPUT_PAYLOAD`.
- `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` is classified at `PARSER_STAGE`.
- `METADATA_ONLY_FULL_END_ONLY` is assessed as `TOP_LEVEL_FULL_END_ONLY`.
- `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` is assessed as `METADATA_ONLY_MTEF_XML`.
- The two lines are therefore close in shape but still distinct in taxonomy and assessment stage.

## Current Decision

- Do not merge the two lines.
- `METADATA_ONLY_FULL_END_ONLY` remains the dominant unsupported subtype line.
- `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` remains taxonomy-only in the current state.

## Future Revisit Trigger

Only elevate `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` into a dedicated investigation candidate if at least one of the following becomes true:

- It repeats across `>= 2` source families.
- A future probe exposes new body/template evidence.
- It develops its own stable fingerprint that stays distinct from `METADATA_ONLY_FULL_END_ONLY`.

## Reproduce

```bash
python3 scripts/workflow/audit_dsmt4_corpus.py \
  --all-presets \
  --extra-workdir work/dsmt4-external-audit/30-li-2025--bd9ae3943a45 \
  --format json
```
