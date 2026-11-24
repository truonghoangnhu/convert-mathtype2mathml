# DSMT4 acceptance snapshot — 2026-11-24

This versioned snapshot closes assessment of the **265 MathType occurrences in the five original exams**. It does not expand decoder support or certify the entire 32-exam corpus.

| Outcome | Occurrences |
|---|---:|
| Accepted | 238 |
| Needs review: source OLE retained | 18 |
| Needs review: presentation limitation | 9 |
| Failed / unsupported in this subset | 0 / 0 |
| Total | 265 |

The outputs contain 247 native OMML conversions and 18 retained OLE objects. Keeping an object is preservation, not editable conversion acceptance. UI coverage is by structure group: 17 Word samples and 17 samples inside Writer documents. It is not a claim that all 265 objects were edited individually.

- [ledger.csv](ledger.csv): frozen copy of the final 265-row ledger; historical columns keep their original, scoped meanings.
- [ledger-summary.json](ledger-summary.json): original aggregate report, including per-exam and per-route results.
- [exceptions.csv](exceptions.csv): all 27 remaining exceptions; retained OLE are explicitly distinguished from the nine presentation limitations.
- [provenance.json](provenance.json): source/Word-output hashes, converter revision, external transpect commit, submodule revisions and runtime JAR hashes.
- [SHA256SUMS](SHA256SUMS): checksums for this snapshot.

Acceptance rules and the named presentation limitations are in [the acceptance document](../../dsmt4_migration_acceptance.md). The independent hoa068 UI check is preserved in [its report](../../working/hoa068_independent_verification_2026-11-24.json).

The original exams, converted exam documents, full screenshots/render sets and transpect runtime remain separate local artifacts. Their hashes identify the exact files; this repository does not redistribute those documents or the external runtime. Existing local evidence is under `work/dsmt4-claude-d-ledger-20261122/` and the `out/` paths recorded in provenance. The snapshot records completed evidence; it does not manufacture new application observations from a successful build.

Verify this snapshot on macOS or Linux:

```bash
cd docs/acceptance/dsmt4-2026-11-24
shasum -a 256 -c SHA256SUMS
```
