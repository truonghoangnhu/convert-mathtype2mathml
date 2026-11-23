# EXP MathML→ODF alignment comparison

Scratch in work/dsmt4-mathml-align-2026-11-12, no production edit/commit/push. Reuses genuine EXP sidecar manual3row split from previous wrap spike; provenance/source limitations there remain. Four variants share exact presentation tree (ignoring added columnalign): table-left, cell-left, row-cell-left, annotation-alignl. Last variant adds an explicit **hand-authored** StarMath5.0 annotation from the observed imported EXP Commands, putting alignl on each matrix row. It is not a generic MathML-to-StarMath serializer or a new adapter rule; annotation can override presentation in the measured importer. No preview reconstruction.

## Actual Writer UI

Opened original align-input.odt in installed LibreOffice26.8.0.3, Object4 Commands imported all3 alignl directives. Changed only last constant200000→200001 in the captured string, SaveAs new align-writer-edited.odt, closed, reopened viaRecentDocuments; Commands retained3 alignl and200001. Exported align-writer-reopened.pdf byactualWriter. OnlyObject4 individually edited; other3 documentroundtrip. ODT reopening uses saved annotation, not a second independent MathML import. No DOCX or Word claim.

Viewed all4UIpages individually at1200px and contact sheet. Attributes on mtd and mtr still yield centered continuations. Annotation variant shows all3lines flush left, no red marker, expected constant200001 and sentinelbelow. Bundled initial annotation page4 also viewed and flushleft; CLI absolute runtime dependencies/bin/override/soffice, LibreOfficeDev26.8.0.0.alpha0, exact command/profile/version in bundled-run.json. Other bundled pages not yet visually inspected; no claim for them.

## Measurement and checks

verify_alignment.py checks source/input/variant hashes; embedded objects match variant bytes; presentation signatures match except columnalign; bundled/UI annotations match exact expected original/edited commands. It does not claim annotation semantic equivalence from token count. PDF text origins measured with pdfplumber on all4UIpages: variants1/2/3 x0=[110.70,115.30,125.05]pt, spread14.35pt; alignl variant x0=[110.70,110.70,110.70]pt, spread0.00pt. Text origins are not glyph ink or page fidelity. Final command differences are exactly constantedit; hashes/annotations/PDFmetrics in verification.json.

## Limits

Narrow layout improvement for one hand-authored EXP annotation with unary continuation rows. No automatic breakpoint selection, leading relation, general formula grammar, tall formula, pageedge or source-exam placement check. INT MathML already fails import before wrapping and is not fixed. Shared normalizedMathML/OMML untouched; no safety skip expansion or FULL_END_ONLY claim; corpusneeds_review, accepted_promotions0. Any future annotation generator must prove grammar/structure correspondence and reject unsupported/mixed/metadata shapes; this scratch is not safe for general rollout.

## Claude bounded review

Claude read-only review complete (`claude_dsmt4_mathml_alignment_review_2026-11-12.md`): no P1/P2; narrow hand-authored annotation improvement supported. Three P3 are scoped: annotation authority is inferred from alignl effect, not a deliberately divergent dual-representation test; regenerated presentation MathML requires separate inspection; savedODT reopen is not a second MathML-only import. Inspected regenerated Object4 MathML attributes in saved-mathml-alignment.json, without claiming consumer/reimport equivalence. Deliberate divergence and a general guarded serializer remain unimplemented. This result is ready as experimental evidence, not rollout.
