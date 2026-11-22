Em đã review chỉ đọc. Không sửa file, không build, không chạy test. Các con số 119 Python / 102 Java là theo log anh gửi, em chưa chạy lại.

## Kết luận nhanh
- **Rule G:** ngữ nghĩa MathML đúng. `mfenced` có `separators=""` gom nhiều con vào một `mrow` thì vẫn tương đương bản gốc. Số con của phần tử cha không đổi (vẫn là một `mfenced`). Chạy lại lần hai không đổi gì vì sau khi gom `len(el)==1`. Nhánh mixed/metadata dừng sớm ở `:140-144` nên G không bao giờ chạy vào `semantics`. Whitelist thuộc tính chặn luôn thuộc tính có namespace. Không có lỗi chặn.
- **Telemetry:** đúng như yêu cầu. Nhánh từ chối OMML ở `:326-333` dùng `return` chứ không `throw`, nên `catch` ở `:334-336` chỉ đếm ngoại lệ thật. Test `DocxMathPatchWorkflowTest.java:35` và `:155` so khớp chính xác cả map, nên nếu đếm hai lần thì test sẽ fail. Snapshot ở `:406` là TreeMap bọc unmodifiable, tách khỏi field bị `clear()` ở `:93`, và test `:157-161` đã kiểm tra việc tách này.

## Phát hiện

**M1 (Medium): G tạo `mrow` mới, rồi L/T lại chạy trên chính `mrow` đó**, ở `prepare_libreoffice_mathml.py:81-87` → `:114-115` → `:93-113`.
- Trước khi có G, con của `mfenced` không bao giờ qua L/T, vì `mfenced` không nằm trong `CONTAINERS`.
- Giờ G tạo `mrow` nằm trong `CONTAINERS`, nên L/T/operator_only có thể chạy bên trong dấu ngoặc. Ví dụ `<mfenced separators=""><mo>=</mo><mn>1</mn></mfenced>` ra G+L, còn `…<mi>x</mi><mo>→</mo></mfenced>` ra G+T.
- Ngữ cảnh này chưa được probe trên LO. Ngoài ra `path` của L/T sẽ trỏ tới `…/mfenced[i]/mrow[0]`, là node không có trong source.
- Đề xuất: đánh dấu wrapper do G tạo và chỉ `note('L/T', …)` cho nó. Nếu muốn giữ hành vi cascade thì cần probe LO và thêm test.

**M2 (Medium, evidence): `generate.py:8` lấy `lo_math.prepared_mathml` làm đầu vào, không lấy `source_mathml`** (`ledger.json:146` có field `source_mathml`).
- Vì vậy phép so canonical ở `:11` và kết luận "21 thay đổi / 244 giữ nguyên byte" chỉ chứng minh `prepare(prepared_cũ)`, tức là chuẩn bị lại trên candidate đã prepare. Nó không chứng minh kết quả `prepare(source)`.
- Nhờ M1 không xảy ra trên candidate đã prepare, nên 21 file này không bị ảnh hưởng. Nhưng đường production thật (chạy từ source) thì chưa được kiểm chứng.
- Đề xuất: chạy lại từ `source_mathml` và so canonical với `out/dsmt4-math-fence-grouping-2026-11-06/mathml/*`.

**L1 (Low, evidence): `all21/result.json:4-90` có 22/42 dòng `annotation: null`**, tức cả bản raw lẫn G của toan010…toan069 (11 cặp).
- Với 11 cặp này, phần mở lại chỉ có bằng chứng hình ảnh (`render-2.png`), không có đối chiếu StarMath.
- Chính các ID này trong `result.json:5,13,21` (batch nhỏ) lại có annotation, nên nhiều khả năng đây là lỗi do chạy batch lớn.
- Đề xuất: điều tra hoặc chạy lại theo batch nhỏ trước khi coi 21/21 là đã được đối chiếu annotation.

**L2 (Low): metadata của G ở `:87`** thiếu số con (W thì có `children`). Nó cũng không phân biệt `open`/`close` khai báo tường minh với giá trị mặc định. Đề xuất thêm `children` và đánh dấu giá trị mặc định để dễ audit.

**L3 (Low): `note('G')` ở `:89` bắn cho mọi `mfenced` nhiều con ngoài phạm vi**, kể cả trường hợp separator mặc định (dấu phẩy). Probe `default-sep` cho thấy trường hợp đó LO render đúng, nên các note này chủ yếu là nhiễu. Đề xuất chỉ note khi có `separators` và `strip()` ra rỗng (ví dụ `" "`), hoặc khi `open`/`close` ngoài whitelist. Đó mới là các trường hợp G có thể bỏ sót.

**N1 (Nit): `.strip()` ở `:79-80`** coi NBSP và U+2000–200A là khoảng trắng, trong khi khoảng trắng XML chỉ gồm ` \t\r\n`. Không mất dữ liệu, vì text được chuyển sang wrapper và tail đi theo con. Nên đổi thành `.strip(' \t\r\n')` cho khớp đúng ý "không có text có nghĩa".

**T (Low): thiếu test** trong `tests/test_prepare_libreoffice_mathml.py`:
- G kết hợp L/T theo M1.
- Kiểm tra `path`/`open`/`close` của change G (`:71` hiện chỉ kiểm tra `rule`).
- `mfenced` có text/tail chỉ gồm khoảng trắng (input pretty-printed): vẫn gom và giữ nguyên khoảng trắng.
- `open="|"` mà không có `close`, phải ra không gom.
- W+G cùng lúc, chạy hai lần không đổi.
- `mfenced` nhiều con lồng trong `mfenced` nhiều con, kiểm tra cả hai đều được gom và path đúng.
- Vòng lặp ở `:101` chưa dùng `subTest`.

**J1 (Low, Java):** test `preservesOriginalPackageWhenSidecarHasNoUsableFormula` (`DocxMathPatchWorkflowTest.java:99-121`) không kiểm tra `conversionDiagnostics`. Do đó chưa chốt được input nào rơi vào `unusable_mathml`, input nào rơi vào `conversion_exception` (ví dụ `<math><mi>broken</math>` nếu `normalize()` ném lỗi). Đề xuất assert key mong đợi cho từng input.

**J2 (Nit, Java):** `RuntimeException` ném từ `hasFormula`/`ommlRejectionReason` (`:319`, `:326`) cũng được đếm là `conversion_exception`. Chấp nhận được, chỉ cần ghi rõ trong tài liệu ý nghĩa của key này.

Constructor nhận map null không được xếp là bug, đúng như anh dặn. Không có nhận định nào ở trên là acceptance.
