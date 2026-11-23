**Kết luận:** Không thấy lỗi High. D có 2 vấn đề Medium (phạm vi ngữ cảnh rộng hơn phần đã probe, và path báo cáo bị lệch), cộng vài điểm Low. Riêng phần sửa tag thì đúng: idempotent, giữ nguyên base, độ, `mi C`, tail và số phần tử con. Mình chỉ đọc code, không chạy gì. Kết quả review này không có nghĩa là đã chấp nhận (acceptance) cũng như không có nghĩa DSMT4 đã xong.

## Issues

**M1 — D chạy ở cả những ngữ cảnh chưa probe** (`prepare_libreoffice_mathml.py:182-188`, `:238-239`)
"Mrow trần" ở đây chỉ có nghĩa là bản thân mrow không có attr (`:103`). `visit` đi vào mọi phần tử con, nên D vẫn chạy với mrow nằm trong `mfrac`, base hoặc script của `msub`/`msup`, `munderover`, `msqrt`/`mroot`, `mtd>mrow`, `menclose`, và `mstyle` có `mathvariant`/`scriptlevel`/`displaystyle` (thuộc tính kế thừa không được kiểm tra). Nó cũng chạy khi một row có nhiều lần `(°C)`, hoặc khi đi kèm W/L/T/B. Mới chỉ có tn022 (một row cấp trên) được render.
→ Nên giới hạn D ở `math/mrow[0]` (hoặc wrapper của W) và chỉ khi tổ tiên không có attr. Các trường hợp còn lại thì `note('D', …)` thay vì rewrite.

**M2 — Path của D lệch khỏi `candidate_tree`** (`:118`, thứ tự gọi `:187-188`, chèn L ở `:228`)
D ghi `msup[i]` trước khi B hoặc L sửa cùng row:
- `<mrow><mo>=</mo><msup>(°)</msup><mi>C</mi><mo>)</mo></mrow>`: báo cáo ghi `msup[1]`, nhưng trong candidate là `msup[2]` (L chèn `mrow` vào index 0).
- `|a_b| = t (°C)`: báo cáo ghi `msup[5]`, thực tế là `msup[3]` (B gộp 3 node thành 1).

D là rule duy nhất ghi path tới cấp node con nên chỉ D bị ảnh hưởng. Cách sửa: gọi `explicit_fences` trước, rồi tính path của D sau khi L/T chạy xong (hoặc ghi path theo node rồi resolve ở cuối). Đổi thứ tự D/B là an toàn vì hai mẫu không chồng lên nhau.

**L1 — "Matched close" chỉ là kề nhau, không kiểm tra cân bằng** (`:106-117`)
Một row như `( t (°C) )` hay `(°C))`, có ngoặc thừa hoặc thiếu ở chỗ khác, vẫn bị rewrite cặp này. Ngoặc còn lại giữ là `mo`, nên cách LO ghép cặp ngoặc có thể thay đổi; trường hợp này chưa probe. Nên thêm guard: các `mo` `(`/`)` khác trong cùng row phải cân bằng, nếu không thì note.

**L2 — Bản ghi change chỉ có path của `msup`** (`:118-119`)
Bản ghi không có path của `mtext ")"` (vị trí `i+2`). Nên thêm `close_path` để audit được cả hai node bị đổi.

**L3 — Note `table_alignment` hẹp hơn giới hạn thực tế của LO** (`:173-177`)
- Không note `maligngroup`/`malignmark`/`groupalign`. Đây đúng là phần `SmXMLAlignGroupContext` bỏ qua.
- Không note `mlabeledtr`, `rowalign`, hay `columnalign` đặt qua `mstyle`.
- `right` cũng bị note dưới câu "left-alignment probe failed" dù `right` chưa được probe.

**L4 — Input mixed hoặc có metadata làm mất note căn chỉnh** (`:265-269`)
Nhánh này ghi đè `untested`, nên các bảng `columnalign="left"` trong đó không được báo.

**L5 — Thiếu test** (`tests/test_prepare_libreoffice_mathml.py:242-313`)
Chưa có test cho:
- W+D (`math` chứa thẳng 3 node)
- L+D, B+D (sẽ lộ ra M2)
- 2 lần `(°C)` trong một row
- D trong `mfrac`/`msub`/`mtd>mrow`/`mstyle` có attr (M1)
- assert path ở test đầu (`:242`)
- `columnalign="right"`, nhiều giá trị, `maligngroup`

Ngoài ra, các case `semantics`/`xmlns=""` (`:284-285`) dừng ở guard toàn tài liệu (`:265`), chưa hề tới guard riêng của D.

*(Cũ, không riêng D, không audit lại: ET bỏ comment/PI/XML declaration và prefix `m:` khi reserialize.)*

## D có thể rewrite một phần hoặc rewrite case chưa probe không?
- **Trong một lần match: không bao giờ rewrite một phần.** Cả 3 node được kiểm tra trước, rồi 2 tag mới được đổi cùng lúc, giữa đó không có nhánh nào thoát ra.
- **Ngoặc lệch cặp: có thể.** D đổi cặp kề nhau dù phần còn lại của row không cân bằng (L1).
- **Ngữ cảnh chưa probe: có.** D chạy được ở mọi mrow không nằm trong mfenced, kể cả lồng sâu (M1). Corpus hiện tại (264 file không đổi) không có case nào như vậy, nên rủi ro chỉ đến từ input mới.
- **Không fire, không báo (no-op an toàn):** `mi mathvariant="normal">C`, `℃`, `°` dạng `mi`/`mtext`, `mo` có khoảng trắng hoặc attr, D trong mfenced. Đáng lưu ý: DSMT4 hay xuất C đứng dạng `mathvariant="normal"`, nên tn022 có thể không đại diện cho các file khác.
