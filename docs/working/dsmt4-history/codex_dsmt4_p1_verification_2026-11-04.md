# Kiểm chứng độc lập hai P1 — 2026-11-04

Claude đã kết thúc lượt triển khai hai P1. Codex kiểm chứng bản chụp mã riêng tại
`work/codex-p1-validation/candidate-001/`; SHA-256 của toàn bộ mã/fixture trong
bản chụp vẫn khớp working tree khi kiểm chứng. Không có thay đổi mã triển khai
bổ sung từ Codex trong lượt này. Chưa commit.

## Kết luận theo phạm vi

- Đã xác nhận mang `w:sz`, `szCs`, `color`, `u`, `highlight` của run chứa OLE
  sang các run OMML mới, cho inline, block và nhiều object trong một đoạn.
- Đã xác nhận khoảng cách trong `10,0 A` và `HCl khan` không còn bị xoá ở các
  độ rộng được ánh xạ. Run khoảng trắng dùng `m:nor` và `xml:space="preserve"`.
- **Chưa đóng toàn bộ finding theo nghĩa “giữ mọi định dạng run / mọi mspace”.**
  Đậm, nghiêng và vị trí baseline từ run OLE không được sao chép theo lựa chọn
  của Claude; MathML quyết định kiểu toán. Codex chưa xác nhận bằng render các
  ca thật có bold/italic rằng lựa chọn này tương đương preview nguồn.
- Khoảng nhỏ hơn 0,12em, gồm 0,08em, vẫn bị bỏ. Mã coi đó là khoảng tự động;
  chưa có bằng chứng rằng mọi khoảng như vậy đều dư thừa. Các độ rộng lạ và
  ánh xạ kích thước ngoài corpus không được nghiệm thu ở đây.
- Mẫu Hóa vẫn có mũi tên ngắn hơn preview gốc. Hai bản sửa không đủ để kết luận
  đã khớp bố cục hoàn toàn. Corpus tiếp tục `needs_review`.

## Bằng chứng trước và sau

Probe độc lập: `work/codex-p1-validation/check_p1.py`.

- JAR trước sửa: mất toàn bộ năm nhóm thuộc tính trên; chuỗi thành `10,0AHClkhan`.
- JAR bản chụp: giữ năm nhóm thuộc tính; chuỗi thành
  `10,0\u2004A\u2003HCl\u2006khan`.
- Probe còn yêu cầu sao chép `w:b`, vì vậy trường tổng `passed` trong
  `candidate-001/independent/result.json` vẫn **false**. Không bỏ qua hay đổi
  kỳ vọng này để làm xanh kết quả; phần không đạt chính là quyết định bold
  cần được đánh giá riêng. Các kiểm tra spacing và vị trí OMML đều true.

Đối chiếu 32 DOCX trong `work/claude-review/fixed/` với nguồn, ghép đúng thứ tự
2.508 object đã thay bằng OMML:

| Thuộc tính nguồn tường minh | Số công thức có thuộc tính | Số run mới kiểm tra | Sai khác |
| --- | ---: | ---: | ---: |
| sz | 1.034 | 3.797 | 0 |
| szCs | 479 | 2.093 | 0 |
| color, gồm cả đen | 1.419 | 4.909 | 0 |
| underline | 25 | 102 | 0 |
| highlight | 20 | 63 | 0 |

Kết quả: `work/codex-p1-validation/candidate-corpus-properties.json`.
Chạy lại checker bảo toàn của reviewer trên bản P1 cho 0 khác biệt giữa các lá
nội dung ngoài toán và rPr của chúng trong mọi paragraph; log tại
`work/codex-p1-validation/preservation.log`. Các khác biệt đóng gói/metadata POI
đã ghi trong review vẫn là giới hạn của kiểm tra này.

## Kiểm thử và ứng dụng

- Build/test trong bản chụp riêng: **59 Java tests, 0 failures/errors**.
- Python: **104 tests** và **4 workflow tests** qua.
- Modern smoke: 4 qua, 1 ca âm dự kiến, 0 lỗi ngoài dự kiến.
- Generated-output gate: **4/4 package/structure checks** qua.
- Mẫu Hóa tạo từ đề gốc với JAR bản chụp, không sửa đề gốc.
- Word mở và nhận hai công thức native; đã xem đúng đoạn phản ứng. Các run mới
  mang `sz=24` (12pt), nhãn chứa hai khoảng U+2006. Hình quan sát trong chat xác
  nhận mũi tên và nhãn hiện diện. Không tuyên bố đã thử lại chu trình chỉnh sửa,
  lưu và mở lại trên bản P1; chu trình cũ thuộc bản trước P1.
- Writer đã import/render chính DOCX P1 thành PDF và Codex đã xem trang 4 PNG:
  nhãn có lại khoảng cách giữa HCl/khan. Không coi render này là nghiệm thu toàn
  bộ corpus hoặc thử sửa embedded formula trong Writer.

Mã chụp và log: `work/codex-p1-validation/candidate-001/`.

## Kết quả có phiên bản

32 bản P1 được lưu tại `out/dsmt4-p1-2026-11-04/patched/` và manifest tại
`out/dsmt4-p1-2026-11-04/manifest.json`. Bản cũ trong
`out/dsmt4-real-corpus/patched/` giữ nguyên để đối chiếu.

Kiểm tra trực tiếp lại phiên bản mới: 2.535 OMML tổng cộng (27 cũ + 2.508 ứng
viên mới), 109 DSMT4 và 10 OLE khác còn lại. Các hash đề gốc vẫn khớp; văn bản
`w:t` ngoài toán, OMML nguồn, số paragraph và byte embedding được giữ nguyên;
không có OMML lồng trong `w:r`.

## Việc còn lại

1. Làm rõ và kiểm chứng trực quan quyết định bold/italic và khoảng 0,08em;
   không ghi “giữ mọi run properties” hoặc “giữ mọi mspace”.
2. Đối chiếu độ dài mũi tên và khoảng cách nhãn với nguồn sau khi đã sửa cỡ chữ.
3. Xử lý P2 về căn lề block, cổng ký tự vô hình, test rollback/assert và nguồn
   sidecar WMF; chưa được triển khai trong lượt hai P1 này.

FULL_END_ONLY vẫn `unsupported`, không thêm suy luận nội dung hay recovery.
