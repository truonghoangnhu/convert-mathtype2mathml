# DOCX Export Architecture Spec v1

## 0. Scope And Constraints

This phase is architecture/spec first for exporting `.docx` from canonical JSON contract outputs.

In-scope:

- architecture for contract-driven DOCX export
- mode separation (`student_exam`, `teacher_exam`, `question_pack`, optional `review_copy`)
- MathML -> OMML -> WordprocessingML strategy
- export QA/report design
- minimal low-risk scaffolding only

Out-of-scope:

- full production exporter
- question_bank integration
- converter redesign
- moving answer/reconciliation logic out of canonical JSON

Core decision kept unchanged:

- canonical internal math remains MathML
- DOCX equation path remains `MathML -> OMML -> WordprocessingML -> .docx`

---

## 1. Export Sources

Supported canonical sources:

1. `exam_bundle.json`
2. `question_bank_items.json`

### Source Priority Decision (Phase 1)

Default priority in Phase 1:

1. `exam_bundle.json` (primary)
2. `question_bank_items.json` (secondary)

Reason:

- `exam_bundle.json` carries the strongest bundle-level context (`bundle_id`, source pointers, per-exam grouping, publish/QA context).
- current `question_bank_items.json` is intentionally compact and does not include full stem/choice HTML needed for high-fidelity DOCX reconstruction.
- `exam_bundle.source.html_path` and `exam_bundle.source.asset_dir` provide deterministic pointers needed to rebuild content blocks and MathML placement.

---

## 2. Export Targets

Planned targets:

1. Student-facing exam DOCX
2. Teacher version DOCX with answers/solutions/rubric notes
3. Question handout DOCX from selected bank items

---

## 3. Export Modes

Required modes:

1. `student_exam`
2. `teacher_exam`
3. `question_pack`
4. `review_copy` (optional but defined here)

Mode intent:

- `student_exam`: hide canonical answers and reconciliation internals.
- `teacher_exam`: include answer key and optional solution/rubric appendix.
- `question_pack`: selected item export, configurable answer visibility.
- `review_copy`: reviewer-friendly copy with QA/reconciliation notes (not student-facing).

---

## 4. Math Handling

## 4.1 Input math source

Phase 1 source:

- MathML extracted from canonical HTML blocks referenced by `exam_bundle.source.html_path`.
- placement hints from existing parser conventions (`inline`, `display`, `table-cell`).

## 4.2 Conversion path

Required path:

1. parse MathML fragment
2. apply `mml2omml.xsl`
3. inject resulting OMML (`m:oMath`/`m:oMathPara`) into WordprocessingML runs/paragraphs

## 4.3 Inline vs block mapping

- inline MathML -> `m:oMath` inside a paragraph run
- display MathML -> `m:oMathPara` (or equivalent block equation paragraph)

## 4.4 Failure behavior

Math issue families (export-side):

- `mathml_missing_in_source`
- `mathml_to_omml_transform_failed`
- `math_inline_block_mapping_failed`
- `omml_injection_failed`

Severity guidance:

- `blocker`: transform/injection failure for equations that are required for question semantics
- `warning`: non-critical math formatting drift with fallback still readable
- `info`: redundant or auto-corrected math layout normalization

Fallback policy:

- strict export: refuse output on math blocker
- non-strict export: keep document, mark unresolved math token and emit report warning/blocker summary

---

## 5. Asset Handling

Asset classes:

1. context figures
2. essential figures
3. diagrams/charts
4. generic images

Placement policy input:

- consume existing placement hints (`inline`, `display`, `context-right`, `context-below`, `centered`, `table-cell`)
- consume asset role hints (`equation`, `diagram`, `chart`, `chemical-diagram`, `generic-image`, `unknown-preview`)

DOCX rendering policy (Phase 1):

- `inline`: inline drawing anchored in text run
- `display`/`centered`: centered paragraph image
- `context-right`: two-column table block (text left, figure right) when feasible
- `table-cell`: keep figure inside table cell run context

Size policy:

- preserve aspect ratio always
- clamp width by mode/profile defaults (exam text width aware)
- avoid oversized images crossing margins

Metadata policy:

- preserve alt/caption text where available
- keep unresolved/placeholder labels out of student-facing content

---

## 6. Answer And Rubric Handling

## 6.1 Student mode (`student_exam`)

- hide `answer_key`, `answer_sources`, `reconciliation`
- no answer-summary appendix by default

## 6.2 Teacher mode (`teacher_exam`)

- include canonical answer output from reconciliation
- include short-answer accepted forms
- include true/false subanswer mapping by label (`a/b/c/d`)
- include rubric appendix/blocks for essay items where available
- include answer summary appendix only if requested by options/profile

## 6.3 Question pack (`question_pack`)

- default: no answers
- option `include_answers=true`: include canonical answers
- option `include_rubric=true`: include rubric blocks in teacher/review contexts

## 6.4 Review mode (`review_copy`)

- include reconciliation status/notes and key QA flags
- intended for internal review, not student distribution

---

## 7. Document Structure Mapping

Canonical mapping to DOCX:

1. bundle/exam title -> document heading
2. `exams[]` groups -> section heading blocks
3. question block -> numbered paragraph set
4. choices -> lettered list paragraphs
5. true/false subquestions -> nested label lines (`a/b/c/d`)
6. answer summary (optional by mode) -> appendix table/list
7. rubric/solution (mode dependent) -> appendix or per-question teacher block

Mapping notes:

- Phase 1 reconstruction relies on canonical source pointers + parser segmentation conventions.
- `question_bank_items.prompt_preview` is not sufficient for full-fidelity rendering by itself.

---

## 8. Styling And Template Strategy

Default recommendation:

- **built-in WordprocessingML styles first** for v1 prototype (`Normal`, `Heading 1/2`, `List Paragraph`, `Table Grid`, equation paragraph conventions).

Why:

- deterministic and low coupling for first exporter milestone
- avoids external template drift while architecture stabilizes

Planned extension:

- v2 optional template support (hybrid model) after baseline export behavior is stable

---

## 9. Failure Strategy

Export verdicts:

1. `safe_to_export`
2. `needs_review`
3. `blocked`

Blocker examples:

- required source artifact missing (`exam_bundle`, source HTML, asset dir)
- canonical question reconstruction fails structurally
- math transform failure on essential equations in strict mode
- output `.docx` package cannot be finalized

Warning examples:

- non-critical image placement downgrade
- missing optional caption/alt metadata
- answer summary appendix omitted by mode policy

Graceful degradation (non-strict mode only):

- unresolved math placeholders with explicit report flags
- fallback placement from `context-right` to `display` when layout constraints fail

Refuse-output conditions:

- one or more blockers with strict mode enabled

---

## 10. Phase Plan

## v1 (this phase): architecture/spec

- finalize architecture decisions
- define interfaces and report contract
- add minimal scaffold only

## v1 minimal prototype (next phase)

- implement `student_exam` from `exam_bundle.json`
- basic MathML -> OMML transform path
- basic asset embedding and numbering
- emit `docx_export_report.json`

## v2 (format/template expansion)

- richer template-driven formatting
- stronger section/choice layout controls
- `question_pack` and `teacher_exam` feature completion
- tolerance-aware short-answer rendering integration (after tolerance runtime exists)

---

## 11. Exporter Interfaces (v1 design note)

## 11.1 `export_exam_bundle_to_docx(...)`

Inputs:

- `exam_bundle_path`
- `manifest_path` (optional)
- `qa_path` (optional)
- `output_docx_path`
- `mode` (`student_exam | teacher_exam | review_copy`)
- `options` (strict_math, include_answer_summary, include_rubric_appendix, profile)

Outputs:

- `.docx` file (if not blocked)
- `docx_export_report.json`

Expected generated artifacts:

1. DOCX output
2. export report JSON
3. optional debug logs for transform/placement diagnostics

## 11.2 `export_question_pack_to_docx(...)`

Inputs:

- `question_bank_items_path`
- `selection` (item ids and ordering)
- `output_docx_path`
- `mode` (`question_pack | review_copy`)
- `options` (include_answers, include_rubric, strict_math)

Outputs:

- question-pack `.docx`
- `docx_export_report.json`

Constraint:

- when source lacks full question body HTML, exporter must either:
  - resolve full content through bundle source pointers, or
  - fail clearly as unsupported for high-fidelity mode

---

## 12. Export Report Artifact (`docx_export_report.json`)

Schema draft version:

- `schema_version`: `docx_export_report.v1`
- `artifact_type`: `docx_export_report`
- `bundle_id`
- `export_mode`
- `source_paths`
- `output_docx_path`
- `verdict`: `safe_to_export | needs_review | blocked`
- `metrics`
  - `question_count`
  - `math_detected_count`
  - `math_converted_count`
  - `math_failed_count`
  - `image_embedded_count`
  - `image_failed_count`
  - `answer_block_count`
  - `rubric_block_count`
- `issues` (code/severity/message/location)
- `warnings_count`
- `blockers_count`
- `timings`

---

## 13. Package / Tooling Direction

Recommended default:

1. **XSLT-driven MathML -> OMML using `mml2omml.xsl` executed by Saxon-HE**
2. DOCX writing via WordprocessingML assembly in current repo stack (Apache POI compatible)

Why this default:

- consistent with canonical math decision
- deterministic transform layer with auditable failures
- aligned with existing Java/Saxon stack already present in repository

Recommended fallback option:

- Python orchestration fallback for prototype-only execution path (contract loading + report generation), while deferring full OMML injection to the XSLT/WordprocessingML core path.
- if OMML transform is unavailable, do not silently flatten math semantics; fail or mark unresolved by strictness policy.

This keeps export direction explicit and avoids ambiguous sidecar-only math behavior.
