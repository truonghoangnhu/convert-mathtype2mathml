# Bounded Math row alignment implementation plan

**Goal:** Close the demonstrated left-alignment import defect for the verified flat three-row assignment-system shape in the separate LibreOffice Math preparation route. Existing user scope is DSMT4 fidelity with verified decoding, preserving unsupported cases. Codex implements; the same single Claude Code session reviews. No commits or new worktree.

**Decision:** Add bounded rule A using generated StarMath annotation while retaining the original presentation MathML. Pure columnalign was already shown ineffective in the current importer. Padding changes geometry without a reliable unit; keeping only a prototype leaves the demonstrated defect unresolved. The annotation route has real initial/roundtrip measurements and a standalone Math UI edit/reopen of the exact toan015 command. Annotation is authoritative, so unsupported grammar must never generate one.

**Shape:** Unstyled math → exactly one mfenced(open={,close=empty,separators=empty) → mtable(columnalign=left) → exactly three mtr/mtd rows. Leaves have no attributes/children. Each row is one ASCII-letter lhs, equals, integer/ASCII-letter rhs terms, optional initial minus, then binary plus/minus. A term is integer optionally followed by one letter, or one letter. XML whitespace only between elements. No nested structure, metadata, foreign namespace, arbitrary commands or chained relations. Presentation nodes/attributes/text/order stay intact. Unicode minus stays in presentation; only StarMath syntax spells minus as ASCII hyphen.

**Files:** `scripts/transpect/prepare_libreoffice_mathml.py`, public command tests in `tests/test_prepare_libreoffice_mathml.py`, versioned evidence under work/out. Normalized MathML/OMML Word is unchanged.

## Tasks

- [x] Add failing public-CLI regression for actual three-row formulas, exact generated command, unchanged presentation and needs_review/not_run status.
- [x] Add counterexamples: leading/trailing/double operator, adjacent integers/variables, chained equals, unsupported styles/namespaces/metadata/structures/delimiters/row counts, non-XML whitespace. Verify current positive test fails for missing A.
- [x] Implement strict whole-shape parser and annotation before other adaptation rules, with no cascading edits. Metadata rerun remains byte-identical.
- [x] Run the full Python suite; prepare all265 into a new directory. Confirm changed cases and investigate any mismatch: actual toan013–015 change; toan016 is nested and remains deferred. Compare generated toan015 command/presentation to the UI-tested probe.
- [x] Render and save/reopen all changed candidates in isolated ODT, verify presentation row text/ordering, annotation and bbox alignment. Keep UI evidence scoped; do not infer DOCX/full-exam acceptance.
- [x] Review with the existing Claude session, reproduce real findings before fixes, update ledger evidence/docs and keep accepted0/corpus needs_review.

Review focus: metadata priority, parser command injection/implicit multiplication ambiguity, mixed text/attributes, semantic token preservation and byte-idempotence. Earlier source/ZIP/fixtures/output remain unchanged; initial skips/FULL_END_ONLY remain outside this change.
