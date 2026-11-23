# Review lượt 3: rule A (annotation StarMath) trong tuyến LibreOffice Math (2026-11-06)

**Không có P1. Parser, cách sinh annotation và cách tích hợp rule A không có lỗi P2.** Có một P2 về bằng chứng: `measurement.json` chưa chứng minh nội dung render đầy đủ. Tôi chỉ đọc file; không chạy test, render, UI hay shell, không sửa file. Tôi không coi phần verify 265+4 đang chạy là đã đạt.

## Parser `_aligned_assignment_command` (`prepare_libreoffice_mathml.py:53-108`)

**Chuỗi token trong annotation trùng khớp với presentation.** Mọi lá trong `mtd` đều bị đọc thành token, nên không có phần nào của presentation bị bỏ ra ngoài annotation:
- Có con lồng hoặc có thuộc tính thì từ chối (`:78`).
- Có text trộn hoặc tail thì từ chối, kể cả NBSP vì `strip` chỉ bỏ ` \t\r\n` (`:65-68`).
- Regex `[A-Za-z]` và `[0-9]+` chỉ khớp ASCII.

Phép đổi duy nhất là `−`→`-`, và StarMath vẽ `-` thành dấu trừ. Vì hai biểu diễn chứa cùng nội dung, việc annotation được LO ưu tiên (theo đo trên 26.8.0.3) không làm đổi nội dung hiển thị, kể cả trên bản LO có hành vi khác.

**Grammar đúng như mô tả.** Tôi đã lần từng nhánh:
- `= 1` (ký tự `=` thứ hai) bị từ chối.
- Toán tử ở cuối, hai toán tử liền nhau, `mn mn`, `mi mi`, `mn mi mi`, `mi mn` đều bị từ chối.
- `+` đơn ngôi đầu RHS bị từ chối.
- `len(cell) < 3` chặn trường hợp RHS rỗng.

Không có từ khóa StarMath một chữ cái nào có thể bị chèn qua grammar này.

**Whitespace và namespace.** Gate mixed/metadata chạy trước A (`:371`), nên không có phần tử ngoại lai nào lọt vào. Thuộc tính được so khớp chính xác cả dict, nên thuộc tính ngoài namespace cũng bị từ chối. Khai báo `xmlns:tr` không dùng tới (có trong toan015) bị ET bỏ khi serialize lại; việc này vô hại.

**Không chặn mất rule khác (cascade).** Với đúng hình dạng S, không rule nào khác có thể kích hoạt:
- W: root chỉ có 1 con.
- G: `mfenced` chỉ có 1 con.
- L/T và I/B: không chạy bên trong fence.
- C và D: không có `msup`.

Nên việc A return sớm không làm mất thay đổi nào. Khi A từ chối, `_adapt` chạy như trước và vẫn ghi `table_alignment`.

**Input A không xử lý được giữ nguyên.** Các ca bị từ chối vẫn đi qua `_adapt` như cũ. Chạy lại trên output của A sẽ đi vào nhánh metadata và giữ nguyên byte (`:371-375`, test `:38-40`).

## Findings

| Mức | Vị trí | Vấn đề và ví dụ | Cách sửa |
|---|---|---|---|
| **P2 (bằng chứng)** | `math-alignment-probe/measurement.json:6-10, 21-25` | `row_text` của cả hai PDF là `x=2+5`, `y=2+2`, `z=−1−3`, đều **thiếu `t` cuối mỗi hàng**. Có thể bước trích chỉ lấy từ đầu tiên trên mỗi dòng, vì LO chèn khoảng trắng giữa `5` và `t`. Dù nguyên nhân là gì, file này hiện không chứng minh được nội dung render đầy đủ; chỉ `roundtrip.presentation_rows` mới có `t`. | Gom mọi glyph trong dải y của từng hàng rồi so với `x=2+5t`, `y=2+2t`, `z=−1−3t`, cho cả `pdf` lẫn `rt-pdf`. Áp dụng cách trích này cho đợt verify 265+4. Trước khi sửa, không ghi criterion "text từng hàng khớp" là pass. |
| P3 (phạm vi) | `:81-107` | Grammar nhận cả những dạng chưa từng được render: `x = 12`, `x = t`, `x = −t`, `-` ASCII. Token map 1:1 nên rủi ro thấp, nhưng bằng chứng đo mới chỉ có toan015. | Mỗi file corpus thật nào được gắn A phải có hàng render/roundtrip riêng trong kết quả verify trước khi được tính. |
| P3 (report) | `:385-387`; nhánh chạy lại `:372-374` | Change record của A không ghi lại command đã sinh. Khi chạy lại, report ghi lý do "mixed namespace or metadata", dễ đọc nhầm là input lạ. | Thêm `command` (hoặc hash của nó) và `annotation_priority_measured_on: 26.8.0.3` vào change record. Tùy chọn: thêm lý do riêng cho output đã có annotation A. |
| P3 (test) | `tests/test_prepare_libreoffice_mathml.py:42-87` | Thiếu phản ví dụ phía LHS: `<mn>1</mn><mo>=</mo>…`, `<mi>x</mi><mi>y</mi><mo>=</mo>…`, hàng không có `=`, token có khoảng trắng như `<mo> = </mo>`. Mã hiện tại đã từ chối các ca này; chỉ là chưa có regression giữ hành vi. Test nhận (`:81-87`) chỉ kiểm rule, không kiểm command sinh ra, ví dụ `-` ASCII ra `-`. | Thêm 4 ca LHS và một assert so command chính xác. |
| Nit | `:9-14` | Docstring bị chèn giữa câu: "…position. Preparation / A supplies…/ Preparation does not validate…". | Sửa câu. |

## Checklist trước khi tính A vào production

1. Sửa cách trích text từng hàng (P2), rồi chạy lại để có bằng chứng cho toan015 với đủ `t`.
2. Mỗi file được gắn A trong đợt 265+4 phải có hàng riêng ghi: khoảng lệch x-trái về 0, text từng hàng đầy đủ, `presentation_rows` sau khi lưu khớp nguồn, đủ `alignl`. Đặc biệt kiểm toan013, toan014, toan016: ca nào A từ chối phải còn `table_alignment`.
3. Bằng chứng UI hiện chỉ có cho bản standalone #15. Ghi đúng phạm vi đó; không suy ra cho Writer DOCX hay bố cục toàn ODT.
4. `lo_row_alignment` của toan015 chỉ được đổi từ failed sau bước 1–2, và chỉ cho tuyến Math. Writer DOCX vẫn failed. Accepted vẫn 0.

## Chưa kiểm

Tôi chưa mở `ui-verification.json`, ảnh PNG, ledger mới hay log của 265+4. Chưa xem phần sửa mapping (guard, unique, ordinal, block props, slot/hash) ở mức mã, nên không đánh giá ở đây.
