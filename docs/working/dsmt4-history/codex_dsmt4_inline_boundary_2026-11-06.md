# DSMT4 inline boundary preservation — 2026-11-06

Đã chặn việc thay OLE khi khoảng hở với chữ liền sau chưa được biểu diễn trong dữ liệu. Đây là sửa chính sách bảo toàn, chưa giải quyết chuyển đổi sửa được của các OLE giữ lại. Corpus vẫn `needs_review`; không nâng occurrence nào lên `accepted`, không commit/push/merge hoặc đổi Draft PR.

## Nguyên nhân và phạm vi

Hai lỗi đã được review độc lập là li002 `p,khối` (Lý ¶33) và li010 `ptheo` (¶80). Sidecar lần lượt chỉ có `p,` và `p`, không có mspace cuối. Prose kế tiếp không có space đầu. Object nguồn có viewport riêng; chuyển sang OMML làm mất khoảng hở của viewport. Bằng chứng Word trước sửa nằm trong hai ảnh so sánh nguồn/output của đợt `dsmt4-acceptance-final-20261105T1448`. Không thể suy một độ rộng space chính xác từ những dữ liệu này.

`InlineBoundarySafety` kiểm tra chữ Unicode liền sau object: phần đuôi cùng run trước, rồi các run kế tiếp. Bỏ qua run rỗng, bookmark, proofErr và lastRenderedPageBreak; không coi rendered-page marker là dấu phân cách thực. Chỉ đi qua các phần tử Word có namespace đúng. Dừng ở text không rỗng đầu tiên, tab, break, object, field hoặc container chưa xử lý. Khi ký tự đầu là chữ, giữ nguyên và báo `needs_review` / `INLINE_SPACING_REQUIRES_REVIEW`. Không chèn padding, không đoán nội dung từ preview hoặc fingerprint.

Multi-object paragraph giữ nguyên toàn đoạn nếu một object chạm điều kiện. Các gate native OMML, source/relationship chưa xác định, manifest và conversion lỗi vẫn có ưu tiên trước quyết định này. Đây là guard có phạm vi: chưa kiểm chữ trước object, chữ số, ký tự vô hình đứng đầu hay nội dung bên trong wrapper như hyperlink. Giữ nguyên có thể từ chối cả ranh giới công thức/đơn vị có chủ ý; đó là giới hạn bảo thủ, không phải bằng chứng mọi ranh giới đều đang hiển thị sai.

Skip breakdown đếm một quyết định cho single object hoặc một quyết định cho multi-object paragraph. Không dùng số quyết định này làm số OLE giữ lại. Smoke runner nay đưa reason mới vào structural residual; JSONL vẫn giữ các bộ đếm hiện có và conversion diagnostics riêng, không trộn layout skip vào conversion failure.

## Kiểm thử và review

Đã dùng quy trình systematic-debugging và test-driven-development. Hai test đầu tái hiện thay sai 1 và 2 object trước guard (`boundary-red-valid.log`). Test bao phủ chữ Việt/ký tự bổ sung Unicode, bookmark/proofing/empty-run, separator thực và conversion priority. Hai test cũ được cập nhật kỳ vọng giữ OLE khi nhãn chữ không có separator; không sửa input để né guard.

Claude đã review chỉ đọc trên snapshot đầu, session `c1780205-5a4b-4ce5-8fc0-84fcdd5c8f6e`. [Review](./claude_dsmt4_inline_boundary_review_2026-11-06.md) phát hiện Medium ở đuôi mixed run, Low ở lastRenderedPageBreak và Low ở telemetry smoke. Codex tái hiện cả ba bằng test đỏ rồi sửa (`review-red.log`, `smoke-red.log`). Thêm kiểm tra ưu tiên native/missing-sidecar cho cả single và multi, và assert chính xác reason của multi retention. Chưa có vòng Claude thứ hai cho các sửa cuối.

Kết quả mới: **109 Java, 136 Python, 4 workflow test đạt; generated-output gate 4/4**. `mvn -q package` đã dựng JAR chứa guard cuối. Gate chỉ chứng minh package/XML/structure, không phải Word/Writer render. Log và script mới ở `work/codex-dsmt4-inline-boundary-2026-11-06/`.

## Output và bảo toàn

Output cuối: `out/dsmt4-inline-boundary-final-2026-11-06/`.

| Phạm vi | OMML chèn | DSMT4 giữ lại | OMML nguồn | OMML output |
| --- | ---: | ---: | ---: | ---: |
| 32 đề | 2.286 = 71 block + 2.215 inline | 331 | 27 | 2.313 |
| 5 đề gốc | 247 | 18 | 18 | 265 |

Còn 10 OLE khác ngoài DSMT4 trong bộ 32 đề. So với snapshot symbol-scope, giữ thêm **131 object trong 43 đoạn thuộc 12 tệp**; cả 200 DSMT4 giữ trước đó vẫn nguyên vẹn. Không mở rộng 108 safety skip ban đầu, hai OLE Lý ¶91 hoặc FULL_END_ONLY. Trong bộ năm đề, thay đổi trạng thái gồm li002, li003, li010, li011, li012: thêm 5 OLE giữ, không phải thêm 5 conversion thành công. `occurrence-delta.json` chỉ là delta trạng thái, không phải ledger nghiệm thu mới 265 ca.

`report.json` ghi từng tệp và từng đoạn giữ thêm. 32/32 qua các kiểm tra: non-math leaf/run properties, paragraph properties, OMML nguồn, mọi OLE giữ trước đó, OLE còn lại khớp nguồn và embedding bytes. Mỗi đoạn giữ thêm khớp toàn bộ XML nguồn sau chuẩn hóa khoảng trắng thuộc tính; text nội dung không chuẩn hóa. Tất cả source hash vẫn khớp mốc.

Hai lần audit đầu dừng vì comparator chưa cho phép chuẩn hóa newline/CRLF trong thuộc tính VML gfxdata; không phải lỗi nội dung. Output/log tạm vẫn giữ ở các thư mục phiên bản đầu/v2. Bản v3 qua đủ 32 đề. Sau sửa review, chạy lại output cuối; mọi package part của cả 32 tệp trùng byte với v3 đã dùng cho Word UI. Không dùng kết quả audit thất bại làm thành công.

## Quan sát ứng dụng thực

**Word:** mở bản sao đề Lý, xem li002/li010, Save As sang tệp mới, đóng, mở lại và xem lại cả hai. Ảnh `word-li002[-reopened].png`, `word-li010[-reopened].png` ghi hiển thị OLE nguồn. Bản lưu lại giữ đủ 8 OLE và 13 OMML; payload của cả 8 embedding còn được tham chiếu trùng hash. Word bỏ 10 embedding không còn được tham chiếu khỏi package khi lưu; patcher output trước Word vẫn giữ nguyên toàn bộ embedding bytes theo chính sách.

Kiểm tra text sau Word save cũng ghi một biến đổi ở công thức khác: `B=3,5.10−5T` thành `B=3,5.10-5T` (U+2212 thành ASCII hyphen). 12/13 OMML giữ text ký tự như trước; không gọi toàn tài liệu là bảo toàn byte/Unicode sau Word save, hoặc chứng nhận công thức này từ số đếm. Không thay rule converter chỉ để ép byte khớp sự chuẩn hóa của Word trong lượt này.

**Writer:** xem trực tiếp cả source copy và output copy. li002 có khung OLE rỗng ở p,/rho; li010 có p/pV trống và phân số chỉ còn nét chéo. Hiện tượng cũng có trong source trước conversion, nên không phải mất payload mới do guard. Các ảnh `writer-li002-observed.png`, `writer-li010-observed.png`, `writer-source-li002.png`, `writer-source-li010.png` ghi giới hạn này. Không đạt render đầy đủ; không chạy save/reopen hoặc edit OLE trong lượt này.

Một thao tác Find bằng AX ở Writer đã nhập nhầm vào bản QA chưa lưu. Đã đóng bằng Don’t Save, mở lại từ đĩa và tìm bằng paste với xác minh focus trước Return. Bản QA trên đĩa vẫn trùng byte output cuối, source copy vẫn trùng byte in/. Hai ảnh tìm sai/QA tạm được loại khỏi evidence trong verification.json; không sửa nguồn hoặc output để che lỗi.

## Còn mở

- Retained OLE chưa phải editable migration, và Writer có thể không render đủ OLE nguồn. Cần tuyến MathML/Math được kiểm trong bố cục thật cho các ca này trước khi nâng trạng thái.
- Các lỗi/giới hạn Word ngắt công thức qua dòng/trang, font/spacing; Writer DOCX quan hệ đầu/mũi tên; Math system alignment và UI chưa chạy vẫn mở.
- Các ledger/overlay cũ giữ làm lịch sử. Không dùng tổng failed/needs_review cũ làm số liệu nghiệm thu mới cho output đã đổi trạng thái; accepted vẫn 0.

`verification.json` và `artifact-verification.log` ghi số liệu, phạm vi UI, hash đối chiếu snapshot và giới hạn cụ thể. Bước tiếp theo là giải quyết bố cục công thức trong Word và tuyến Writer/Math cho các trường hợp giữ lại, rồi cập nhật ledger theo từng ứng dụng bằng bằng chứng mới.
