# DSMT4: sửa ranh giới run letterlike, chờ Claude review

Đã sửa finding P1 bằng cách dùng chung `m:IsLetterlikeMtext` cho FNor và điều kiện gộp run. Hai token mtext khác loại normal/math không còn bị gộp. Regression kiểm x → ℝ/ℤ/ℕ/ℓ → kg, gồm cả hai ranh giới; trước sửa tạo 1 run thay vì 3, sau sửa giữ đúng từng loại.

Với ký hiệu nằm trong cùng một mtext trộn text thường như `xℝ`, chưa có phép tách giữ khoảng trắng đã kiểm chứng. Vì Word lưu ký hiệu trong m:nor thành chữ thường, cổng OMML nay từ chối các run m:nor bật chứa ℝ/ℤ/ℕ/ℓ; workflow giữ nguyên OLE/package, báo failed kèm lý do. Không thay đổi MathML/HTML; không thêm ký tự hoặc đoán cách tách. Regression thật đi qua converter và patcher với 4 mixed token kiểm package output trùng byte nguồn. Đây là bảo toàn khi chưa hỗ trợ, không phải giải mã thành công mixed text.

Đã sửa P3 về số liệu trong báo cáo Claude: đúng là 12 file, 48 công thức, 51 run; không sửa artifact gốc.

Kiểm chứng mới trong `work/codex-dsmt4-run-boundaries-2026-11-05/`:

- `red.log`: cả 2 regression thất bại đúng lý do trước sửa.
- `green.log`: `mvn -q -o package`, 97 Java tests đạt.
- Python 116 tests, workflow 4 tests đạt; gate 4/4 (`gate.log`).
- Chạy lại 32 đề vào `out/dsmt4-run-boundaries-2026-11-05/corpus/`. So với output letterlike của Claude, toàn bộ tập part và nội dung canonical từng part trùng nhau; không tăng số object vá hay mở rộng safety skip.
- Word 16.114.3: mở QA `word-run-boundaries.docx` gồm ℝ, x+ℝ, ℝ+x, ℝ+kg. Sửa nhãn văn bản đầu đoạn thành QA để buộc Word serialize, lưu, đóng, mở lại: đã xem cả 4 biểu thức còn ℝ; XML lưu R + m:scr=double-struck, x/kg vẫn m:nor. Không sửa ký tự bên trong công thức ở probe này; không chứng nhận bố cục đề gốc. Chỉ đóng file QA của đợt này.
- `verification.json` ghi kết quả và hash file Word sau lưu. Ảnh UI đã xem nằm trong tool trace của chat.

Không commit/push/merge hoặc đổi Draft. Các vấn đề Writer DOCX, Math và nghiệm thu 265 occurrence vẫn còn như ledger của Claude. Không thay ledger baseline hoặc tăng accepted. FULL_END_ONLY vẫn unsupported. Bản sửa này đang chờ Claude review độc lập khi có credit.

## Chỉ thị review cho Claude

Review read-only trên ROOT hiện tại, không checkout/worktree/reset/stash, không sửa mã hoặc input/output/fixture. HEAD chưa chứa các sửa local. Đọc báo cáo này, `codex_dsmt4_letterlike_review_2026-11-05.md` và chính sách hỗ trợ.

Tập trung `src/main/resources/mml2omml.xsl` (FNor, IsLetterlikeMtext, nndBeforeLim), `MathmlContent.hasOmmlRunContent`, thông báo từ chối của DocxMathPatchMain, và hai regression mới. Tìm phản ví dụ gộp token, mất khoảng trắng, khác font/namespace hoặc nhận nhầm normal-text unsafe. Kiểm điều kiện m:nor bật/tắt và package được giữ khi mixed token bị từ chối. Đối chiếu log corpus và Word, không coi XML/test xanh là nghiệm thu ứng dụng toàn bộ. Không cần audit lại 265 BIN hoặc render toàn corpus khi không có thay đổi mới. Bàn giao finding có mức độ và ca tái hiện, hoặc ghi không có finding quan trọng trong phạm vi này. Không tuyên bố DSMT4 hoàn tất.
