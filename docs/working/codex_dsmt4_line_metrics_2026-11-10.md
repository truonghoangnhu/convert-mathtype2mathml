# DSMT4 line and formula height experiment

10/11/2026. Hai bản thử riêng đã cho thấy phải tách chiều cao công thức khỏi chỗ dành cho dòng. Chưa có quy tắc sửa chung được chứng minh; không sửa production, không commit/push/merge. Corpus giữ needs_review, accepted promotions0.

## Phạm vi và phép đo

Nguồn/bản OMML là cùng snapshot Toán của đợt09/11, sao chép vào `work/dsmt4-line-metrics-2026-11-10/`; `inputs.json` lưu hash. Không phải output vừa sinh từ converter hiện tại. Không sửa in/, ZIP, fixture, output cũ hoặc mở rộng safety skip/FULL_END_ONLY/Lý¶91.

**Word:** không có document session/API bố cục kết nối. Đã thử thêm nền theo85paragraph trên bản sao và xuất PDF bằng chính Word. Native có toàn bộ vị trí chữ PDF khớp bản không tô nền; nguồn OLE bị dịch tích luỹ tới1.92pt. Bản nguồn không tô nền xuất mới vẫn khớp bản09/11. Vì vậy số đo source-shaded bị loại làm chuẩn. Đối chứng khác chỉ thêm vạch biên trái theo paragraph: toàn bộ chữ và hình học chữ trích xuất trong PDF khớp nguồn không biên; không chỉ22nhãn Câu/70nhãn đáp án. `word-border-envelopes.json` lưu85paragraph đã đánh dấu.

Vạch biên/nền được trích từ polygon màu trong PDF, cho **dải được vẽ** của từng dòng/đoạn. KHÔNG phải API nội bộ Word về ascent/descent hoặc toàn bộ line advance. Thử nghiệm min-line phía dưới chứng minh dải tô có thể bỏ qua leading. Riêng hàng I.2 không có before/after và nằm giữa hai đoạn đơn giản cùng trang: dùng khoảng từ đáy dải cuối của thân câu tới đỉnh dải Câu3 để đo phần chiều cao hàng được cấp trong luồng. Không áp dụng phép suy ra này cho bảng, khoảng trước/sau, ngắt trang hay đoạn phức tạp khác.

**Writer:** dùng backend UNO headless riêng của chính LibreOffice đã cài, không điều khiển cửa sổ qua shell. Export PDF trước, đi tới trang cuối rồi dump layout. CLI dump trực tiếp lúc đầu chỉ có3trang và các frame cao0 ở cuối: loại bỏ. Bản forced-PDF có4trang và không còn frame cao0; toàn bộ85paragraph khớp theo thứ tự và văn bản đầy đủ sau khi bỏ khoảng trắng/placeholder*, kể cả ghép frame follow của đoạn cắt trang. Namespace/Math text không được suy diễn từ placeholder.

Dump cho intrinsic `SwLineLayout.height`, khung inline công thức và print-area của paragraph, đơn vịtwip đối chiếu với pgSz XML. Nó không xuất đầy đủ RealHeight/advance của từng dòng: min-line cho intrinsic46.30pt nhưng print-area57.40pt. Bộ lọc dump còn invalidates một số geometry flag sau khi format; baseline source63/85frame và native70/86frame có đủ3flag hợp lệ. Các giá trị cached khác được đánh dấu trong ledger, chỉ là chẩn đoán; không gọi toàn85frame là live-valid. Các frame I.2/I.6 dùng trong kết luận hẹp đều có3flag hợp lệ. Mã chính thức mô tả bộ lọc và cấu trúc line layout: [LibreOffice dumpfilter](https://docs.libreoffice.org/sw/html/dumpfilter_8cxx_source.html), [porlay.cxx](https://github.com/LibreOffice/core/blob/master/sw/source/core/text/porlay.cxx).

`height-ledger.md` ghi đủ22thân câu: các dải Word source/native, print-area Writer và dấu* cho cached flag. `writer-line-metrics.json` ghi từng dòng/frame/fly của85paragraph. Không gộp dải vẽ, intrinsic line-height, allocated height và glyph ink thành một loại chiều cao.

## Hai đối chứng độc lập tại I.2

Hàng đáp án p11 có4hệ3dòng. Nó chứa5matrix tổng cộng vì C có thêm matrix1dòng lồng trong; đối chứng matrix-gap chỉ sửa4matrix3dòng, không sửa cái lồng1dòng.

1. **Minimum line:** chỉ đổi w:spacing line=1148,lineRule=atLeast tại p11, tương đương57.4pt (lấy từ chiều cao nguồn Word57.36pt rồi làm tròn lên twip). Không đổi cây toán. Mục đích kiểm tra phần chỗ dành cho hàng, không phóng hình/cỡ chữ.
2. **Matrix gap:** từ native gốc độc lập, chỉ thêm m:rSpRule val=1 vào4matrix3dòng tại p11. Không mang min-line sang. Đây là1.5row gap theo [Microsoft RowSpacingRule](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.math.rowspacingrule?view=openxml-3.0.1), không phải khẳng định đã giải mã spacing MTEF tương ứng. Mọi m:t và phần còn lại giữ nguyên sau khi bỏ4thuộc tính thử.

Cả hai giữ màu nền đo của native. Không đưa nền/vạch biên hoặc tham số fit này vào converter.

| Word I.2 | Nguồn | Native | Minimum line | Matrix gap |
|---|---:|---:|---:|---:|
| Tổng dải vẽ của2dòng thân câu (pt) | 42.00 | 27.60 | 27.60 | 27.60 |
| Hàng đáp án được cấp trong luồng giữa các dải kề nhau (pt) | 57.36 | 39.36 | 57.36 | 51.12 |
| Dải nền của chính hàng đáp án (pt) | 57.36 (biên) | 39.36 | 37.44 | 51.12 |
| Chiều cao nét hệ A, raster (pt, xấp xỉ) | 50.52 | 35.88 | 35.76 | 47.40 |
| Sai số Câu2→A so nguồn (pt) | 0 | −18.96 | +1.20 | −12.96 |
| Sai số Câu2→Câu3 so nguồn (pt) | 0 | −31.92 | −13.92 | −20.16 |

Hàng “dải nền” trong bảng ghi hai loại dấu đo khác nhau (biên ở nguồn, nền ở native), không được dùng riêng để kết luận line-height hai bản khác nhau. Hàng allocation giữa các dải kề và phép đo ink độc lập mới là các đối chiếu được nêu. Minimum line thêm19.92pt leading trước dải nền; nền37.44pt không thể được gọi là toàn bộ chiều cao dòng57.36pt. Nét công thức gần như không cao lên (chênh1pixel ở600dpi); khớp row allocation không làm công thức khớp hình học nguồn. Matrix gap thực sự làm công thức cao hơn trong Word, nhưng vẫn hụt khoảng3.12pt nét và không sửa thân câu đang thấp hơn nguồn14.4pt. Đây là kết quả trong mẫu, chưa phải một hệ đúng vị trí/độ cao nguồn.

| Writer I.2 | Native | Minimum line | Matrix gap |
|---|---:|---:|---:|
| Intrinsic line-height p11 (pt) | 46.30 | 46.30 | 46.30 |
| Paragraph print-area height p11 (pt) | 46.30 | 57.40 | 46.30 |
| Inline formula frame A (pt) | 46.30 | 46.30 | 46.30 |
| Chiều cao nét A, raster (pt) | 44.88 | 44.88 | 44.88 |

Nguồn OLE Writer có print-area58.25pt, fly55.15pt, ink49.80pt, chỉ dùng chẩn đoán; Word source vẫn là tham chiếu. Chưa kết luận Writer luôn bỏ rSpRule: chỉ quan sát không có tác dụng về chiều cao trong đúng đối chứng này. Không dùng Writer OLE làm đích fit.

## Kiểm tra và giới hạn

- Word xuất thực qua UI; Writer forced-PDF/export layout bằng API trên instance headless scratch riêng. Không sửa–lưu–đóng–mở lại qua UI đối với hai bản thử mới. Không lấy bằng chứng UI cũ để nghiệm thu chúng.
- Đã xem9crop hệ A và vùng đo, cùng trang1 của cả2trial trong Word/Writer. Nét/công thức vẫn còn; chưa xem toàn bộ trang còn lại. Không tuyên bố kiểm nội dung toàn đề hay bố cục đầy đủ.
- Ink ở600dpi, khoảng0.12pt/pixel, threshold RGB<100. Thuật toán riêng cho hệ3dòng có ngoặc nhọn: tìm component ngoặc cao ở bên trái rồi chọn component có tâm nằm trong phạm vi dọc ngoặc để loại chữ đoạn kề. Word ROI có thể chứa dấu chấm theo sau; Writer ROI theo fly frame không lấy dấu chấm prose bên ngoài. Đây là ink extent, không phải font ascent/descent hoặc logical equation box; không suy tổng quát từ một hệ. Các crop ban đầu chạm mép bị từ chối và thay bằng vùng/segmentation đã kiểm ảnh.
- Word min-line đổi3→4trang nhưng vẫn có4/22heading ở trang khác nguồn (I.12,III.1,III.5,III.6); matrix-gap vẫn3trang và5heading khác. Các cặp first-answer mới tách so source: native/matrix-gap III.2; min-line không có trong phép kiểm đầu này. Không coi đủ4trang hoặc hết một kiểu tách là layout pass.
- `verify_scope.py` xác nhận5probe chỉ có mutation dự kiến:85shading,85left-border,1min-line hoặc4matrix-gap; các ZIP part khác đúng byte; source hashes không đổi. Việc này không phải semantic/layout acceptance. Chưa chạy lại production Java/Python suite vì không sửa production.

Quyết định: giữ scratch. Phép đo đã phân biệt được công thức thấp hơn nguồn với leading/row allocation và hành vi ứng dụng khác nhau. Chưa áp dụng w:line hoặc m:rSpRule chung. Cần kiểm thêm sự bền vững khi chỉnh sửa/mở lại, nguyên nhân spacing trong payload/MathML và mẫu khác trước khi chọn chính sách converter.

## Helper correction during verification

Phát hiện driver UNO ban đầu dùng hằng số số học4 cho MacroExecutionMode; tra constant cho thấy đó là ALWAYS_EXECUTE_NO_WARN, không phải NEVER_EXECUTE. Đã thay bằng constant có tên `MacroExecMode.NEVER_EXECUTE` (=0), compile lại và chạy lại cả6DOCX read-only trong thư mục/profile mới `writer-verified/`. Các DOCX không có phần VBA hoặc macroEnabled content type. `verify_writer_reexport.py` xác nhận toàn bộ hình học chữ PDF và từng metric line/frame trích xuất khớp lần trước; metric/raster hiện đọc bản verified. Không thay đổi thiết lập macro toàn cục hoặc dùng cơ chế bỏ qua bảo vệ hệ thống. Các PDF/layout cũ vẫn được giữ riêng để đối chiếu. Không tính những lần helper lỗi import/compile hoặc đầu vào chưa tạo là lỗi tài liệu.

## Review resolution

Claude review read-only đã xong tại `docs/working/claude_dsmt4_line_metrics_review_2026-11-10.md`: không cóP1/P2;3P3 đã xử lý. Đã đo trực tiếp ink trên `Word-source-control.pdf` không có border, vẫn50.52pt; raw crop600dpi khớp pixel với border probe (`source-ink-control-check.json`), nên không chỉ dựa vào chữ PDF để suy hình công thức. `compare_height_trials.py` nay sinh cả cột nguồn42.00/57.36 và gap trước/sau0 từ hình học các dải. Bảng được chú thích rằng biên và nền là hai instrument khác nhau. Marker binding nay đòi đúng từng nhãn một lần, không chỉ đúng tổng số. Không có thêm thay đổi DOCX từ các sửa review này. Claude chưa kiểm các sửaP3 cuối hoặc helper UNO; đó là phần kiểm chứng Codex được ghi riêng, không suy thành review toàn bộ backend.

Backend helper còn được siết instance isolation: cổng loopback chọn tự động, đối chiếu user-profile URI của remote context trước khi tạo Desktop/load/terminate. Test profile sai bị từ chối trước load; test profile đúng xuất lại native có chữ PDF và metric layout khớp bản verified (`complete-layout-run-isolation-check-v2.json`). Lần negative-test đầu vướng Java UNO bridge giữ JVM sau exception; đã dùng exit lỗi rõ ràng trước Desktop và test lại thành công. Không dùng lại instance Writer đang mở của người dùng.

## Final verification status

10scratch script chạy đạt,10artifact đo tái tạo ổn định, helper UNO compile đạt và `git diff --check` đạt (`targeted-checks-final.json`). Lượt Claude rà bổ sung các sửaP3/helper bị chặn bởi hạn mức5giờ; phản hồi gốc được giữ, không tự retry vô hạn hoặc dùng agent thay thế. Review chính đã xong không cóP1/P2; các sửa cuối/helper mới được Codex kiểm chứng. Chỉ thị rà bổ sung nằm ở `work/dsmt4-line-metrics-2026-11-10/claude-followup-prompt.md`. Không nâng accepted, không thay đổi production và chưa commit/push.

## Superseding follow-up 2026-11-11

Claude đã hoàn tất review bổ sung P3/helper: không P1/P2 (`claude_dsmt4_line_metrics_followup_2026-11-11.md`). Các câu trước ghi review bị credit-blocked/chưa kiểm là lịch sử Nov10, nay đã được thay thế bởi kết quả này. Đã thêm và chạy `verify_isolation_export.py`, so toàn bộ PDF word geometry và extract layout của positive isolated output với verified baseline; kết quả ở `isolation-geometry-check.json`. Listener UNO scratch là loopback không xác thực trong thời gian chạy, dù profile/cổng riêng và guard kiểm identity trước load; không thay setting toàn cục.

Bốn UI roundtrip mới và phát hiện Writer bỏ rSpRule khi lưu DOCX được ghi riêng ở `codex_dsmt4_height_ui_roundtrip_2026-11-11.md`; Claude review trên không bao gồm UI. Giữ scratch và needs_review.
