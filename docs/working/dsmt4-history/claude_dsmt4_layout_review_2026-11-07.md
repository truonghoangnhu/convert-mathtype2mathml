# Review hypothesis "height floor" cho layout Writer (2026-11-07)

**Chưa đủ bằng chứng để đưa height floor vào production.** Floor chỉ bù được khoảng một nửa độ trôi, có chỗ còn vượt quá nguồn. Nó cũng đổi ngữ nghĩa paragraph (atLeast áp cho mọi dòng) mà chưa có bằng chứng nào từ Word. Không có P1. Có 2 điểm P2 về cách đo và diễn giải, cộng vài P3.

Tôi chỉ đọc file; không chạy lệnh, render hay UI, không sửa file. Mọi số liệu dưới đây lấy từ `anchor-review-v2.json` và `height-floor/result.json`.

## Probe thực sự cho thấy gì (Toán, cùng candidate `writer-comparison-2026-11-06`)

| Neo (thứ tự) | Trôi baseline | Trôi probe | Nhận xét |
|---|---:|---:|---|
| Câu 1 trang 1 | −9.55 | −5.65 | Đã có trôi ngay tại/trước Câu 1 |
| Câu 9 trang 1 | −105.8 | −53.65 | Bù khoảng 50% |
| Câu 12 trang 2 | −129.75 | −81.9 | |
| Câu 5 trang 4 | −267.35 | −150.8 | |

Tính theo **chênh lệch khoảng cách giữa hai neo liên tiếp** trên trang 1 của probe:
- Câu 1→2: −7.55
- Câu 2→3: −12.2
- Câu 5→6: −19.2
- Câu 7→8: −9.05
- **Câu 8→9: +3.5**, tức floor **vượt quá** nguồn (baseline ở đoạn này là −4.15).

Như vậy floor vừa bù thiếu vừa bù thừa. Một ngưỡng chung bằng chiều cao OLE lớn nhất không mô tả đúng cơ chế của nguồn. Hóa (−236pt, đổi trang 4 neo) và Lý cũng trôi, nên đây không phải chuyện riêng của Toán.

## Findings về cách đo

| Mức | File:dòng | Vấn đề | Cách sửa |
|---|---|---|---|
| **P2** | `measure.py:16`, summary của probe | `changed_vertical_over_2pt` đếm độ trôi **cộng dồn**. Chỉ cần một dòng sớm lệch là mọi neo phía sau trên trang đều bị đếm. Đọc "18→19" như "floor không cải thiện" là sai: độ lớn đã giảm khoảng một nửa, và chỉ số này cũng che mất chỗ bù thừa. | Báo cáo theo chênh lệch khoảng cách giữa hai neo liên tiếp cùng trang để chỉ ra đoạn nào gây trôi. Giữ tổng trôi chỉ làm thông tin phụ. |
| **P2** | `measure.py:15` | `dy_same_page` sau một sự kiện đổi trang không còn so sánh được. Ví dụ: Câu 10/11 chuyển sang trang 1, nên Câu 12 và Câu 1–3 của phần sau trên trang 2 (−82…−98) bị so với phần đầu trang có nội dung khác. | Chỉ tính chênh lệch khoảng cách trong cùng một đoạn liên tục, không cắt qua neo bị đổi trang; đánh dấu các neo sau ranh giới đổi trang là `confounded`. |
| P3 | `measure.py:11` | Neo lấy `yMin` của chữ "Câu". Nếu cùng dòng có object cao hơn, baseline bị đẩy xuống và `yMin` đổi theo, nên dy trộn lẫn "nội dung phía trên" với "ascent của chính dòng neo". Điều này có thể giải thích −5.65 tại Câu 1. | Đo theo box `<line>` (cả `yMin` và `yMax`), hoặc theo baseline. |
| P3 | `measure.py:10,21` | Regex `\d+[.:]?` bỏ qua dạng `Câu 1)`. Chữ "Câu" trong lời văn tham chiếu có thể tạo neo giả. Cách bind theo cả chuỗi số có thứ tự an toàn khi hai bên khác nhau, vì sẽ từ chối, nhưng không phát hiện được neo giả xuất hiện ở cả hai bên. `next(glob('*.pdf'))` không xác định nếu thư mục có nhiều PDF. | Ghi số neo mỗi trang. Kiểm neo nằm đầu paragraph hoặc ở `xMin` lề trái. Đặt tên PDF tường minh. |
| P3 | `probe_height.py:11-14` | Chỉ sửa paragraph có `w:spacing` trực tiếp với `lineRule=auto`. Paragraph kế thừa spacing từ style bị bỏ qua lặng lẽ, nên không biết 40 paragraph đã sửa chiếm bao nhiêu trong tổng số paragraph có OLE. `atLeast` lấy max đặt cho **mọi dòng** của paragraph, kể cả dòng chỉ có chữ, nên có thể gây vượt. Floor cũng bỏ qua hệ số 1.15 của `auto 276`. | Ghi tổng số paragraph có OLE và số đã sửa. Không dùng probe này làm mô hình production. |

## Các nhóm nguyên nhân có thể (chưa đo)

1. **Chiều cao hộp dòng:** chiều cao dòng có OLE (preview) so với dòng có OMML trong Writer. Có thể có hệ số tỷ lệ của `auto` nhân lên object.
2. **Vị trí dọc/baseline:** `w:position` của run OLE bị bỏ khi chèn OMML (`XmlBeansOmmlInjector`, comment ở `CARRIED_RUN_PROPERTIES`). Hạ thấp object làm tăng descent của dòng nguồn.
3. **Xuống dòng (wrapping):** chiều rộng OMML khác chiều rộng preview làm đổi số dòng của paragraph.
4. **Kích thước viewport:** `v:shape` height/width so với chiều cao math thực tế do Writer vẽ ở cỡ chữ được mang sang (`w:sz`).
5. **Font:** CN trùng pixel và TN phần lớn bằng 0, nên font chữ thường ít khả năng là nguyên nhân. Font và metric bên trong dòng math thì vẫn có thể.

## Bước tiếp theo nên làm (một bước, chỉ đo, không sửa)

**Phân rã theo từng dòng, Toán trang 1, đoạn Câu 1–9** (cả hai bên đều cùng trang, không có đổi trang chen giữa).

**Từ PDF:** dùng các phần tử `<line>` của `pdftotext -bbox-layout` cho source và candidate. Bind dòng theo **chuỗi từ chữ thường (prose)**. Preview OLE trong PDF nguồn là ảnh, không có text, nên không bind theo text của math. Với mỗi paragraph, ghi:
- số dòng;
- `yMin`/`yMax` từng dòng, chiều cao dòng;
- dòng nào chứa math (chèn bằng vùng ảnh ở nguồn, glyph math ở candidate).

**Từ DOCX** (đọc XML, cùng các paragraph đó):
- `v:shape` height/width;
- `w:position` của run OLE;
- `w:sz`;
- `w:spacing` hiệu lực (kể cả kế thừa từ style);
- số OMML và loại inline/block.

**Kết quả cần ra:** gán mỗi phần chênh khoảng cách ở trên (−7.55, −12.2, −19.2, −9.05, +3.5) vào một trong bốn loại: chiều cao dòng, số dòng (wrap), `w:position`, hoặc dòng không có math. Chỉ khi một nhóm giải thích phần lớn chênh lệch *và* có cơ chế khớp với nguồn mới thiết kế probe hẹp cho đúng nhóm đó. Probe đó phải đi kèm đo trên Word, không chỉ Writer.

## Ràng buộc giữ nguyên

- Không đề xuất vá tổng quát chỉ vì số trang khớp. Không thêm khoảng trắng tổng hợp hay phantom; không suy nội dung từ preview.
- Height floor giữ ở dạng `probe_only`. Production không đổi.
- Chưa chạy: đo trên Word, UI, đo line-box, inventory `w:position`, đo các đề khác ngoài Toán.
- needs_review, accepted 0. FULL_END_ONLY, các safety skip và Lý ¶91 không đổi.
