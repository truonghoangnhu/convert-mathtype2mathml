# DSMT4 — native Formula-group geometry review, 2026-11-14

Scratch continuation of the partial region inventory. No production change, commit/push, or accepted promotion. This is a bounded geometry review of five existing November6 native-OMML full-exam snapshots, not certification of the current converter or source semantics.

## Findings

Codex linked all704 native MathML frames uniquely to704 tagged Formula/MCID groups in the fully formatted native PDFs. All769 embedded frames have actual Writer positions;65 retained OLE objects are outside this Formula-group method. The five PDF/layout pairs cover31 pages and match the earlier native controls in glyph text/font/size/boxes to five decimal places.

The method uses actual frame positions to identify a unique Formula group, then measures all non-whitespace, nonzero-area character rectangles in that whole group. It does not clip the measured group to its frame. All25 cases unresolved by the earlier line-portion reconstruction now have exact PDF Formula-group links. Their line-portion reconstruction and intended tab-column contract remain separate unresolved questions.

No Formula-group character bounding box exceeds the actual paragraph print box horizontally by more than2pt or a physical cell border by more than0.2pt. These tolerances are screening thresholds, not a declaration of zero overhang or full layout correctness. PDF character rectangles are not isolated solid-ink masks; some earlier JSON fields use the name glyph_ink_box_pt for these rectangles.

The only reciprocal character-box intersection flags are Tuyên Quang Object274/Object278 on page5. The enlarged crop shows that the radical character rectangle includes white space below its extended top bar; no visible stroke collision with the following S_min line was observed. This is a visual disposition, not a pixel-mask intersection proof. It supplies no reason to split or alter the formulas.

The three TQB interval candidates Object47/48/49 remain unsuitable for W/L: about1pt padding intrusion, no physical border crossing, and no continuation relation. Six pre-existing Formula error markers remain in Tuyên Quang; the other four inputs have none under this marker screen. No new eligible natural overflow case was established, so no new W/L pair was created.

## Limits and evidence

Intended tab-column boundaries, arbitrary vector-path geometry,65 retained OLE objects and source-equivalent mathematical meaning are not certified. All documents remain needs_review; accepted is unchanged. Previous GUI/backend/INT conclusions are unchanged.

Evidence root: `work/dsmt4-claude-region-overflow-20261113T201043/attempt-03/review/`.

- `glyph-groups/check.py`, `formula-group-review.json`, `summary.json`: unique Formula mappings and bounded screens.
- `glyph-groups/visual-review.json`, `TQ-radical-screen-5.png`: explicit visual disposition and image/PDF pins.
- `glyph-groups/verify.py`: independent fresh PDF/group/pin verification.
- `verify_all.py`: native PDF/layout calibration,769 frame maps, source/input/executable and tracked-file checks.

Both verifiers passed again during this continuation:704 unique groups, all25 prior unknown-frame groups found,31-page calibration,221 tracked files and HEAD unchanged. They are read-only and do not regenerate or overwrite evidence.

## Worker recovery checkpoint

Claude attempt04 in session2fdbb5a4-0d12-417c-a96c-304c0bdbdc80, model claude-fable-5-2, stopped with autocompact thrashing rather than quota. It created only its checkpoint. Tool outputs were1–12KB; repeated post-compaction requests still carried roughly74–81k input/cache tokens under an explicitly configured100k window. That evidence suggests the small window may be unsuitable, but does not identify every component of the request overhead.

Attempt05 tests only returning the CLI autocompact window to its documented auto mode. Session/model/tools/guard remain unchanged; no clear, transcript edit, fallback or hook bypass is used. Worker writes only new execution/continuation-05 artifacts. Its handoff must be reviewed before any completion claim; starting the process is not task completion.
