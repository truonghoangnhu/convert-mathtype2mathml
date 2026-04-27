# Modern DOCX + OMML Operational Baseline (Consolidated)

Date: 2026-04-25
Status: active stable baseline for current modern-path work

## Required Guardrails

- Modern `.docx` only.
- Native OMML path only for baseline acceptance.
- No default parser/converter behavior changes unless a separate behavior checkpoint explicitly authorizes them.
- No legacy `.doc` reopening, no DSMT4 legacy reopening, no workflow/schema redesign in baseline maintenance checkpoints.

## Required CI/Stable Baseline Path

These are the required stable commands for the current baseline:

```bash
mvn -q -Dtest=DocxMathPatchWorkflowTest,DocxToHtmlCliPatchSummaryJsonlTest test
python3 scripts/workflow/run_modern_docx_omml_smoke.py
python3 scripts/workflow/run_modern_docx_omml_generated_output_gate.py
```

Required active repo-tracked baseline scope:

- Inventory: `regression_set/modern_docx_omml_inventory.json`
- Active supported fixtures (status `active`, classification `supported`):
  - `samples/sample-inline-omml.docx`
  - `samples/sample-block-omml.docx`
  - `samples/sample-omml.docx`
  - `samples/sample-multi-inline-omml.docx`
- Active negative fixture (status `active`, classification `out_of_scope`):
  - `samples/sample-malformed-document-xml.docx`
- Generated-output gate baseline: 4 positive modern cases (from active supported set), structural/openability gate must remain green.

## Local-Only Confidence Expansion Path

Local-only cases are confidence evidence, not required CI gate inputs.

Current local-only inventory entries:

- `modern_patchable_modern_object_path_sample` -> `in/Hoa_Ha_Noi_L1.docx`
- `modern_mixed_block_object_path_sample` -> `in/Hoa50/Đề 26. MHTHPT 2024 - TRẦN THANH HIÊN - QUẢNG NGÃI. đã sửa.docx`

Current local-only evidence reports:

- Detector/classification confidence: `regression_set/modern_docx_omml_detector_confidence_report.json`
- Mixed-candidate expansion scan: `regression_set/modern_docx_omml_mixed_candidate_expansion_report.json`

## Current Thin Spots

- No repo-tracked mixed embedded-object + native OMML fixture in active CI/stable baseline path.
- Mixed object+OMML confidence currently depends on local-only corpus evidence.

## Promotion Criteria (Local-Only -> Repo-Tracked)

Promote only when all criteria are met:

- Candidate is legally/operationally safe to track in-repo.
- Candidate is stable and reproducible in this repository (not machine-private/transient).
- Candidate adds clear incremental coverage beyond current active samples.
- Candidate keeps baseline size practical for frequent smoke/gate execution.
- Promotion does not require workflow/schema redesign or behavior-default changes.

If any criterion fails, keep the case local-only and update only confidence reports.

## Stop Conditions and Reopen Triggers

Stop baseline consolidation work when all are true:

- Required CI/stable baseline commands are green.
- Active fixture scope remains unchanged and sufficient for current acceptance baseline.
- Local-only evidence remains clearly separated from required CI scope.

Reopen baseline scope/promotion decision only if one or more triggers occur:

- A safe repo-trackable mixed object+OMML candidate becomes available.
- CI/stable baseline starts missing a now-required modern case family.
- Generated-output gate or smoke gate shows new structural drift/unexpected failures.
- Policy or product scope changes explicitly require expanding required baseline coverage.
