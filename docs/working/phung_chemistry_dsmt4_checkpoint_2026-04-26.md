# Phung Chemistry DSMT4 Checkpoint 2026-04-26

Local-only chemistry pass over `in/Phung/*`.

## Target Set

- `in/Phung/On theo chu de thi THPT 2026_GV.docx`
- `in/Phung/On theo chu de thi THPT 2026_HS.docx`

Both files have the same embedded-object profile:

- `Equation.DSMT4`: 217 objects
- `ChemDraw_x64.Document.6.0`: 6 objects
- `ChemWindow.Document`: 5 objects
- `ACD.ChemSketch.20`: 2 objects
- DSMT4 single-object paragraphs: 73
- DSMT4 multi-object paragraphs: 56

ChemDraw, ChemWindow, and ChemSketch are chemistry-structure assets. They are preserved as non-OMML assets and remain out of scope for native OMML conversion.

## Fixed Issue

The DSMT4 blocker was not paragraph alignment first. The sidecar work directory included spaces from the source filename, and Calabash/Mtef2Xml received `file:` URIs containing encoded `%20` path segments. Mtef2Xml then failed with ENOENT while reading staged WMF/BIN files.

`scripts/transpect/generate_sidecars.sh` now creates temporary URI-safe symlink aliases for Calabash/Mtef2Xml source and target paths. The real output directory is unchanged, but the converter receives paths without encoded spaces.

## Before And After

| File | byte identical | DSMT4 mapped | unresolved | skipped_multi | block | inline | native | OMML after |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| GV before | n/a | 0/217 | 140 | 57 | 0 | 0 | 45 | eq:52,inline:29,block:23 |
| GV after | false | 216/217 | 12 | 2 | 20 | 195 | 45 | eq:267,inline:224,block:43 |
| HS before | n/a | 0/217 | 140 | 57 | 0 | 0 | 45 | eq:52,inline:29,block:23 |
| HS after | false | 216/217 | 12 | 2 | 20 | 195 | 45 | eq:267,inline:224,block:43 |

New DSMT4 content persisted as OMML in both selected files. Each output now has 267 `m:oMath` and 43 `m:oMathPara` nodes.

## Remaining Blockers

- One DSMT4 payload class still fails sidecar generation in each file.
- That unresolved DSMT4 payload leaves one multi-object paragraph with 2 remaining `Equation.DSMT4` objects in each output.
- The 13 non-DSMT4 chemistry-structure objects are intentionally untouched and remain as embedded chemistry assets.

Decision: `dsmt4_partial_gain_note_remaining_blockers`
