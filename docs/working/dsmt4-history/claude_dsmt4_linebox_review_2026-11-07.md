# Xác nhận P3 tái lập và review đợt linebox isolation (2026-11-07)

**P3 tái lập đã đóng. Đợt linebox isolation không có P1/P2 và không có lỗi diễn giải số liệu.** Còn 2 điểm P3 nhỏ cho doc và script verify.

Tôi chỉ đọc file. Không chạy shell, test, render hay UI, không sửa file.

## 1. P3 tái lập `measurement-v2.json`: ĐÓNG

Những gì `reproduce_height_measurement.py` làm:
- **Anchors:** tính lại `anchor_comparison` từ PDF nguồn và PDF probe, dùng `measure.compare` (`:29`).
- **Inventory:** dựng lại từ DOCX nguồn và DOCX candidate (`:32-46`): mỗi paragraph có `w:object` ở nguồn, kèm `display_math` (có `m:oMathPara`), `retained_object` và `direct_spacing`.
- **Scope counts:** tính lại ở `:47-50`.
- **So khớp:** assert **toàn bộ dict** bằng `measurement-v2.json` (`:52`) trước khi thêm khối provenance. Có kiểm `changed ⊆ inventory` (`:45`). Không ghi đè file đã có (`:20-21`).

Output khớp với những gì Codex báo:
- `scope_counts` là 40 / 40 / 5 display / 0 unmodified (`measurement-v2-reproduced.json:1177-1182`).
- Có `reference_semantically_identical: true`.
- Có sha256 của DOCX, PDF, `result.json`, file tham chiếu, `measure.py` và chính script (`:1183-1196`).

Giới hạn còn lại (không chặn): tập "changed" lấy từ `result.json` do chính probe ghi, chứ không diff lại `Toan-height-floor.docx` với candidate. Vì vậy "40 changed" vẫn là probe tự báo. Nếu muốn chặt hơn thì diff `w:spacing` giữa DOCX probe và candidate. Điều này không cần để đóng P3.

## 2. Linebox isolation (`codex_dsmt4_linebox_isolation_2026-11-07.md`, `verify_probe.py`)

**Số liệu đã kiểm:**
- Lệch 9.55pt = 36.858 − 27.308.
- Phần giải thích được bởi ảnh 12pt là 8.70pt = 36.858 − 28.158.
- Khoảng cách stem→choice: 21.50 / 16.35 / 21.50 / 15.10, khớp các cặp `yMin` trong bảng.

**Cách diễn giải đã có giới hạn đúng:**
- Ghi rõ là bounding box của text, không phải baseline hay line box.
- Biến thể ảnh 12pt làm méo glyph công thức nên không phải cách sửa, và nó không tái tạo được khoảng cách stem→choice: 15.10 còn xa nguồn (21.50) hơn cả candidate (16.35).
- Mẫu 2 paragraph không được tổng quát hóa.
- Phần Word chỉ là quan sát UI định tính; không có đo PDF và không có sửa/lưu/mở lại.
- Không claim accepted hay full fidelity.
- Kết luận "Writer bỏ qua `w:position`, còn Word dùng nó" có bằng chứng: Writer cho ảnh pixel-identical (đã kiểm ở `verify_probe.py:27-30`), Word là quan sát định tính. Hệ quả là mọi số đo layout dựa trên Writer chỉ mô tả Writer, không suy sang Word được. Doc đã viết đúng tinh thần này ở `:22`.

| Mức | File:dòng | Vấn đề | Cách sửa |
|---|---|---|---|
| P3 | `verify_probe.py:33-48` | Script chỉ so cấu trúc XML của paragraph trong `word-linebox-comparison.docx`. Không kiểm `word/_rels`, các part OLE/ảnh mà `r:id` trỏ tới, và các khai báo trong `[Content_Types]`. Vì vậy việc "Word hiển thị đúng nhóm nào" chưa được gắn với đúng asset. Rủi ro thấp vì cả bốn biến thể lấy từ cùng một package. | Thêm assert mỗi `r:id` trong 8 paragraph đều resolve, và hash part đích bằng part của DOCX biến thể tương ứng. |
| P3 | doc `:32` | Câu "confirmation … still blocked by the reported usage reset" và "not been reviewed by Claude" đã cũ sau lượt này. Doc cũng dùng "His" cho Claude. | Cập nhật: P3 tái lập đã đóng; isolation đã được review đọc-only, không có P1/P2. Thay "His" bằng "Claude's". |

## 3. Phạm vi và chưa kiểm

- Chưa xem `comparison.png`, `word-comparison.png` hay các `bbox.html`.
- Chưa chạy `verify_probe.py` hay script tái lập.
- Chưa đo Word bằng PDF.
- Trạng thái giữ nguyên: needs_review, accepted 0. Writer DOCX arrow/layout vẫn open. FULL_END_ONLY, các safety skip và Lý ¶91 không đổi.
