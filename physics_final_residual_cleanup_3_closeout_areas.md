# physics_final_residual_cleanup_3_closeout_areas.md

Task: physics final residual cleanup — 3 closeout areas

Read these as source of truth:
- core_vs_subject_mapping_and_codex_run.md
- subject_profiles_spec_v1.md
- core_omml_mathtype_image_policy.md
- generic_inline_image_whitespace_trim_crop_policy.md
- latest Ly_2026_Big-transpect.html
- latest Ly_2026_Big.after.qa.json
- latest Ly_2026_Big.docx
- latest asset bundle / conversion log if available

Current subject: physics

Goal:
Close the final 3 visible residual issue groups in the Physics bundle:
1. generic inline-image trim/crop still incomplete
2. physics unit/text corruption residuals
3. mixed text + MathML lines still split or awkward in visible output

Confirmed issue groups:

A. Generic inline-image trim/crop incomplete
- Many `inline-image` assets are still not trimmed
- Some still have:
  - `data-trim-candidate="false"`
  - `data-trim-applied="false"`
- These can still create excessive whitespace and large gaps before/after images
- This is a CORE image pipeline issue

B. Physics unit/text corruption residuals
Visible examples include patterns like:
- `c m²` instead of `cm²`
- `c m³` instead of `cm³`
- `mo l^-1` instead of `mol^-1`
- residual text corruption such as:
  - `đồ dài`
  - `thế tích`
  - `biến đối`
  - `truờng`
  - `chuyền thành nhiệt`
- These are PHYSICS SPEC cleanup items, using a conservative dictionary/context policy

C. Mixed text + MathML lines still awkward
Examples include:
- “Cho biết” lines and similar mixed constant/notation lines
- state labels or inline math tokens that look split or wrapped unnaturally
- punctuation attached awkwardly to MathML fragments
- Do only minimal wrapper/spacing cleanup here
- Do not redesign MathML conversion in this task
- If you discover a true OMML/MathType source bug, report it as CORE separately

Mapping:
- generic inline-image trim/crop -> CORE
- generic image sizing/display policy -> CORE
- physics unit normalization -> PHYSICS SPEC
- physics text corruption dictionary cleanup -> PHYSICS SPEC
- mixed text + MathML wrapper spacing cleanup -> CORE if generic, otherwise PHYSICS SPEC only when clearly domain-specific

What to do:

1. Finish generic inline-image trim/crop
- inspect all remaining `inline-image` assets with `trim-applied="false"`
- detect excessive outer whitespace safely
- apply trim only when safe
- preserve all visible content
- do not crop blindly
- improve display sizing after trim so images no longer create obvious vertical gaps
- keep `bad_crop_count = 0`

2. Clean physics units
Normalize conservatively:
- `c m²` -> `cm²`
- `c m³` -> `cm³`
- `Mpa` -> `MPa`
- `mo l^-1` and similar broken mol notation -> project-preferred clean form
- do not over-normalize unrelated tokens

3. Clean physics text corruption
Apply conservative context-based fixes for clearly wrong words, including known residual dictionary items only when unambiguous.

4. Clean mixed text + MathML output
- inspect visible awkward mixed lines
- fix wrapper spacing, punctuation binding, and obvious token splitting
- do not rewrite math semantics
- do not redesign MathML conversion
- preserve `total_mathml_formulas`

QA requirements:
Add or update:
- `generic_inline_image_count`
- `generic_inline_image_trim_candidate_count`
- `generic_inline_image_trim_applied_count`
- `generic_inline_image_oversized_whitespace_count`
- `generic_inline_image_bad_crop_count`
- `physics_unit_fix_count`
- `physics_text_fix_count`
- `remaining_physics_unit_issues`
- `remaining_physics_text_corruption_issues`
- optionally:
  - `mixed_math_text_cleanup_count`
  - `remaining_mixed_math_text_layout_issues`

Constraints:
- keep the current branch and pipeline structure
- do not redesign the pipeline
- do not regress MathML quality
- do not regress Visio/physics-diagram rendering
- do not reintroduce previews, placeholders, or unresolved objects
- do not apply chemistry-specific rules
- keep fixes minimal, safe, and evidence-based

Required outputs:
1. summary of fixes mapped to core
2. summary of fixes mapped to physics spec
3. code changes
4. before/after QA JSON
5. before/after QA markdown summary
6. explicit list:
   - fixed now
   - still unresolved
   - deferred

Success criteria:
- generic inline-images no longer create obviously excessive spacing due to whitespace-heavy canvas
- bad crop count stays at 0
- residual unit corruption is reduced meaningfully
- residual text corruption is reduced meaningfully
- mixed text + MathML lines look more natural
- MathML count is preserved
- physics diagrams remain rendered correctly
- final HTML is closer to the source in both layout and readable content
