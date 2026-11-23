# Review lượt 2: inline root, mapping ledger, probe alignl (2026-11-06)

**Không có P1 hay blocker.** Có 3 điểm P2 nên sửa trước khi dùng mapping làm cơ sở gắn bằng chứng, hoặc trước khi đưa annotation vào production. Tôi chỉ đọc file. Không chạy test, render, UI hay shell; không sửa file nào.

## (a) Sửa inline root: đạt

- `XmlBeansOmmlInjector.java:532-533` nay chặn cả CDATA có nội dung. Đúng với ca mất text `"lost text"` (test `:1741`).
- Test `:1781-1791` có đủ các assert đã đề xuất. `assertSame(documentElement, math.getParentNode())` đúng với cách `xmlText()` bọc kết quả trong root `xml-fragment`.
- Ca phần tử `w:r` nằm trong `oMathPara` (`:1740`) đi đúng nhánh throw ở `:539`.

Không có finding mới.

## (b) `reconcile_ledger.py` và `current-ledger.json`

Phần cô lập verdict lịch sử đạt. Hàng mới chỉ copy các field định danh (`:76`), verdict cũ nằm riêng trong `historical_review`, `application_verdicts_auto_carried=False`, `current_failed_total=None`. Không thấy verdict cũ lọt vào trạng thái hiện tại.

| Mức | File:dòng | Vấn đề | Ví dụ, cách sửa |
|---|---|---|---|
| **P2 (thiếu guard)** | `reconcile_ledger.py:65`, `:73-74` | Không có gì bảo đảm mỗi hàng ledger trỏ tới đúng một node riêng. `mapped[(pi, rid)] = current` sẽ ghi đè im lặng nếu một paragraph có hai `w:object` cùng `r:id`. Ví dụ: OLE copy-paste dùng chung relationship, hoặc cặp Choice/Fallback trong `mc:AlternateContent`. Khi đó hai hàng ledger trỏ cùng một node hiện tại mà assert `:117` (đếm theo hàng) vẫn qua. Trường `ordinal` của ledger cũng không được dùng. Tôi **chưa chứng minh** corpus có ca này. | Assert `(pi, rid) not in mapped` trước khi gán. Assert 265 hàng trỏ tới 265 node khác nhau (`id(current[2])` cho OMML, `id(node)` cho OLE). Đối chiếu `ordinal` với vị trí slot. |
| P3 | `:27-36`, `:92` | Equation block không có box mới nhưng vẫn được gắn tag `identical_mod_new_box`. Tag này cũng không xác nhận box có mặt: nếu một inline bị thiếu box, nó vẫn được gắn `identical_mod_new_box`. | Tách thành `identical_with_new_box` (inline, box bắt buộc có) và `identical_block_no_box`. |
| P3 | `:24-26`, `:92` | Với block, `sig` chỉ so cây `oMath`, không so `oMathParaPr/jc` nằm ở `oMathPara` bao ngoài. Đổi căn lề display sẽ không bị phát hiện. | So luôn `oMathPara` cha của equation block. |
| P3 | `:92`, summary | 3 hàng `expression_or_properties_changed` không ghi id hay loại thay đổi. | Ghi id (có thể là toan078, tn017, tn020) và diff cụ thể, ví dụ chỉ khác letterlike. Không suy đoán. |
| P3 | `:101-109` | Bằng chứng UI của tn019 và toan086 được hard-code. Không hash `qa/TN-THPT-2026-ui-edited.docx`, không kiểm `q` nằm trong đúng slot math. Lưu ý thêm: Word thường đánh số lại `r:id` khi lưu, nên với file Word đã lưu phải map theo (paragraph, slot), không theo `rid`. | Thêm sha256 và kiểm theo slot. |
| Ghi chú | `qa/~$*.docx` | Còn 5 file khóa Word trong `qa/`. | Đóng Word và không đưa các file này vào artifact hay commit. |

Mapping nguồn → output theo vị trí trong paragraph là đúng. Có các assert sau: số paragraph bằng nhau, số slot trong mỗi paragraph bằng nhau, native không đổi, OLE giữ lại cùng `rid` và cùng bytes embedding. Các assert này fail ồn ào nếu cấu trúc lệch. Chỉ riêng trường hợp trùng key ở hàng P2 là lọt im lặng.

## (c) Probe alignl Toán#15

| Mức | File:dòng | Vấn đề | Ví dụ, cách sửa |
|---|---|---|---|
| **P2 (bằng chứng)** | `alignment_probe.py:76-79`, `math-alignment-probe/result.json` | Các kết quả Codex báo (control hiển thị `x=9`; khoảng lệch x-trái giữa 3 hàng 5.6pt ở baseline, 0pt khi có alignl) **không có trong bất kỳ file nào** của `work/dsmt4-joint-followup-2026-11-06/`. Script không đo gì; `result.json` chỉ có `annotations_after_save`, còn lại là hai ảnh PNG. Ngoài ra chưa kiểm presentation MathML **sau khi lưu**. Đó mới là dấu hiệu LO tạo lại cây từ annotation, tức là có thể thay nội dung. | Lưu vào `result.json` cho từng item và cả hai PDF (render đầu và sau mở lại): bbox glyph đầu mỗi hàng, text từng hàng, chuỗi lá presentation sau lưu so với nguồn. Riêng control phải ghi presentation sau lưu là `1` hay `9`. |
| **P2 (nếu đưa vào production)** | `alignment_probe.py:34-38` | Grammar của serializer cho phép ô bắt đầu hoặc kết thúc bằng toán tử, và hai toán tử liền nhau. Ví dụ `<mtd><mo>=</mo><mn>1</mn></mtd>` sinh ra `alignl { = 1 }`, StarMath báo lỗi parse. Vì annotation quyết định nội dung hiển thị, LO sẽ hiện ký hiệu lỗi thay cho nội dung presentation đúng, tức là **mất nội dung mà không báo**. Hai `mn` liền nhau (`2`,`5` → `2 5`) cũng mơ hồ. toan015 không gặp các ca này. | Chỉ nhận ô dạng `operand (binop operand)*`. Unary `-`/`−` chỉ được ngay đầu ô hoặc ngay sau `=`. Cấm `mn`/`mn` liền nhau. Bỏ `len(table)==3` hard-code. Thêm test phản ví dụ. |
| Ghi chú | `:39-42` | Kiểm whitespace và thuộc tính đã chặt; `mfenced` và `mtable` khớp dict chính xác. | Giữ nguyên. |

## Checklist trước khi đưa annotation (rule A) vào `prepare_libreoffice_mathml.py`

1. Lưu kết quả đo đỏ→xanh (bbox, text từng hàng) và control vào JSON, cho cả lần render đầu lẫn sau khi lưu và mở lại.
2. Sau khi lưu, chuỗi lá presentation từng hàng phải bằng nguồn, gồm `−` và thứ tự token. Nếu khác thì không phát annotation.
3. Siết grammar như hàng P2 ở trên, có test phản ví dụ: toán tử đầu hoặc cuối ô, toán tử liền nhau, `mn` liền nhau, `columnalign` center/right/thiếu, thuộc tính lạ, `mtd` lồng cấu trúc, ký tự ngoài whitelist, input đã có `semantics`.
4. Chạy lại adapter trên output cũ phải giữ nguyên byte (đi vào nhánh metadata). Report ghi `rule: 'A'`, `needs_review`, `application_acceptance: not_run`.
5. Chạy candidate production thật (không phải bản trial), sau đó UI Math: thêm `q`, lưu, đóng, mở lại, còn `alignl` và còn `q`.
6. Kiểm riêng toan013, toan014, toan016. Ca nào không đúng hình dạng phải giữ diagnostic `table_alignment`.
7. Không đụng normalized MathML/OMML của Word. Không đổi `lo_row_alignment` của toan015 sang pass trước khi xong các bước 1–5. Accepted vẫn 0.

## Chưa kiểm

Tôi chưa mở `current-ledger.json` ngoài vài dòng grep, chưa xem các PNG/PDF probe, `pagination-comparison.json` hay `TN-THPT-2026-ui-edited.docx`. Chưa xác minh corpus có `r:id` trùng trong cùng một paragraph hay không.
