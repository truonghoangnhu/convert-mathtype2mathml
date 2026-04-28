# Physics DOCX last-mile checkpoint: `_10_Li_2025` Câu 11 DSMT4 cluster

Scope:
- Physics only
- DOCX only
- target file only: `_10_Li_2025`

Inputs:
- source: `in/_10_Li_2025.docx`
- baseline converted: `out/check_docx/_10_Li_2025.omml.docx`
- sidecar workdir: `work/dsmt4-external-audit/10-li-2025--a56f3697ec68`

## Exact p158 cluster evidence

Paragraph p158 text:
- `C. song song với . D. tạo với một góc 600. II`

In source and output, p158 still contains:
- 4 `Equation.DSMT4` OLE occurrences (`oleObject37/38/39/40.bin`)
- previews on `image41.wmf` and `image44.wmf`
- one `mc:AlternateContent` run in the same paragraph

## Root-cause finding for unresolved Câu 11 cluster

Observed with patch run using warnings and the same manifest:
- initial blocker: `Skipped multi-object paragraph: run contains unsupported element <AlternateContent>`
- after a narrow exploratory whitelist attempt for `AlternateContent`: blocker shifts to
  `Skipped multi-object paragraph: not all resolved objects could be mapped back into paragraph order`

Evidence chain:
- sidecar for previews exists and is usable:
  - `/word/media/image41.wmf -> mathml/wmf/...b428d980...wmf.mathml` (usable)
  - `/word/media/image44.wmf -> mathml/wmf/...0f061d31...wmf.mathml` (usable)
- no manifest entries for BIN parts `oleObject37/38/39/40.bin` (expected in this family)
- paragraph-level XML shape is compatibility-heavy: detector sees 4 occurrences in p158, but the multi-object safety mapping path cannot deterministically map all resolved occurrences back into one stable paragraph segment sequence when `AlternateContent`/compat structure participates.

Conclusion:
- this is not a simple missing-sidecar case for p158.
- this is a paragraph-structure/mapping safety-model limitation in multi-object patching.

## Decision

`residual_not_safely_fixable_now`

Reason:
- A safe one-line local adjustment did not improve Câu 11 and immediately exposed a deeper ambiguous mapping guard.
- A real fix now would require broader core changes in detector/multi-object mapping for compatibility (`mc:AlternateContent`) structures, which exceeds “one narrow safe DOCX-side fix” for this pass.

## Verification summary

- Câu 11 vector-choice defect: remains.
- p158 residual `Equation.DSMT4` objects: unchanged.
- nearby structure: no new local regression introduced in baseline output path for this pass.
