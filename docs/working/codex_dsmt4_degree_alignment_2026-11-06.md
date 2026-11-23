# DSMT4 Celsius and alignment follow-up 2026-11-06

**Đã sửa lỗi nhập độ C của tn022 ở tuyến LibreOffice Math riêng.** Không sửa normalized MathML/OMML Word. Căn hàng hệ toan015 vẫn failed. Không nâng ca nào lên accepted hoặc thay trạng thái PR; chưa commit/push/merge.

## Sửa có phạm vi

Nguồn tn022 chứa `msup(mo '(', mo '°'), mi 'C', mo ')'`. Importer chuyển phần này thành cú pháp StarMath có ngoặc mở nằm trong base script, rồi parse lại thành ký hiệu lỗi. Bản thử giữ `mo` và chỉ đặt `fence=false`/`stretchy=false` vẫn lỗi. Bản thử dùng empty-base trong cặp `mfenced` hoặc prescript có thể render, nhưng thay cấu trúc nhiều hơn nên không tích hợp.

**D giữ nguyên base `(`, số mũ `°`, `mi C`, thứ tự, arity và whitespace; chỉ đổi `mo` của base `(` và dấu đóng tương ứng thành `mtext` literal.** Rule chỉ áp dụng ba sibling liền nhau có đúng hình dạng đó, không thuộc tính/mixed text có nghĩa, trong đúng một hàng phẳng `math/mrow[0]` không có thuộc tính, với root math không có thuộc tính, một mẫu đơn vị và chỉ cho phép W+D. Các ngoặc mo khác phải cân bằng, đơn vị không nằm trong ngoặc khác; các sibling còn lại chỉ là token không style hoặc mspace(width). Từ chối ngữ cảnh lồng, nhiều đơn vị, kết hợp B/L/T và font/style kế thừa. Không áp dụng cho °F, dấu prime, `mi C` có style riêng, ngoặc thiếu, metadata, foreign namespace hoặc mrow trong fence. Lần chuẩn bị lại giữ nguyên output. Candidate vẫn needs_review, application_acceptance vẫn not_run vì CLI chỉ chuẩn bị dữ liệu.

Test đỏ trước sửa: `degree-red.log`; toàn bộ **135 Python test đạt** ở `review-boundaries-green.log`. Có test bảo toàn whitespace, không đổi cặp ngoặc T(K), giữ width mspace và script, cùng các phản ví dụ ranh giới. Không chạy lại Maven/gate vì Java/XSLT/Word không đổi; mốc trước là 102 Java, workflow 4 và gate 4/4, không phải test mới của lượt này.

## Production và UI

- `out/dsmt4-degree-followup-2026-11-06/mathml/`: 265 candidate từ **source_mathml gốc**; chỉ tn022 đổi byte so với `out/dsmt4-math-compat-2026-11-06/mathml/`, 264 file giữ nguyên. `preparation.json` ghi source/hash và report từng ca.
- Nhập MathML production tn022 vào Math object trong ODT thử, render, lưu ODT, render sau mở lại. Xem `production-reopened-1.png`: `T(K)=t(°C)+273` hiển thị dấu độ, ngoặc và mọi ký tự, không có `¿`. Đã xem đối chiếu đoạn nguồn Word ở `work/dsmt4-acceptance-final-20261105T1448/renders/word-segments/TN-THPT-2026__027_PIIICâu2.png`. Không chứng nhận font, spacing hoặc vị trí trong toàn đề chỉ từ hai bản công thức khác ngữ cảnh.
- UI trên bản `ui-tn022-production.odt`: sửa **mn 273 → 274** bằng Math editor, lưu, đóng, mở lại, vào editor. AX/ảnh hiển thị `T(K)=t(°C)+274`; XML có `mn 274` và annotation giữ `"(" ^ ° C ")"`. Đây là thay đổi có chủ ý trên QA, không phải candidate/source.
- Đã hoàn tất quan sát còn thiếu của li002: mở lại toàn `writer-Li_Nghe_An_L5.docx`, xem Câu 8 có `p,q` như phép sửa trước. Ảnh `writer-li002-reopened.png` xác nhận q giữ trong công thức; vấn đề khoảng cách với chữ “khối” vẫn chưa sửa.

Mọi bằng chứng mới và script trong `work/codex-dsmt4-degree-alignment-2026-11-06/`. Không ghi đè output/ảnh/log cũ; không sửa in/, ZIP hoặc fixture.

## Căn hàng là giới hạn được báo rõ

Source toan015 đã có `mtable columnalign="left"`; các probe cũ với thuộc tính ở mtable/mtr/mtd cũng không giữ căn trái trong Math. Mã importer upstream hiện tại tạo matrix mà không đọc columnalign ở các table context; AlignGroup context cũng chưa áp dụng căn lề. Điều này phù hợp với bằng chứng runtime, nhưng không chứng minh mọi bản LibreOffice đều như nhau. [Mã importer LibreOffice](https://github.com/LibreOffice/core/blob/master/starmath/source/mathml/mathmlimport.cxx#L1679), [hướng dẫn nhập công thức](https://help.libreoffice.org/latest/en-GB/text/smath/01/06020000.html).

CLI nay báo `untested`/`table_alignment` cụ thể khi mtable/mtr/mtd có columnalign left/right, không đổi XML hay bỏ thuộc tính. Diagnostic hiện xuất hiện ở toan013–016. Không coi warning này là kết luận mới rằng mọi ca đều failed; ledger cũ chỉ có bằng chứng failed cụ thể cho toan015, các ca khác vẫn needs_review. Test diagnostic đỏ trước sửa: `alignment-diagnostic-red.log`.

Không tích hợp bộ sinh StarMath, padding giả hoặc ảnh để che giới hạn này. Tuyến thay thế muốn giữ căn trái bằng annotation/native ODT cần được thiết kế và kiểm chứng riêng; hiện không thuộc phạm vi production đã chốt.

## Trạng thái nghiệm thu

35/36 lỗi nhập/render Math trong ledger cũ nay có sửa có phạm vi; còn căn hàng toan015. Điều đó không có nghĩa 35 công thức đạt mọi tiêu chí của Word/Writer/Math. Ledger gốc giữ nguyên; overlay mới nối tiếp overlay trước và giữ toàn bộ finding Word/Writer, font/spacing/phân trang và UI chưa chạy. FULL_END_ONLY unsupported; safety skip và OLE cũ giữ nguyên. Corpus vẫn needs_review.

Review Claude ở `claude_dsmt4_degree_review_2026-11-06.md` đã hoàn tất trên snapshot 132-test: phát hiện hai Medium về ngữ cảnh quá rộng và path có thể lệch sau B/L. Codex thêm phản ví dụ đỏ trước sửa, thu hẹp như mô tả trên, chạy D sau mọi thay đổi cấu trúc và thêm close_path. Toàn bộ135 Python xanh; 265/265 payload hiện tại vẫn trùng byte với bộ đã render/UI. Các guard cuối do Codex kiểm, chưa có vòng Claude thứ hai. Diagnostic table_alignment có chủ ý chỉ bao phủ columnalign left/right ở table/row/cell; không tuyên bố là inventory mọi giới hạn căn lề của importer. Mixed/metadata vẫn nhận warning toàn tài liệu và giữ nguyên byte, không phân loại markup trong annotation như presentation đang dùng.

`current-preparation.json` là report sau sửa review; `preparation.json` và ảnh/log trước đó giữ nguyên. Overlay nối tiếp suy ra accepted0 / needs_review252 / failed13 / unsupported0, chỉ cập nhật35 lỗi Math đã kiểm và giữ mọi finding Word/Writer khác; đây không phải audit nghiệm thu mới265.

Audit đọc thêm về ranh giới inline trong32 nguồn tìm thấy88 object DSMT4 đứng ngay trước chữ không có space trong XML;62 trong số đó đã được thay ở snapshot Word cuối. `inline-boundary-audit.json` là inventory rủi ro, không phải62 lỗi đã xác nhận. Hai ca p,/p trong Lý không có mspace trong sidecar và prose kế tiếp không có space đầu; chưa tự thêm ký tự hoặc mở một policy giữ OLE mới vì cần đối chiếu render riêng.
