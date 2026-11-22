# DSMT4 synthetic growth and page boundary roundtrips

Bộ thử riêng ngày11/11/2026: Word và Writer giữ phân số lồng trong hệ ba hàng sau sửa tử số5→6, lưu–đóng–mở lại qua UI. Word tự ngắt tổng24hạng tử thành ba dòng; Writer không tự ngắt và phần cuối tràn khỏi trang. Một bản riêng được sửa bằng Writer Commands thành stack ba dòng; sau lưu–đóng–mở lại, đủ24hạng tử hiển thị trong Writer và trong Word mở bản sao chỉ xem. Chưa sửa production, chưa commit/push, corpus vẫn needs_review và accepted không tăng.

## Thiết kế và phạm vi bằng chứng

`work/dsmt4-growth-boundaries-2026-11-11/build_probes.py` tạo ba DOCX giống byte ban đầu: control bất biến, Word UI, Writer UI. Lấy cây hệ từ math13 của probe Toán Nov10 nhưng dựng một tài liệu stress tổng hợp mới, trang450×600pt, lề54pt (text width342pt). Không gọi đây là giữ bố cục đề nguồn. Prose kế thừa mặc định Georgia11; một số run hệ kế thừa thuộc tính riêng của công thức cũ. Không so định lượng với mẫu cũ12pt để suy tăng chiều cao chính xác.

A: hàng đầu hệ được dựng sẵn thành x=(5+2t)/((t+1)/(t+2)), hai hàng sau giữ y=2+2t,z=−3+t. Paragraph dùng minimum1148twip atLeast từ đối chứng trước. Phân số lồng đã có trước mở UI; thao tác UI chỉ thay5→6 trong tử số, không phải chèn phân số bằng UI hay đo mức tăng chiều cao trước/sau cùng một edit. Bằng chứng mới là cấu trúc cao thực sự còn hiển thị và paragraph thích ứng sau roundtrip.

B: một oMath chứa L=1t+2t+…+24t, không có explicit break/eqArr ban đầu. Đây là stress với phép cộng có chỗ ngắt toán học rõ ràng, không đại diện mọi công thức.

C: cùng hệ cao ban đầu đặt sau paragraph spacer có exact425pt ở trang3. Khoảng trống còn lại không đủ cho hệ; kết quả cả hai ứng dụng chuyển nguyên hệ sang trang4 và AFTER_C còn ở dưới. Đây là kiểm thiếu chỗ ở cuối trang, không phải trường hợp vừa khít sát mép hoặc hệ cao hơn cả một trang. Nhãn GROWTH C vẫn ở trang3; chưa giữ nhãn và hệ cùng trang.

## UI thực đã chạy

Word: mở bản word-growth-ui, sửa5→6 trong tử số, CmdS, đóng, mở lại, xác nhận spoken equation có6+2t và nested denominator, xuất PDF bằng Word Print→PDF. Lần click đầu chọn nhầm cả phân số và xóa nó trong bộ nhớ đã Undo trước lưu; bản lưu cuối đã xác nhận đúng cấu trúc hai tầng phân số. Chọn bằng tọa độ đúng trên screenshot sau đó mới sửa được ký tự trong tử số.

Writer: mở bản writer-growth-ui, chọn Object1 qua CmdHome/ShiftF4, Enter Commands, sửa5→6; lưu định dạng DOCX qua nút Use Word2010–365, đóng, mở lại, xác nhận Commands giữ6+2t trên tử và hai tầng over, xuất PDF trực tiếp từ Writer. B/C không có interactive edit riêng: chúng đi qua cùng lần save/close/reopen của tài liệu; không ghi thành ba edit-roundtrip độc lập.

Hai PDF đều4trang. Đã render/xem toàn bộ8trang cùng crop công thức cao và công thức dài. A còn đủ ba hàng/phân số, AFTER_A ở dưới, không thấy mất nét/chồng chữ trong vùng. C còn đủ hệ ở trang4 với AFTER_C bên dưới. Chỉ kiểm các mẫu tổng hợp này, không suy265occurrence.

Nút Open trong native file picker nhiều lần disabled với bản mới/copy; mở thành công qua Finder Open hoặc Open With LibreOffice và qua Recent Documents khi mở lại. Không sửa thiết lập mặc định Open With, không dùng shell điều khiển UI. Những lần mở lỗi không tính là bằng chứng roundtrip.

## Đo và lỗi công thức dài

`verify_and_render.py` kiểm ba oMath, số phân số[2,0,2], tử số caA=6+2t và caC=5+2t,24hạng tử đúng thứ tự, control hash không đổi và hash bản xem chéo không đổi. XML là kiểm bổ sung, không thay render/UI. Script render cả4PDF ra ảnh từng trang và crop.

Chiều cao nét hệA raster600dpi: Word-save60,12pt; Writer-save78,00pt; bản Writer explicit-lines xem bằng Word58,56pt. Đây là raster ink extent, không phải logical formula box/ascent/line advance. ROI có padding gồm cả prose kề; thuật toán chọn ngoặc cao rồi component có tâm trong phạm vi dọc ngoặc để loại prose; đã xem crop để kiểm. Crop đầu theo text bbox bị chạm mép dưới đã loại bỏ, không dùng làm số đo. Không dùng các số này để fit toàn đề hay quy toàn bộ chênh lệch cho một thuộc tính.

CaB: Word tự xuống ba dòng, đủ đến24t; Writer render một dòng cắt ở mép phải, mặc dù DOCX vẫn chứa đủ24hạng tử. Vì thế đếm/XML không bắt được lỗi này. PDF actual UI sau reopen là `word-growth-reopened.pdf`, `writer-growth-reopened.pdf`; `long-comparison.png` cho đối chiếu trực tiếp. Kết luận Writer automatic wrapping thất bại trong đúng mẫu này.

## Bản thử ngắt dòng tường minh

Sao writer-growth-ui thành writer-explicit-lines-ui riêng. Trong Writer UI Object2 Commands, thay biểu thức bằng alignl stack chia sau8t và16t, mỗi dòng tiếp nối bắt đầu bằng+. Lưu DOCX, đóng, mở lại qua Recent Documents, Commands vẫn stack ba dòng, xuất `writer-explicit-lines-reopened.pdf`. Writer export chuẩn hóa alignment thành stack căn giữa; không tuyên bố giữ align-left. DOCX lưu thành m:eqArr với ba m:e; concatenated m:t vẫn đúng toàn bộ biểu thức ban đầu.

Một bản sao mới `explicit-lines-word-view.docx` được Word mở và xuất `explicit-lines-word-view.pdf`, không save lại; hash giữ nguyên. Word nhận equation array ba dòng. Đã xem crop caB của hai ứng dụng: đủ đến24t, không tràn lề và AFTER_B còn dưới. Các ảnh còn lại cũng được render để giữ bằng chứng; cần reviewer kiểm độc lập các trang mới ngoài crop chính nếu muốn kết luận rộng hơn.

Đây là workaround trên mẫu phép cộng đã biết, không phải quy tắc tự chèn break vào MathML chuẩn hóa hoặc converter Word. Nó làm thay đổi cây trình bày, cần chính sách riêng và bằng chứng với dạng toán khác trước mở rộng. Không sửa nguồn/ZIP/fixture/output cũ; FULL_END_ONLY và safety skips không thay đổi.

## Trạng thái review

Gói bàn giao Claude read-only: script/plan, verification.json, DOCX và PDF/ảnh trong thư mục batch này. Chưa coi review cũ về line metrics là review của bộ stress mới. Kết quả Claude được lưu riêng khi có phản hồi.

Lượt Claude mới đã gửi nhưng bị credit-blocked trước kết luận (exit1, is_error=true; reset04:00 Asia/Saigon). Báo cáo trạng thái riêng `claude_dsmt4_growth_boundaries_review_2026-11-11.md`. Không có review approval cho batch này. Sau khi gửi, Codex còn thay số trang hệC hardcode trong verifier bằng tìm token x thực từ PDF vùng trang3trở đi; đã chạy lại đạt. Phiên review sau phải đọc bản script hiện tại.

Codex đã xem thêm contact sheet đủ8trang của hai PDF explicit-lines/cross-view (`explicit-all-pages.png`): A/C và sentinel còn hiển thị, B đủ ba dòng. Đây là kiểm ảnh tổng quan; không suy giữ chính xác font/căn lề hoặc bố cục đề gốc. Script kiểm mới đạt; git diff --check đạt. Không chạy lại production suite vì lượt này chỉ tạo scratch và tài liệu.

## Review follow-up 2026-11-12

Claude đã hoàn tất review read-only trong đúng session, không P1/P2,5P3. Codex đã kiểm và xử lý5P3 về kiểm đủ hàng/nhãn ở trang cuối, anchor/biên crop, ảnh toàn chiều ngang trang, nguồn của bản xem chéo và mô tả khác biệt nhìn thấy. Bản verifier/ảnh/JSON mới nằm riêng trong `work/dsmt4-growth-review-2026-11-12/`, không thay dữ liệu gốc. Xem `codex_dsmt4_growth_review_resolution_2026-11-12.md` và báo cáo Claude cùng ngày. Review này không nghiệm thu corpus; vẫn needs_review, chưa commit/push.
