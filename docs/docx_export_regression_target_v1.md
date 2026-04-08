# DOCX Export Regression Target v1

This is the small Phase G export regression set used to validate the teacher DOCX prototype.

## Coverage

1. OMML-clean baseline
2. real sample with images and answer summary
3. harder MathType/OLE/preview-heavy sample

## Inventory

The machine-readable inventory lives at:

- `regression_set/docx_export_inventory.json`

## Expected Artifacts

Each case writes:

- exported `.docx`
- `docx_export_report.json`
- `docx_export_parity_report.json`
- `docx_export_parity_report.md`
- export log
- parity log

## Why These Three Cases

- the OMML-clean sample proves the prototype works on a simple bundle
- the real image-heavy sample exercises practical layout and parity checks
- the hard OLE sample catches the failure modes that are most likely to regress

## Note

Openability is still tracked in the export report. In this workspace the LibreOffice probe is environment-sensitive, so the regression target keeps that signal separate from parity comparison.
