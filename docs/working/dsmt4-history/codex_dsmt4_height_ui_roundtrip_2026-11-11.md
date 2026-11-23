# DSMT4 height controls after editing and reopening

Ngày 11/11/2026. Hai đối chứng tại I.2 của đề Toán được thử độc lập qua Word và Writer trên bốn bản sao riêng. Cả bốn giữ phép sửa `x=5+2t+1` trong hàng đầu hệ sau sửa–lưu–đóng–mở lại bằng UI. Chưa nghiệm thu bố cục: Writer bỏ thuộc tính giãn hàng ma trận khi lưu DOCX, và hệ thấp đi khi Word mở bản đó. Không thay đổi production, không commit/push; corpus vẫn needs_review, không nâng accepted.

## Input và phạm vi

`work/dsmt4-height-ui-2026-11-11/ui-plan.json` ghi bản nguồn và SHA256 trước UI. Đây là bản sao các probe Nov10 từ snapshot Toán cũ đã nêu trong báo cáo line metrics, không phải output mới từ converter hiện tại. `ui-plan.json` là kế hoạch ban đầu (status not_run); kết quả thực nằm trong `ui-observations.json` và các verifier, không sửa lịch sử kế hoạch.

Minimum-line chỉ đổi p11 w:spacing thành line=1148, lineRule=atLeast. Matrix-gap độc lập chỉ thêm m:rSpRule=1 vào bốn matrix ba hàng tại p11. Không gộp hai đối chứng. Màu nền là instrument đo, không đưa vào converter. Chỉ sửa hàng đầu math occurrence13 bằng +1; đây là thử chỉnh sửa chiều ngang nhỏ, không phải test tăng chiều cao, công thức dài buộc xuống dòng hay sát cuối trang.

## Kết quả trực tiếp

| Bản QA | Sau mở lại | Thuộc tính giữ trong DOCX | Dải nền p11 của PDF thực |
|---|---|---|---:|
| Word minimum-line | +1 đúng hàng đầu, ba hàng còn | line1148 atLeast | 37,44 pt |
| Word matrix-gap | +1 đúng hàng đầu, ba hàng còn | cả bốn rSpRule1 | 51,12 pt |
| Writer minimum-line | Commands giữ +1, ba hàng còn | line1148 atLeast | 57,40 pt |
| Writer matrix-gap | Commands giữ +1, ba hàng còn | cả bốn rSpRule bị bỏ | 46,30 pt |
| Writer matrix-gap mở bằng Word, chỉ xem | +1 vẫn có | không lưu lại bằng Word | 37,68 pt |

PDF được xuất từ ứng dụng qua UI sau mở lại: `word-minline-reopened.pdf`, `word-matrixgap-reopened.pdf`, `writer-minline-reopened.pdf`, `writer-matrixgap-reopened.pdf`; bản xem chéo là `writer-matrixgap-word-view.pdf`. Bản xem chéo được sao riêng, hash không thay đổi sau Word mở/xuất. Hai PDF Word lần lượt 4/3 trang; hai PDF Writer đều 4 trang; bản xem chéo Word 3 trang. Số trang không chứng minh đúng phân trang.

Đã xem ảnh ghép `roundtrip-local-comparison.png` tạo từ cả năm PDF: hệ A có +1 và ba hàng, các đáp án B/C/D cùng Câu3 còn hiển thị, không thấy cắt nét hay chồng dòng trong vùng này. Writer-save→Word nhìn rõ hệ ngắn hơn Word-save matrix-gap. Không gán toàn bộ chênh lệch cho duy nhất rSpRule vì Writer còn chuẩn hóa spacing/run khác; kết luận an toàn là hiệu ứng giãn hàng không bền qua tuyến Writer DOCX→Word.

Dải tô không phải chiều cao nét hay toàn bộ line advance. Minimum-line Word có leading ngoài dải tô như đối chứng Nov10; không so 37,44 với 57,40 để suy công thức khác độ cao. Writer vẽ nền trùng hai lần; script deduplicate rectangle giống nhau, không cộng thành hai dòng. Chưa đo lại ink 600dpi sau +1.

## Kiểm chứng và thao tác không thành công

`verify_ui_saved.py` xác nhận bốn DOCX còn 85 paragraph,115 oMath; hàng đầu math13 đúng phép sửa, hai hàng sau giữ; các nguồn Nov10 đúng hash. Delta text các công thức khác khi Word chuẩn hóa được ghi là chẩn đoán, không coi đó là semantic pass toàn tài liệu. `measure_reopened.py` tái tạo crop, số trang/dải nền và kiểm hash bản xem chéo.

Writer: click AX vào nhãn Commands từng rơi nhầm vào body. Thao tác thay toàn nội dung QA trong bộ nhớ đã Undo trước khi lưu; sau đó chọn đúng Object13, Enter vào Commands và nhập trực tiếp tại focus. Bản lưu cuối đã kiểm lại đủ 85 paragraph/115 công thức. Lần Word nhập +1 trước t cũng đã Undo và sửa đúng sau t trước lưu. Không tính các thao tác lỗi này là roundtrip đạt.

Chỉ quan sát vùng I.2/Câu3, không audit toàn bộ trang/công thức, không suy accepted bằng XML, số đếm hay hash. Chưa chứng minh hai quy tắc này an toàn cho công thức cao thêm sau sửa, dài phải xuống dòng hoặc sát cuối trang. Giữ scratch, không áp dụng giãn hàng/line-height chung.

## Review

Claude đã hoàn tất review read-only phần đo Nov10 và helper UNO, không có P1/P2; báo cáo riêng `claude_dsmt4_line_metrics_followup_2026-11-11.md`. Review đó loại trừ các thử UI hôm nay. Script `verify_isolation_export.py` đã bổ sung nguồn tái tạo kiểm geometry cho positive isolation test. Helper scratch dùng listener loopback không xác thực trong thời gian chạy, profile/cổng riêng và kiểm profile trước load; đây vẫn là giới hạn vận hành của helper, không phải cơ chế sản phẩm.

Reviewer Codex độc lập `/root/review_dsmt4` đã đọc bốn DOCX/JSON, đo lại hai PDF matrix-gap và xem crop. Không thấy P1/P2 trong phạm vi chứng cứ hẹp; xác nhận hash bản xem chéo, bốn thuộc tính giữ/bị bỏ và số đo51,12/37,68pt. Reviewer yêu cầu không quy toàn bộ delta riêng cho rSpRule và không gọi +1 là test tăng chiều cao; báo cáo tuân theo hai giới hạn này. Đây không phải lượt Claude review UI.

Bước tiếp theo có ý nghĩa: trên bản sao mới, tăng chiều cao thật bằng phân số trong hàng đầu, đo allocation/ink sau roundtrip; sau đó mới thử công thức dài và vị trí sát cuối trang. Không mở rộng quy tắc matrix-gap chung vì nó đã không bền qua Writer DOCX.
