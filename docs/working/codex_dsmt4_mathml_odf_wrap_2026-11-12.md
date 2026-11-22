> Latest: EXP actual Writer UI edit–save–close–reopen completed; 200001 and3rows retained. Alignment remains unresolved, no corpus acceptance. Earlier pending-unlock statements below are historical.

# MathML → ODF wrapping spike, 2026-11-12

Scratch only; no production changes, commit/push, corpus promotion, or policy change. Two genuine DSMT4 preview-MTEF-derived MathML sidecars: INT source Toán Tuyên Quang ¶152/rId446/oleObject218.bin/image223.wmf; EXP source Toán Tạ Quang Bửu ¶64/rId166/oleObject80.bin/image80.wmf. This is positional provenance reused from the earlier real-wrap plan, not fresh BIN semantic verification. No preview-based formula reconstruction.

## Input design and checks

`work/dsmt4-mathml-wrap-2026-11-12/` contains INT; `exp/` contains EXP. Each has four-page ODT with raw single, existing prepare() single, raw table, existing prepare() table. Each object content.xml is MathML without StarMath annotation, forcing the MathML importer. Manual cut points are before the second equals and final plus for INT, and before minus5000 and plus200000 for EXP. A one-column mtable with three mtr/mtd/mrow rows is generated; no script/fraction/integral subtree is flattened or rebuilt. Input token sequence and original top-level child signatures are checked exactly; adding wrapper/empty mrow does not count as formula acceptance.

Only the existing Math-only preparation is invoked: INT table adds L empty mrow group before = (not an empty table row); EXP table gets no adapter changes. No new adapter rules or StarMath annotation are authored. Text column180pt in a400pt×500pt artificial page. This is not original full-exam layout.

Bundled renderer CLI is absolute runtime `dependencies/bin/override/soffice`, version LibreOfficeDev26.8.0.0.alpha0 build2c87e51eeaa2b413ff4ae097b2705eea1995d8e5; fresh profile per PDF/ODT save. Logs and exact command/version in each bundled-run.json. UI uses installed LibreOffice26.8.0.3 separately; no equivalence between them is assumed.

## INT: actual UI save–close–reopen failed

Opened original MathML-only input in Writer26.8.0.3. Prepared table imports to `matrix{ { S = { int ^ 2 _ 0 mline } ... } ## { { } = ... } ## { + ... } }`; AX Formula contains several ¿ markers. Saved As new mathml-wrap-writer-saved.odt, closed, reopened through Recent Documents, and opened Object4 Commands: same invalid matrix text persists. Exported mathml-wrap-writer-reopened.pdf from actual Writer. Viewed all4pages via contact sheet plus page4 at larger size: table is flattened into one long line, clips beyond page, and has red markers. Raw-single splits tokens vertically; prepared-single also clips and has parse errors. None is a passing INT form. No UI formula edit was made in this INT batch; it is a document-level import/save/reopen negative control.

The raw sidecar already has integral marker and following operand pieces separated, plus literal bars spanning style boundaries. These are preserved rather than inferred/repaired; which of these contexts causes the matrix parse collapse has not been isolated. Do not generalize INT failure to all mtable input.

## EXP: initial headless candidate (UI completed below)

Same construction on real EXP sidecar: bundled render shows raw/prepared table in three rows with visible minus/plus and sentinel below; prepared single stays one long line; raw single has vertical token breakup. Viewed all4pages contact sheet and page4 larger. This is not UI edit/save/reopen or source-fidelity acceptance. Mac locked while opening this separate candidate; user unlock requested. Input and existing artifacts are preserved. Next: open EXP input in Writer, verify Commands, edit last constant200000→200001 only on QA copy, save/close/reopen ODT and export actual PDF. If candidate fails, record failure rather than modifying normalized MathML/OMML.

## Checks and limits

`verify_probe.py` verifies source and input hashes, four original MathML hashes,3rows, exact ordered tokens/top-level subtrees and no annotation. Bundled ODT annotation captures stored separately. These checks do not equate input-preservation with importer output equivalence. INT remains failed, EXP needs_review, accepted_promotions0. FULL_END_ONLY unsupported and earlier safety skips unchanged. No source in/, ZIP, fixture, older output or user documents changed.

## Claude review and bounded resolution

Claude reviewed scripts/plans/checks and contact sheets (`claude_dsmt4_mathml_odf_wrap_review_2026-11-12.md`), no P1, two P2 interpretation gaps. Both are accepted: bundled INT render also fails and visually matches the UI at contact-sheet level (Codex separately viewed its page4). Prepared-single INT already has parse markers without wrapping, so INT is **inconclusive for mtable wrapping**, though its resulting documents fail. This differs from the earlier binary-dependent OMML case.

EXP only demonstrates a three-row table with unary minus/plus continuation on the bundled binary. It does not test leading relational operators, and installed Writer UI remains not_run because Mac is locked. The raw/prepared EXP tables are byte-identical, so pages3/4 are duplicates, not independent passes. EXP raw-single has red parse markers as well as vertical token breakup.

Left alignment is not preserved: mtable columnalign=left imports as plain matrix with centered/indented continuation rows; existing prepare report already flags this as untested/failed alignment. No placement or full-layout pass is claimed.

Verifier now also checks prepared-single tokens and exact embedded Object content against each variant file. `dependencies.json` pins the adapter/content code and original provenance plan hashes; it was added after review launch. `annotation-provenance.json` links extraction files to saved ODT/binary. No new refs.json validation is claimed; source mapping remains positional and recorded in earlier plan/corpus.

Mac unlock is the only pending input for EXP interactive edit/save/reopen. No production code changed; git diff --check passed, and construction checks passed. Review does not close this UI debt or promote accepted.

## EXP actual UI after unlock

User authorized one-hour awake command; caffeinate -di -t3600 launched separately (prevents idle sleep/display sleep, not manual lock). Opened **original EXP MathML-only input** directly in installed Writer26.8.0.3, not headless-resaved ODT. Object4 Commands as imported:
`matrix{ { P left ( t right ) = 2000 e ^ { 0,1 t } } ## { - 5000 e ^ { - 0,03 t } } ## { + 200000 } }`

Replaced the exact captured Commands string with the same string changing only200000→200001. Save As new `exp/exp-mathml-writer-edited.odt`, closed, reopened via Recent Documents; Commands retains200001 and same matrix rows. Exported `exp/exp-mathml-writer-reopened.pdf` by actual Writer. Viewed page4 at larger size: three rows visible, plus/minus/limits of the exponent visible, sentinel below, no red marker; continuation alignment remains centered/indented rather than requested left. `exp/UI-verification.json` records original/reopen Commands, four annotations and final hashes. Only Object4 individually edited; other three objects only document-level save/reopen.

This closes EXP UI debt for the narrow unary-continuation case. It does not cover leading relations, general automatic break selection, full-source semantic equivalence, source-exam placement, tall fractions or page-edge cases, and does not solve INT. No promotion beyond needs_review; no production edit/commit/push.

## Final UI review

Claude đã review delta UI (`claude_dsmt4_mathml_odf_ui_review_2026-11-12.md`): không P1/P2, không blocker mới; chỉ xác nhận phạm vi unary-continuation. Lần mở đầu là MathML-only import; lần mở lại dùng ODT đã lưu có StarMath annotation, nên chứng minh edit tồn tại trong định dạng Writer, không phải một lần import MathML độc lập thứ2. Căn trái/quan hệ đầu hàng/INT vẫn mở. Checkpoint đã bổ sung artifacts EXP. Không chạy lại corpus/Maven khi production không đổi; kiểm construction và git diff --check đạt.
