# Đóng nợ review: 2 P2 đo layout và các mục P2/P3 Codex đã xử lý (2026-11-07)

**Không có P1/P2 mới. Cả hai P2 về đo layout và P2 nội dung 7 ca đã đóng.** Còn 1 P3 mới về khả năng tái lập của `measurement-v2.json`, và một câu trong doc Codex cần cập nhật vì nay tôi đã đọc v4.

Tôi chỉ đọc file. Không chạy test, render hay UI, không sửa file. **Tool đọc được PNG**, và tôi đã xem trực tiếp 3 ảnh được yêu cầu.

## 1. Hai P2 về phép đo layout

| Nợ | Trạng thái | Bằng chứng |
|---|---|---|
| **P2: độ trôi cộng dồn bị đếm như lỗi** | **CLOSED** | `measure.py:29-33`: một khoảng chỉ được so khi **cả 4 neo** (trước/sau, nguồn/candidate) cùng trang. Bộ đếm chính là `local_gap_delta_over_2pt` (`:38`); vị trí tuyệt đối được đánh dấu là phụ (`:39`). Số trong doc khớp: 28+28+28+28+22=134 neo, 19+23+24+24+14=104 khoảng so được, 12+4+2+0+12=30 khoảng lệch >2pt, 4+4=8 neo đổi trang. |
| **P2: dy tuyệt đối sau khi đổi trang bị nhiễu** | **CLOSED** | `measure.py:24-25`: cờ `confounded` bật khi có neo lệch trang, và chỉ tắt khi cả hai render cùng sang trang mới tại cùng một neo. Logic này thận trọng: với Toán, cờ vẫn bật từ neo 10 đến cuối. Phép đếm khoảng không dùng cờ này nên không bị ảnh hưởng. |
| P3: ascent của chính dòng neo | CLOSED (dạng giới hạn) | Có ghi `label_yMax` và line box (`:17`); doc `:17` nêu đúng giới hạn. Khoảng vẫn tính từ `yMin` của nhãn, nên phần ascent của dòng neo vẫn nằm trong delta. Đây là giới hạn đã ghi, không phải lỗi. |
| P3: neo giả / binding | CLOSED | Chuỗi neo phải khớp chuỗi `Câu n.` trong XML nguồn (`:46-49`). Chỉ khi không khớp mới lọc theo cột tiêu đề, và kết quả lọc phải khớp chính xác XML, nếu không thì assert dừng (`:51-56`). 5 tham chiếu trong Lý bị loại. |
| P3: chọn PDF không xác định | CLOSED | `single_pdf` assert có đúng 1 PDF (`:7-10`). |
| P3: phạm vi probe | CLOSED về số liệu | `measurement-v2.json:1177-1182`: 40 paragraph có OLE, 40 đã đổi, 5 là display, 0 không đổi. |
| **P3 mới: không tái lập được** | **OPEN** | Không có script nào trong workspace sinh ra `measurement-v2.json` (khối `inventory` / `scope_counts`). `probe_height.py` không tạo hai khối này, và grep không thấy file nào khác tham chiếu tới. Vì vậy tôi không kiểm được cách tính "40/40, 0 bị bỏ do kế thừa spacing". **Cách sửa:** lưu script sinh file, hoặc ghi hash script và lệnh đã chạy. |

Claim trong `codex_dsmt4_layout_investigation_2026-11-07.md` không vượt bằng chứng: height floor bị loại khỏi production, không claim Word/UI, prose trace chỉ là chẩn đoán. Riêng câu ở `:39` ("Claude did not … verify the final v4 implementation") giờ đã cũ, vì phần đọc mã v4 trong bảng trên đã được thực hiện. Đây là chỉnh sửa tài liệu, không phải finding.

## 2. Các mục Codex xử lý sau review closeout

| Nợ | Trạng thái | Bằng chứng |
|---|---|---|
| **P2 nội dung 7 ca** (hoa037/042/066/067/086, toan053/054) | **CLOSED cho tuyến Math đứng riêng** | Đã xem `claude-followup/pdf/page.png` và `rt-pdf/page.png`, hai ảnh giống nhau về hình. Thấy rõ: ⇌ kèm nhãn `t°,p,xt`; → kèm `t°,p` (hoa042); → không nhãn (hoa066, 067); hai → kèm `+O₂,t°` và `+C,t°` (hoa086); ∫ cận 2/0 cùng `f(x)dx=5` và `(2f(x)−1)dx`. Khớp `seven-content-review.json` và `pdf_glyph_counts` (⇌1, →5, ∫2). |
| Vectơ toan011/069 | CLOSED (Math đứng riêng) | `out/dsmt4-vector-followup-2026-11-07/rt-pdf/page.png`: mũi tên trên `u` hiện ở cả hai dòng, `(5;2;−3)` và `(91;75;0)`. |
| P3 test V | CLOSED | `test_prepare_libreoffice_mathml.py:122-131` có đủ các ca từ chối đã nêu: `display`, `mi`/`mo` có style, `mover` có thuộc tính thêm, dấu `+` và `−−`, bộ 2 tọa độ, `separators=","`, NBSP, `mstyle`. `:137-142` có ca dương với input đã chuẩn bị sẵn, assert toàn bộ cây presentation giữ nguyên trong `semantics` và có field mới. |
| P3 report V | CLOSED | `prepare_libreoffice_mathml.py:443` có `annotation_priority_measured_on`. |
| P3 test Java | CLOSED | `DocxMathPatchWorkflowTest.java:1750-1766`: tuyến multi-object (2 inline), run `>` nằm trong `m:d` có `color=123456`, `sz=28`. `:1769-1781`: OMML trực tiếp có `" > "` không bị gom vào `m:d`, text giữ nguyên. |
| P3 artifact QA trong `out/` | CLOSED (bằng ghi chú phạm vi) | `verification.json:26`: inventory chỉ đếm `mathml/*.mathml`; file ODT của QA bị loại ra. |

Ghi chú từ ảnh, **không phải finding**: ở tuyến Math, mũi tên không co giãn theo nhãn (hoa086 rõ nhất), và chữ hóa học hoa042 in nghiêng. Cả hai thuộc fidelity mũi tên có nhãn và font_style, vốn đã ở trạng thái open/needs_review. Bằng chứng 7 ca chỉ chứng minh glyph, nhãn và cận có mặt.

## 3. Còn mở và chưa kiểm

- **Còn mở:** fidelity mũi tên có nhãn trong Writer DOCX; reflow toàn đề. needs_review, accepted 0, failed total chưa xác lập. FULL_END_ONLY, các safety skip và Lý ¶91 không đổi.
- **Chưa kiểm:**
  - chưa chạy Java 118, Python 144, cũng chưa tái hiện 265 byte MathML;
  - chưa đọc toàn bộ `anchor-review-v4.json` và `prose-trace.json` (chỉ đối chiếu số tổng và cờ `selected_prose_sequence_equal`, cả 9 đều true), chưa kiểm số y-level;
  - chưa xem `height-comparison.png` hay ảnh PDF nguồn/candidate toàn đề;
  - chưa có Word/UI cho bất kỳ mục nào ở trên.
