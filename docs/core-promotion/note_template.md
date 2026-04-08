# CP-XXX - <Short title>

## Metadata

- Candidate ID: `CP-XXX`
- Status: `open | accepted | in_progress | done | rejected`
- First observed: `<YYYY-MM-DD>`
- Last updated: `<YYYY-MM-DD>`
- Owner: `<name/team>`
- Proposed layer: `core | subject:<name> | mixed`

## Problem Summary

Describe the repeated behavior and why one-off patching is risky.

## Cross-subject Evidence

List concrete evidence from QA/parser/perf outputs.

- Subject/exam:
- Artifact path:
- Metric/warning:
- Value:

## Scope Decision (Core vs Subject)

- Why this belongs to core or subject.
- Risk if implemented in the wrong layer.

## Proposed Fix Class

- `parser` / `classifier` / `render` / `cleanup` / `qa-gate` / `subject-normalization`

## Acceptance Checks

- Baseline metrics that must not regress.
- Metrics expected to improve.
- Regression samples to run.

## Override Relationship

- Is override allowed as a temporary mitigation? `yes/no`
- If yes, limit and expiry condition.
- Trigger to replace override with core/spec fix.

## Open Questions

- Unknowns or dependencies.

## Decision

- Final decision and rationale.
