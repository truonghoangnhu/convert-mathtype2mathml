# Kiểm chứng tiếp sau bàn giao P2 trong Word

Codex đã review bản bàn giao Claude và chạy độc lập 80 test Java, 106 test
Python, 4 test workflow, gate 4/4 và corpus 32 đề trước khi áp dụng 18 tệp
vào working tree của `feature/dsmt4-migration-fidelity`. Chưa commit/push.
Bằng chứng lần đó: `work/codex-p2-validation/verification-summary.json`.

## Lỗi còn lại được phát hiện bằng Word

Mở bản P2 thực của `Toan-So-GD-Tuyen-Quang-lan-1.docx` bằng Word 16.114.3:
đoạn 183, 186 và các đoạn công thức đứng riêng vẫn bị căn giữa. XML có
`w:jc="left"` và `m:oMath` trực tiếp dưới `w:p`, không có `m:oMathPara`.
Word vẫn hiển thị chúng theo kiểu display; vì vậy inline fallback của P2
không đủ để giữ căn lề. Writer đã giữ căn trái ở bản đó.

Thử trên bản sao, chỉ bọc sáu công thức đứng riêng căn trái bằng
`m:oMathPara` với `m:oMathParaPr/m:jc="left"`: Word hiển thị căn trái; Writer
headless cũng render căn trái. Không thay nội dung công thức hay `w:pPr`.
Đây là kiểm chứng một ca thực, không phải nghiệm thu tất cả kiểu căn lề.

## Sửa tiếp và hồi quy

- Đoạn chỉ có object, bố cục đơn giản: đặt justification toán học tường minh
  từ căn lề nguồn. `center` thành `centerGroup`, trái/mặc định trái thành
  `left`, phải thành `right`; `both` dùng `left` như dòng cuối chứa một ảnh.
  Nhánh phải và `both` có test XML, chưa có nghiệm thu render riêng.
- Đoạn có indent, numbering, bidi, frame hoặc xung đột style chưa giải quyết:
  giữ OLE, ghi `needs_review` trong chẩn đoán `OTHER_UNSAFE_MODEL`. Không dùng
  inline fallback cho đoạn đứng riêng, không chèn ký tự đệm vô hình.
- Chỉ có một object nằm trong đoạn có nội dung khác vẫn dùng inline theo
  chính sách an toàn cũ; không mở rộng 108 safety skip trước đó.
- Hai test hồi quy mới đã đỏ trên mã P2 trước sửa; sau sửa, cả 82 test Java
  đạt với `mvn -q -o package`. Những test P2 từng khẳng định inline fallback
  được cập nhật theo hành vi Word quan sát được.
- Modern generated-output gate đạt 4/4, không lỗi cấu trúc hoặc package.

Trong Word, mở mẫu một công thức thực lấy từ đoạn 186 và do CLI mới chuyển,
đưa con trỏ vào equation, thêm `q`, lưu, đóng và mở lại. Word nhận lại
`qh(x)=f(x)-g(x)` là equation native và giữ căn trái. XML sau lưu có một
`m:oMath`, `m:jc="left"`, ký tự `q` trong `m:t`, không có chữ body ngoài toán.
Việc sửa này chỉ áp dụng lên bản thử ở `work/`, không sửa đề gốc hay output
corpus. Mẫu thử này có ký tự thêm cố ý, không phải bản chuyển đổi để sử dụng.

## Corpus hiện tại

Output mới: `out/dsmt4-word-placement-2026-11-04/`; các output cũ vẫn giữ.

| Chỉ tiêu | Kết quả |
| --- | ---: |
| Công thức chèn | 2.499 |
| Block / inline | 71 / 2.428 |
| Block centerGroup / left | 54 / 17 |
| OMML nguồn / OMML output | 27 / 2.526 |
| DSMT4 giữ lại | 118 = 1 unsupported + 117 safety/review skips |
| OLE khác giữ lại | 10 |
| Unresolved theo CLI cũ | 11 |
| Discovered / scanned / unscanned object | 2.627 / 2.627 / 0 |
| Tệp đạt kiểm tra bảo toàn cấu trúc | 32 / 32 |

Chín skip mới đều ở `Hoa_Bac-Ninh_L1`, đoạn 94, 126, 149, 250, 262, 304,
340, 354, 387; đều có `firstLine=283`. Toàn bộ đoạn nguồn của từng ca này
được giữ nguyên. Hai ca 126/304 chứa nhãn TCVN3 sai trong sidecar nên hiện
không còn bị thay bằng chữ sai; lỗi decoder/font encoding vẫn chưa được sửa.

32 hash nguồn không đổi và khớp inventory trước đó. Kiểm tra toàn bộ 2.526
OMML output với bản nền cùng commit: không khác nội dung. Chín chênh lệch
về số công thức là các object vừa giữ lại, không phải mất công thức nguồn.
Số `unresolved` của CLI không bao gồm các safety/review skip; không dùng nó
để kết luận chỉ còn 11 công thức cần xem.

Bằng chứng có thể chạy lại nằm trong `work/codex-post-p2/`: log đỏ/xanh,
`formula-content-audit.json`, `additional-retained.json`, `modern-gate.log`.
Corpus report mới có chín `equation_content_differs` khi so với baseline:
đây là chín phương trình giữ OLE; audit bổ sung xác minh từng đoạn nguyên vẹn.

## Giới hạn còn mở

Corpus vẫn `needs_review`. FULL_END_ONLY vẫn `unsupported`. Chưa nghiệm thu
hiển thị/chỉnh sửa/mở lại cả 32 đề trong Word/Writer, chưa kiểm tra lại tương
tác Writer cho đợt này, và không tuyên bố giữ nguyên phân trang. Các giới hạn
mũi tên Writer, bold/italic và khoảng cách nhỏ vẫn còn. Chưa xác định được
danh sách 5 đề tại thời điểm kiểm tra ngày 2026-11-04. Ngày 2026-11-05,
người dùng đã cung cấp ZIP; [đối chiếu payload từng object](./dsmt4_five_exam_reconciliation_2026-11-05.md)
đã xác định đúng bộ 265 và đóng phần kiểm kê. Nghiệm thu nội dung/ứng dụng
của bộ này vẫn mở.
