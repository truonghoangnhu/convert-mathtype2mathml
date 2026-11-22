# Review delta JSONL `conversion_diagnostics` (chỉ đọc)

**Kết luận: không có lỗi P1/P2.** Có 3 điểm P3 nên sửa và vài chỗ test còn thiếu. Các điểm bạn yêu cầu kiểm tra đều đúng:
- **Không rò số đếm giữa các lần gọi `patch()`:** map được `clear()` ở đầu mỗi lần patch (`DocxMathPatchMain.java:93`).
- **Snapshot không bị sửa ngược:** `PatchSummary` nhận bản sao bất biến (`:178`), và constructor gọn của record sao chép thêm một lần (`:402`).
- **Tương thích ngược:** hai constructor cũ 15 và 14 tham số vẫn còn và truyền `Map.of()` (`:405-431`).
- **Chi tiết phân loại có lý do từ chối:** lý do được đưa vào chuỗi `"failed: OMML conversion …: OMML rejected: <reason>"` (`:329`, `:335`).
- **Ngữ nghĩa đếm theo lần thử:** đúng như đã thống nhất. Với đoạn có nhiều object, vòng lặp dừng ở object lỗi đầu tiên (`:262-269`), nên chỉ có 1 lần đếm.

## Phát hiện

**P3-1: Thứ tự key trong JSONL thay đổi giữa các lần chạy** — `DocxMathPatchMain.java:178`, `:402`, `DocxToHtmlCli.java:17`, `:271`
- `Map.copyOf` bỏ thứ tự chèn của `LinkedHashMap`. Với từ 2 key trở lên, thứ tự duyệt của map bất biến (`MapN`) được xáo ngẫu nhiên theo mỗi JVM, và `ObjectMapper` mặc định không sắp xếp key.
- Ví dụ: một tài liệu có cả `normal_text_symbol_requires_review` và `missing_script_base`. Hai lần chạy có thể ghi ra `{"a":1,"b":2}` rồi `{"b":2,"a":1}`. Người đọc JSON theo ngữ nghĩa không bị ảnh hưởng, nhưng so sánh JSONL theo byte hoặc dòng sẽ lệch.
- Bản thân repo đã có tiền lệ dùng thứ tự xác định: `ObjectInventory.java:35` dùng `TreeMap`.
- Đề xuất: trong constructor gọn dùng `Collections.unmodifiableMap(new TreeMap<>(...))`. Test hiện tại chỉ có 1 key nên không bắt được lỗi này.

**P3-2: Ngoại lệ từ converter/normalizer không được ghi vào diagnostics** — `DocxMathPatchMain.java:318`, `:325`, `:331-336`
- Nếu `normalize()` hoặc `convert()` ném `RuntimeException` (ví dụ lỗi XSLT), lần đó vẫn được tính vào `OMML_CONVERSION_FAILED` trong skip breakdown nhưng không có key nào trong `conversion_diagnostics`.
- Hệ quả: tổng `conversion_diagnostics` có thể nhỏ hơn số `OMML_CONVERSION_FAILED`, nên phía đọc không thể coi map này là bảng phân rã đầy đủ.
- Đề xuất: thêm key `conversion_exception` trong `catch`. Cần tránh đếm hai lần, vì `throw` ở `:329` cũng rơi vào cùng `catch` đó. Có thể đánh dấu bằng một cờ, hoặc chỉ đếm khi ngoại lệ không đến từ lệnh `throw` của mình.

**P3-3: Constructor chính của record ném NPE khi nhận `null`** — `DocxMathPatchMain.java:401-403`
- `Map.copyOf(null)` sẽ ném NPE, trong khi `objectInventory` đứng ngay cạnh lại được phép null.
- Code nội bộ không bị ảnh hưởng. Chỉ code bên ngoài gọi constructor 16 tham số với `null` mới lỗi.
- Đề xuất: `conversionDiagnostics = conversionDiagnostics == null ? Map.of() : …`.

## Ghi chú (không chặn)
- `DocxMathPatchMain` giờ có trạng thái thay đổi được (`:37`), nên `patch()` không an toàn đa luồng và không reentrant. Hiện tại chưa phải bug, vì CLI tạo instance mới cho mỗi lần chạy (`DocxToHtmlCli.java:246`) và tôi không thấy chỗ nào khác tạo instance. Nếu sau này dùng chung instance, nên chuyển sang một biến tích lũy cục bộ truyền xuống `resolveOccurrence`.
- Bản summary dạng text (`DocxToHtmlCli.java:355-369`) không in diagnostics. Nếu chạy ở mức log SUMMARY mà không bật JSONL thì người đọc sẽ không thấy lý do. Nên thêm nếu muốn đồng bộ với JSONL.
- **Test còn thiếu:**
  - Test ở `DocxMathPatchWorkflowTest.java:30` tạo instance mới cho mỗi token, nên chưa kiểm chứng việc không rò số đếm khi gọi `patch()` nhiều lần trên cùng một instance.
  - Chưa có test cho key `unusable_mathml`.
  - Chưa có test cho đoạn nhiều object (để khẳng định đúng 1 lần đếm).
  - Chưa có test thứ tự key ổn định khi có từ 2 key trở lên.

## Giới hạn
- Chỉ đọc bằng Grep/Read các vùng liên quan. Không chạy build, test hay UI, không sửa file nào.
- Bằng chứng tôi chỉ đối chiếu sơ: `verification.json` ghi 101 test và 0 failures; `final-java-verbose.log:122` ghi 101 test Java đạt, trong đó `DocxToHtmlCliPatchSummaryJsonlTest` 15 test và `DocxMathPatchWorkflowTest` 54 test.
- Tôi chưa kiểm tra lại các con số 116 Python, 4 workflow, gate 4 và corpus 4/32.
- Các kết quả này không phải là nghiệm thu: chưa mở các file DOCX bằng Word và chưa có người duyệt hiển thị thực tế.
