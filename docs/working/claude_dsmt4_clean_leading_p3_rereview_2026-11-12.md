# Clean leading-relation experiment: rereview of the three P3 fixes (read-only)

**Scope:** I read report lines 35-43, `validate_review_hardening.py`, `probe_utils.py` (current version), `dependencies-before-confirmed-runs.json`, `review-hardening-verification.json` and `confirmed-observations.json`, and grepped both `confirmed-*-run.json` files for version, profile and preflight fields. I viewed no PNGs or PDFs.

**Verdict:** All three P3 findings are resolved. No P1, P2 or P3 issues remain. There is one optional strengthening below, which is not a finding.

## P3-1: the gated baseline must be the same input as page 1 — resolved

- `validate_review_hardening.py:9-10` asserts that `prepared-baseline.odt` Object 1, `leading.odt` Object 1 and `prepared-baseline-prepared-single.mathml` are all byte-identical.
- Both ODT hashes are pinned (`dependencies-before-confirmed-runs.json:12-19`), and `baseline_object_byte_equality: true` is recorded (`review-hardening-verification.json:17`).
- The *timing* claim (baseline inspected before `build_wrap.py` ran) is still supported by observation only. The report no longer leans on it as machine-checked (line 41). That is acceptable: the byte linkage was the substantive gap.

## P3-2: fresh profiles must be enforced — resolved

- `render()` now runs `assert not profile.exists()` before launching (`probe_utils.py:37-38`) and keeps `out.mkdir(exist_ok=False)` (`:36`).
- The `profile_absent_before_launch: true` field (`:41`) is written only after that assertion, so it is guarded, not a bare literal.
- The new runs use new labels and record the field in all four entries (`confirmed-leading-run.json:19,38`; `confirmed-reimport-run.json:19,38`), together with the system 26.8.0.3 version and distinct `confirmed-*-profile-{pdf,odt}` paths. The verifier asserts the field (`validate_review_hardening.py:23`).
- The fresh runs reproduce the original result:
  - all three saved object XML byte strings are equal to the original first-pass output (`:18-19`);
  - the PDF text of every page is equal (`:20-21`);
  - this holds for both the confirmed comparison and the confirmed reimport (`review-hardening-verification.json:2-15`).
- The original artifacts are kept. Report line 43 states that the original helper did not have the preflight.

## P3-3: pin the code version and the source mapping — resolved, with honest scope

- The hashes of `prepare_libreoffice_mathml.py`, `manifest.tsv`, both input ODTs and the render helper are captured before the confirmed runs (`validate_review_hardening.py:4-5,11`) and rechecked after them (`:25`; `review-hardening-verification.json:16`).
- Manifest line 202 is asserted exactly as `/word/media/image282.wmf` ⇥ `mathml/wmf/6a301f…wmf.mathml` (`validate_review_hardening.py:7-8`; `dependencies-before-confirmed-runs.json:25`).
- The pin is labelled "after original experiment … not a retroactive original launch pin" (`dependencies-before-confirmed-runs.json:2`; report line 41). That is accurate, because the pinned helper is the hardened version, not the one used for the original runs.

**Optional strengthening, not a finding:** the confirmed runs only re-render the existing `leading.odt`; they never call `prepare()`. So the pinned `prepare` hash identifies the code that exists now, but nothing shows it *produced* the artifacts. A cheap determinism check would close that link: rerun the current `prepare()` on the source sidecar and on the raw split, and assert byte equality with `prepared-baseline-prepared-single.mathml` and `leading-prepared-leading-equals.mathml`.

## Scope unchanged

These are hardening checks only:
- system 26.8.0.3, headless, one short genuine sidecar;
- no GUI, editability or semantic claim (`semantic_claim: false`);
- no production change, serializer, commit or push.

Corpus stays `needs_review`, accepted 0, FULL_END_ONLY unsupported, safety skips unchanged.
