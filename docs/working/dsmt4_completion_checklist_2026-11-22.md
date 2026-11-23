# Checklist hoàn tất DSMT4 — 2026-11-22

**Trạng thái (cập nhật 23/11):** Ledger 265: **accepted 237** (Hóa 94, Toán 112, TN 22, Lý 9), needs_review 28 (18 OLE giữ + 9 giới hạn trình bày + hoa068 thiếu mẫu Writer), failed 0, unsupported 0.
- PR #4 đã merge vào `main` ngày 23/11 (merge commit `6dcccb1`; CI generated-output gate xanh trên `0fc3eec`).
- 23/11: B7, B9 xong trên Word; D2 Word mới xong 6 mẫu Hóa (màn hình khoá lại khi sang đề Lý). Đã dựng tài liệu Writer nhúng LibreOffice Math từ MathML cho 4 đề: 241 pass, 6 giới hạn trình bày, 18 OLE giữ. Sau đó D4 có 237 accepted (xem D4) và PR #4 được merge.
- 23/11, sau merge: commit `12ed317` sửa hai lỗi review (P1: giữ `w:vanish` của run nguồn trên mọi run của phương trình; P2: từ chối base của chỉ số trên/dưới chỉ chứa run rỗng hoặc ký tự vô hình, kể cả qua `m:box`). Chạy lại 32 đề bằng jar build tại `12ed317` (`work/dsmt4-claude-p12-impact-20261123`): output giống hệt A7 ở mọi phần ZIP, nên ledger 237/28 không đổi. Bản sửa vào `main` qua PR riêng.

Ký hiệu: `[ ]` chưa làm · `[~]` đã làm một phần · `[x]` xong.
Cột **Xong khi** là tiêu chí nghiệm thu, không phải mô tả công việc.

---

## A. Đưa bản sửa converter từ scratch vào production

Candidate mới nhất nằm ở `work/dsmt4-codex-symbolic-charge-fix-20261117/build/`.
Production (`src/main/resources/mml2omml.xsl`) mới có letterlike và box `noBreak`. Chưa có các mục A1–A4 dưới đây (kiểm bằng grep cho kết quả 0).

| # | Việc | Bằng chứng hiện có | Xong khi |
|---|---|---|---|
| A1 `[x]` | Tách mỗi `mo` thành một run riêng, để Writer không biến `= + =` thành `mtext` | `dsmt4-codex-operator-roundtrip-20261116`; Claude review không có P1/P2, chỉ một P3 assertion; P3 đã sửa ở `…-operator-p3-20261116` | Đã port vào production (A7, 22/11) |
| A2 `[x]` | Gom điện tích dạng hậu tố số trong chỉ số trên (`X²⁺`) | `…-charge-fix-20261116`: P1 của blast-radius đã được xử lý | Đã port vào production (A7, 22/11) |
| A3 `[x]` | Leading numeric continuation (3 ca Hà Tĩnh) | `…-leading-fix-20261117` | Đã port vào production (A7, 22/11) |
| A4 `[x]` | Điện tích ký hiệu `M^{n+}` (Hóa Ninh Bình L5 ¶89, ¶94) | `…-symbolic-charge-fix-20261117`: thay đổi so với candidate trước là 2 công thức, giữ nguyên 2.311 | Đã port vào production (A7, 22/11) |
| A5 `[x]` | Chạy lại audit native 32 đề trên **bản cuối** A1–A4 | `work/dsmt4-claude-a5-final-native-20261122` (22/11): build lại đạt 150 test; render mới 64/64 lượt; dấu lỗi old 10 → final 10 (leading 14); 0 trang đổi số dấu lỗi; 2.313 công thức native; nội dung chỉ đổi ở 2 cải thiện `bar`/`Ni`; `verify.py` đạt 23/23 | **Đạt:** 0 dấu lỗi mới trên 32/32 đề. Còn A6 (8 trang chuyển trang ở 3 đề Toán) |
| A6 `[x]` | Quyết định về hồi quy bố cục do A1: ở Toán 02 PII Câu 2d, dấu chấm rớt xuống dòng riêng trong Writer và Câu 3d sang trang 3 | `work/dsmt4-claude-a6-layout-20261122` (22/11): Word không đổi ở cả 3 đề (Toán 02 kiểm mới); Writer chuyển trang do `=` thành toán tử thật (+0,75–1,7 pt); so với bản gốc, final không lệch xa hơn old (Long Thành/ThAn gần hơn) | **Đã quyết (chủ dự án, 22/11): chấp nhận, không sửa converter.** Dấu chấm đứng riêng dòng ở Toán 02 trong Writer ghi là giới hạn hiển thị đã biết; phân trang lệch so với bản gốc để B4 xử lý |
| A7 `[x]` | Tích hợp: port patch và test, chạy `mvn -o package`, Python, workflow, generated-output gate, sinh lại output 32 đề và so với snapshot trước | `work/dsmt4-claude-a7-integration-20261122` (22/11): test port trước, đỏ 17/28 (`red.log`); port XSL, xanh 150/150 Java (`green.log`); Python 144, workflow 4, gate 4/4; output 32 đề tại `out/dsmt4-a7-integration-20261122/corpus/` trùng mọi part với output đã audit ở A5 | **Xong.** Chưa commit; mã nguồn production trùng candidate |

## B. Bố cục trên Word (OLE → OMML làm thấp chiều cao dòng)

Các run 18–21/11 chỉ là chẩn đoán, chưa có thay đổi converter.

| # | Việc | Bằng chứng | Xong khi |
|---|---|---|---|
| B1 `[x]` | Tìm nguyên nhân repagination | `…-word-metrics-20261118`, `…-system-split-20261118`: OMML chiếm ít chiều cao hơn OLE; hệ phương trình Câu 3 giải thích toàn bộ phần chênh dọc | — |
| B2 `[x]` | Chứng minh có thể giữ metrics mà không đổi glyph | `…-rsp-cause-20261119`, `…-strut-20261119`: phantom ma trận trống (bare479 Long Thành, bare480 ThAn) cho sai lệch 0,00 pt tại mọi mốc, giữ nguyên sau save/reopen | — |
| B3 `[x]` | Kiểm khả năng sửa của phantom | `…-semantic-edit-20261120`, `…-no-phantom-control`, `…-same-value-edit`, `…-roundtrip-value`, `…-digit48-20261121`: sửa giá trị giữ đúng; nấc lệch 0,24 pt chỉ xuất hiện ở phép 3→5 và cũng có ở control không phantom, tức là hành vi của Word chứ không do phantom | — |
| B4 `[x]` | **Quyết định chính sách:** dùng phantom giữ chiều cao, hay chấp nhận phân trang lệch | B1–B3; `work/dsmt4-claude-b4-brief-20261122` (22/11): Writer 32 đề có 166 → 160 trang (6 đề mất 1 trang), 92% mốc đúng trang gốc; phantom chưa có cách tính tổng quát và Writer bỏ phantom khi nhập | **Đã quyết (chủ dự án, 22/11): phương án A — không dùng phantom.** Chấp nhận phân trang lệch theo tiêu chí trong `support_scope_policy.md` |
| B5 `—` | ~~Thiết kế phantom cho mọi công thức~~ | Không áp dụng theo B4 | — |
| B6 `—` | ~~Triển khai phantom~~ | Không áp dụng theo B4 | — |
| B9 `[x]` | Đo số trang trên **Word** cho 29 đề có công thức chuyển đổi (nguồn và output), theo tiêu chí của B4 | Mới có 6 đề trên Word: giữ số trang, điểm ngắt trang khác. Bản sao 29 cặp đã chuẩn bị ở `work/dsmt4-claude-b9-word-pages-20261122/` (`exams.json`); 23/11: **Word 149 → 140 trang; 9/29 đề mất 1 trang** (Hóa Bắc Ninh 12→11, Lý TN L2, TN Hóa, TN Hóa lần 2, Toán Tuyên Quang 7→6, Toán 02, Toán Phú Thọ, Toán TQB 4→3, VL Ninh Bình); không đề nào tăng (`word-pages.json`). (Trước đây ghi 28; thực tế 29 đề) | Có bảng số trang Word cho 28 đề; đề nào mất trang được ghi cụ thể |
| B10 `[ ]` | (Tuỳ chọn, không chặn) Chỉnh khoảng cách hàng của 25 hệ phương trình cho gần MathType (A+) | Codex 18/11: xử lý phần lớn chênh lệch của hệ, còn thiếu ~8 pt; chưa có quy tắc tổng quát | Có quy tắc từ dữ liệu nguồn, test đỏ → xanh, đo trên Word |
| B7 `[x]` | Công thức quá rộng và phân trang toàn đề sau box `noBreak` (toan086 đã đạt trên probe) | `dsmt4-history/codex_dsmt4_nobreak_2026-11-06.md`; `work/dsmt4-claude-b7-word-overwide-20261123` (23/11): khung AX của mọi công thức trên Word, 4 đề: **0 tràn lề, 0 công thức inline bị ngắt dòng** | Toàn bộ 4 đề có DSMT4 không còn công thức bị ngắt hoặc tràn lề |
| B8 `[x]` | Các lỗi Word đã thấy ngày 05/11 | `claude_dsmt4_acceptance_final_…T1448.md` | **Đã quyết (22/11, theo uỷ quyền của chủ dự án): cả năm mục ghi là giới hạn đã biết, không sửa converter trong PR này** (chi tiết dưới) |

Chi tiết B8 (quyết định 22/11):
- ⇌ có nhãn không giãn: giới hạn của Word (probe `groupChr` và `limUpp` đều không giãn);
- mũi tên mẫu rỗng thành `→` ngắn: giữ `→`, **không** đổi sang `⟶` (đổi ký tự là suy diễn trình bày ngoài MTEF);
- `S.ABCD` hiện thành `S. ABCD`: giới hạn khoảng cách; sửa cần tách run `.` trong logic gom token, để sau;
- phân số và tích phân inline bị thu nhỏ: OMML không có display-style cho inline (cùng nguyên nhân B4);
- font Cambria Math thay cho Times New Roman: font toán mặc định của Word, chấp nhận.

## C. Writer và LibreOffice

| # | Việc | Ghi chú | Xong khi |
|---|---|---|---|
| C1 `[x]` | Đối chiếu lại các mục Writer DOCX đã báo ngày 05/11 với output sau khi tích hợp A | `work/dsmt4-claude-c1-writer-recheck-20261122` (22/11): hoa068 `>150°C` **đã sửa**; mũi tên có nhãn vẫn cỡ chỉ số và toan015 vẫn lệch cột (**giới hạn**, Word đúng); 10 `¿` còn lại trên corpus là phép trừ tập `ℝ\{0}` ở 5 công thức ngoài bộ 265 (**còn mở**) | Mỗi mục được đánh dấu đã sửa, giới hạn đã chấp nhận, hoặc còn mở, kèm render |
| C2 `[x]` | Lệnh `prepare_libreoffice_mathml.py` (W/L/T/G/C/I/B/D/A/V): đo lại 36 lỗi nhập đã báo ngày 05/11 | `work/dsmt4-claude-c2-lo-math-20261122` (22/11): 265/265 chuẩn bị rc 0; nhập và render 8 trang: 0 `¿`, **36/36 lỗi cũ không còn**; còn mũi tên có nhãn ngắn (hoa037/042/086). Chưa chạy UI sửa–mở lại | Nhập lại 265 ứng viên, 0 lỗi nội dung, hoặc mỗi lỗi còn lại được ghi lý do |
| C3 `[x]` | **Quyết định:** Writer DOCX là tuyến bắt buộc khi nghiệm thu, hay chỉ ghi giới hạn đã biết | Theo `support_scope_policy.md`, tuyến Writer hiện là MathML → LibreOffice Math | **Đã quyết (22/11):** tuyến Writer bắt buộc là MathML → LibreOffice Math; Writer mở DOCX (OMML) phải giữ đủ nội dung nhưng lỗi trình bày (mũi tên có nhãn, căn hàng hệ, ¿ của `ℝ\{0}`) ghi là giới hạn đã biết. Đã ghi vào `support_scope_policy.md` |

## D. Nghiệm thu 265 occurrence (bộ 5 đề)

| # | Việc | Xong khi |
|---|---|---|
| D1 `[x]` | Dựng lại ledger trên output production cuối cùng (sau A và B): render đề đầy đủ bằng Word và Writer, tách đoạn, ghi tiêu chí từng occurrence | Ledger mới; 0 occurrence chưa có trạng thái |
| D2 `[~]` | Sửa–lưu–đóng–mở lại qua UI, theo **từng nhóm cấu trúc**, trên Word, Writer DOCX và LibreOffice Math/ODT | Mỗi nhóm có ít nhất một mẫu đạt trên mỗi tuyến bắt buộc |
| D3 `[x]` | Với những gì chưa chạy, ghi `not_run`; không suy rộng từ mẫu | `ui_edit_reopen_final_output = not_run` cho 265 |
| D4 `[~]` | Chuyển sang `accepted` chỉ những occurrence đạt đủ nội dung, khả năng sửa, vị trí và hiển thị sau khi mở lại | Đối chiếu tổng accepted + needs_review + failed + unsupported = 265 |

D1 (22/11): `work/dsmt4-claude-d-ledger-20261122/` dựng lại 265 dòng trên output A7 từ ledger 05/11 cộng bằng chứng C1/C2 và quyết định B8/C3. Output: 247 OMML + 18 OLE giữ (5 mới do `INLINE_SPACING_REQUIRES_REVIEW`). Kết quả: accepted 0, needs_review 265, failed 0 (05/11: 219/46). Hết `failed` vì lỗi đã sửa hoặc được ghi giới hạn, **không** vì đã nghiệm thu. D4: chưa occurrence nào đủ bằng chứng accepted.

D2 (23/11): **Word** sửa–lưu–mở lại trên output cuối đạt **17/17 mẫu** (`work/dsmt4-claude-d2-ui-20261123`), phủ đủ 13 nhóm cấu trúc; Word chỉ chuẩn hoá `−`→`-`, `′`→`'`, `ℓ`→script `l` (hiển thị không đổi). **Writer (tài liệu đề thực, LibreOffice Math nhúng)** đạt **16/16 mẫu** (`work/dsmt4-claude-d4-writer-ui-20261123`): công thức sau mở lại đúng bản sửa, 231 công thức khác không đổi; phủ 12/13 nhóm — thiếu quan hệ đầu công thức (hoa068 không chọn được bằng Navigator khi điều khiển nền). Tuyến Writer DOCX không bắt buộc (C3). LibreOffice Math/ODT tách riêng: 12 ca cũ.

D4 — tài liệu Writer (23/11, `work/dsmt4-claude-d4-writer-doc-20261123`, người dùng chọn dựng tài liệu thay vì nới tiêu chí): 4 đề gốc mở trong Writer với `MathTypeToMath=false`; mỗi OLE (khớp byte và rId với đề gốc, 265/265) có output Word là OMML được thay bằng đối tượng LibreOffice Math chứa MathML đã chuẩn bị (247, trùng byte C2); 18 OLE giữ nguyên. Headless trong tài liệu: 247/247 công thức bằng bản nạp riêng, không đổi sau lưu–mở lại (vòng 2 cũng ổn định), còn as-char ở đúng đoạn, văn bản và thứ tự khung trùng bản gốc; 18 trang vẫn 18. Đã xem cả 18 trang trước/sau: không lỗi nội dung, chồng lấn hay tràn lề. `writer_in_document`: pass 241, known_limitation 6 (hoa037/042/086 mũi tên có nhãn không giãn; hoa066/067 mũi tên template thành `→` ngắn; li009 phân số nghiêng vẽ thành phân số đứng), retained_ole 18. Sau đó (23/11): soát từng trang Word trên bản đã Word lưu–mở lại cho Toán, TN, Lý (mọi công thức đúng; toan022/027/090 có khoảng trống sau `S.` = giới hạn B8); XML mọi công thức của 4 bản Word lưu giữ nguyên. **D4: accepted 143** (Toán 112, TN 22, Lý 9). needs_review 122 = Hóa 100 (chưa soát hiển thị Word, màn hình khoá giữa chừng) + 18 OLE giữ + li009 + toan022/027/090. Quy tắc và cột mới: `work/dsmt4-claude-d-ledger-20261122/README.md`. Sau khi mở khoá: soát xong Word đề Hóa → **accepted 237**, needs_review 28 (18 OLE giữ; hoa037/042/066/067/086 mũi tên; li009; toan022/027/090; hoa068 thiếu mẫu Writer — Navigator không chọn được khi điều khiển nền).

Các nhóm cấu trúc ở D2:
- công thức hóa học inline;
- công thức trong ô bảng;
- công thức block (căn trái và căn giữa);
- mũi tên có nhãn;
- quan hệ ở đầu công thức;
- `sPre`;
- phân số, phân số nghiêng, căn;
- hệ phương trình;
- tích phân;
- vectơ;
- prime;
- điện tích;
- ℝ và ℓ.

Hiện có từ ngày 05/11:
- Word: 14 mẫu, cộng 2 mẫu trên output đã sửa;
- Writer DOCX: 2 mẫu;
- LibreOffice Math: 2 mẫu.

## E. Phạm vi và chính sách cần chốt

- `[x]` 18 OLE giữ nguyên trong bộ 5 đề (331 trên toàn corpus), gồm hai OLE Lý ¶91. **Chốt (22/11):** giữ nguyên OLE là kết quả bảo toàn hợp lệ theo hợp đồng thất bại (`needs_review`/`unsupported`), không phải conversion; không mở rộng chuyển đổi trong PR này.
- `[x]` `FULL_END_ONLY` vẫn `unsupported`. Chỉ thay đổi khi có đường giải mã trung thực.
- `[x]` Ngưỡng chấp nhận cho trình bày: theo "Layout tolerance" (B4) và giới hạn B8 trong `support_scope_policy.md`. Số trang Word toàn corpus vẫn chờ B9.

## F. Đóng project

- `[x]` Dọn `docs/working`: 24/11 gom 105 ghi chú từng vòng (claude_*/codex_*/dsmt4_*) vào `docs/working/dsmt4-history/` có mục lục; sửa đường dẫn tham chiếu trong README và docs; không xoá file nào.
- `[ ]` Cập nhật `docs/dsmt4_migration_acceptance.md`, `docs/support_scope_policy.md`, README theo snapshot cuối.
- `[x]` Commit, push, chờ CI xanh trên đúng commit cuối (`0fc3eec` xanh trước khi merge PR #4).
- `[x]` Cập nhật mô tả PR #4. Tách rõ phần đã kiểm với phần giới hạn.
- `[x]` Merge chỉ sau khi D4 và E có kết quả rõ ràng (PR #4 merge 23/11, merge commit `6dcccb1`).
- `[x]` Đưa bản sửa P1/P2 (`12ed317`) vào `main`: PR #5 merge 23/11 (merge commit `c28235d`, CI xanh trên `f933cca`).

---

### Thứ tự đề xuất

1. ~~A5 (audit 32 đề trên bản cuối)~~ — xong 22/11.
2. ~~A6 và B4~~ — đã quyết 22/11 (A6: chấp nhận; B4: không phantom).
3. ~~A7 (tích hợp)~~ — xong 22/11 (chưa commit).
4. ~~C1–C3, B8, E, D1, D3~~ — xong 22/11.
5. ~~B9, B7~~ — xong 23/11. ~~Tài liệu Writer cho D4~~ — dựng và kiểm headless 23/11. ~~D2 Word 17 mẫu, Writer trong tài liệu 16 mẫu~~ — xong 23/11. ~~Soát hiển thị Word Toán/TN/Lý, D4 lần 1 (143 accepted)~~ — xong 23/11. ~~Soát Word đề Hóa~~ — xong (accepted 237). **Còn mở:** mẫu Writer cho hoa068. 24/11 thử lại trên bản sao mới: Navigator Next/Previous, Tab/Shift+Tab đều nhảy qua đối tượng này (067 ↔ 069/070), cây Navigator không nhận nhấp khi điều khiển nền; cần quyền toàn màn hình để nhấp đúp trực tiếp (chưa được cấp).
6. ~~F: merge chỉ sau D4~~ — PR #4 merge 23/11. PR #5 (P1/P2) merge 23/11; `docs/working` đã gom 24/11.

Các mục A và B chặn D, vì ledger phải chạy trên output cuối cùng.
