# Chemistry closeout: `_30_Hoa_2025` (2026-04-28)

## Scope
- source file: `_30_Hoa_2025(1).docx`
- converted file: `_30_Hoa_2025.omml.docx`
- html package: `Archive(4).zip`

## Final status
- `practically_acceptable_with_chemistry_object_boundary`

## Findings summary
- HTML package appears structurally clean and usable.
- No missing asset pattern was observed in the reviewed package.
- OMML conversion increased strongly and no broad structural collapse was observed.
- Not pure-native OMML end-to-end.

## Boundary note
- Chemistry-specific structure/editor objects remain present and preserved, including families such as:
  - `ChemDraw.Document.6.0`
  - `ACD.ChemSketchCDX`
  - `ChemWindow.Document`
- These are chemistry-structure object families, not normal math-only OMML targets.
- They should be treated as accepted chemistry-object boundary unless a future dedicated chemistry-asset normalization lane is opened.

## Residual note
- One residual `Equation.DSMT4` object remains in the converted DOCX.
- This is a lone residual, not currently treated as a strong enough family to justify a dedicated fix lane.

## Decision
- `note_and_close_no_dedicated_chem_fix_lane_for_now`

## Reopen condition
- Reopen only if:
  - a visible rendering defect appears in practical use, or
  - the project goal changes to near-pure-native normalization including chemistry-structure assets.

## Suggested next-state wording
- Chemistry is practically acceptable for current DOCX + HTML use, with chemistry-object boundary explicitly noted.
