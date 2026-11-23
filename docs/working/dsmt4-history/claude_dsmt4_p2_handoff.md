# Bàn giao bốn P2 DSMT4 — 2026-11-04 (Claude)

Trạng thái: **ứng viên chờ Codex review, chưa commit/push**. Không đổi Draft/auto-merge của PR #4.

> Codex đã kiểm chứng độc lập bản này, sau đó tìm thấy lỗi căn lề còn lại khi mở
> bằng Word. Phần P2-2 và số liệu dưới đây là mốc bàn giao lịch sử; xem
> [bản sửa tiếp và bằng chứng Word](./codex_dsmt4_word_placement_2026-11-04.md)
> cho trạng thái hiện tại. Các phần P2-1/P2-3/P2-4 vẫn được giữ.
> Ngày 2026-11-05, người dùng đã cung cấp ZIP định danh bộ 5 đề; khoảng trống
> định danh 265 object dưới đây đã được đóng bằng
> [đối chiếu từng payload](./dsmt4_five_exam_reconciliation_2026-11-05.md).

- Worktree: `.claude/worktrees/dsmt4-p2`, nhánh local `claude/dsmt4-p2`, tách từ `467370f`
  (`feature/dsmt4-migration-fidelity`). Thay đổi để ở working tree (file mới đã `git add -N` để diff có đủ).
- Patch đầy đủ, độc lập với worktree: `work/claude-p2/claude-dsmt4-p2.diff`.
- `in`, `tools`, `work` trong worktree là symlink tới dữ liệu dùng chung; `out/` trong worktree là thư mục
  thật chứa symlink (để generated-output gate không ghi đè `out/modern-docx-omml-generated` dùng chung).
  Không commit các symlink này, cũng không commit `p2-probes/` (bản sao ở `work/claude-p2/scripts/`).

## Kết quả từng P2

### P2-2 — căn lề block: **đã sửa**
- Tái hiện trước khi sửa: 4 test mới đỏ trên mã gốc (`work/claude-p2/logs/p2-2-regression-red.log`),
  gồm cả bookmark bị dời ra sau phương trình.
- Quyết định: Word đặt `m:oMathPara` theo `m:jc` riêng, không theo căn lề đoạn; còn OLE gốc là ảnh inline
  được đoạn sắp chỗ. Vì vậy chỉ đoạn chỉ có object, **căn giữa hiệu dụng**, không thụt lề, không đánh số,
  không `framePr`, không `bidi` mới thành block. Thứ tự xác định căn lề: pPr trực tiếp → chuỗi style đoạn
  (hoặc style đoạn mặc định) → style bảng → docDefaults → mặc định trái. Định dạng bảng có điều kiện
  (`tblStylePr`) và xung đột giữa style đoạn với style bảng bị coi là không xác định, nên dùng inline.
  Mọi trường hợp khác dùng inline, tức giữ đúng cơ chế bố cục của OLE.
- Block được đặt đúng vị trí của run object (bookmark giữ hai bên) và có `m:oMathParaPr/m:jc="centerGroup"`
  tường minh để `m:defJc` khác của tài liệu không dời được nó.
- Mã: `DisplayEquationPlacement.java` (mới), `PoiMathSourceDetector.isBlockEquationCandidate`,
  `XmlBeansOmmlInjector.injectBlock`.
- Corpus (so với mốc cùng commit 467370f): 80/2.428 → **54 block / 2.454 inline** (tổng 2.508 giữ nguyên).
  Có 26 đoạn block→inline = 21 đoạn reviewer nêu (6 `left`, 3 `both`, 12 không `jc`) + 5 đoạn `center`
  có `firstLine=283`. Có 0 inline→block, 0 phương trình khác nội dung. Cả 54 block đều có nguồn căn giữa,
  không indent. Probe: `work/claude-p2/block_alignment_p1.json` (80) và `block_alignment_p2.json` (54).
- Render **Writer** (LibreOffice 26.8.0.3, headless, profile riêng):
  `out/dsmt4-p2-2026-11-04/render-writer/`. Với `Toan-So-GD-Tuyen-Quang-lan-1` (đoạn 183…, `jc=left`):
  nguồn căn trái (trang 7 của PDF nguồn), mốc 467370f căn giữa, P2 căn trái. Ca `center+firstLine`
  (`Hoa_Bac-Ninh_L1`) và ca đối chứng block giữ nguyên (`Toan_01`) đã render, nhưng chỉ xem bằng mắt.
  **Word chưa chạy** cho P2: không tự động hoá GUI Word trong phiên nền. Đây là bằng chứng XML + Writer,
  không phải nghiệm thu ứng dụng.
- Giới hạn: 26 phương trình nay ở dạng inline, nên Word/Writer dựng theo kiểu toán inline (có thể gọn hơn
  display). Chưa so với preview OLE. Ảnh hưởng của indent lên display math trong Word chưa được đo; vì vậy
  mới chọn inline cho đoạn có indent.

### P2-1 — cổng nội dung vô hình: **đã sửa**
- Một token chỉ được tính khi có ít nhất một code point ngoài Cc, Cf, Zs, Zl, Zp (và khác U+EF0A đã biết).
  Quy tắc này giống hệt ở `MathmlContent.hasFormula`, `hasOmmlRunContent` (Java) và
  `mathml_content.is_usable_math` (Python). Vector dùng chung:
  `fixtures/mathml_content/visible_content_vectors.json` (34 code point, 14 tài liệu MathML), được kiểm
  bởi `MathmlContentVectorTest` và `tests/test_mathml_content.py`. Lệch U+0085 giữa Java và Python đã hết.
- Không xoá gì khỏi công thức: gate chỉ quyết định có patch hay không. Test `keepsInvisibleOperatorsBesideVisibleTokens`
  cho thấy U+2061 còn trong OMML. **Phát hiện:** chính `mml2omml.xsl` của Microsoft (template `OutputText`)
  xoá U+2062 và U+200B khỏi text. Hành vi này có từ trước, nằm ngoài gate; tôi không sửa mà ghi lại trong test.
- PUA (ngoài U+EF0A) và `mpadded width="0"` vẫn được tính là có nội dung, vì chưa có bằng chứng render.
- Quét lại 2.523 sidecar bằng gate cũ và mới: 0 thay đổi (2.521 dùng được, 2 không)
  (`work/claude-p2/sidecar_gate_rescan.json`).
- `explain_unresolved_manifest.mathml_status` là bộ phân loại chẩn đoán riêng, không phải gate; không đổi.
- Giới hạn: mỗi bên dùng cơ sở dữ liệu Unicode của runtime (Java 25 → Unicode 16, Python 3.9 → 13). Vector
  chỉ chứa ký tự có cùng category ở cả hai.

### P2-3 — tách run, assert, rollback: **đã sửa**
- Nhánh tách run **có chạy** ở đường nhiều object; đường một object vẫn chặn run hỗn hợp (giữ OLE). Bảo vệ
  được giữ nguyên. Test DOM chính xác: `splitsMixedObjectRunAroundEquationInMultiObjectParagraph` và
  `retainsMixedObjectRunUnchangedOnSingleObjectPath`.
- **Bug thêm tìm được:** tách run tạo `w:r` rỗng từ các nút khoảng trắng giữa con của run. Đã sửa: chỉ phần
  tử mới tính là nội dung. Corpus thật không có khoảng trắng như vậy.
- Assert nhãn `"."`/`" "` vốn luôn đúng nay so chuỗi `w:t`/phương trình thực theo thứ tự (`paragraphSequence`).
- Rollback, xác nhận đúng giả thuyết của Codex: trên JAR 467370f, sau khi lỗi giữa chừng thì
  `getCTP().getDomNode()` ném `XmlValueDisconnectedException`
  (`work/claude-p2/logs/restore_probe_base_467370f.log`). Probe của Codex cũng cho
  `originalParagraphAttached=false`. Thêm nữa, theo SuccessProbe của Codex, khi **thành công**, commit cũ
  thay mọi con của đoạn nên `XWPFRun` đã cache bị mồ côi và `getText()` ném lỗi.
- Cách sửa (`XmlBeansOmmlInjector.editParagraph`): sửa trên bản sao sâu của đoạn; mọi lỗi lúc sửa không đụng
  đoạn thật. Khi thành công, chỉ phần chênh lệch được đưa vào: phần tử con không đổi giữ nguyên node (nên
  `XWPFRun` vẫn sống), run bị thay đi qua `XWPFParagraph.removeRun`, run tách mới đi qua `insertNewRun` tại
  đúng vị trí. Nhờ đó `getRuns()`/`getText()` đúng sau patch. Chỉ so khớp phần tử, vì XMLBeans không giữ
  identity ổn định cho nút text.
- Test: `leavesParagraphIntactWhenMultiObjectPatchFailsPartWay` (object trong hyperlink làm lỗi sau 2 lần
  thay; kiểm bộ đếm `XML_MUTATION_ROLLBACK`, `unresolved`, chữ ký đoạn, thứ tự text/drawing/break),
  `leavesParagraphIntactWhenReplacementFailsAfterStarting` (lỗi cài qua seam ở cả multi, inline, block),
  `keepsXwpfParagraphUsableAfterFailedMultiObjectPatch` (OMML hỏng bên trái như probe Codex; identity node,
  sourceNode của plan còn trong đoạn, `xmlText()`/`getText()`, patch lại cùng plan, save/reopen),
  `savesUntouchedParagraphAfterFailedMultiObjectPatch`, `keepsLiveRunsAndTextAfterSuccessfulPatch` (làm
  nóng `getRuns/getText` trước patch; ba nhánh; save/reopen).
- Probe Codex chạy trên JAR P2: `work/claude-p2/logs/codex_rollback_probe_on_p2.log` (`attached=true`,
  `xmlText` đọc được) và `codex_success_probe_on_p2.log` (`inject=true`, `paragraphText=before `).
- Caller thực tế: walker thu thập mọi occurrence trước khi patch; sau `inject` không mã nào đọc lại
  `XWPFRun`/`sourceNode` (chỉ `inspectOmmlStructure` đọc DOM gốc, rồi `document.write`). Ref còn stale **có
  chủ đích**: `XWPFRun` của object run đã thay, cùng `MathOccurrence.sourceNode/runIndex` của object đó.
  Run tách mới tạo bằng `insertNewRun` rồi mới được nạp nội dung, nên danh sách ảnh (pictures) mà `XWPFRun`
  cache khi khởi tạo không gồm drawing đã chuyển vào. Text vẫn đọc trực tiếp từ CTR.
- Giới hạn: bước commit (insert/remove, không parse) không có rollback nếu chính XML store lỗi ở bước đó.
- Kèm theo: gom paragraph theo identity node thay vì chuỗi `identityHashCode`, vốn có thể trùng
  (`DocxMathPatchMain.groupByParagraph`).

### P2-4 — nguồn dữ liệu, kiểm kê, tài liệu: **đã sửa phần mã/tài liệu; mục 265 còn mở**
- Nguồn sidecar: cả 32 manifest chỉ có WMF (2.521 mục, 0 BIN). 31/32 `generate.log` ghi "BIN parts required
  after WMF pass: 0"; file còn lại cần 1 BIN, chính là FULL_END_ONLY.
- Đối chiếu mới, mạnh hơn kiểm tra đa tập (`work/claude-p2/bin_vs_wmf_mtef.json`, dùng parser `mathtype`
  của transpect JRuby 9.3.8.0): **2.617/2.617** occurrence có MTEF của WMF = MTEF của BIN + đúng 1 byte đuôi
  (LF 1.446; giá trị khác 1.171). Điều này không chứng minh MathML/OMML/hiển thị đúng, cũng chưa chứng minh
  decoder bỏ qua byte đó.
- Tài liệu đã nêu rõ việc này, và rằng kiểm tra đa tập ký tự không chứng minh thứ tự/cấu trúc
  (`docs/dsmt4_real_corpus_2026-11-03.md`, `docs/support_scope_policy.md`).
- 265 object / 5 đề: **không định danh được**. Repo và bằng chứng local không có danh sách 5 đề. "265" duy
  nhất tìm thấy là `_30_Toan_2025.docx` (một file của bộ 28 file cũ, không có trong `in/` hiện tại). Gap đã
  ghi; không bịa bảng ánh xạ.
- Kiểm kê object (`ObjectInventory.java` mới): đếm mọi `w:object` của document và của các part
  wordprocessingml khác, đối chiếu với các object walker đã đưa vào. Object ngoài walker được ghi theo
  container (`sdt`, `textbox`, `alternate_content`, `tracked_change`, `custom_xml`, `smart_tag`, `field`,
  `part:header` …), log `unsupported`, và giữ nguyên. Hợp đồng chẩn đoán chỉ được **bổ sung**: JSONL có
  thêm `discovered_objects`, `scanned_objects`, `unscanned_objects`, `unscanned_containers`; `scanned` giữ
  nghĩa cũ; dòng `Patch summary:` không đổi; thêm dòng riêng `Object inventory:`. Constructor 14 tham số
  của `PatchSummary` vẫn dùng được.
- Test tổng hợp `reportsObjectsOutsideWalkedParagraphsAndLeavesThemUnchanged` (block `w:sdt`, inline `w:sdt`,
  header): discovered 4 = scanned 1 + unscanned 3; `w:sdt` và header không đổi; object ở body được patch.
  Test CLI `reportsObjectInventoryAdditivelyInJsonAndHumanSummary`.
- Corpus: mọi file có discovered = scanned (tổng 2.627), 0 unscanned.

## Lệnh đã chạy và kết quả
Runtime: OpenJDK 25.0.2, Maven 3.9.14, Python 3.9.6, POI 5.5.1, JRuby 9.3.8.0 (transpect), LibreOffice 26.8.0.3.

| Lệnh | Kết quả | Log |
| --- | --- | --- |
| `mvn -q test` | 80 test, 0 fail/error (trước P2: 64) | `work/claude-p2/logs/mvn-test.log`, `mvn-test-final.log` |
| `python3 -m unittest discover -s tests` | 106 OK (trước: 104), chạy lại sau gate vẫn OK | `logs/python-tests.log`, `python-tests-after-gate.log` |
| `python3 -m unittest discover -s scripts/workflow -p "test_*.py"` | 4 OK | `logs/python-workflow-tests.log` |
| `scripts/workflow/run_modern_docx_omml_smoke.py` | passed 4, expected_failed 1, unexpected 0 | `logs/modern-smoke.log` |
| `scripts/workflow/run_modern_docx_omml_generated_output_gate.py` | 4/4 openability + structural | `logs/modern-generated-gate.log`; output `out/dsmt4-p2-2026-11-04/modern-docx-omml-generated/` |
| `work/claude-p2/scripts/run_corpus_p2.py` (mốc + P2) | xem bảng dưới | `out/dsmt4-p2-2026-11-04/report.json`, `baseline-467370f/report.json` |

## Số liệu cũ/mới (32 đề)

| | Mốc 467370f | P2 |
| --- | ---: | ---: |
| Block / inline | 80 / 2.428 | 54 / 2.454 |
| Tổng OMML chèn / OMML output | 2.508 / 2.535 | 2.508 / 2.535 |
| Unresolved | 11 | 11 |
| OLE còn lại (DSMT4 + OLE khác) | 119 (109 + 10) | 119 (109 + 10) |
| Block có nguồn không căn giữa | 21 | 0 |
| discovered / scanned / unscanned object | không đo | 2.627 / 2.627 / 0 |
| File đạt mọi kiểm tra cấu trúc | 32/32 | 32/32 |

Kiểm tra cấu trúc gồm: OMML nguồn không đổi; `w:t` ngoài toán không đổi; số paragraph không đổi; không có
OMML trong `w:r`; OLE còn lại không đổi; byte embeddings không đổi; `pPr` mọi đoạn không đổi; lá nội dung
ngoài toán kèm `rPr` hiệu dụng không đổi ở mọi đoạn của mọi part. So với mốc: 0 phương trình khác nội dung.
Thư mục `out/dsmt4-p1-2026-11-04/` có trước sửa #5 (groupChr), nên khác mốc ở 32 đoạn mũi tên; vì thế nó không
dùng làm mốc so phương trình.

Hash đề gốc: 32/32 không đổi trước, trong và sau khi chạy, và khớp `out/dsmt4-real-corpus/batch_report.json`.
SHA-256 của bảng hash (JSON sort_keys): `a3a751ab11f03aa9ebcc830a4b8b989428f6849fcc527fe8b9a5559183f3cb95`.
JAR P2 đã chạy corpus: `f2543289e9fe9e799def2abc59513b82f29177cb079cfe12875c84bb8e62ff70` (sau đó chỉ xoá
một import thừa). JAR mốc là JAR của checkout chính (`mml2omml.xsl` khớp HEAD; chưa so từng class):
`a0c9718a2d8a7ba08da990b968a733479700475b7a6eff4bcb238c5a6297b0f4`. Cả hai đã được sao vào
`out/dsmt4-p2-2026-11-04/`. Ứng viên cũ trong `out/dsmt4-real-corpus/` và `out/dsmt4-p1-2026-11-04/` vẫn giữ.

## Giới hạn và finding chưa đóng
- Corpus vẫn `needs_review`. Không có kết luận "accepted" hay "hiển thị đúng" nào rút ra từ XML/số đếm.
  Word chưa chạy cho P2; Writer chỉ render 4 ca đại diện.
- FULL_END_ONLY vẫn `unsupported`. Không vá thêm trong số 108 object bị giữ. Giới hạn đã công bố của
  Writer (mũi tên), bold/italic và `mspace` < 0,12em giữ nguyên.
- `mml2omml.xsl` xoá U+2062/U+200B (có từ trước).
- `Hoa_Bac-Ninh_L1` đoạn 126 và 304 (một sidecar): nhãn mũi tên do decoder sinh ra ở mã TCVN3
  (`®iÖn ph©n dung dÞch`, `cã mµng ng¨n`). Công thức sai về chữ. Có từ trước, ngoài P2.
- Mục tiêu 265 object / 5 đề chưa đối chiếu được.
- Kiểm kê chỉ đếm `w:object`. Ảnh/hình chứa công thức hoặc OLE dạng khác (`w:pict` không có `w:object`)
  không được nhận diện.

## Đề xuất commit/PR (sau khi Codex review)
- Một commit trên `feature/dsmt4-migration-fidelity`, ví dụ:
  `fix(dsmt4): keep block placement, invisible-content gate, live-paragraph edits and object inventory (P2)`.
  Commit các file trong `git status` trừ symlink `in/ tools/ work/`, `out/` và `p2-probes/`.
- Cập nhật mô tả PR #4: bảng số liệu ở trên, 26 đoạn block→inline, thay đổi hợp đồng JSONL (chỉ bổ sung),
  và phần giới hạn. Giữ Draft.
