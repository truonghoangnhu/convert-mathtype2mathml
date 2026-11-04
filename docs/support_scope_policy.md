# Support Scope Policy

This is the canonical support boundary. It supersedes older statements that
DSMT4 investigations are frozen or outside the product roadmap.

## Supported inputs and verified decoding scope

- Modern `.docx` with native OMML equations.
- `.docx` containing legacy MathType OLE, including `Equation.DSMT4`, as
  **migration input** to MathML/OMML.
- DSMT4 support is conditional on the actual extracted MTEF payload and a
  verified decoder path. ProgID identifies the object, not its MTEF version,
  structure, formula contents, or conversion capability.
- A payload class is verified only for the structures covered by recorded
  real-source tests. A successful example does not establish support for all
  objects with that ProgID, MTEF version, or byte fingerprint.

## Canonical migration path

`OLE → extracted MTEF → normalized MathML → native OMML for Word`

Use the normalized MathML artifact to import an editable formula into
LibreOffice Math. Writer acceptance must verify the imported formula in its
actual document and after reopening. A preview image is reference evidence,
not an editable conversion. Existing native OMML remains on its current path.
The existing external transpect runtime decodes OLE/MTEF; this policy does not
claim a new general DSMT4 decoder or bundle that runtime into Maven.

## Failure and preservation contract

- `unsupported`: no verified usable decoder output, missing sidecar, empty or
  metadata-only MathML. Preserve original OLE, preview and placement.
- `failed`: conversion or transformation error. Preserve the original and
  report the reason; never substitute an empty formula.
- `needs_review`: candidate conversion exists but content, editing, placement
  or Word/Writer reopening has not been verified, or a placement safety check
  prevents patching. Retain the source document for comparison and recovery.
- Nonempty XML, a `<math/>`, nested empty containers, annotations, whitespace,
  or a preview alone cannot establish successful formula conversion.
- Current patch counters remain technical counters: `unresolved` and skip
  reasons are not evidence of content correctness. Diagnostic logs label
  unusable sidecars `unsupported` and transform exceptions `failed`.

## Acceptance

Counts are the first reconciliation check. Acceptance also requires correct
formula contents (including arrow direction, scripts, labels and conditions),
editable mathematical structure, original position and correct display after
saving and reopening in Word and Writer. Package/XML validation alone does
not prove application reopening or visual correctness.

Start with the chemistry arrow formula, then reconcile every one of the
265 MathType occurrences across the five original exams. See
[the acceptance procedure](./dsmt4_migration_acceptance.md).

## FULL_END_ONLY investigation

Continue investigating extracted payload boundaries, parser interpretation,
MTEF records and independent source evidence. Existing `FULL_END_ONLY` and
`UNSUPPORTED_SUBTYPE` labels are observed diagnostic classifications, not proof
that decoding is possible or intrinsically impossible. No production recovery
rule is justified yet. Do not generate a formula from a fingerprint or infer
content from counts. Keep these objects unchanged and report `unsupported`
until a faithful decoding path is demonstrated.

The prior [taxonomy](./dsmt4_taxonomy_baseline.md),
[MTEF semantics note](./dsmt4_mtef_spec_reference_note.md) and
[corpus audit](./dsmt4_full_in_corpus_audit_2026-04-23.md) remain evidence
snapshots. Their historical roadmap/freeze language is superseded here;
their recorded observations remain available for investigation.

## Out of scope

Direct binary `.doc` ingestion and malformed pseudo-DOCX packages. Resave
`.doc` to a valid `.docx` before migration, retaining the original for comparison.
Unverified broad legacy-format recovery is not a support promise.
