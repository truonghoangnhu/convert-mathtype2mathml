# Core Promotion Workflow (Phase C)

This folder defines how repeated issues are promoted from ad-hoc subject fixes into shared core behavior.

## Goals

- Keep core vs subject boundaries explicit.
- Reduce repeated patching across Chemistry, Physics, and Math.
- Use evidence from QA/parser/perf outputs instead of one-off assumptions.

## Folder Layout

- `note_template.md`: reusable template for each promotion candidate.
- `candidate_registry.md`: current candidate inventory and status table.
- `CP-*.md`: one note per candidate.

## Promotion Rules

1. Candidate threshold:
- If an issue appears in 2+ subjects or in 3+ exams of the same subject, open a core-promotion candidate note.

2. Promotion expectation:
- If an issue appears in 3+ subjects and shares the same root cause class (parser/classifier/render/cleanup/gate), promote to core unless there is a clear reason not to.

3. Keep in subject profile when:
- The rule is domain semantic (chem notation, physics unit semantics, math notation semantics), or
- A global rule would likely degrade other subjects.

4. Do not use override as a substitute for core work:
- Repeated override for the same pattern is a signal to promote a core/spec fix.

## Required Evidence Per Candidate

- Repro paths (HTML/QA/parser reports).
- Quantitative signal (counts, warnings, or gate impact).
- Scope map (core vs subject).
- Proposed fix class and acceptance checks.

## Current Phase Inputs

Current candidate notes in this folder are based on:

- Phase A contract artifacts under `out/phase-a-contract-20260407-1`
- Phase B regression + baseline under `out/phase-b-regression-20260408`
