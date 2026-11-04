# Real DSMT4 corpus audit — 2026-11-03

## Scope and verdict

The supplied `in/` corpus contains **32 DOCX files**, **2,617 Equation.DSMT4 occurrences**, **27 native OMML equations**, and **10 other OLE objects**. Counts include raw XML occurrences, not inferred formulas inside images. The initial 265-object / five-exam target is not treated as a measured subset of this expanded corpus.

**Verdict: `needs_review`.** All files generated review candidates; this is not semantic or layout acceptance for all formulas. The originals remain byte-identical.

## Actual MTEF evidence

- Parsed all **2,100 distinct MathType BIN hashes**, representing all 2,617 DSMT4 occurrences. No MathType BIN parse failed.
- Extracted **1,934 distinct MTEF byte hashes**. All parsed headers report **MTEF version 5**, with `DSMT7` in 1,903 distinct BINs and `DSMT6` in 197.
- 2,099 BINs contain body records and remain `BODY_PRESENT_UNVERIFIED`; body records alone do not certify correct MathML, OMML or display.
- One BIN is `FULL_END_ONLY`, occurring once in `TN-THPT-2026-Hoa-Lan-2.docx`, `word/embeddings/oleObject81.bin`, XML paragraph 95 (1-based). Its 192-byte MTEF has `encoding_def,font_def,font_def,font_def,font_def,eqn_prefs,full,end`, with no char/slot/template body.
- That occurrence remains **`unsupported` and unchanged**. Its OLE SHA-256 is `f5ca4fc93dbe5d16810672dda31d3e1f49b89565385500d5ad82060cbf0e6859`; extracted MTEF SHA-256 is `8b4bd7d65209e8963c91c987255962da12bb62c3a624c9497c0c236579d151a0`. This is parser evidence, not proof that recovery is possible or impossible.

Runtime provenance:

- `transpect/calabash-frontend`: `a4cf3ae17cf117100447744e285b92fce9e3699d`
- `transpect/mathtype-extension`: `f57c9429f882bcc510fd5dad7465aada4938f7d6`
- Local runtime is ignored under `tools/calabash/`; no upstream decoder was modified.

## Generated candidates and preservation

- Usable MathML sidecar coverage: **2,616 / 2,617** MathType occurrences.
- Native OMML candidates inserted: **2,508** (80 block, 2,428 inline).
- **109 MathType objects retained**: 1 unsupported payload and 108 occurrences not patched under current paragraph/placement safety rules. All 10 non-MathType OLE objects were also retained.
- Output inventory: **2,535 OMML equations** = 27 existing + 2,508 inserted.
- All 32 sources retain their original SHA-256. All 32 outputs preserve non-math `w:t` sequences, existing OMML subtrees, paragraph counts, remaining OLE subtrees and their paragraph positions, and embedded file bytes. No injected OMML remains nested in a Word run.
- These XML/package checks do not certify visual position, semantic equivalence or application behavior for the full corpus.

| Source | Native OMML | DSMT4 | MathML mapped | Patched candidates | DSMT4 retained |
| --- | ---: | ---: | ---: | ---: | ---: |
| `CN_12_HKI_PNH_CM_25_26.docx` | 0 | 0 | 0 | 0 | 0 |
| `Hoa_11_HK1_LTT_25_26.docx` | 0 | 0 | 0 | 0 | 0 |
| `Hoa_Bac-Ninh_L1.docx` | 0 | 103 | 103 | 101 | 2 |
| `Hoa_Ha_Noi_L1.docx` | 0 | 100 | 100 | 100 | 0 |
| `Hoa_Ha_Tinh_L1.docx` | 3 | 90 | 90 | 90 | 0 |
| `Hoa_Hue_L1.docx` | 0 | 3 | 3 | 3 | 0 |
| `Hoa_LTT_DN_Lan_03.docx` | 0 | 8 | 8 | 8 | 0 |
| `Hoa_NB_L3.docx` | 0 | 2 | 2 | 2 | 0 |
| `Hoa_NinhBinh_L5.docx` | 0 | 25 | 25 | 25 | 0 |
| `LI-12-So-GD-Bac-Ninh-25-26.docx` | 0 | 94 | 94 | 71 | 23 |
| `Li_HP_c5_L5.docx` | 0 | 7 | 7 | 7 | 0 |
| `Li_LDlan03.docx` | 0 | 16 | 16 | 16 | 0 |
| `Li_Nghe_An_L5.docx` | 3 | 18 | 18 | 16 | 2 |
| `Li_TN_L2.docx` | 0 | 74 | 74 | 74 | 0 |
| `TN-THPT-2026-Hoa-Lan-2.docx` | 6 | 139 | 138 | 134 | 5 |
| `TN-THPT-2026-Hoa.docx` | 0 | 97 | 97 | 97 | 0 |
| `TN-THPT-2026.docx` | 0 | 32 | 32 | 32 | 0 |
| `TNCN_CN_DaNang.docx` | 0 | 34 | 34 | 34 | 0 |
| `Thi_Thu_TN_CN.docx` | 15 | 0 | 0 | 0 | 0 |
| `Toan-So-GD-Tuyen-Quang-lan-1.docx` | 0 | 355 | 355 | 355 | 0 |
| `Toan_01.docx` | 0 | 181 | 181 | 150 | 31 |
| `Toan_02.docx` | 0 | 138 | 138 | 138 | 0 |
| `Toan_10_NTB_HK1_25_26.docx` | 0 | 121 | 121 | 104 | 17 |
| `Toan_Chuyen_TP_HP_L1.docx` | 0 | 127 | 127 | 124 | 3 |
| `Toan_Gia_Lai.docx` | 0 | 151 | 151 | 151 | 0 |
| `Toan_Long_Thanh.docx` | 0 | 122 | 122 | 122 | 0 |
| `Toan_Phu-Tho-Lan-5.docx` | 0 | 132 | 132 | 106 | 26 |
| `Toan_TQB_HN_Lx.docx` | 0 | 115 | 115 | 115 | 0 |
| `Toan_ThAn_AG_L3.docx` | 0 | 122 | 122 | 122 | 0 |
| `Toan__0102.docx` | 0 | 77 | 77 | 77 | 0 |
| `VL_NB_Lan03.docx` | 0 | 66 | 66 | 66 | 0 |
| `Vat-Li-So-GD-Vinh-Long.docx` | 0 | 68 | 68 | 68 | 0 |

Files with zero OMML/OLE counts can still contain formulas as images or text; no image-semantic recognition was performed.

## Chemistry arrow: actual application checks

Source: `Hoa_NB_L3.docx`, short-answer question 4, reaction `CH₃CH(NH₂)COOH → X → Y`.

- Both OLEs contain MTEF5 / `DSMT7`. Extracted BIN and paired WMF MTEF match exactly after removing the one trailing `0x0A` byte from WMF.
- Recovered MathML contains right arrows, upper labels `CH₃OH, HCl khan` and `NH₃`, and lower labels containing `−H₂O` and `−NH₄Cl`, including commas present in the source.
- **Word 16.114.3**: opened native equations; arrows and labels visible after the placement fix. Inserted `9` inside the second equation, saved, and verified it appeared in that equation’s `m:t`. Undid the edit, saved, closed and reopened; both equations remained.
- **LibreOffice 26.8.0.3 Math**: explicitly imported MathML to ODF. Edited the first formula from `H₂O` to `H₉O`, saved and verified its formula annotation. Restored `H₂O`, saved, closed and reopened successfully.
- **Writer**: loaded the fixed DOCX, saved ODT with two native embedded formula objects, and reopened/rendered the ODT. Both arrows and labels remained visible. Source and candidate Writer PDF renders each had 5 pages.
- **Still `needs_review`**: arrows are shorter and label spacing differs from the OLE preview; exact layout has not passed. Interactive editing of the embedded object inside Writer itself was not tested. No application acceptance was performed for every other formula in the corpus.

The Word formula API recognizes OMML as native mathematical structure; application checks were also observed here. For general format mapping see [Microsoft MathML documentation](https://learn.microsoft.com/en-us/office/math/mathml). LibreOffice formula command strings are documented in [FormulaProperties](https://api.libreoffice.org/docs/idl/ref/servicecom_1_1sun_1_1star_1_1formula_1_1FormulaProperties.html). These references do not establish corpus acceptance.

## Bugs exposed by real data and fixed

1. Inline patching placed `oMath` inside `w:r`. Word displayed a missing arrow base and Writer omitted the formula. The injector now splits runs and places `oMath` under `w:p`, retaining surrounding text, drawings, markers and run properties, with rollback on failure.
2. The short-text block heuristic deleted units and answer labels such as `kJ/mol`, `(gam)`, `[A]`, and `Suy ra:`. Block replacement now requires an object-only paragraph; other cases use inline placement or remain unchanged.

3. Inline/block OMML dropped the source run's size, colour, underline and highlight, so equations took the paragraph-style size instead of the surrounding text size (1,031 of 1,041 explicitly sized object runs differed). The injector now copies `w:color`, `w:sz`, `w:szCs`, `w:highlight` and `w:u` of the object's run onto every `m:r` (schema order, never overriding what the transform set). Bold, italic and `w:position` are intentionally not copied: math style comes from the MathML and `w:position` only aligned the OLE picture.
4. `mml2omml.xsl` had no `mspace` rule, so explicit spaces were dropped (`CH₃OH, HCl khan` became `CH₃OH,HClkhan`; `10,0 A` became `10,0A`). Widths ≥ 0.12em now become Unicode spaces (U+2006 / U+2004 / U+2003) in a normal-text run; MathType's automatic 0.08em thin space is deliberately still omitted. The arrow regression test previously asserted the space-less text and now asserts the spaces.

5. Labelled reaction arrows (`\xrightarrow`, a `munderover`/`mover`/`munder` over an arrow `mo`) kept a one-character arrow with the labels set around it, so the arrow never reached across the text. When the arrow has a non-empty label, `mml2omml.xsl` now emits Word's stretching `m:groupChr` over the wider label, with the other label through `m:limLow`/`m:limUpp`; arrows without labels keep the generic rule. The form was chosen by rendering OMML variants in Word, and the two chemistry-arrow objects were rendered in Word (arrow spans each label's width, labels keep their spaces and subscripts). 39 `m:groupChr` arrows appear in the regenerated candidates.

   **Writer limitation found while checking this.** The first form (a bare `groupChr` inside `limLow`/`limUpp`) imported into Writer as `{label} csub {arrow} csub {label}` and rendered no arrow and collapsed labels with stray `¿` glyphs, so it was not kept. In the two-label forms the `groupChr` therefore sits inside an invisible `m:d` (empty begin/end characters). Re-checked with LibreOffice 26.8.0.3 Writer (headless DOCX→PDF and DOCX→ODT→PDF): both chemistry arrows keep their labels in the right order (upper label, arrow, lower label) and the ODT holds two formula objects that reopen identically, but Writer draws the arrow at script size. It has no stretching group character, so the arrow does not span the labels there. Interactive editing of these formulas inside Writer was not tested. Word and Writer therefore differ in arrow length. Decision (2026-11-04): the script-size arrow in Writer is accepted as a known limitation of that application rather than reverting to the short `→` form; the Writer arrow length remains `needs_review` and is not an acceptance of the corpus.

Fixes 3 and 4 were applied to all 32 sources and `out/dsmt4-real-corpus/patched/` plus `batch_report.json` were regenerated with `work/dsmt4-real-corpus/repatch_verify.py` (the earlier candidates and reports are kept in `work/claude-review/pre-fix-backup/`). Patch counts are unchanged (80 block, 2,428 inline, 11 unresolved; 29 of 32 output hashes changed, the other three contain no DSMT4), all sources keep their SHA-256, every preservation check in the report passes, and an independent paragraph-by-paragraph comparison of non-math content and effective run properties shows 0 differences. In the new outputs 3,810 `m:r` carry the source size (13 before) and 143 space runs are emitted.

`out/dsmt4-real-corpus/patched/` was regenerated again after fix 5. The Word/LibreOffice/Writer results and the `chemistry-arrow-evidence/` DOCX files above were obtained on earlier candidates; the Word and Writer rendering of the two chemistry arrows was repeated on the current ones. Arrow length and spacing were judged by eye, not measured against the OLE preview, so the corpus stays `needs_review`.

Regression fixtures retain the actual two arrow MathML/MTEF payloads and FULL_END_ONLY parser XML/MTEF, with source and payload hashes under `fixtures/dsmt4/`.

## Verification and artifacts

- `mvn -q test`: 64 Java tests passed (52 before the fixes below plus 12 regressions).
- `python3 -m unittest discover -s tests`: 104 Python tests passed.
- `python3 -m unittest discover -s scripts/workflow -p "test_*.py"`: 4 passed.
- Modern smoke: 4 passed, 1 expected negative, no unexpected failures.
- Modern generated-output gate: 4/4 package and structural checks passed.

Local artifacts below are ignored generated files; retain them together with the original sources when reproducing the audit:

- `out/dsmt4-real-corpus/source_inventory.json`: source hashes, object locations and image inventory.
- `out/dsmt4-real-corpus/mtef_inventory.json`: actual BIN parser evidence linked to every DSMT4 occurrence.
- `out/dsmt4-real-corpus/payload_audit.json`: existing corpus classifier output, including the deep-audited FULL_END_ONLY case. Renderable classes here are sidecar-stage classifications; direct BIN parsing is recorded separately above.
- `out/dsmt4-real-corpus/batch_report.json`: final candidate counts and per-file preservation checks.
- `out/dsmt4-real-corpus/patched/`: final DOCX review candidates.
- `out/dsmt4-real-corpus/chemistry-arrow-evidence/`: parser comparison, application evidence and renders.
- `out/dsmt4-real-corpus/lo-math/`: imported editable ODF formulas.
- `work/dsmt4-real-corpus/`: staged inputs, logs and local batch/probe drivers.

Reproduce sidecars with the README workflow, then patch a separate output using each manifest. Audit existing workdirs with:

```bash
python3 scripts/workflow/audit_dsmt4_corpus.py \
  --scan-path work/dsmt4-real-corpus --format json
```

The next acceptance work is formula-level comparison across the full corpus and exact arrow/label layout, followed by edit/save/reopen checks in both applications. Counts and nonempty outputs must not promote these candidates to accepted.
