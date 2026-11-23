# Audit nghiệm thu bộ 5 đề DSMT4 — Claude, 2026-11-05

Trạng thái: **chưa nghiệm thu. Corpus và 263 ứng viên vẫn `needs_review`; 12 object `failed` trong Writer.**
> Các số liệu dưới đây thuộc snapshot đã audit. Codex đã kiểm chứng và sửa
> tiếp hai nguyên nhân converter; xem
> [ghi chú follow-up](./codex_five_exam_followup_2026-11-05.md). Chưa đo lại
> toàn bộ ledger hoặc nghiệm thu Word; không xem đây là kết luận cho output mới.
> Correction from Codex follow-up: the Lý #8 `sPre` was **not schema-correct**: converter
> emitted `e/sub/sup`, whereas the required order is `sub/sup/e`. Correcting the order
> restores C in Writer, including UI edit/save/reopen. See [new evidence](./codex_dsmt4_prescript_order_2026-11-05.md).
> Original findings below remain a historical snapshot.

Word: **not_run** — phiên này không có công cụ UI hợp lệ cho Word; không suy kết quả Word từ XML hay Writer.
Không commit/push, không đổi Draft/auto-merge PR #4, không sửa production, `in/`, ZIP, fixture hay output cũ.

## Phạm vi và điều kiện chạy

- Audit trực tiếp working tree `feature/dsmt4-migration-fidelity` (HEAD `467370f` + thay đổi chưa commit),
  JAR `target/docx-html-math-1.0.0-jar-with-dependencies.jar`, output `out/dsmt4-word-placement-2026-11-04/patched/`.
- Guard workflow của Claude Code chặn Write/Edit trong checkout dùng chung ("This background session hasn't
  isolated its changes yet. Call EnterWorktree first…"). Prompt cấm tạo/chuyển worktree nên tôi không gọi
  EnterWorktree và không đổi setting guard. File mới chỉ ghi bằng shell heredoc vào ba vị trí được giao.
- Hash ZIP (`1c3b702e…08035`), 5 nguồn, 5 output và cả 32 tệp `in/` giống nhau trước/sau
  (`work/claude-five-exam-acceptance/evidence/hashes_{before,after}.json`, `manifest.json`).
- Test trên tree hiện tại: `mvn -o test` 82/82, Python 106 + workflow 4 đạt (`work/claude-five-exam-acceptance/logs/`).
  Chỉ là test tự động, không phải nghiệm thu ứng dụng.

## 1. Review sửa căn lề của Codex

Đọc `DisplayEquationPlacement`, `PoiMathSourceDetector.isObjectOnlyParagraph`, `InlineSafetyEvaluator`,
`XmlBeansOmmlInjector.injectBlock/editParagraph`. Chạy CLI thực trên 29 bản thử biến đổi đoạn thật của
Hoa_Ha_Noi_L1 (¶73 thân văn bản, ¶41 ô bảng) với manifest sidecar có sẵn
(`work/claude-five-exam-acceptance/probes/probes.json`, script `scripts/placement_probes.py`).

| Ca thử | Kết quả CLI | Render Writer |
| --- | --- | --- |
| không `jc`, `left`, `both`, `ind` 0, `numId=0`, style thiếu | block `left` | `left`/`both` đã xem: trái |
| `center`, style `jc=center`, docDefaults `jc=center` | block `centerGroup` | giữa |
| `right` (thân, ô bảng) | block `right` | phải (ảnh `probes/pdf/right-2.png`) |
| style center + trực tiếp `left` | `left` | — |
| `start`, `end`, `distribute`, `bidi`, numbering, `firstLine=283`, `left=-142`, style `ind left=720` | giữ OLE | — |
| style `ind 720` + trực tiếp `left=0` | `left` | — |
| ô bảng `center`/không `jc`/`left`/`right` | `centerGroup`/`left`/`left`/`right` | khớp |

Phát hiện:

- **R1 – trung bình, cần Word.** `isObjectOnlyParagraph` coi `w:proofErr` hoặc run có `w:t` rỗng là nội dung,
  nên đoạn đó đi nhánh inline (probe `body-proofErr-before-object`, `body-empty-text-run` → `inline`).
  Sau patch, đoạn chỉ còn một `m:oMath` không có chữ: đúng mô hình lỗi P2-2 mà Word căn giữa dù `w:jc=left`.
  Không có ca nào như vậy trong bộ 5 đề. Toàn corpus có 4 đoạn inline chỉ kèm một dấu cách:
  `Hoa_LTT_DN_Lan_03` ¶151, ¶153, ¶155, ¶157 (không `jc`) (`evidence/lone_inline_corpus.json`). Cần
  Word xác nhận một khoảng trắng có làm Word coi đó là inline hay không. Đề xuất: cho `isObjectOnlyParagraph`
  bỏ qua `proofErr`, `lastRenderedPageBreak`, run rỗng/khoảng trắng khi quyết định block, hoặc giữ OLE.
- **R2 – thấp, an toàn.** Gộp `w:ind` theo tên thuộc tính nên không hiểu `hanging` thay `firstLine`,
  `start`↔`left`, `*Chars`. Probe style `firstLine=283` + trực tiếp `hanging=0` vẫn giữ OLE dù Word thụt 0.
  Chỉ lệch về phía bảo thủ.
- **R3 – thấp.** `jc=start/end` (tên strict/2010) và `distribute` → giữ OLE; chưa có test cho các giá trị này.
- **R4 – thông tin.** Kiểu bảng mặc định (bảng không có `tblStyle`) không được xét; `tblStylePr` có `jc/ind`
  thì giữ OLE (đúng hướng). Thứ tự ưu tiên pPr trực tiếp → style đoạn → style bảng → docDefaults khớp probe.
- **Thiếu test:** start/end/distribute, hanging vs firstLine, proofErr/run rỗng, docDefaults `jc`, right
  trong ô bảng. Nhánh `right` và `both` nay đã render Writer trên probe; **Word chưa kiểm**.
- Việc dùng `m:oMathParaPr/m:jc` tường minh và giữ OLE cho đoạn thụt/numbering là đúng hướng. Trong 5 đề:
  13 block (11 `centerGroup` gồm 8 trong ô bảng, 2 `left`) đều khớp căn lề nguồn trong Writer.

## 2. Đối chiếu 263 công thức (Writer)

Phương pháp: render Writer (LibreOffice 26.8.0.3, profile riêng) nguồn và output 5 đề (22/22 trang, số
trang giữ nguyên); dựng **bảng đối chiếu từng đoạn** (nhãn → đoạn NGUỒN với preview OLE → đoạn OUTPUT
với OMML, cùng styles/section) và **xem bằng mắt toàn bộ 40 nửa trang**. Cộng thêm kiểm XML từng object,
kho ký tự text WMF ↔ OMML (định hướng, không phải pass), đặc trưng OMML, và Writer lưu lại/mở lại.

Ledger: `work/claude-five-exam-acceptance/ledger.json`, `ledger.csv` (265 object × 11 tiêu chí),
`ledger_native_omml.csv` (18 OMML gốc). Ảnh: `out/dsmt4-five-exam-acceptance-2026-11-05/review-sheets/png/`.

| Tiêu chí | verified | needs_review | failed | not_run |
| --- | ---: | ---: | ---: | ---: |
| identity_payload (BIN/thứ tự/parser) | 265 | | | |
| position_xml (đoạn, thứ tự, chữ quanh) | 265 | | | |
| writer_content | 254 | | 11 | |
| writer_structure (chỉ số, phân số, nhãn) | 230 | 33 | 2 | |
| writer_spacing | 167 | 97 | 1 | |
| writer_font_style | 219 | 46 | | |
| writer_position | 261 | 4 | | |
| writer_resave_reopen_no_edit | | 260 | 3 | 2 |
| writer_ui_edit_reopen, word_display, word_edit_save_reopen | | | | 265 |

`verified` ở cột Writer nghĩa là đã nhìn thấy khớp preview nguồn trong Writer; không phải nghiệm thu Word.
Kết quả object: **12 failed, 251 needs_review, 2 OLE giữ nguyên**; 18 OMML gốc giữ nguyên XML (Công nghệ
output trùng byte nguồn).

### Lỗi `failed` theo object

| Đề | Object (đoạn) | Mức | Hiện tượng và nguyên nhân |
| --- | --- | --- | --- |
| Li_Nghe_An_L5 | #1 (¶28) | cao | `0°C?`: MathML `msup` có cơ sở `mspace`; mml2omml bỏ `mspace` → `m:sSup` có `m:e` rỗng; Writer in ô placeholder |
| Li_Nghe_An_L5 | #8 (¶58) | cao | `¹⁴₆C` là `m:sPre` đúng, nhưng Writer bỏ chữ C và in ô; lưu lại trong Writer mất hẳn `C` |
| Toan_TQB_HN_Lx | #54 (¶43) | cao | `∫₀²(2f(x)−1)dx`: `m:d` `sepChr=""` với 5 `m:e` (từ `mfenced separators=""`); Writer in `fleft (x¿)`, lưu lại thành chữ `left` trong `m:t` |
| Toan_TQB_HN_Lx | #15 (¶11) | trung bình | hệ `{` thành `m:m` cột căn giữa: các dòng lệch nhau rõ, nguồn thẳng hàng |
| TN-THPT-2026 | #27 (¶125), #30 (¶128) | cao | `²³⁸₉₄Pu`: `msubsup` cơ sở `mrow` rỗng → `m:sSubSup` `m:e` rỗng rồi `Pu`; Writer in ô placeholder |
| Hoa_Ha_Noi_L1 | #66 (¶146), #67 (¶147) | cao | `mover(→, mrow rỗng)` → `m:limUpp` có `m:lim` rỗng; ô placeholder trên mũi tên ngắn |
| Hoa_Ha_Noi_L1 | #68 (¶148) | cao | `>150°C`: Writer hiện `¿150°C`, lưu lại **mất dấu `>`** |
| Hoa_Ha_Noi_L1 | #37 (¶90), #42 (¶93), #86 (¶155) | cao (Writer) | mũi tên có nhãn `m:groupChr`: nhãn cỡ thường, mũi tên tí hon bên dưới; phương trình đọc thành `CO₂(g)t°,p(NH₂)₂CO`, `ZnS+ O₂,t°ZnO` |

Năm ô placeholder (#1, #27, #30, #66, #67) có nguồn gốc ở converter (đối số OMML rỗng); Word thường cũng
hiện placeholder trên màn hình — cần Word xác nhận. #8, #68, mũi tên `groupChr` là giới hạn nhập OMML của
Writer, OMML không thiếu ký tự; Word chưa kiểm.

### Nhóm `needs_review` chính

- 21 object Toán dùng `m:d` nhiều `m:e` với `sepChr=""` (vd. `M(2;2;1)`, `log₄(x−1)`, `(C)`): Writer vẫn vẽ
  đúng trừ #54; chỉnh sửa trong Word sẽ có nhiều ô riêng — cần Word.
- Toán #13/#14/#16 (¶11): hệ `{` căn giữa thay vì thẳng hàng; dấu chấm sau hệ lên dòng giữa.
- Lý #9/#11: phân số nghiêng `type=skw` đúng, Writer vẽ phân số đứng.
- Lý #10: nguồn không có dấu cách sau object; output đọc thành `ptheo`.
- Kiểu chữ: `m:sty=p` (Lý #16/#17) và Δ/Ω đứng trong nguồn (TN #4, #7, #12, #15, #21) bị Writer vẽ nghiêng;
  ngoặc `m:d` mảnh, dễ đọc thành `|…|`.
- Khoảng cách: Writer tách chữ trong công thức hóa học (`C H₃`, `A l₂O₃`, `c m³`), `S . ABCD`, `2 a`,
  `3,5. 10` (97 object).
- Độ U+2218 (∘) thay cho ký tự vòng MT Extra trong nguồn (Lý #16/#17): nhìn giống nhau.
- Writer render preview nguồn đôi khi mất glyph MT Extra (mũi tên vectơ Toán #11/#69, ⇌ Hóa #37); bản ghi
  text WMF xác nhận nguồn có ký tự đó và output có mũi tên.

### Writer lưu lại/mở lại (headless, không chỉnh)

Lưu 4 output qua Writer thành DOCX rồi render lại (`out/dsmt4-five-exam-acceptance-2026-11-05/writer-resave/`).
Số công thức giữ 19/115/32/100, OLE ¶91 vẫn còn. Text `m:t` khác ở 6 object: **mất/hỏng ở Lý #8 (`C`),
Toán #54 (thêm `left`), Hóa #68 (`>`)**; Hóa #37/#42/#86 mũi tên chuyển từ `groupChr` vào text. 257 còn lại
giữ text; ảnh sau lưu chỉ xem mẫu (Toán tr.1–2, Hóa tr.4), nên để `needs_review`. Đây không phải roundtrip
có sửa ký tự qua UI.

## 3. Ứng dụng và roundtrip

- **Word 16.114.3: not_run.** Không có công cụ UI; không chạy AppleScript nền vì có thể treo chờ quyền.
- **Writer sửa 1 ký tự qua UI: not_run.** Chỉ có lưu lại/mở lại headless ở trên.
- Đề nghị Codex chạy trong Word trên **bản sao** output (không tráo vào output), mỗi ca: xem hiển thị, thêm
  1 ký tự bên trong cấu trúc, save/close/reopen, kiểm ký tự trong `m:t`:
  1. Inline thường: Toán #18 ¶13 `x=63`; Lý #15 ¶97 `J₀=1,00 lít/s`.
  2. Display/căn lề: Hóa #21 ¶73 (block `left`), Hóa #60 ¶129 (`centerGroup`), Toán #46 ¶26 (ô bảng).
  3. Phân số: Toán #32 ¶18 `y=(4x+1)/(x−1)`; phân số nghiêng Lý #9 ¶78.
  4. Chỉ số: Hóa #59 ¶128 `C₆H₈O₆`; Toán #43 ¶22 `x²+y²+z²…`.
  5. Nhãn mũi tên: Hóa #42 ¶93, #37 ¶90, #86 ¶155; mũi tên trống nhãn Hóa #66/#67.
  6. Ô placeholder: Lý #1 ¶28, TN #27 ¶125 / #30 ¶128 — Word có in placeholder không.
  7. `m:sPre` Lý #8 ¶58; `>` đầu công thức Hóa #68 ¶148; `m:d` nhiều `m:e` Toán #54 ¶43 (sửa bên trong ngoặc).
  8. Hệ phương trình Toán #15 ¶11 (căn dòng).
  9. Lone-inline R1: `Hoa_LTT_DN_Lan_03` ¶151 — Word có căn giữa không.

## 4. Hai OLE giữ lại — Li_Nghe_An_L5 ¶91

Đoạn ¶91 có: một run chứa ảnh neo `wp:anchor` (wrapSquare) và `lastRenderedPageBreak`; object #13
(`rId37`, `oleObject13.bin`) `⁶⁰₂₇Co`, object #14 (`rId39`, `oleObject14.bin`) `⁶⁰₂₈Ni`, mỗi object nằm
một mình trong run riêng ngay dưới `w:p`; một OMML gốc `H`; còn lại là chữ, tab và `w:br`. Chính sách hiện tại
giữ cả đoạn vì có OMML gốc. Output đúng là đoạn nguồn nguyên vẹn, render giống hệt.

Hỗ trợ hẹp khả thi về XML: chỉ cho patch inline khi (a) mỗi object là con duy nhất (ngoài `rPr`) của run
riêng nằm trực tiếp dưới `w:p`; (b) không object nào là tổ tiên/hậu duệ của `m:oMath` gốc; (c) sau sửa,
c14n của mọi `m:oMath` gốc, run ảnh neo, chuỗi chữ/tab/br và thứ tự giữa chúng không đổi, nếu không thì
rollback cả đoạn (đã có `editParagraph` trên bản sao). **Nhưng chưa nên bật**: hai công thức là tiền chỉ số
(`mmultiscripts` → `m:sPre`), đúng loại Writer đang làm mất cơ sở (Lý #8) và Word chưa kiểm. Điều kiện trước:
Word hiển thị/sửa `m:sPre` đạt và có cách cho Writer.

Regression cần có: đoạn giống ¶91 (ảnh neo + OMML gốc + 2 object) → OMML gốc byte-giống c14n, ảnh neo giữ,
thứ tự chữ giữ; biến thể object chung run với chữ → vẫn giữ OLE; biến thể OMML gốc lồng trong vùng sửa →
giữ OLE; lỗi chuyển đổi một object → cả đoạn giữ nguyên.

## 5. Đề xuất sửa và test (chưa làm trong audit này)

1. Đối số rỗng: `msup/msubsup` có cơ sở `mspace`/`mrow` rỗng đứng trước một phần tử → `m:sPre` với phần tử
   đó làm cơ sở, hoặc giữ OLE; không xuất `m:e` rỗng. Test: Lý #1, TN #27.
2. `mover(→, mrow rỗng)` → mũi tên thường, không `m:limUpp` rỗng. Test: Hóa #66.
3. `mfenced separators=""` → một `m:e` chứa cả dãy. Test: Toán #54 và một ca `M(2;2;1)`.
4. Hệ `{` (`mtable` một cột) → `m:eqArr` hoặc `m:m` có `m:mcJc` trái. Test: Toán #15.
5. Mũi tên có nhãn: chọn dạng theo kết quả Word trước, sau đó mới xem đến Writer.
6. R1 ở mục 1: chuẩn hóa nội dung rỗng trước khi quyết định block/inline, hoặc giữ OLE.
7. Mọi sửa: test hồi quy đỏ trước, xanh sau; render lại bảng đối chiếu bằng `scripts/contact_sheet.py`.

## 6. Giới hạn đã biết vẫn còn

Writer: mũi tên có nhãn (`groupChr`), `m:sPre`, `>` đầu công thức, `m:sty=p`/chữ đứng–nghiêng, đậm/nghiêng,
khoảng cách (`mspace` bị mml2omml bỏ; Writer tách chữ). Không tuyên bố giữ nguyên phân trang (số trang
giống nhau nhưng vị trí dòng xê dịch). FULL_END_ONLY vẫn `unsupported`. Đối chiếu ký tự WMF, hash và số đếm
chỉ là định hướng, không phải pass.

## Chạy lại

```bash
cd work/claude-five-exam-acceptance
python3 scripts/hash_inputs.py check evidence/hashes_check.json
python3 scripts/structure.py <repo> evidence/structure.json
python3 scripts/wmf_text.py <repo> evidence/structure.json evidence/wmf_vs_omml_text.json
python3 scripts/omml_features.py <repo> evidence/structure.json evidence/omml_features.json
python3 scripts/contact_sheet.py <repo> evidence/structure.json <repo>/out/dsmt4-five-exam-acceptance-2026-11-05/review-sheets
python3 scripts/placement_probes.py <repo> probes
python3 scripts/writer_resave_compare.py <repo> evidence/structure.json evidence/writer_resave_compare.json
python3 scripts/build_ledger.py <repo> evidence
```

Render: `scripts/render_writer.sh`, `scripts/strips.py`. Ghi chú xem ảnh từng object:
`evidence/visual_notes_<đề>.json`. Checkpoint giữa chừng: `work/claude-five-exam-acceptance/checkpoint.md`.
