# DSMT4 MTEF Semantics Note

This note freezes the current spec/reference-level interpretation that the repo can support from local evidence only.

Scope:

- docs/reporting only
- no product-logic changes
- no patch-engine changes
- no Java matching-path changes
- no usable-sidecar filter changes
- no parser/converter default-behavior changes

## Repo-Known Semantics

### `full`

- In the bundled MathType reader, record type `10` is `full`.
- In [typesizes.rb](../tools/calabash/extensions/transpect/mathtype-extension/ruby/mathtype-0.0.7.5/lib/records5/typesizes.rb), `RecordFull` is an empty typesize marker: it marks following equation content as full size and does not carry its own branch payload.
- In the repo's DSMT4 tooling, the decisive split is therefore the first record after `full`:
  - `full -> end` = metadata-only termination
  - `full -> slot -> ...` = renderable continuation path

### `slot`

- In [mtef.rb](../tools/calabash/extensions/transpect/mathtype-extension/ruby/mathtype-0.0.7.5/lib/records5/mtef.rb), record type `1` is `slot`.
- Current repo evidence treats `slot` as the first clear continuation marker after `full`.
- The strongest local behavioral reading is not "slot by itself means a specific semantic subtype", but "slot shows that the stream continues into renderable structure instead of terminating immediately at `end`."

### `tmpl` / template / subobject

- In [tmpl.rb](../tools/calabash/extensions/transpect/mathtype-extension/ruby/mathtype-0.0.7.5/lib/records5/tmpl.rb), template records expose:
  - `selector`
  - `variation`
  - `template_specific_options`
  - `subobject_list`
- The same file states that template class determines the order and meaning of its subobjects.
- Local repo evidence therefore supports a narrow claim:
  - `tmpl` and `subobject_list` are real structural carriers for renderable math content
  - but the current DSMT4 degenerate lines under audit do not reach a stable `tmpl`/subobject path before termination

### `mt_comment`

- In [mtef.rb](../tools/calabash/extensions/transpect/mathtype-extension/ruby/mathtype-0.0.7.5/lib/records5/mtef.rb), record type `102` is `mt_comment`.
- In [explain_empty_generated_sidecar_with_renderable_body.py](../scripts/workflow/explain_empty_generated_sidecar_with_renderable_body.py), `mt_comment`, `comment_length`, `comment_type`, and `comment_data` are treated as non-renderable comment artifacts.
- Current repo evidence supports a narrow reading:
  - `mt_comment` can create body-present surface area in MTEF XML
  - but `mt_comment` alone is not renderable math body evidence

## Mapping To Current Taxonomy

### `METADATA_ONLY_FULL_END_ONLY`

- Current role: dominant unsupported subtype line
- Best current interpretation: parser-input subtype line
- Why:
  - it repeatedly collapses to `eqn_prefs -> full -> end`
  - the observed split against renderable controls is visible at `FIRST_RECORD_AFTER_FULL`
  - repo tooling already shows this split before XML materialization
- Current safe claim:
  - this line is closest to a parser-input interpretation/subtype boundary
  - but the repo still does not have enough spec evidence to name the exact unsupported subtype with confidence

### `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY`

- Current role: narrow converter/classification-boundary follow-up line
- Best current interpretation: `mt_comment`-driven classification-boundary line
- Why:
  - the payload begins with `mt_comment` before the usual metadata records
  - deeper diagnostics show `COMMENT_ARTIFACT_ONLY`, not real renderable math body
  - no `line`, `char`, `tmpl`, `slot`, or other renderable math records appear before MathML generation
- Current safe claim:
  - this line is not a parser-input subtype line
  - it is a converter/classification-boundary line driven by comment-artifact over-reading

### `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER`

- Current role: taxonomy-only near-variant
- Best current interpretation: near-`FULL_END_ONLY` classification variant, not a separate proven failure mode
- Why:
  - it still collapses to the same metadata-only `eqn_prefs -> full -> end` shape
  - it differs mainly by taxonomy stage/assessment boundary, not by new body or template evidence
  - no stable `slot`/`tmpl`/subobject pivot has appeared
- Current safe claim:
  - keep this line taxonomy-only
  - do not promote it into a separate semantics line without new parser-stage/body evidence

## Open Questions

- What is the authoritative MTEF/DSMT4 semantic meaning of `full -> end` in these degenerate payloads beyond "typesize marker followed by immediate termination"?
- Is `METADATA_ONLY_FULL_END_ONLY` a true unsupported subtype, or only the strongest current parser-input symptom of one?
- What is the precise top-level relationship between `full`, `slot`, and template/subobject dispatch in authoritative MTEF references?
- When `mt_comment` survives into MTEF XML, what upstream producer behavior causes it to look body-present without creating real renderable math structure?
- Is there any corpus/spec evidence that would separate `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` from `FULL_END_ONLY` by semantics rather than taxonomy boundary?

## Current Handoff

- parser-input subtype line:
  - `METADATA_ONLY_FULL_END_ONLY`
- converter/classification-boundary line:
  - `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY`
- taxonomy-only near-variant:
  - `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER`

Related artifacts:

- [dsmt4_taxonomy_baseline.md](./dsmt4_taxonomy_baseline.md)
- [dsmt4_taxonomy_lines_report.md](./dsmt4_taxonomy_lines_report.md)
- [dsmt4_metadata_only_no_renderable_body_other_deep_audit.md](./dsmt4_metadata_only_no_renderable_body_other_deep_audit.md)
- [empty_generated_sidecar_with_renderable_body_investigation_10_toan_hcm_2026.md](./empty_generated_sidecar_with_renderable_body_investigation_10_toan_hcm_2026.md)
- [dsmt4_30_li_2025_source_local_split.md](./dsmt4_30_li_2025_source_local_split.md)
