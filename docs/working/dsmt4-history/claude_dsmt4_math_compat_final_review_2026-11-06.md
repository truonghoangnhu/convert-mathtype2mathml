Em chỉ đọc code và bằng chứng. Không sửa file, không build, không chạy test và không xem PDF hay ảnh chụp màn hình. Các con số 125 Python, 102 Java và workflow 4/4 là theo log, em chưa chạy lại: `remaining-cli-green.log` ghi "Ran 125 tests… OK". Đây không phải acceptance tổng thể.

## Đã kiểm chứng trên artifact
- **M1 đã đóng.** Ở `prepare_libreoffice_mathml.py:179-183`, `mrow` là con trực tiếp của `mfenced` chỉ còn được `note`, không còn bị L/T sửa. Test `:83-92` có kiểm tra cả trường hợp chạy lại.
- **M2 đã đóng.** `generate_final.py:9-11` dùng `source_mathml` gốc làm đầu vào và so canonical với `trial(group(baseline))` trên cả 265 công thức. Trong `preparation.json:3-4` có `canonical_changed_count` = `byte_changed_count` = 34, nên 231 công thức còn lại giữ nguyên.
- **Số lần áp rule khớp với tuyên bố 7 / 5 / 1.** C có 15 lần trên 7 ID, I có 5 lần, B có 1 lần, cộng lại 13 ID.
- **Annotation đủ.** `final-production/result.json` có đủ 34/34 annotation, không còn dòng `null`.
- **Oracle `trial()` lỏng hơn production.** Nó không kiểm tra `;`, regex dấu phẩy thập phân, `msub` hay thuộc tính. Vì canonical vẫn bằng nhau, các điều kiện chặt hơn của production không bỏ sót trường hợp nào trong corpus, và trên corpus này oracle cũng không áp rule thừa.
- **Ngữ nghĩa và namespace ổn.** I và B chỉ biến các `mo` mở/đóng ngoặc thành `open`/`close` của `mfenced`; mọi token khác được giữ nguyên, kể cả `2,7`, `;`, `msub`. Phần tử mới đều nằm trong namespace MathML. Thuộc tính `open`/`close`/`separators` không có namespace. Khoảng trắng text/tail được giữ lại (`:107`, `:112`, `:120`, `:124`).
- **Arity ổn.** I thay 5 con bằng 1 con, trên một `mrow` mà toàn bộ nội dung chính là khoảng đó. B thay 3 con bằng 1 con. `mfenced` mới tạo luôn có đúng 1 đối số.
- **Idempotent.** Cả C, I, B đều có test cho lần chạy thứ hai.

## Phát hiện

**L1 (Low): G vẫn kéo theo I/B bên trong dấu ngoặc** (`:153-154`).
- Bản sửa M1 chỉ chặn L/T. Còn `explicit_fences` vẫn chạy trên `mrow` mà G vừa tạo, hoặc trên `mrow` là con trực tiếp của `mfenced`.
- Ví dụ: `<mfenced separators=""><mo>[</mo><mn>2,7</mn><mo>;</mo><mn>3,0</mn><mo>)</mo></mfenced>` cho ra G rồi I, thành `mfenced` lồng nhau. Path báo cáo là `…/mfenced[0]/mrow[0]`, một node không có trong source. Với B cũng tương tự.
- Các ký tự vẫn được giữ nguyên, nhưng ngữ cảnh này chưa được probe trên LO.
- Oracle `trial(group(...))` cũng duyệt cả `mrow` do G tạo, nên phép so 265 công thức không phát hiện được trường hợp này. Corpus hiện tại không dính.
- Đề xuất: khi `parent_name == 'mfenced'` thì không gọi `explicit_fences`, chỉ `note('I/B', …)`. Thêm test tương tự `:83`.

**L2 (Low): `path` là path trên cây đầu ra, không phải trên source** (`:204-205`).
- Sau B, chỉ số của các anh em phía sau giảm 2. Ví dụ `msqrt` ở vị trí 4 trong source sẽ được báo cáo là `…/msqrt[2]`.
- W cũng có vấn đề tương tự từ trước, nhưng B làm lệch thêm.
- Đề xuất: ghi rõ trong report rằng path tham chiếu cây candidate, hoặc tính path trước khi biến đổi.

**N1 (Nit): tên và metadata của C** (`:76`, `:93-94`).
- Rule khớp mọi `msup(mi, +)`, kể cả ngữ cảnh toán học như giới hạn một phía `a^+` hay `ℝ^+`. Về XML thì đây cùng hình dạng với `H^+` đã probe, nên bằng chứng render vẫn áp dụng. Chỉ là nhãn `charge` và docstring "positive charge" gây hiểu nhầm. Nên đổi thành `exponent`.
- Trường hợp `mo +` trực tiếp được bọc lại thành `mrow[mo, mrow]`, còn trường hợp `mrow` có sẵn thì chỉ thêm một con. Report ghi giống nhau cho cả hai, nên khó audit. Nên thêm `shape: wrapped|appended`.

**T (Low): còn thiếu test** cho các ranh giới mà code đã cố ý đặt ra:
- C: base `mi` có thuộc tính (ví dụ `mathvariant="normal"`), `msup` có thuộc tính, và exponent có khoảng trắng do pretty-print.
- I: input pretty-print (kiểm tra `inner.text`/`fence.tail` vẫn được giữ), `;` bị thay bằng `,`, điểm mút là số nguyên như `[2;3)`, và `mrow` có 4 hoặc 6 con.
- B: trường hợp `|e_c|=` không có vế phải (`len == 4`), `msub` có `mn` làm chỉ số dưới, và cặp `|…|` không nằm ở đầu hàng.
- Test cho L1.
- Vòng lặp ở `:132` và `:147` chưa dùng `subTest`.

Không có lỗi chặn. Việc tn022 (dấu độ) và toan015 (căn hàng) vẫn hỏng đã được ghi nhận; em không coi đó là kết quả đã được chấp nhận.
