# Review cuối: helper `>` nhiệt độ (Java) và rule V (vectơ, tuyến Math), 2026-11-07

**Không có P1.** Không có lỗi P1/P2 trong mã của cả hai thay đổi. Có **một P2 về bằng chứng** và một số khoảng trống test P3. Tôi chỉ đọc file: không chạy test, render hay UI, không sửa file nào. Review đã chạy xong, không bị chặn vì thiếu credit.

## Helper `groupLeadingTemperatureComparison` (`XmlBeansOmmlInjector.java:574-612`)

Không có finding chặn. Những gì tôi đã kiểm:
- **Phạm vi:** chỉ chạy cho inline mới, vì được gọi trong `keepInlineObjectTogether` (`:556`). Block và native không đi qua đây; test `:1725-1727` xác nhận block không có `m:d`.
- **Điều kiện khớp:** đúng 3 con phần tử. Phần tử đầu là `m:r` có text đúng `>` và không có `nor`/`lit` (`:579-585`). Phần tử giữa là `sSup`, chỉ được chứa `e`/`sup`/`sSupPr`, mỗi loại không lặp (`:588-593`). Base là chữ số ASCII, sup là `°`, phần tử cuối là `C`. `mathRunText` từ chối run có hai `m:t` hoặc có con lạ (`:626-643`).
- **Bảo toàn nội dung:** chỉ chuyển nguyên node run `>` vào `m:e` của một `m:d` có `begChr`/`endChr` rỗng, đúng thứ tự schema. Không thêm ký tự, toán hạng hay `m:e` rỗng; test `:1722` kiểm điều này.
- **Không làm hỏng paragraph khi lỗi:** helper chạy trên node đã import, trước `editParagraph`.
- **Định dạng run:** `carryRunFormatting` chạy sau và đệ quy vào cả run nằm trong `m:d`.
- **Kho dữ liệu:** inventory chỉ có hoa068 khớp dạng này.

## Rule V (`prepare_libreoffice_mathml.py:111-149`, `:431-443`)

Không có finding chặn. Những gì tôi đã kiểm:
- **Thứ tự chạy:** gate mixed/metadata chạy trước (`:412`). V chạy **sau** `_adapt`.
  - Với dạng tại `:106`, W bọc root và G gom các đối số của `mfenced`. Lá được xác minh trên chính cây đã adapt, nên annotation khớp đúng presentation được lưu.
  - Không rule nào khác của `_adapt` có thể kích hoạt với dạng này: L/T và I/B không chạy bên trong fence, và không có `msup`.
- **Grammar:**
  - thuộc tính so khớp chính xác: `accent="true"`, `open="("`, `close=")"`, `separators=""`;
  - mọi lá đều không được có thuộc tính hay con; tên vectơ là đúng một chữ ASCII; `mo` bắt buộc là `→`;
  - mỗi tọa độ: tùy chọn `-` hoặc `−`, rồi số nguyên `0|[1-9][0-9]*`; đúng 3 tọa độ, ngăn bởi `;`, không dư token (`:147`);
  - text trộn, kể cả NBSP, bị từ chối (`:121-123`).
- **Tương đương token:** chuỗi lá của presentation trùng 1:1 với chuỗi trong command; phép đổi duy nhất là `−`→`-`.
- **Chạy lại:** output có `semantics` nên đi vào nhánh metadata và giữ nguyên byte (test `:112-114`).
- **Bằng chứng:** chỉ có 2 `mover accent="true"` trong 265 candidate (toan011, toan069), khớp với "đổi 2/265". Saved command trong `ui-verification.json:53,62` khớp grammar.

## Findings

| Mức | File:dòng | Vấn đề | Tái lập / cách đóng |
|---|---|---|---|
| **P2 (bằng chứng)** | `out/dsmt4-vector-followup-2026-11-07/mathml/` (hoa037, hoa042, hoa066, hoa067, hoa086, toan053, toan054) | Bài học của toan011 là "không có lỗi parse" không có nghĩa là đủ nội dung. Bảy ca này còn chứa `mover` không accent (mũi tên có nhãn) hoặc `munderover` (tích phân/giới hạn). Thư mục closeout không có bằng chứng mức nội dung cho tuyến Math của chúng; kết quả `pass` cũ cũng không phải là chứng nhận ngữ nghĩa trên snapshot hiện tại. | Render 7 file headless. Trích text/glyph từ PDF và kiểm có code point mũi tên (U+2192/U+21CC…), text nhãn trên/dưới và cận tích phân, không chỉ là "không có ¿". Ghi theo từng ca. Nếu thiếu thì ghi `failed`, không vá rộng. |
| P3 (test V) | `tests/test_prepare_libreoffice_mathml.py:105-125` | Thiếu các phản ví dụ: root có `display="block"`; `mi` hoặc `mo →` có thuộc tính (`mathvariant`, `stretchy="false"`); `mover` có thuộc tính thêm; dấu `+` đầu hoặc `- -`; bộ 2 tọa độ; `separators=","`; NBSP; bọc `mstyle`. Mã hiện tại đã từ chối các ca này, chỉ là chưa có regression. | Thêm các subTest. Thêm ca dương: input đã có `mrow` bọc sẵn và `mfenced` chỉ có một `mrow` (W/G không chạy), assert toàn bộ cây presentation bên trong `semantics` bằng cây trước khi bọc, không chỉ kiểm `mo →` (`:111`). |
| P3 (report) | `prepare_libreoffice_mathml.py:441-443`, `:415` | Change record của V thiếu `annotation_priority_measured_on` (A có). Khi chạy lại, report ghi lý do "mixed namespace or metadata", dễ đọc nhầm là input lạ. | Thêm field; tùy chọn ghi lý do riêng cho output đã có annotation A/V. |
| P3 (test Java) | `DocxMathPatchWorkflowTest.java:1706-1747` | Chưa test việc giữ định dạng run: object run có `w:color`/`w:sz`, assert run `>` bên trong `m:d` có cùng `w:rPr`. Chưa test tuyến multi-object. Chưa test `m:t` có khoảng trắng (`" > "` phải bị từ chối). | Thêm 2–3 ca. |
| P3 (artifact) | `ui-verification.json:60` | Bản QA đã sửa `vectors-ui-edited.odt` nằm trong thư mục output `out/dsmt4-vector-followup-2026-11-07/`, không ở `work/`. | Loại file này khỏi mọi phép so hash/đếm snapshot; lần sau đặt bản QA vào `work/`. |

**Probe limUpp bị loại** (`work/dsmt4-next-batch-2026-11-06/checkpoint.md:3`): quyết định loại là đúng. Writer có cải thiện vai trò nhãn, nhưng Word UI cho mũi tên ngắn, không co giãn, tức Word bị hồi quy. Không đề xuất thay `groupChr` dùng chung khi chưa có bằng chứng fidelity của Word.

## Phạm vi và chưa kiểm

- **UI:** bằng chứng UI gồm 6 lần sửa trên Math/ODF đứng riêng và 1 lần trên ODT nhúng trong Writer. Không có Word UI mới, không có full layout, không có roundtrip DOCX.
- **Writer full render:** 4 đề có chuyển đổi bị reflow (Toán reflow nhiều), CN trùng pixel. Đây là bằng chứng layout, không phải nghiệm thu.
- **Tôi chưa kiểm:**
  - chưa chạy Python 143, Java 116 hay gate;
  - chưa xem PNG/PDF hay nội dung các ODF/ODT trong `qa-packaged`;
  - chưa so cây presentation của toan011/069 với snapshot trước.
- **Trạng thái không đổi:** accepted 0; failed total hiện tại chưa xác lập; FULL_END_ONLY vẫn unsupported; các safety skip cũ và Lý ¶91 giữ nguyên; không commit/push/merge/PR.
