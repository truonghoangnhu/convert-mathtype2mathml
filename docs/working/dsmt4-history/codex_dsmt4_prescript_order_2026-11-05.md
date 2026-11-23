# DSMT4: sửa thứ tự prescript và kiểm chứng lại — 2026-11-05

## Kết luận và đính chính

Lý Nghệ An #8 mất `C` trong Writer do **converter xuất sai thứ tự phần tử**,
không phải vì OMML đúng mà Writer không hỗ trợ tiền chỉ số. `m:sPre` trước sửa
là `e/sub/sup`; schema yêu cầu `sPrePr? / sub / sup / e`. Tham chiếu primary:
[Open XML SDK schema của Microsoft](https://github.com/dotnet/Open-XML-SDK/blob/main/data/schemas/schemas_openxmlformats_org_officeDocument_2006_math.json),
`CT_SPre`, `Particle.Kind=Sequence`. Bản tải dùng đối chiếu nằm ở
`work/codex-five-exam-fixes/omml-sdk-schema.json`.

Đã sửa cả hai nhánh XSL: chỉ có prescript và có cả prescript/postscript. Test
hồi quy kiểm thứ tự, cơ số C, chỉ số 6/14 và các biến thể postscript. Trước sửa
đỏ: `[sub,sup,e]` nhưng nhận `[e,sub,sup]`; sau sửa toàn bộ **90 test Java đạt**.
Log: `work/codex-five-exam-fixes/prescript-order/{red,green,final-package}.log`.

## Kiểm chứng ứng dụng

- Probe chỉ đổi thứ tự, giữ nguyên cơ số và chỉ số: Writer render đúng ¹⁴₆C.
- Word mở toàn đề Lý mới: câu 16 đáp án B hiển thị đồng vị inline đúng, còn C,
  không placeholder. Chưa đối chiếu toàn bộ phân trang với nguồn Word.
- Writer render toàn đề Lý mới: đã xem trang 2, đồng vị ở câu 16 đủ C và 14/6.
  Lưu toàn đề lại DOCX bằng Writer headless: text của đoạn 58 vẫn `614C`.
- **Word và Writer UI:** bản sao công thức đúng schema được thêm `q`, lưu DOCX,
  đóng và mở lại. Cả hai giữ C và q, Writer hiển thị ¹⁴₆Cq không placeholder.
  Trong phép thử Writer, Mac khóa giữa chừng; sau khi người dùng mở khóa đã
  đọc lại editor và xem ảnh xác nhận bước mở lại cuối cùng.

Bằng chứng: `work/codex-five-exam-fixes/prescript-order/verification.json`,
`li8-order-writer-ui.docx`, `li8-order.docx` (bản Word đã sửa ký tự thử),
`li-full-page2.png`. Không dùng bản có q làm reference nội dung nguồn.
Đây là kiểm chứng đại diện; chưa nghiệm thu mọi prescript trong corpus.

## Output và kiểm tra bảo toàn mới

5 đề: `out/dsmt4-prescript-order-2026-11-05/` — 252 chèn, 13 OLE giữ nguyên,
18 OMML nguồn, tổng 270 OMML output. Ledger mới `acceptance-ledger.json` có
265 occurrence, giữ tiêu chí audit cũ dưới `prior_snapshot_criteria`, bổ sung
bằng chứng mới với phạm vi rõ. Không ghi đè ledger Claude, không dùng số cũ
12 failed để kết luận về bản hiện tại, không đếm các ứng viên là accepted.

32 đề: `out/dsmt4-prescript-corpus-2026-11-05/report.json`:

- 2.417 chèn = 71 block + 2.346 inline; tổng output 2.444 OMML gồm 27 OMML nguồn.
- 200 DSMT4 giữ nguyên và 10 OLE khác. So với snapshot Word-placement, 82 object
  được giữ thêm bởi guard cơ số rỗng và tính nguyên tử của đoạn nhiều object.
- 32/32 tệp qua kiểm bảo toàn; không có khác biệt nội dung/thuộc tính run ngoài
  công thức; nguồn trùng hash đầu vào và inventory trước đó.
- Mọi object được giữ ở snapshot trước vẫn còn nguyên trong output mới; không
  mở rộng 108 skip cũ hay FULL_END_ONLY. Chứng cứ bổ sung:
  `work/codex-five-exam-fixes/prescript-order/corpus-preservation.json`.

## Còn mở

Corpus vẫn `needs_review`. Dấu `>` Hóa #68 vẫn hỏng/mất khi Writer lưu; probe
riêng original/empty-rPr/lit/nor đều chưa khắc phục (`leading-relation/probes.pdf`).
Không đưa thay đổi các property này vào production. Hệ phương trình/mũi tên
có nhãn, font/spacing, bố cục ngữ cảnh gốc và các nhóm nghiệm thu còn lại vẫn
cần kiểm. Hai OLE Lý đoạn 91 vẫn giữ theo chính sách cũ; sửa prescript không
đồng nghĩa đã cho phép sửa đoạn có OMML nguồn và ảnh neo.

Chưa commit/push/merge hoặc đổi Draft PR #4. Các output cũ, nguồn và fixture
không bị thay thế trong đợt sửa này.
