# Physics DOCX residual checkpoint: `_10_Li_2025`

Scope:
- Subject lane: Physics only
- File family: `_10_Li_2025` only
- DOCX only
- Source: `in/_10_Li_2025.docx`
- Converted: `out/check_docx/_10_Li_2025.omml.docx`
- Date: 2026-04-28

## Residual inventory (converted DOCX)

Total remaining OLE objects: 19
- `Equation.DSMT4`: 13
- `Equation.3`: 2
- `Visio.Drawing.15`: 1
- `Word.Picture.8`: 1
- blank/none: 2 (none observed in this pass)

Residual loci (paragraph index in `word/document.xml` of converted DOCX):
- `Equation.DSMT4`:
  - p158 x4
  - p332 x3
  - p712 x2
  - p1124 x4
- `Equation.3`:
  - p412 x2
- `Visio.Drawing.15`:
  - p213 x1
- `Word.Picture.8`:
  - p794 x1

Representative nearby context:
- p158: "C. song song với . D. tạo với một góc 600. II"
- p332: "Đồng vị phóng xạ - xenon ..."
- p412: "Bắn hạt prôtôn ... phản ứng hạt nhân ..."
- p213: "Hình bên biểu diễn sự thay đổi độ phóng xạ ..."
- p794: "Hình nào sau đây biểu diễn không đúng vector lực từ ..."

## User-reported symptom mapping

1. Câu 11 missing vector B in choices C/D
- Correlates directly with residual object cluster at p158 (`Equation.DSMT4` x4).
- Status in this pass: remains.

2. Table border loss
- Not correlated with residual embedded objects.
- Evidence: table structure counts are stable source->output in this pass (`w:tbl` unchanged; `w:tblPr/w:tblBorders` unchanged).
- Classification: likely_not_object_related.

3. Tab/alignment drift
- Not strongly correlated with residual object families.
- Evidence: paragraph alignment/indent/tab property counts are stable or near-stable (`w:pPr/w:tabs`, `w:pPr/w:jc`, `w:pPr/w:ind` unchanged; only tiny global delta `w:tab` -2 over whole file).
- Classification: likely_not_object_related.

## Practical classification buckets

### clearly_fixable_now_for_docx
- None confirmed in this pass.

### maybe_fixable_but_needs_risky_core_change
- `Equation.DSMT4` residuals (p158/p332/p712/p1124), especially p158 Câu 11 vector-choice defect.
  - Reason: user-visible correctness impact exists, but remaining cases indicate upstream unresolved conversion/manifest gaps rather than a narrow DOCX-local post-patch tweak.
- `Equation.3` residuals at p412.
  - Reason: likely requires extension of object-conversion path with non-trivial blast radius.

### preserve_and_note_only
- `Visio.Drawing.15` (p213).
- `Word.Picture.8` (p794).
  - Reason: legacy embedded families, low-volume, usually require family-specific conversion policy.

### likely_not_object_related
- table border loss
- tab/alignment drift

## Strongest next DOCX target (if reopening fix lane)

Candidate:
- p158 Câu 11 vector-choice defect (`Equation.DSMT4` residual cluster x4)

Why it is strongest:
- user-visible correctness issue
- repeated object cluster in one local question block

Why this pass does not implement fix now:
- no narrow, low-blast-radius DOCX-local patch point demonstrated by evidence in this pass
- likely requires core conversion behavior change for unresolved DSMT4 handling

## Decision

`diagnosis_only_note_remaining_residuals`

## Explicit stop reason

Residual defects are mixed between unresolved equation-object conversion families and non-object layout behavior. The leading user-visible defect (Câu 11 vector B) is real but does not present a proven narrow DOCX-only local leverage point in one safe change during this pass.

## Verification summary

- Câu 11 vector-choice defect: remains (not improved in this diagnosis-only pass).
- Residual object counts: unchanged in this pass (no converter code change applied).
- Nearby regression check (around p155-p160 and p793-p795): no additional new residual families introduced by this pass.
