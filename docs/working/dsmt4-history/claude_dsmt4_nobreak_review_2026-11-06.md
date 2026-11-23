# Claude read-only review: inline noBreak — 2026-11-06

Snapshot review before Codex tightened inline supplied-root handling and test assertions. No tests or application validation were run by the reviewer. Session: `675b163e-2674-4748-90ab-1654b1d1ec54`.

The original reviewer text follows. Its spelling/schema comment is a reviewer claim, not a separately verified schema verdict; both `1` and `on` were accepted in the Word probes. Codex selected `on` for stylesheet consistency. See the Codex follow-up for reproduced findings, fixes and application evidence.

I found no correctness bug introduced by the noBreak change on the production path. The real issues are an inconsistent `m:val` spelling, an older bug in how supplied OMML roots are handled (now also on the box path), and a few test assertions that are weaker than they look. This was a read-only review: I ran nothing, and none of this is a corpus or acceptance claim.

## What the fix does

- **Callers:** `XmlBeansOmmlInjector.java:90` (multi-object) and `:157` (single inline, including the `runIndex` fallback) both go through `buildInlineMath` → `keepInlineObjectTogether` (`:518–556`).
- **Block equations untouched:** the block path builds with `buildMathPara` at `:107`, so no box is added there.
- **Native OMML untouched:** the injector only acts on resolved `w:object` targets, so existing native OMML never reaches it.
- **Which branch runs in production:** `mml2omml.xsl:17–21` always emits a root `<oMath>` in the math namespace (default prefix, `:5`). So only the first branch (`:520–521`) runs.

## Order, formatting, namespace and schema

- **Child order:** `:552` moves `firstChild` one at a time into `m:e`, which keeps document order, including attributes and non-element nodes. The box is appended only after `oMath` is empty, so `oMath` ends up with exactly one child: `m:box` containing `m:boxPr`, then `m:e`. That matches the schema order for `CT_Box`.
- **Schema validity:** `m:e` (`CT_OMathArg`) allows the same content group as `m:oMath`, so any valid `oMath` content is valid inside the box. `m:noBreak` is a legal child of `m:boxPr`.
- **Namespace:** new elements use the `m:` prefix with `MATH_NS`. Imported nodes use the default prefix with the same URI. Mixing the two prefixes is harmless.
- **Run formatting:** `carryRunFormatting` runs after the wrap (`replaceObjectRun`, `:333`), and `collectMathRuns` searches nested elements. So the carried `color`/`sz`/`highlight`/`u` properties still reach every `m:r` inside the box.
- **HTML export:** the `m:box` template (`omml2mml.xsl:3386`) passes its content through and `m:boxPr` is ignored, so the MathML output is effectively unchanged. The inline/block counters (`DocxMathPatchMain.java:655`, `validate_modern_docx_omml.py:44–80`) only count `oMath`/`oMathPara`, so neither they nor drift classification is affected.

## Findings, by priority

**1. Inherited bug in supplied-root handling, now also on the box path (medium).** `buildInlineMath` `:523–538` mishandles OMML whose root isn't `oMath`:
- An `oMathPara` root keeps only its first `oMath`. Any other `oMath` siblings are silently dropped.
- Any other root (`m:r`, `m:f`, a wrapper fragment) has its *children* moved into the new `oMath`, not the root itself. For example, `<m:r><m:rPr/><m:t>x</m:t></m:r>` becomes `oMath/box/e/{m:rPr, m:t}`, which is invalid. `<m:f>` likewise loses its wrapper and leaves `fPr`/`num`/`den` loose.
- An `oMathPara` with no `oMath` child sends `oMathParaPr` into `m:e`.
- The name checks don't verify the namespace.

The output before the fix was the same, minus the box, so this is not introduced. It can't happen with XSLT output, but it can through the public `inject(MathOccurrence, String)` and through `MultiObjectPatchPlan` segment `ommlXml`. Suggested fix, as a separate ticket:
- If the root is any other math element, put the root itself inside the new `oMath`.
- Refuse (`return false`) when an `oMathPara` has more than one `oMath` child.

**2. `m:val="1"` doesn't match the stylesheet (low).** At `:548` the code writes `"1"`, while `mml2omml.xsl` writes `"on"`/`"off"` everywhere (`:1174`, `:1336`, `:2828`, …). `"1"` is valid in the Transitional schema, and Word accepted it in your prototype. However, the first-edition math `ST_OnOff` only allows `on`/`off`, so a strict validator would reject it. I'd use `"on"` for consistency; the test at `:1683` would then need updating.

**3. Test gaps.**
- `keepsNewLegacyInlineRelationsInsideOneUnbreakableMathGroup` (`:1669`):
  - It doesn't check structure. Add `count(oMath/*)=1` and assert that the box's children are exactly `boxPr` then `e`.
  - It checks "expression unchanged" only by text. For the vector sample, the arrow accent and the `(`…`)` delimiters live in attributes, not text, so they aren't checked. Add assertions that `e` contains the accent (`m:acc`) and the delimiter structure (`m:d`, `begChr` = `(`, `endChr` = `)`). Or better, compare the child name sequence of `m:e` with the converter's own `oMath` output.
- `multiObjectParagraphKeepsEachLegacyEquationInItsOwnUnbreakableGroup` (`:1691`): counting 2 boxes across the document doesn't prove one per equation, since one `oMath` could hold both. Assert one box per `oMath`.
- `displayConversionDoesNotReceiveAnInlineNoBreakWrapper` (`:1705`): this is sufficient for the block guarantee.
- `retainsLabeledArrowContentFromRealChemistryMtefSidecars` (`:241`): the new XPath is correct. Each `oMath` has one direct box, so `(base)[1]` and `(base)[2]` map to equations 1 and 2, and the test now implicitly asserts the box exists.
- No unit tests cover the `oMathPara` and fallback branches. They are new box behaviour too, and they're where finding 1 lives.

**4. Minor (harmless).** There's no `m:ctrlPr` in `boxPr`, which is fine because the box draws nothing. Supplied OMML that is already boxed would get a second box, which renders the same.

## Fidelity limits (expected, not defects)

- An inline equation wider than the line now runs past the margin instead of wrapping. That matches how the OLE image behaved.
- Tables (`mtable` → `eqArr`, `mml2omml.xsl:2803`) still stack correctly inside the box. `mml2omml.xsl` never emits `m:brk`, so no explicit-break conflict can arise today.
- In Word, the box shows up when editing: linear format shows `□(…)`, and anything the user types goes inside the box.
