# Đối chiếu bộ 5 đề và 265 object DSMT4

Người dùng cung cấp `kiem-tra-word-va-doi-chieu-tay-a3.1.zip` trong Downloads.
Năm phiếu `kiem_tra_tay/phieu_doi_chieu/*.md` ghi rõ tên đề gốc. Cả năm đề
đó có trong `in/`; bộ này không phải `_30_Toan_2025.docx` từng được nhắc trong
audit cũ. Khoảng trống về định danh bộ 265 object nay đã được giải quyết.

SHA-256 ZIP:
`1c3b702ef81391b14e6c895caa0b95465a8ba5fe81cb9e5e49de3b6829f08035`.
Không giải nén hoặc ghi đè đề gốc; chỉ đọc archive và các tệp hiện có.

## Bảng đối chiếu

| Đề gốc trong in | DSMT4 | OMML nguồn | DSMT4 chuyển thành ứng viên | DSMT4 giữ lại | OMML output |
| --- | ---: | ---: | ---: | ---: | ---: |
| Li_Nghe_An_L5.docx | 18 | 3 | 16 | 2 | 19 |
| Thi_Thu_TN_CN.docx | 0 | 15 | 0 | 0 | 15 |
| Toan_TQB_HN_Lx.docx | 115 | 0 | 115 | 0 | 115 |
| TN-THPT-2026.docx | 32 | 0 | 32 | 0 | 32 |
| Hoa_Ha_Noi_L1.docx | 100 | 0 | 100 | 0 | 100 |
| **Tổng** | **265** | **18** | **263** | **2** | **281** |

Đề Công nghệ dùng 15 OMML native, không có DSMT4; 265 DSMT4 thuộc bốn đề
còn lại. Cả 18 OMML nguồn được bảo toàn trong output hiện tại.

## Mức bằng chứng

- Với từng đề, toàn bộ dãy SHA-256 BIN theo thứ tự occurrence trong `in/`
  trùng dãy trong `word/<đề>/4b_qua_odt_da_sua.docx` và
  `word/<đề>/<đề>_oxt_da_sua.docx` của ZIP. Đây là so khớp byte BIN và thứ tự,
  mạnh hơn chỉ khớp tên, số lượng hoặc đa tập ký tự công thức.
- Gắn từng BIN vào kết quả parser thực tế đã có bằng chính SHA-256 BIN:
  **265/265 có status ok, MTEF version 5, application key DSMT7**.
  Không suy khả năng chuyển từ ProgID. Mỗi occurrence có liên kết preview,
  sidecar MathML và hash MTEF riêng trong bảng máy đọc được bên dưới.
- Theo vị trí paragraph và thứ tự object trong source, đối chiếu với
  `out/dsmt4-word-placement-2026-11-04/patched/`: 263 occurrence có OMML ứng viên,
  2 occurrence vẫn là OLE. Phần kiểm tra này không chứng minh ý nghĩa công thức.
- Hai object giữ lại thuộc `Li_Nghe_An_L5.docx`, đoạn 91 (đếm 1-based theo
  `//w:p`), occurrence 13 và 14: `/word/embeddings/oleObject13.bin` và
  `oleObject14.bin`, relationship `rId37` và `rId39`. Đoạn có sẵn một OMML,
  nên thuộc chính sách giữ nguyên đoạn nhiều object lẫn native OMML. Cả đoạn
  source được giữ nguyên, không phải mất công thức hoặc decoder không hỗ trợ.
- Các bản đã trộn có thể đổi thứ tự. Riêng bản học sinh Hóa có 97 BIN khớp
  với 100 occurrence nguồn; không dùng bản đã trộn này làm chuẩn để định danh
  đủ 265. Bản `4b` và bản `oxt` ở trên đều khớp đủ 100 theo thứ tự.
- Các bản đối chứng `4_khu_hoi_2_qua_odt.docx` có ProgID rỗng nhưng vẫn chứa
  các BIN tương ứng; không đếm bằng riêng chuỗi `Equation.DSMT4` trong chúng.

## Bằng chứng và khả năng chạy lại

[Bảng máy đọc được](./dsmt4_five_exam_reconciliation_2026-11-05.json) ghi
đủ 265 occurrence với tên source, SHA-256 source/BIN/MTEF/MathML, paragraph,
ordinal trong source và các bản không trộn, part/relationship, trạng thái
chuyển, cùng danh sách và hash các biến thể trong ZIP. Không kèm nội dung BIN.

Script local chỉ đọc:
`python3 work/codex-five-exams/reconcile.py`.
Kết quả gốc: `work/codex-five-exams/report.json`.
Script kiểm tra tổng 265, hash trước/sau, native OMML không đổi và toàn bộ
đoạn chứa hai object giữ lại. Các hash nguồn và output được ghi theo từng đề.

## Chưa nghiệm thu ứng dụng

`ket_qua_word.csv` trong ZIP có 24 dòng cho các biến thể, nhưng các ô kết quả
Word đều chưa điền; các phiếu đối chiếu cũng còn ô đánh dấu trống. Đây là bộ
kiểm tra và tài liệu đối chiếu, không phải kết quả đã chạy Word/MathType.

Chưa đánh dấu 265 công thức là đúng ngữ nghĩa, hiển thị đúng, sửa và mở lại
đúng trong cả Word/Writer. Những kiểm tra ứng dụng trước đó vẫn chỉ áp dụng
cho các ca đã ghi bằng chứng riêng. Trạng thái corpus và 263 ứng viên trong
bộ này vẫn là `needs_review`; định danh đủ object chỉ đóng bước kiểm kê.
