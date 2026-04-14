# Core Promotion Index

This folder is the compact index for repeated cross-subject issues that should be promoted into shared core behavior.

## Purpose

- Keep core vs subject boundaries explicit.
- Reduce repeated patching across Chemistry, Physics, and Math.
- Track which repeated patterns are already known core candidates.

## Promotion Rule

- If the same root-cause class appears in multiple subjects, prefer a core fix unless the behavior is domain semantic.

## Current Candidates

| id | title | scope | status |
|---|---|---|---|
| `CP-001` | Parser question boundary stabilization | `core` | `open` |
| `CP-002` | OLE/EMF/WMF preview classification consistency | `core` | `open` |
| `CP-003` | Generic inline image trim/crop governance | `core` | `open` |
| `CP-004` | Structural HTML cleanup consistency | `core` | `open` |
| `CP-005` | Cross-subject normalization governance | `mixed` | `open` |

## Baselines

- Phase A: `out/phase-a-contract-20260407-1`
- Phase B: `out/phase-b-regression-20260408`

## Note

This folder is intentionally reduced to one index page. Candidate notes and templates were merged into this summary and removed.
