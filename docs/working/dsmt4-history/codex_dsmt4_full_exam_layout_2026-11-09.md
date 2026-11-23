# DSMT4: đo bố cục toàn đề Toán và đối chứng theo ứng dụng

Đợt đo bắt đầu 09/11, đóng gói review 10/11/2026 (Asia/Ho_Chi_Minh). Chưa có bản sửa bố cục đủ điều kiện đưa vào production. Bù khoảng cách theo từng hàng cải thiện khoảng cục bộ nhưng không bảo toàn phân trang và phân nhóm câu. Không thay đổi accepted; corpus vẫn needs_review. Không commit/push/merge.

## Nguồn và phạm vi

Mẫu toàn đề `in/Toan_TQB_HN_Lx.docx`; ứng viên là snapshot `out/dsmt4-writer-comparison-2026-11-06/patched/Toan_TQB_HN_Lx-omml.docx`, không phải vừa tái sinh từ converter hiện tại. Bản sao, SHA-256 và đường dẫn gốc ở `work/dsmt4-full-exam-layout-2026-11-09/inputs.json`. Source và native không bị sửa khi xuất PDF. Mẫu native chứa 115 cây oMath. Đây là nghiên cứu bố cục trên một đề; không nghiệm thu nội dung 115 công thức và không suy rộng sang toàn bộ corpus.

Word source là tham chiếu chính. PDF Word được xuất từ chính Word qua Print → PDF; Writer được render bằng LibreOffice headless profile riêng. Word source 4 trang, Word native 3; Writer source/native đều 4. OLE source trong Writer chỉ là dữ liệu chẩn đoán, không dùng làm đích tối ưu.

Đã ràng buộc đủ 22 nhãn Câu theo thứ tự XML (I:12, II:4, III:6) và 70 nhãn đáp án (48 A–D, 16 a–d, 6 [A]) trong từng bản Word source/native, Writer source/native, Word grouping control và Writer own profile. Mỗi nhãn phải có đúng một kết quả trong khoảng câu tương ứng. Đây là kiểm tra định vị, không phải xác nhận đúng nội dung. Bảng đủ 22 câu: `work/dsmt4-full-exam-layout-2026-11-09/question-ledger.md`; dữ liệu đầy đủ `all-answer-bindings.json`.

Tọa độ là đỉnh bounding box chữ trích xuất từ PDF, KHÔNG phải baseline hay chiều cao line box. Sai số khoảng cục bộ chỉ tính khi cả cặp nhãn của từng bản nằm cùng trang. Không coi tọa độ y ở hai trang khác nhau là khoảng liên tục. Các trang mang cùng số không nhất thiết có cùng phân đoạn nội dung. Heuristic first-body-text-line không chứng minh paragraph thực sự ở page top.

`measure.py` còn ghi spacing hiệu lực theo từng thuộc tính: docDefaults → chuỗi basedOn → định dạng trực tiếp, contextualSpacing, keepNext/keepLines, pageBreakBefore, đoạn bảng, kích thước OLE và compat XML. Không giả định đây là mô hình đầy đủ của engine Word/Writer. Source/native cùng compat mode15; không thấy suppressTopSpacing tường minh.

## Thí nghiệm trên bản riêng

1. Baseline khoảng Câu → A của I.1–I.12 có độ hụt khác nhau: Word từ 0 đến 18.96pt; I.11 không so khoảng vì source cắt trang. I.9 có bảng/các đoạn xen giữa. Không đủ cơ sở dùng một hằng số cho mọi đoạn.
2. `Toan-choice-gap-trial.docx`: bù w:before ở 9 hàng đơn giản theo gap Word đã đo. 8 khoảng cục bộ sau sửa gần khớp, nhưng I.12 mới bị tách thân câu/đáp án qua trang. Không loại ca mất tính so sánh rồi tuyên bố thành công. Áp cùng bản vào Writer gây dư khoảng, ví dụ I.6 +9.25pt, I.2 +7.27pt.
3. `Toan-word-profile.docx`: hoàn tác riêng buffer I.12, giữ 8 hàng. Vẫn tách I.12 vì khoảng thêm phía trước làm đổi phân trang. `Toan-writer-profile.docx`: 9 giá trị bù riêng từ render Writer, vẫn lấy Word source làm đích. Hai profile không chuyển được cho nhau: Word dùng Writer profile còn hụt I.2 −7.20pt, I.6 −9.12pt. Không có quy tắc chia sẻ được chứng minh.
4. `Toan-word-profile-grouped.docx`: thêm đúng keepNext ở thân I.12 (paragraph43) vào Word profile. I.12 và A về cùng trang2; đây là định dạng nhóm MỚI, không phải bảo toàn định dạng nguồn. Thân III.1/đáp án bị tách trang2→3, III.6 bị tách3→4, trong khi từng cặp ở cùng trang trong source. Vì vậy đây là đối chứng cho tác dụng phụ, không phải bản sửa đạt.

| Chỉ số trên cùng 11 khoảng I.1–10,I.12 | Word native → grouping control | Writer native → own profile |
|---|---:|---:|
| Trung bình trị tuyệt đối sai số Câu → A (pt) | 7.265 → 1.331 | 4.459 → 0.975 |
| Nhãn Câu ở trang khác source, trên đủ22câu | 5 → 3 | 1 → 1 |
| Cặp thân câu/đáp án đầu mới tách trang so source, trên đủ22câu | III.2 → III.1 và III.6 | III.5 → III.5 |

Các số này là độ khớp ngay trên dữ liệu đã dùng hiệu chỉnh, KHÔNG phải kiểm chứng ngoài mẫu. Khoảng còn lệch ở Word I.9 −2.88pt và I.12 −11.52pt; Writer I.9 +10.26pt. I.11 vẫn không có gap reference cùng trang. Không biến việc đủ4trang thành layout pass.

## Bằng chứng và kiểm tra

- Đã xem toàn bộ 4 trang Word source, 3 trang Word native, 4 trang Word grouping control, 4 trang Writer native và 4 trang Writer own profile. Không thấy cắt chồng trong các trang grouping control đã xem; các tách câu nêu trên vẫn tồn tại. Các bản cross-profile khác chủ yếu được đo tự động, không tuyên bố đã xem toàn bộ. Writer source chỉ đo/chẩn đoán trong đợt này.
- `summarize.py` tái tạo `summary-metrics.json` và bảng từng câu; `all_answers.py`, `measure.py`, `evaluate_trial.py`, `evaluate_app_trials.py` lưu phương pháp và dữ liệu từng bước.
- `verify_artifacts.py` kiểm độc lập 4 DOCX trial: đúng9/8/9 thay đổi w:before; grouping control đúng8 before +1 keepNext; 115 cây toán không đổi; các ZIP part khác byte-identical. Khôi phục riêng các thuộc tính được phép rồi so canonical document XML. Hash source, native và bản gốc đều khớp. Kiểm tra này chứng minh phạm vi mutation, không chứng minh semantic/layout acceptance.
- Đợt full-profile này chỉ mở/xuất PDF, KHÔNG có sửa–lưu–đóng–mở lại qua UI. Bằng chứng UI công thức dài/cao của các đợt trước không xác nhận các profile mới này.
- Không đổi production trong đợt này nên không chạy lại toàn bộ Java/Python corpus suite. Log render thất bại ban đầu do file chưa được tạo được giữ ở `writer-app-profiles/word-profile/render.log`; lần thành công ở `writer-app-profiles-v2/`, không tính lỗi khởi chạy scratch là lỗi tài liệu.

## Quyết định và phần tiếp theo

Giữ tất cả profile ở scratch; không đưa spacing constant hoặc keepNext toàn cục vào converter. Đợt này chứng minh bù cục bộ một mình không xử lý được pagination toàn đề. Cần mô hình/chiến lược có tính đến nhóm thân câu–đáp án, các hàng bảng, vùng ảnh và ngân sách chiều cao trang, sau đó kiểm ngoài mẫu và sửa–mở lại. Không nối thêm keepNext theo từng điểm hỏng mà coi là quy tắc tổng quát.

Review Claude cần kiểm phương pháp ghép nhãn/spacing hiệu lực, phạm vi mutation và cách diễn giải chỉ số; đặc biệt tránh che các ca cross-page, lấy Writer OLE làm đích hoặc gọi fit trong mẫu là bảo toàn bố cục. FULL_END_ONLY và các safety skip/Lý¶91 không thay đổi.

## Bổ sung sau review Claude (10/11/2026)

Review gốc ở `docs/working/dsmt4-history/claude_dsmt4_full_exam_layout_review_2026-11-09.md`: không có P1 hoặc sai số tính toán; có2P2 về diễn giải chỉ số. Đã xử lý như sau, không thay đổi DOCX/render đã review.

**Khoảng Câu → A không đồng nghĩa khoảng cách đoạn.** Nó trộn số dòng thân câu, pitch/chiều cao dòng, vị trí chữ A bên cạnh công thức cao, và khoảng giữa các đoạn. Bù w:before chỉ khớp một nhãn được chọn; không phục hồi chiều cao công thức, đáy hàng đáp án hoặc khoảng tới câu sau. Review nêu I.2/I.6 có thành phần do kích thước công thức; đây là nhận định từ render, chưa có phân rã định lượng đủ để nói “phần lớn” sai số do một nguyên nhân cụ thể.

Đã bổ sung `diagnose_line_boxes.py`/`line-object-diagnostics.json`: ví dụ I.2 có4OLE đáp án khai báo cao55.15pt, nhưng fragment PDF chứa nhãn A chỉ cao16.79pt. Điều đó cũng cho thấy không thể lấy fragment text của pdftotext làm chiều cao cả hàng toán. Diagnostic ghi riêng chiều cao VML được khai báo và fragment chữ; không suy native formula cao14.06pt chỉ vì fragment chữ đo như vậy. Chưa có số đếm line box thật hoặc baseline đủ cho phân rã4thành phần của cả22câu.

**Đã thêm khoảng Câu → Câu kế tiếp**, không chỉ nhãn đang được fit, trong `question-pitch-metrics.json` (generator `summarize.py`). Mỗi khoảng bao gồm nội dung cả câu và có thể có tiêu đề phần xen giữa. Chỉ lấy cùng một tập khoảng có cả source/baseline/trial cùng trang bên trong từng bản. Không nối tọa độ y qua trang.

| Tập khoảng Câu → Câu kế tiếp | Word native → grouped MAE (pt) | Writer native → own MAE (pt) |
|---|---:|---:|
| Xuất phát từ cohort11 ban đầu; còn so chung10 Word /11 Writer | 12.192 → 5.640 | 6.312 → 3.245 |
| Toàn21 cặp kế tiếp; còn so chung15 Word /17 Writer | 14.096 → 9.728 | 7.809 → 5.825 |

Cohort chung toàn đề của Word có các ordinal xuất phát 1–10,13,14,15,19,21; Writer 1–10,12,13,14,15,17,18,19. JSON lưu từng cặp, cả các cặp bị loại do cross-page và mẫu số từng giai đoạn (Word baseline16/trial17 cặp riêng lẻ, Writer17/17). Không dùng việc mất ca so được để hạ MAE. Các khoảng giảm sai số vẫn không xoá các ca tách câu đã ghi; đây tiếp tục là fit trong mẫu và không phải layout pass.

**Phạm vi guard và association:** các guard builder chỉ phù hợp snapshot đã đo; không xử lý tổng quát numbering pPr, table-style pPr hoặc precedence của spacing theo line units. App builder được thêm sau khi tạo/render các profile để từ chối beforeLines/afterLines và autospacing tường minh trong context đã đọc. Guard mới chỉ được compile, chưa chạy lại builder trên output mới; nó không tham gia tạo các artifact đã render. Snapshot hiện tại không có các thuộc tính đó; chưa chứng minh đây là bộ bảo vệ tổng quát. 70 marker là association trong PDF bằng thứ tự câu và tính duy nhất, không phải liên kết trực tiếp marker PDF→paragraph XML; một marker bị thiếu và body word trùng tên vẫn có thể đánh lừa phương pháp. Chưa dùng phương pháp này làm acceptance gate.

**Tái tạo:** verifier nay lấy toàn bộ9thay đổi của trial đầu từ `trial-plan.json` và đối chiếu với app-plan, thay vì chỉ dùng hằng số. `build_grouping_control.py --output NEW_PATH` tái tạo được control có các ZIP part đúng byte như bản đã render, từ chối ghi đè. Các đầu ra đo/ledger/verifier tái tạo ổn định; `git diff --check` đạt. Không cần render mới vì không sửa mẫu DOCX.

Quyết định giữ scratch không đổi. Việc tiếp theo là đo metric của toàn dòng/hàng toán bằng nguồn đáng tin cậy và liên kết tới paragraph trước khi chọn cơ chế sửa; không thêm tiếp hằng số w:before/keepNext theo từng điểm hỏng.

Review bổ sung đã xong: `docs/working/dsmt4-history/claude_dsmt4_full_exam_layout_followup_2026-11-10.md` xác nhận cả2P2 đã giải quyết, không có P1/P2 mới trong phần bổ sung. Đã xử lý các P3 cuối: lưu lệnh/exit code/output path của lần tái tạo grouping control trong `targeted-checks-post-review.json`; nói rõ guard thêm sau render chưa được thực thi; verifier lấy entry I.12 từ trial-plan, bỏ hằng số44/230. Verifier cuối và diff check đạt. Đây là đóng gói xong đợt đo/review, KHÔNG phải hoàn tất hỗ trợ DSMT4 hoặc đạt bố cục toàn đề.
