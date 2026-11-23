# Review độc lập bản sửa letterlike và bàn giao Claude — 2026-11-05

Phạm vi: nhánh FNor mới và hai regression, các artifact lưu Word, snapshot 32 output, số liệu ledger 265 occurrence. Không sửa mã production, fixture, nguồn, output cũ hoặc ledger Claude. Không thao tác UI Word/Writer mới trong lượt review này; không commit/push/merge hay đăng review lên GitHub.

## P1 — Phân loại FNor mới chưa tham gia điều kiện tách run

Vị trí: `src/main/resources/mml2omml.xsl:800`; điều kiện gộp run tại `nndBeforeLim` vẫn chỉ phân biệt mtext/non-mtext và kiểu font, chưa phân biệt normal-text với letterlike-math.

Probe bằng converter/JAR hiện tại:

```xml
<math xmlns="http://www.w3.org/1998/Math/MathML">
  <mtext>x</mtext><mtext>ℝ</mtext>
</math>
```

Cho một run chứa `m:nor` và `m:t=xℝ`: mtext ℝ vẫn bị gộp vào run normal-text của x, dù nhánh FNor mới yêu cầu ℝ là math run. Khi đảo thứ tự, `ℝ` và `x`/`kg` cùng bị gộp vào math run `m:sty=p`; text thường không còn thuộc run normal-text như hợp đồng của bản sửa.

Các artifact Word do Claude lưu (`qa/probes/word-probe-1-saved.docx`, `word-probe-2-saved.docx`) xác nhận letterlike trong m:nor bị lưu thành R/Z/N/l mà không có m:scr; math run thì có m:scr. Chưa chạy UI mới cho chính probe adjacency; kết luận trực tiếp của lượt này là converter vẫn xuất dạng unsafe đã được các probe Word trước đó xác nhận.

Hai regression mới chỉ kiểm letterlike đứng riêng sau mi/mo và mixed text đứng riêng; không kiểm hai mtext liền kề theo cả hai thứ tự. Cần đưa phân loại normal/math vào ranh giới gộp run, giữ normal-text cho text thường và thêm các regression đó trước khi coi bản sửa đã đầy đủ. Mixed text trong cùng một mtext như `xℝ` cũng vẫn là m:nor; phạm vi chưa xử lý này phải được ghi rõ hoặc có cách giữ ký hiệu an toàn.

Trong 51 run thực sự đổi ở snapshot corpus, không có run trộn letterlike với text thường; không suy rằng probe mới đã làm hỏng 48 công thức hiện tại.

Tái lập: `work/codex-dsmt4-letterlike-review-2026-11-05/LetterlikeReviewProbe.java`, `probes.txt`.

## P3 — Số file/run thay đổi trong báo cáo không khớp artifact

Vị trí: `docs/working/claude_dsmt4_acceptance_final_dsmt4-acceptance-final-20261105T1448.md:105`.

Báo cáo nói 13 file / 56 run. Đối chiếu độc lập 32 DOCX với baseline finalization và đọc cả `corpus/report.json` của chính Claude đều cho:

- **12 file** thay đổi, chỉ `word/document.xml`;
- **48 công thức** thay đổi;
- **51 run** đổi nor → sty=p;
- không có thay đổi khác về element/attribute/text ngoài phép đổi run property này (bỏ qua prefix/binding XML không dùng);
- không có run thay đổi trộn text thường với letterlike.

Cần sửa số liệu mô tả; không cần sinh lại output. Script và kết quả: `verify_corpus.py`, `corpus-check.json` trong thư mục review.

## Phần đã xác minh

- Chạy mới `mvn -q -o package`: **95 Java tests**, 0 failure/error/skip.
- Chạy mới Python tests: **116 đạt**; workflow tests **4 đạt**.
- File Word QA đã lưu chứa R + m:scr=double-struck cho toan078, l + m:scr=script cho các mẫu TN; không xem R/l thuần trong XML là mất ký hiệu khi m:scr vẫn còn. Đây là kiểm tra artifact, không phải quan sát UI độc lập mới.
- Ledger có đúng 265 ID duy nhất; cộng lại kết quả và từng tuyến khớp: **219 needs_review / 46 failed**, Word 9 failed, Writer DOCX 7 failed, Math 36 failed. Số liệu đó thuộc baseline, không phải kết quả đã cập nhật sau sửa letterlike.
- Các phép kiểm Word/Writer/Math còn thiếu vẫn chưa được chạy trong lượt review này. Không nâng occurrence thành accepted.

Kết luận: bản sửa có bằng chứng tác dụng trên các mẫu thực tế đã ghi nhận, nhưng cần xử lý P1 về ranh giới run và thêm regression trước khi chốt. Giữ nguyên trạng thái corpus needs_review.
