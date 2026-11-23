# EXP annotation authority: rereview of the P2-1 and P3 fixes (read-only)

**Scope:** I read the current report (lines 1-25), `verify_probe.py`, `verification.json` and `observations.json`. I did not reread my prior review document; I relied on its findings from this session. I viewed no images or PDFs and opened no ZIPs.

**Verdict:** **P2-1 is resolved at the evidence and reporting level** (no converter fix was needed or claimed). **All the P3 findings are resolved.** No P1, P2 or P3 issues remain.

## P2-1: the presentation-only reimport changes structure — resolved

**Evidence is recorded and asserted.**
- The verifier stores the exact original Commands and the exact reimported Commands (`verify_probe.py:32-37`; `verification.json:51-56`).
- It asserts that the reimported string equals the observed regrouped form (`:34-35`).
- It also asserts that this string differs from the original even after `alignl` is removed (`:36`). I checked by hand that stripping `alignl ` from the original gives the same bracket layout, so the remaining difference really is the grouping: `{ left(t right) = 2000 }`, `{ - 5000 }` and `{ - 0,03 }`.
- The `equal_after_removing_alignl: false` field is a literal, but the assertion at line 36 guards it.

**Reporting is correct.**
- Report line 15 states the regrouping with the exact strings.
- It ties the regrouping to the nested `mrow` in Writer's saved presentation. That is consistent with `saved-with-annotation.mathml`, which I saw in the previous round.
- It explicitly makes **no** claim of semantic inequivalence, certifies **no** structural or semantic correspondence, and says the saved presentation is "not a validated reference for a serializer". That is exactly the boundary the finding needed.

## P3 findings: all resolved

| Finding | Resolution |
|---|---|
| Source ODT unchanged after the GUI attempt | Rehashed against the plan (`verify_probe.py:9`); `source_saved_odt_unchanged: true` (`verification.json:4`). |
| Observations hardcoded in the verifier | Moved to `observations.json` with the observer named, and linked by SHA (`verify_probe.py:50`; `verification.json:97-98`). |
| ZIP name list not asserted | The exact member set is now asserted: scaffold files plus `Object 1-4/content.xml` (`verify_probe.py:12`). |
| First sandbox attempt not recorded | Recorded honestly as a tool-output observation, not a captured log, with its root cause marked as not isolated (`observations.json:5-12`). |

The narrow conclusions still hold: the annotation is authoritative for the constant in the divergent EXP control, and a presentation-only reimport loses `alignl` and regroups the formula. Both rest on system 26.8.0.3 headless with fresh profiles. GUI acceptance, source semantic acceptance, production change, commit/push and corpus promotion are all explicitly not claimed (report lines 3, 21-23; `verification.json:96,99-100`).

## Guardrails for the next leading-relation scratch test (advisory, not findings)

The candidate is Tuyên Quang `6a301f…` (`b=c=2,5`), from `leading-relation-candidates.json` (report line 25). I did not inspect that inventory.

1. **Check the baseline import first.** Import the raw single form with system 26.8.0.3, record its Commands, and confirm there are no ¿ markers *before* splitting it. If the baseline fails, discard the candidate, as with INT.
2. **Choose the cut in advance.** Split before the second top-level `=`. Use the existing signature and token-order checks unchanged.
3. **Compare raw against the existing rule L.** Raw continues with `= …`; rule L continues with `{ } = …`. Record the imported Commands for both. Do not hand-author an annotation, so that the MathML importer's own behaviour is what gets tested.
4. **Record the binary for every run.** If the GUI is unavailable, label the result headless only.
5. **Keep it diagnostic.** The token strings in the inventory are not to be used for reconstruction (report line 25). No `prepare()` change, no generator, no rollout to normalized MathML/OMML.

**Status:** scratch only. Corpus stays `needs_review`, accepted 0, FULL_END_ONLY unsupported, safety skips unchanged, no commit or push.
