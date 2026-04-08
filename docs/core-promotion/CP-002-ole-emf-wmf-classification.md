# CP-002 - OLE/EMF/WMF preview classification consistency

## Metadata

- Candidate ID: `CP-002`
- Status: `open`
- First observed: `2026-04-08`
- Last updated: `2026-04-08`
- Owner: `core object-classifier/render`
- Proposed layer: `core`

## Problem Summary

Legacy OLE/preview assets still appear across subjects. Classification and render routing are shared-core concerns and should not be repeatedly patched per subject.

## Cross-subject Evidence

Source: `out/phase-b-regression-20260408/samples/*/qa/*.qa.json` (`totals`)

- `ole_preview_images`: total `27`
  - chemistry: `5`
  - physics: `22`
- `emf_wmf_previews`: total `27`
  - chemistry: `5`
  - physics: `22`

Additional unresolved examples:

- chemistry sample `chem_hoa_2026_big`: unresolved `17` objects (mostly `chemical-diagram`)
- math sample `math_toan_deso_11_tb`: unresolved `1` object (`equation` fallback)

## Scope Decision (Core vs Subject)

The decision logic for preview assets, ProgID mapping, and fallback classification is shared across subjects. Domain semantics can still be handled in subject profiles after core classification.

## Proposed Fix Class

- `classifier`
- `render`
- `qa-gate`

## Acceptance Checks

- Keep MathML conversion quality unchanged.
- Reduce unresolved preview artifacts without forcing subject-specific hacks.
- Keep publish gate behavior stable in publish mode.

## Override Relationship

- Temporary override allowed: `yes`, for isolated asset-level mismatches.
- Trigger to promote core fix: same mismatch pattern appears in 2+ subjects or 3+ exams.

## Decision

- Keep as active core candidate.
