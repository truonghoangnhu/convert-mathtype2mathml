# DSMT4: quyết định bố cục A6 và B4 — 2026-11-22

Chủ dự án đã chốt hai quyết định:
- **A6:** chấp nhận việc Writer chuyển trang sau khi tách toán tử `mo`; không sửa converter.
- **B4:** không dùng phantom giữ chiều cao (phương án A); chấp nhận phân trang lệch so với bản gốc theo tiêu chí trong [chính sách](../support_scope_policy.md), mục Acceptance.

Bằng chứng chi tiết (scratch, không commit) nằm ở `work/dsmt4-claude-a5-final-native-20261122/`, `work/dsmt4-claude-a6-layout-20261122/` và `work/dsmt4-claude-b4-brief-20261122/`.

## A5 — candidate cuối không tạo lỗi mới

- Candidate cuối (tách `mo`, gom điện tích số và ký hiệu, quan hệ số đầu công thức) được build lại: 150 test đạt.
- Chạy converter trên 32 đề, rồi render native trong LibreOffice 26.8.0.3 (64/64 lượt hợp lệ).
- Dấu lỗi `¿`: old 10 → final 10 (candidate trước 14). Không trang nào đổi số dấu lỗi.
- 160/160 trang; 2.313 công thức native.
- Tập ký tự giống hệt ở 30/32 đề; 2 đề còn lại chỉ khác ở hai cải thiện `bar` và `Ni`.
- Nội dung chuyển trang chỉ ở 8 trang của Toán 02, Long Thành, ThAn.

## A6 — chuyển trang trong Writer do tách `mo`

- Writer: `=` thành toán tử thật nên có khoảng cách quanh dấu. Công thức rộng thêm 0,75–1,7 pt; đoạn sát lề phải rớt thêm một dòng (Codex, 17/11).
- Word không đổi bố cục:
  - Long Thành và ThAn: so glyph và pixel, giống 8/8 trang (Codex, 18/11);
  - Toán 02: kiểm 22/11, cả hai 4 trang, toạ độ công thức trùng nhau.
- So với bản gốc trong Writer, final không lệch xa hơn old:

| Đề | Mốc đúng trang gốc (old → final) | Lệch trung bình (old → final) |
|---|---:|---:|
| Toán 02 | 17 → 17 | 208,4 → 202,5 pt |
| Long Thành | 18 → 19 | 112,6 → 99,2 pt |
| ThAn AG L3 | 18 → 19 | 127,6 → 114,2 pt |

## B4 — chiều cao OMML so với OLE

- **Nguyên nhân** (Codex, 18/11, đo trên Word): phân số inline vẽ ở 8,4 pt so với khoảng 12,5 pt; hàng hệ phương trình cách nhau 12,7–14,2 pt so với 18,5 pt. Khác biệt này có từ converter cũ.
- **Writer, 32 đề:**
  - 166 → 160 trang; 6 đề mất một trang (Hóa Bắc Ninh, Hóa Hà Tĩnh, TN Hóa lần 2, TNCN Đà Nẵng, Toán Tuyên Quang, Toán Chuyên TP HP);
  - 764/826 mốc "Câu N" đúng trang gốc; output luôn dồn lên.
- **Word:** 6 đề đã kiểm giữ số trang, điểm ngắt trang đổi. Chưa đo toàn corpus (checklist B9).
- **Vì sao không dùng phantom:**
  - chỉ khớp được trên 2 hệ phương trình, với tham số chỉnh tay;
  - chưa có cách tính tổng quát cho khoảng 300 công thức cao (231 phân số inline, 25 hệ, 41 tích phân/tổng);
  - Writer bỏ phantom khi nhập (probe 22/11, không lỗi mới);
  - thêm cấu trúc rỗng không có trong nguồn.
- **Cải tiến tuỳ chọn** (không chặn tích hợp): chỉnh khoảng cách hàng của 25 hệ phương trình (checklist B10).
