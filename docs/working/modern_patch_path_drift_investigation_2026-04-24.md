# Modern Patch-Path Drift Investigation (2026-04-24)

- case_id: `modern_supported_multi_equation_paragraph_generated_output`
- selection_reason: best current modern drift-tracing candidate because it exercises the richest supported placement/run-safety surface (`2` inline equations in one paragraph) while staying fully inside the modern DOCX path
- gate_result: `passed`
- drift_origin_hint: `no_structural_drift_detected`

## Structural Snapshot

- source counts: `equation_count=2`, `block_equation_count=0`, `inline_equation_count=2`
- output counts: `equation_count=2`, `block_equation_count=0`, `inline_equation_count=2`
- source placement summary: `inline OMML only: inline_oMath=2`
- output placement summary: `inline OMML only: inline_oMath=2`
- source paragraph/run safety summary: `inline_paragraphs=1 inline_with_text=1 inline_with_text_before_after=1 block_paragraphs=0 multi_inline_paragraphs=1`
- output paragraph/run safety summary: `inline_paragraphs=1 inline_with_text=1 inline_with_text_before_after=1 block_paragraphs=0 multi_inline_paragraphs=1`
- source paragraph/run safety flags: `inline_paragraph_run_context_safe=true`, `block_omathpara_context_safe=true`, `surrounding_non_math_text_preserved=true`
- output paragraph/run safety flags: `inline_paragraph_run_context_safe=true`, `block_omathpara_context_safe=true`, `surrounding_non_math_text_preserved=true`

## Direct Observation

- `patch_path_diagnostics` does not show structural drift for this case.
- The patch run summary is also non-mutating: `scanned=1 block=0 inline=0 native=1 unresolved=0`.
- The first observable source/output difference is still real, but it is byte-level serialization drift rather than structural drift:
  - source XML declaration: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`
  - output XML declaration: `<?xml version="1.0" encoding="UTF-8"?>`

## First Concrete Handoff

- First concrete handoff where divergence appears, directly observable in this pass: the DOCX rewrite boundary in [DocxMathPatchMain.java](/Users/truonghoangnhu/Desktop/transpect-branch-project/src/main/java/com/example/docxmath/word/DocxMathPatchMain.java:69).
- Evidence:
  - [PoiMathSourceDetector.java](/Users/truonghoangnhu/Desktop/transpect-branch-project/src/main/java/com/example/docxmath/word/PoiMathSourceDetector.java:20) classifies the paragraph as `NATIVE_OMML`, so no injector path is needed for this sample.
  - The patch summary confirms no block or inline injection happened.
  - The generated `word/document.xml` still differs immediately after the `XWPFDocument` load/write cycle, which points to serializer/rewrite normalization as the first observed divergence point for this modern case.

## Conclusion

- No structural divergence is directly observable in the current modern-path diagnostics for this case.
- The earliest real divergence visible in this pass begins at document rewrite/serialization, not at a math placement or paragraph/run-safety handoff.
