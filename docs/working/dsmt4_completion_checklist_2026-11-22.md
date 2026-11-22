# Checklist hoàn tất DSMT4 — 2026-11-22

**Trạng thái:** chưa hoàn tất. Corpus vẫn `needs_review`, accepted = 0.
- PR #4 đang mở, không còn ở Draft. CI xanh chỉ áp dụng cho commit `467370f`.
- Working tree còn 136 thay đổi chưa commit: 16 file `src/main`, 4 `src/test`, 3 `scripts`, 4 `tests`, 102 file trong `docs/working`.
- Các bản sửa mới nhất của converter vẫn chỉ nằm trong scratch.

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
| B9 `[ ]` | Đo số trang trên **Word** cho 28 đề có công thức chuyển đổi (nguồn và output), theo tiêu chí của B4 | Mới có 6 đề trên Word: giữ số trang, điểm ngắt trang khác. Cần quyền điều khiển toàn màn hình để xuất PDF | Có bảng số trang Word cho 28 đề; đề nào mất trang được ghi cụ thể |
| B10 `[ ]` | (Tuỳ chọn, không chặn) Chỉnh khoảng cách hàng của 25 hệ phương trình cho gần MathType (A+) | Codex 18/11: xử lý phần lớn chênh lệch của hệ, còn thiếu ~8 pt; chưa có quy tắc tổng quát | Có quy tắc từ dữ liệu nguồn, test đỏ → xanh, đo trên Word |
| B7 `[ ]` | Công thức quá rộng và phân trang toàn đề sau box `noBreak` (toan086 đã đạt trên probe) | `codex_dsmt4_nobreak_2026-11-06.md` | Toàn bộ 4 đề có DSMT4 không còn công thức bị ngắt hoặc tràn lề |
| B8 `[ ]` | Các lỗi Word đã thấy ngày 05/11, chưa có quyết định | `claude_dsmt4_acceptance_final_…T1448.md` | Mỗi mục có quyết định sửa hoặc ghi giới hạn |

Chi tiết B8:
- ⇌ có nhãn không giãn (giới hạn của Word);
- mũi tên mẫu rỗng thành `→` ngắn (có đổi sang `⟶` không);
- `S.ABCD` hiện thành `S. ABCD` (tách run `.` với `m:nor`);
- phân số và tích phân inline bị thu nhỏ;
- font Cambria Math thay cho Times New Roman.

## C. Writer và LibreOffice

| # | Việc | Ghi chú | Xong khi |
|---|---|---|---|
| C1 `[ ]` | Đối chiếu lại các mục Writer DOCX đã báo ngày 05/11 với output sau khi tích hợp A | Đã báo: hoa068 hiện `¿` và mất `>` khi lưu; mũi tên có nhãn bị dẹt; hệ toan015 lệch hàng; các run 12/11 về leading relation và alignment có thể đã xử lý một phần | Mỗi mục được đánh dấu đã sửa, giới hạn đã chấp nhận, hoặc còn mở, kèm render |
| C2 `[ ]` | Lệnh `prepare_libreoffice_mathml.py` (hiện là W/L/T/G/C/I/B): đo lại 36 lỗi nhập đã báo ngày 05/11 | Gồm ngoặc `separators=""`, khoảng `[a;b)`, `\|…\|`, `²⁺`, `t(°C)` | Nhập lại 265 ứng viên, 0 lỗi nội dung, hoặc mỗi lỗi còn lại được ghi lý do |
| C3 `[ ]` | **Quyết định:** Writer DOCX là tuyến bắt buộc khi nghiệm thu, hay chỉ ghi giới hạn đã biết | Theo `support_scope_policy.md`, tuyến Writer hiện là MathML → LibreOffice Math | Chính sách được cập nhật |

## D. Nghiệm thu 265 occurrence (bộ 5 đề)

| # | Việc | Xong khi |
|---|---|---|
| D1 `[ ]` | Dựng lại ledger trên output production cuối cùng (sau A và B): render đề đầy đủ bằng Word và Writer, tách đoạn, ghi tiêu chí từng occurrence | Ledger mới; 0 occurrence chưa có trạng thái |
| D2 `[ ]` | Sửa–lưu–đóng–mở lại qua UI, theo **từng nhóm cấu trúc**, trên Word, Writer DOCX và LibreOffice Math/ODT | Mỗi nhóm có ít nhất một mẫu đạt trên mỗi tuyến bắt buộc |
| D3 `[ ]` | Với những gì chưa chạy, ghi `not_run`; không suy rộng từ mẫu | — |
| D4 `[ ]` | Chuyển sang `accepted` chỉ những occurrence đạt đủ nội dung, khả năng sửa, vị trí và hiển thị sau khi mở lại | Đối chiếu tổng accepted + needs_review + failed + unsupported = 265 |

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

- `[ ]` 18 OLE giữ nguyên trong bộ 5 đề (331 trên toàn corpus), gồm hai OLE Lý ¶91. Chốt: giữ nguyên OLE như kết quả hợp lệ, hay cần chuyển đổi tiếp.
- `[ ]` `FULL_END_ONLY` vẫn `unsupported`. Chỉ thay đổi khi có đường giải mã trung thực.
- `[ ]` Ngưỡng chấp nhận cho trình bày: font, khoảng cách, phân trang, chiều cao dòng (liên quan B4).

## F. Đóng project

- `[ ]` Dọn `docs/working` (102 file). Chọn những file cần commit; phần còn lại giữ local hoặc gom lại.
- `[ ]` Cập nhật `docs/dsmt4_migration_acceptance.md`, `docs/support_scope_policy.md`, README theo snapshot cuối.
- `[ ]` Commit, push, chờ CI xanh trên đúng commit cuối.
- `[ ]` Cập nhật mô tả PR #4. Tách rõ phần đã kiểm với phần giới hạn.
- `[ ]` Merge chỉ sau khi D4 và E có kết quả rõ ràng.

---

### Thứ tự đề xuất

1. ~~A5 (audit 32 đề trên bản cuối)~~ — xong 22/11.
2. ~~A6 và B4~~ — đã quyết 22/11 (A6: chấp nhận; B4: không phantom).
3. ~~A7 (tích hợp)~~ — xong 22/11 (chưa commit).
4. B7–B9 (B5–B6 không áp dụng; B10 tuỳ chọn).
5. C1–C3.
6. D1–D4.
7. F.

Các mục A và B chặn D, vì ledger phải chạy trên output cuối cùng.
