# DSMT4 migration implementation

The user's five principles define the design: DSMT4 is a migration input;
ProgID identifies an object, while MTEF evidence determines decodability.
Reuse the existing external OLE/MTEF decoder and normalized MathML sidecars,
then produce OMML for Word and MathML for LibreOffice Math import.
Do not infer support from counts or fabricate a FULL_END_ONLY decoder.

Implementation sequence:
1. Add failing regression cases for empty, metadata-only, malformed MathML,
   and conversion exceptions. Assert original OLE/preview and no patch success.
2. Add shared content validation at sidecar consumption and before OMML injection;
   report unsupported/failed explicitly while retaining existing summary contracts.
3. Apply the same usable-content rule to external sidecar manifest/cache handling.
4. Restore README/support policy; document a real-corpus acceptance record with
   source/payload hashes, position, expected formula, editable output and independent
   Word/Writer reopen checks. Start with chemistry arrow, then all 265 occurrences
   across the five source exams. Missing sources/runtime mean unverified, never pass.
5. Run Java/Python tests and modern DOCX gates. Record actual evidence and gaps.

Review focus: nested empty MathML; annotations mistaken for content; invalid XML;
conversion failures deleting OLE; unrelated native OMML regressions.

The checkout contains modern synthetic fixtures, but no in/, work/, tools/ or
five original exam sources. Real decoding and application reopen acceptance
remain pending those inputs and the external decoder runtime.
