# DOCX Export (Phase F Prototype)

Current status:

- architecture/spec is documented in `docs/docx_export_architecture_spec_v1.md`
- runtime prototype exists in `docx_exporter.py`
- report schema draft is in `docx_export_report_schema_v1.json`
- parity review is in `docx_export_parity.py`
- Phase G regression runner is `scripts/regression/run_docx_export_regression.py`

Prototype scope (implemented):

- source: `exam_bundle.json` only
- mode: `teacher_exam` only
- output: one `.docx` + `docx_export_report.json`
- content: title, sections/questions from source HTML, basic teacher answer section, images, MathML -> OMML (best-effort)
- failure behavior: explicit warning/blocker reporting, strict-math option
- parity review against source `exam_bundle.json` is available
- openability checks can be enabled with `--check-openability`
- parity checker can also emit a compact markdown summary with `--md-out`

Out of scope (not implemented yet):

- production styling/template system
- `student_exam` polished output
- `question_pack` export runtime
