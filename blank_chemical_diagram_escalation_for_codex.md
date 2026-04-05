# blank_chemical_diagram_escalation_for_codex.md

Task: blank chemical-diagram escalation

Read these as source of truth:
- core_vs_subject_mapping_and_codex_run.md
- subject_profiles_spec_v1.md
- codex_chemistry_fix_directive.md
- latest chemistry QA files and unresolved object reports

Current subject: chemistry

Problem statement:
- Many remaining chemistry diagram assets are classified correctly as `chemical-diagram`
- But the current fallback images are blank/white and therefore unusable
- Do NOT treat this as an equation problem
- Do NOT route these objects into MathML/equation handling
- This is a chemical-diagram rendering escalation

Known object families to cover:
- ChemDraw.Document.6.0
- ChemDraw_x64.Document.6.0
- ACD.ChemSketch.20
- ChemWindow.Document

Goal:
Replace the current unusable blank fallback path with a reliable chemical-diagram rendering path.

## What to do

### 1. Confirm the failure mode
- Scan all current `chem-diagram-*` assets
- Measure whether images are blank or near-white
- Add QA metrics:
  - `blank_image_count`
  - `near_white_image_count`
  - `suspicious_crop_count`
  - `tiny_image_count`
- Fail QA for chemical-diagram assets that are visually blank

### 2. Keep classification unchanged
- These objects must remain classified as `chemical-diagram`
- Do not reclassify them as `equation`
- Do not send them into MathML conversion

### 3. Escalate renderer strategy
Implement a new renderer path for chemical diagrams with this priority:
- preferred output: SVG
- fallback output: high-quality PNG
- current preview PNG path becomes last-resort fallback only

### 4. Input source priority
Try render sources in this order:
- source EMF/WMF asset if present
- OLE/metafile source associated with the chemical-diagram object
- existing preview PNG only as final fallback

### 5. Package search policy
If a new package/tool is needed, search in this order:
1. current upstream repos/dependencies already used by the project
2. Maven Central / npm / PyPI
3. maintained GitHub repos
4. community forks
5. last resort

Selection criteria for any added renderer/converter:
- open source
- works on EMF/WMF or related metafile sources
- batch-friendly
- stable in headless/dev environments
- integrates with current branch without redesigning the pipeline
- prefer Java-friendly integration, otherwise a small sidecar tool is acceptable

### 6. Output requirements for rendered chemical diagrams
- HTML class: `chem-diagram`
- clean alt text like:
  - `Chemical structure diagram`
  - `Chemical reaction scheme`
- never use misleading alt text like:
  - `Embedded object preview`
  - `Embedded equation preview`

### 7. QA requirements after changes
Produce:
- before/after QA JSON
- before/after QA Markdown
- unresolved object list
- explicit summary:
  - fixed now
  - still unresolved
  - deferred

Required QA fields to add or update:
- `subject`
- `total_previews`
- `chemdraw_preview_count`
- `chemsketch_preview_count`
- `chemwindow_preview_count`
- `emf_count`
- `wmf_count`
- `chemical_diagram_blank_image_count`
- `chemical_diagram_near_white_image_count`
- `chemical_diagram_tiny_image_count`
- `chemical_diagram_bad_crop_count`
- `unresolved_objects`
- `per_exam` summary

### 8. Constraints
- keep the current transpect branch
- do not redesign the pipeline from scratch
- do not migrate pipeline generation
- do not degrade current good MathML quality
- keep chemistry diagram rendering separate from arrow/unit/text normalization

### 9. Deliverables
- root cause summary for blank chemical-diagram images
- code changes
- chosen renderer/converter path and why it was selected
- before/after QA
- final verdict on whether chemical-diagram handling is now publishable
