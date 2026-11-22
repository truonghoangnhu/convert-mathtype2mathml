# DSMT4: Codex + một agent Claude Code — 2026-11-06

Đã đóng phần review root inline cuối, kiểm TN qua Word UI, đối chiếu phân trang bằng PDF xuất từ Word và tạo mapping 265 occurrence theo output hiện tại. Phần Math ở các mục dưới ghi snapshot thử ban đầu; sau đó UI Math đã hoàn tất và rule A có phạm vi đã vào adapter riêng, xem [kết quả cuối](./codex_dsmt4_math_alignment_2026-11-06.md). Corpus vẫn `needs_review`; accepted không tăng. Không commit/push/merge, không sửa nguồn, ZIP, fixture hoặc output cũ.

## Phân công và kết quả review

Một phiên Claude Code, session `2fdbb5a4-0d12-417c-a96c-304c0bdbdc80`, review chỉ đọc bản noBreak cuối, gap ledger và hướng xử lý Math #15. Codex chạy kiểm tra độc lập, UI, chỉnh mã/test và artifact. Không có agent thay thế hoặc subagent khác. Các bản review ở [lượt đầu](./claude_dsmt4_joint_review_2026-11-06.md) và [lượt hai](./claude_dsmt4_joint_followup_review_2026-11-06.md). Claude không chạy shell/test/render/UI; nhận định về ảnh và artifact do Codex kiểm riêng.

Hai gap test của root inline đã được bổ sung: `oMathPara` một phương trình phải trở thành `oMath` trực tiếp trong paragraph, không còn property display, giữ prose đứng trước và có box/noBreak đúng; phần tử foreign namespace phải bị từ chối. Review còn chỉ ra CDATA trực tiếp trong `oMathPara` có thể bị bỏ mất qua API nhận OMML. Codex tái hiện rồi sửa guard để từ chối cả TEXT và CDATA không rỗng. Single/multi giữ nguyên live paragraph khi từ chối. Đây là biên API, không phải output mà stylesheet hiện tại sinh ra.

Log đỏ cuối `root-review-red-correct-oracle.log` chỉ có lỗi CDATA. Hai lượt assert đầu đã được sửa vì CTP.xmlText dùng root `xml-fragment` và thiếu import assertSame; không coi chúng là lỗi production. Full Maven package sau sửa đạt **114 Java**, gate mới **4/4**. Python 136 và workflow 4 đã đạt trên các file không thay đổi trong đợt này. Không chạy lại các bộ đó chỉ để lặp kết quả.

Fresh repatch vào `out/dsmt4-joint-verified-2026-11-06/`: 32/32 qua các kiểm tra bảo toàn và **mọi package part trùng byte** với `out/dsmt4-nobreak-final-2026-11-06/`. Bản sửa CDATA không đổi output production của corpus. Đếm vẫn 2.286 chèn = 71 block + 2.215 inline; 331 DSMT4 giữ lại + 10 OLE khác; 27 native → 2.313 OMML. `fresh-package-verification.json` ghi hash JAR, test, gate và tên 32 tệp đã đối chiếu.

## TN #19: Word edit/save/close/reopen

Đã mở QA copy của output cuối và quan sát `B = 0,400` liền một dòng. Đi vào math bằng bàn phím sau Find, xác nhận Cambria Math/Equation, thêm `q` thành `Bq = 0,400`, Save As sang `TN-THPT-2026-ui-edited.docx`, đóng và mở lại. Ảnh `word-tn019-reopened.png` ghi chữ sửa và công thức vẫn liền. XML xác nhận `q` nằm trong `m:box/m:e`, đúng paragraph/slot của tn019; không gắn bằng chứng chỉ bằng relationship ID vì Word có thể đánh số lại ID khi lưu. Hash artifact được lưu trong ledger.

Đây là một ca trên QA full exam, không phải chứng nhận mọi phương trình hoặc full-page layout. Trước khi vào math, click tọa độ không cho focus tin cậy; chỉ gõ sau khi bàn phím và ribbon xác nhận. Các bản candidate/source trên đĩa chưa sửa vẫn khớp copy ban đầu.

## Phân trang Word: có bằng chứng mới, chưa đạt layout nguồn

Đã dùng **Word UI, PDF “Best for printing” cục bộ**, không dùng dịch vụ online, để xuất các QA copy nguồn/ứng viên của Toán và TN, cùng mốc Toán trước box. PDF và ảnh ở `work/dsmt4-joint-followup-2026-11-06/qa/` và `word-pages/`.

| Tài liệu Toán | Trang | Nội dung trang cuối |
| --- | ---: | --- |
| Nguồn OLE | 4 | Có nội dung câu 4–6 và HẾT |
| Mốc OMML trước box | 4 | Chỉ footer “Trang 4” |
| OMML có box | 3 | Có nội dung kết thúc đề và HẾT |

Đã xem ảnh đối chiếu toàn trang và vùng đầu đề; bbox cũng ghi thay đổi dòng/vị trí. Box giữ liền công thức, có thay đổi ngắt dòng và độ cao dòng nhỏ, làm mất trang trắng cuối của mốc OMML. Không có paragraph nguồn bị xóa theo kiểm tra package/XML. Đây **không phải** bằng chứng giữ phân trang nguồn: phần lớn sự dồn nội dung đã có ở mốc OMML trước box. Không sửa bằng page break hoặc padding đoán. TN nguồn và candidate đều 4 trang nhưng nội dung/formula/ảnh đã dịch vị trí giữa trang 3/4; số trang bằng nhau không phải layout pass.

`pagination-comparison.json` lưu số trang, lượng text mỗi trang và đầu/cuối trang cuối. Text PDF của OLE nguồn có font encoding không đáng tin để suy công thức; dùng ảnh nguồn để xem, không dùng text trích xuất làm nội dung thay thế.

## Mapping 265 occurrence: tách lịch sử khỏi snapshot hiện tại

`current-ledger.json` và `current-ledger-summary.md` ánh xạ theo slot gốc trong từng paragraph, đối chiếu relationship và ordinal nguồn, không suy từ text hay hash công thức trùng nhau. Có guard không cho key relationship trùng trong paragraph, 265 binding tới 265 node riêng, native OMML và số slot/paragraph phải khớp. Guard uniqueness cũng phát hiện một biến cache-key bị dùng lại trong script draft; đã sửa, lượt cuối xanh. Đây là script audit trong work, không thay patcher production.

| Trạng thái/tương đương | Số occurrence |
| --- | ---: |
| OLE giữ từ trước | 13 |
| Nay giữ OLE, thay cho OMML cũ | 5 |
| Inline giống cây cũ sau bỏ đúng box mới | 231 |
| Block giống cây và display properties cũ, không box | 13 |
| Expression hoặc properties khác snapshot lịch sử | 3 |

247 OMML candidate + 18 retained OLE = 265; thêm 18 native không thuộc bộ DSMT4, trong đó có 15 ở đề Công nghệ không có DSMT4. Ba cây khác là **toan078, tn017, tn020**, có diff text/run properties được lưu, không đoán loại thay đổi. Năm ca li002/li003/li010/li011/li012 gắn `now_retained_ole`: verdict OMML cũ bị superseded, không trở thành pass hay editable conversion.

Verdict lịch sử nằm trong `historical_review`; `application_verdicts_auto_carried=false`. Bằng chứng Word mới của tn019/toan086 nằm riêng, có hash và binding paragraph/slot. **Không công bố 46, 14, 13 hay số suy ra 7 là failed hiện tại.** `current_failed_total=null` vì chưa làm lại toàn bộ nghiệm thu ứng dụng; không có nghĩa 0 failed hoặc xóa những finding còn mở. Accepted promotions vẫn 0. Tuyến Math riêng vẫn có input của cả 265 ca, kể cả Word giữ OLE; không lẫn hai tuyến.

## Word save: so biểu diễn, không chỉ ký tự

`word-save-audit.json` so artifact trước/sau Word lưu: 115 OMML Toán và 22 TN còn đủ. Word đổi nhiều U+2212 sang hyphen, U+2032 sang apostrophe trong math. ℝ của toan078 được lưu bằng `R` + `m:scr=double-struck`, ℓ của tn017/tn020 bằng `l` + `m:scr=script`, có `m:sty=p`; không kết luận mất ký hiệu chỉ từ m:t. Đã có ảnh Word reopen cho các ký hiệu trong các đợt trước. Lượt này chỉ thêm artifact audit, không coi mọi text/style normalization là semantic pass, hoặc tự tăng số UI đã xem.

## Snapshot prototype căn trái Toán #15 trong Math riêng

Theo [hướng dẫn LibreOffice Math](https://help.libreoffice.org/latest/en-GB/text/smath/01/03090700.html), `alignl` có thể căn phần tử trong matrix. Probe riêng giữ presentation MathML nguồn và sinh annotation StarMath từ hình dạng ba hàng phẳng đã kiểm. Không viết tay công thức từ preview. `alignment_probe.py`, `math-alignment-probe/items.json`, PDF, ODT roundtrip và `measurement.json` lưu phép thử.

- Control có presentation `x=1` nhưng annotation `x=9`: LibreOffice hiển thị và lưu lại presentation thành **x=9**. Annotation là nguồn quyết định trong runtime này; không được thêm annotation chưa đối chiếu nội dung.
- Baseline toan015: độ lệch mép trái ba hàng **5,6 pt**. Probe có alignl: **0 pt**, cả render đầu và sau save/reopen headless.
- Presentation sau lưu giữ đúng ba chuỗi `x=2+5t`, `y=2+2t`, `z=−1−3t`; annotation giữ ba `alignl`.

**Chưa tích hợp vào adapter production.** Review P2 về grammar đầu/cuối toán tử và toán hạng số liên tiếp là điều kiện chặn tổng quát hóa serializer; probe hiện tại chỉ chứng minh toan015 cụ thể. Phải thêm parser/negative tests, đối chiếu toàn row, kiểm các toan013/014/016 và candidate production thật, rồi UI mới có thể đề xuất rule. Không áp annotation vào normalized MathML/OMML Word.

Math UI chưa hoàn tất: bản thử Writer/ODT đã mở được và hiện căn trái; thao tác Enter khi chọn text object đã xuống dòng thay vì kích hoạt Math. Đã đóng **Don’t Save**, mở lại nguyên vẹn. Không dùng ảnh trạng thái sai làm bằng chứng. Chuyển sang QA Math standalone riêng để kiểm command editor, nhưng Mac khóa trước khi mở. Ghi `not_run/incomplete`, không nâng toan015 layout thành pass. UI chỉ qua cua_repl; không dùng shell để điều khiển ứng dụng hoặc đổi cài đặt khóa máy.

## Việc còn mở ở snapshot này

1. UI edit/save/close/reopen prototype Math #15, rồi quyết định có đủ điều kiện triển khai adapter có phạm vi hay giữ prototype.
2. Nghiệm thu lại các finding Word/Writer/Math trên artifact hiện tại, cập nhật verdict từng tiêu chí thay vì mang pass/fail cũ sang.
3. Review bố cục nguồn/output và công thức rộng/bảng. Giữ số trang hoặc số công thức không đủ chứng nhận vị trí.

Mục 1 và bước parser/render giới hạn của mục 2 đã có follow-up mới: UI standalone #15 giữ q/căn trái; adapter A sửa đúng toan013–015, defer toan016. Các phép đo hoàn chỉnh gồm mọi từ trong từng hàng và presentation sau lưu, khắc phục finding P2 của review lượt 3. Xem báo cáo alignment; các giới hạn Writer/DOCX/full exam của mục 2–3 vẫn mở.

FULL_END_ONLY vẫn unsupported; 108 safety skip ban đầu và hai OLE Lý ¶91 không mở rộng. Retained OLE chưa phải editable migration và Writer có thể hiển thị thiếu ngay trên nguồn. File `~$` là lock của các QA đang mở sau bước reopen; không thu vào artifact/commit. Không đóng hoặc lưu tài liệu ngoài phạm vi của người dùng.
