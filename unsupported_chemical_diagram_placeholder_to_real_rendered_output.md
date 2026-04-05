# unsupported_chemical_diagram_placeholder_to_real_rendered_output.md

Task: unsupported chemical-diagram placeholder -> real rendered output

Read these as source of truth:
- core_vs_subject_mapping_and_codex_run.md
- subject_profiles_spec_v1.md
- codex_chemistry_fix_directive.md
- blank_chemical_diagram_escalation_for_codex.md
- latest chemistry QA files
- latest unresolved object report
- latest before/after diff

Current subject: chemistry

Problem statement:
- The blank-image problem was reduced successfully
- But many chemistry diagram objects are now rendered as unsupported placeholders instead of real visible diagrams
- This is better than blank white images, but still not publishable
- Do NOT treat this as an equation problem
- Do NOT send these objects into MathML/equation handling
- This is a chemical-diagram rendering task

Current situation to respect:
- MathML quality is already good and must be preserved
- total_mathml_formulas stayed unchanged
- preview count dropped significantly
- but unresolved chemical-diagram objects are still not actually rendered
- some objects still show placeholder text like:
  [Embedded chemical diagram: ChemDraw_x64.Document.6.0]

Known object families to cover:
- ChemDraw.Document.6.0
- ChemDraw_x64.Document.6.0
- ACD.ChemSketch.20
- ChemWindow.Document

Main objective:
Replace unsupported chemical-diagram placeholders with real rendered output whenever feasible.

## What to do

### 1. Keep object classification unchanged
- These objects must remain classified as `chemical-diagram`
- Do not reclassify them as `equation`
- Do not route them into MathML conversion
- Do not fold them into arrow/unit/text normalization

### 2. Inventory unresolved placeholder cases
- Scan all current HTML placeholder occurrences for chemical diagrams
- Map each placeholder to:
  - source object family
  - original asset path
  - available source formats (.wmf, .emf, ole/object data, preview png if any)
  - current fallback type
- Group unresolved objects by source family:
  - ChemDraw
  - ChemDraw x64
  - ChemSketch
  - ChemWindow

### 3. Implement a real rendering path
Renderer priority:
- preferred output: SVG
- fallback output: high-quality PNG
- textual placeholder becomes last-resort fallback only

Input source priority:
1. actual source WMF/EMF asset if available
2. associated OLE/metafile source for the chemical-diagram object
3. any higher-fidelity source extracted from the DOCX package
4. existing preview image only as late fallback
5. placeholder text only if all rendering attempts fail

### 4. Select renderer/converter carefully
If a new package/tool is needed, search in this order:
1. current upstream repos/dependencies already used by the project
2. Maven Central / npm / PyPI
3. maintained GitHub repos
4. community forks
5. last resort

Selection criteria:
- open source
- works for WMF/EMF or relevant chemical-diagram vector sources
- batch-friendly
- stable in headless/dev environments
- integrates into the current branch without redesigning the pipeline
- prefer Java-friendly integration, otherwise a small sidecar tool is acceptable
- prefer SVG-capable output, else high-quality PNG

### 5. Add renderer-attempt QA
For every unresolved chemical-diagram object, track:
- render_attempted: true/false
- render_source_used
- render_output_type: svg/png/placeholder
- render_success: true/false
- blank_image_count
- near_white_image_count
- tiny_image_count
- bad_crop_count

### 6. Update HTML output rules
For successfully rendered diagrams:
- HTML class: `chem-diagram`
- alt text:
  - `Chemical structure diagram`
  - `Chemical reaction scheme`
- no placeholder text shown to the user

For failed cases:
- placeholder may remain, but must include clear internal QA trace
- do not use misleading labels such as:
  - Embedded equation preview
  - generic embedded object preview

### 7. Preserve separation of concerns
Keep these independent:
- chemical-diagram rendering
- chemistry arrow/symbol normalization
- chemistry unit normalization
- MathML equation conversion

Do not mix renderer fixes with text/glyph fixes.

### 8. QA requirements after changes
Produce:
- before/after QA JSON
- before/after QA Markdown
- unresolved object list
- explicit progress summary:
  - fixed now
  - still unresolved
  - deferred

Required QA fields to add or update:
- subject
- total_previews
- chemdraw_preview_count
- chemdraw_x64_preview_count
- chemsketch_preview_count
- chemwindow_preview_count
- emf_count
- wmf_count
- chemical_diagram_blank_image_count
- chemical_diagram_near_white_image_count
- chemical_diagram_tiny_image_count
- chemical_diagram_bad_crop_count
- chemical_diagram_placeholder_count
- chemical_diagram_rendered_svg_count
- chemical_diagram_rendered_png_count
- chemical_diagram_render_failed_count
- unresolved_objects
- per_exam summary

### 9. Success criteria
The task is successful only if:
- MathML count is preserved
- blank chemical-diagram images do not return
- unsupported placeholder count goes down meaningfully
- at least some current placeholder cases become real visible rendered diagrams
- QA clearly shows which source families improved and which still fail

### 10. Constraints
- keep the current transpect branch
- do not redesign the pipeline from scratch
- do not migrate pipeline generation
- do not degrade current MathML quality
- do not regress chemistry arrow/unit fixes
- do not apply chemistry renderer logic to physics or math

### 11. Deliverables
- root cause summary for unsupported chemical-diagram placeholders
- code changes
- chosen renderer/converter path and why it was selected
- before/after QA
- unresolved object breakdown by source family
- final verdict on whether chemistry diagram handling is now publishable