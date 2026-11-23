# Writer DOCX leading-temperature comparison — 2026-11-06

Status: **needs_review**. One content-loss fix is implemented locally; no full DSMT4 acceptance, commit, push, merge or PR-state change. Claude's requested independent review of this final change did **not** complete: the same session returned its five-hour usage limit. Earlier Claude analysis is a proposal review, not review of this implementation.

## Failure and bounded repair

The current noBreak output still renders Hóa #68 `>150°C` as `¿150°C` in Writer, and Writer saving DOCX drops `>` altogether. The outer noBreak box does not fix this. A second operator box initially renders correctly and even preserves `>` in saved XML, but reopening displays the error again. That probe was rejected; XML text alone is insufficient.

The installed LibreOffice build is `bce0998afefdbc355585ca324285661a2170ba77`. Its [matching importer source](https://raw.githubusercontent.com/LibreOffice/core/bce0998afefdbc355585ca324285661a2170ba77/starmath/source/ooxmlimport.cxx) differs from the newer source cached in earlier investigations. Runtime behavior was measured separately; newer missing-operand helpers cannot be assumed present.

`XmlBeansOmmlInjector` now groups the existing leading `>` run in `m:d`, with explicit empty `begChr`/`endChr` and a **nonempty** `m:e` containing that original run. It adds no text, hidden character, synthetic operand or empty argument. Original operator/number/superscript/unit nodes and their run properties survive intact. Existing inline noBreak grouping remains outside it.

The rule is restricted to newly inserted legacy inline math with exactly three top-level parts: a nonliteral `>` run, a superscript whose single-run base is ASCII digits and whose exponent is `°`, then a single-run `C`. It does not extend to other relations, leading minus, arbitrary operands, literal/normal-text `>`, standalone `>`, native OMML, display equations or already grouped math. Normalized MathML and the separate Math adapter are unchanged. This is a measured temperature-pattern compatibility rule, not general Writer relation support.

## Application evidence

- **Word, full Hóa QA copy:** candidate displayed `>150°C` without visible delimiter brackets or an empty placeholder. Added `q`, saved under a new name, closed and reopened; displayed `>150°Cq`. XML binds `q` to the same `m:oMath`, **outside** the original noBreak box. This proves editing the equation, not preservation of that box property.
- **Writer, full Hóa context:** candidate and two successive DOCX saves/reopens render `>150°C` correctly. The version first saved by Word, including `q`, also survives Writer save/reopen. Reopened page 4 was visually inspected. Typography, spacing, pagination and other formulas are not accepted by this check.
- **Writer UI, exact-structure minimal extraction:** activated Math, changed `C` to `Cq`, saved as Word DOCX, closed and reopened; visibly `>150°Cq`. Saved XML has the same equation text and a nonempty delimiter argument. Full-exam UI editing was **not completed** because object selection was unreliable; this minimal test is not reported as a full-exam UI pass.

Evidence: `work/dsmt4-writer-docx-followup-2026-11-06/` contains `baseline.json`, `relation-probes/result.json`, `candidate-headless.json`, `word-saved-crossapp.json`, `ui-verification.json`, the separate QA copies, `word-delimiter-reopened.png` and `full-context-reopened.png`. Original sources and earlier outputs/evidence were not overwritten.

## Regression and corpus checks

The new regression fails on the previous implementation (`expected d, got r`) and passes with the repair. Boundary cases cover other relations, no operand, nonleading operators, literal text, a nonnumeric base, another superscript and another unit; display placement remains unmodified.

Fresh `mvn -q package`: **116 tests, 0 failures/errors**. Fresh generated-output gate: **4/4**. `git diff --check` passed. Python remains the previously verified 141-test Math-adapter snapshot; it was not rerun for this Java-only change.

New output: `out/dsmt4-writer-comparison-2026-11-06/`. All **32** files were repatched with the fresh JAR and structurally audited. Exactly **one formula** differs from the preceding boxed snapshot: Hóa #68's operator grouping. Removing that new grouping reproduces its prior entire math tree, including run properties; the fresh target tree equals the UI-tested candidate. Other formula trees are unchanged. Nonmath run contents/properties, paragraph properties, native OMML, retained OLE and embedding bytes are preserved; original source hashes still match.

Counts remain **2,286 inserted** (71 block / 2,215 inline), **331 DSMT4 retained + 10 other OLE**, **2,313 total OMML** including 27 native. The five-exam mapping remains **247 candidates + 18 retained = 265 legacy occurrences**, with 18 native equations unchanged. `work/dsmt4-writer-docx-followup-2026-11-06/current-ledger.json` rebinds all occurrences to this snapshot, preserves earlier scoped evidence for unchanged math and adds only the measured Hóa #68 evidence. Accepted promotions: **0**; the current full failed total is **not established**.

## Remaining acceptance work

Writer labeled-arrow import/save behavior, nested/table alignment outside the measured Math rule, font/spacing and full pagination still require work. Historical failures are not automatically current failures or passes. The two OLE in Lý paragraph 91 and the original safety skips remain retained. `FULL_END_ONLY` remains unsupported. Final independent Claude review is pending credit; no acceptance status is raised while it is pending.
