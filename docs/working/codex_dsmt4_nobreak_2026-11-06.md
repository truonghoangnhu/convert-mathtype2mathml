# DSMT4: giữ liền công thức inline trong Word — 2026-11-06

Đã sửa việc Word tách một công thức chuyển từ một OLE qua dòng hoặc trang tại dấu quan hệ. Output mới ở `out/dsmt4-nobreak-final-2026-11-06/`. Số lượng chuyển đổi và OLE giữ lại không đổi; corpus vẫn `needs_review`, không nâng occurrence nào thành `accepted`. Chưa commit/push/merge hoặc đổi Draft PR.

## Nguyên nhân và sửa đổi

Nguồn OLE chiếm một vị trí không tách trong đoạn. OMML inline sinh trước đây cho phép Word ngắt tại dấu bằng. Đã mở lại baseline Toán và tái hiện toan086: `AB =` ở cuối trang 2, `CD = 16cm` ở đầu trang 3. toan011 và tn019 là các ca quan hệ khác trong ledger lịch sử, không phải ba lỗi mới được đếm thêm.

`XmlBeansOmmlInjector.buildInlineMath` nay đặt toàn bộ nội dung mỗi `oMath` mới vào một `m:box`, gồm `m:boxPr/m:noBreak m:val="on"` rồi `m:e`. Di chuyển các node theo đúng thứ tự, giữ nguyên thuộc tính và text; vẫn áp dụng run formatting qua các `m:r` bên trong. Single-object và multi-object cùng dùng đường này, mỗi object có box riêng. Không thêm box cho block hoặc OMML nguồn. Công thức quá rộng so với dòng cần review bố cục riêng; giữ liền không chứng minh không tràn lề hoặc phân trang đúng.

Claude review chỉ đọc phát hiện một lỗi có trước trong API nhận OMML trực tiếp: root `oMathPara` nhiều công thức bị lấy công thức đầu, còn fragment `m:r`/`m:f` bị bỏ wrapper. Codex tái hiện bằng test đỏ rồi sửa đường inline: chỉ nhận root đúng namespace là `oMath`, hoặc `oMathPara` chứa đúng một `oMath` cùng thuộc tính đoạn tùy chọn. Refuse root chưa kiểm chứng, phần tử lạ, thiếu/nhiều công thức, thay vì làm mất nội dung. Single và multi trả false, giữ nguyên live paragraph và OLE. Đây là kiểm tra root có phạm vi, không phải schema validator đầy đủ cho mọi cây OMML hay đường block.

## Kiểm thử và review

- Test mới ban đầu đỏ vì chưa có box (`nobreak-red.log`), sau sửa xanh. Kiểm tra ba nội dung quan hệ, thứ tự boxPr/e, chỉ một box trực tiếp mỗi phương trình, dấu vectơ U+20D7, delimiter, multi-object và block không bọc.
- Test root trực tiếp đỏ với baseline cũ (`root-rejection-red.log`), sau sửa xanh; bao phủ single/multi không mutation và root paragraph một phương trình hợp lệ.
- Bổ sung assertion sau review có hai kỳ vọng sai trong test: dấu vectơ được lưu ở thuộc tính bằng combining arrow, và ngoặc tròn là mặc định khi thiếu begChr/endChr. Đã sửa oracle để chấp nhận mặc định đúng, vẫn từ chối delimiter sai; không gọi các lần đỏ này là hai lỗi production.
- `mvn -q package`: **114 Java test, 0 failure/error/skip**. Python **136**, workflow **4** đạt. Generated-output gate mới **4/4**, không structural drift.

Review Claude session `675b163e-2674-4748-90ab-1654b1d1ec54` ở [bản review](./claude_dsmt4_nobreak_review_2026-11-06.md). Đây là review trước sửa root/assertion cuối; chưa có review Claude vòng hai. Reviewer không chạy test hoặc UI. Chọn `on` cho nhất quán stylesheet; không kết luận `1` bị mọi schema/Word từ chối. Cả hai spelling đã được Word mở/lưu trong probe.

## Output và kiểm tra bảo toàn

| Phạm vi | OMML chèn | DSMT4 giữ lại | OMML nguồn | OMML output |
| --- | ---: | ---: | ---: | ---: |
| 32 đề | 2.286 = 71 block + 2.215 inline | 331 | 27 | 2.313 |
| 5 đề gốc | 247 | 18 | 18 | 265 |

Còn 10 OLE khác ngoài DSMT4. So với `out/dsmt4-inline-boundary-final-2026-11-06/`, không chuyển thêm hoặc giữ thêm object nào. Tất cả 2.215 inline mới có box. Bỏ đúng outer box mới cho kết quả expression/thuộc tính/text giống baseline, kể cả ký tự khoảng trắng trong `m:t`. Native OMML và display giữ nguyên. Không dùng riêng chuỗi chữ để kết luận cấu trúc đúng.

32/32 tệp qua kiểm tra source hash, package parts, non-math leaf/run properties, paragraph properties, native OMML, mọi OLE đã giữ, OLE còn lại khớp nguồn và embedding bytes. Không còn OMML nằm trong `w:r`. `report.json` ghi từng tệp và hash JAR. Các bộ đếm kỹ thuật `native`/`unresolved` của patcher không thay thế inventory raw XML hoặc số occurrence chưa nghiệm thu.

Các output thử đầu `out/dsmt4-nobreak-2026-11-06/` dùng spelling `1` được giữ nguyên. Bản cuối dùng `on`, dựng bằng JAR sau sửa root; script/log tách riêng. Không sửa source, ZIP, fixture hoặc output lịch sử. FULL_END_ONLY, 108 safety skip ban đầu và hai OLE Lý ¶91 không được mở rộng.

## Word UI đã quan sát

Các thao tác chỉ trên bản QA riêng trong `work/codex-dsmt4-nobreak-2026-11-06/`:

1. Baseline mới mở tái hiện toan086 tách qua trang (`word-baseline-toan086.png`). Probe có box giữ `AB = CD = 16cm` trên một dòng (`word-box-toan086.png`). toan011 vectơ cũng hiện liền trên một dòng (`word-box-toan011.png`).
2. Vào bên trong công thức, thêm `q` thành `AB=CD=1q6cm`, Save As, đóng, mở lại. `word-box-ui-reopened.png` ghi công thức vẫn liền; XML xác nhận `q` trong cấu trúc math/box, không phải prose. Bản QA lưu có 115 `oMath`, 110 box.
3. Probe spelling `on` cũng Save As, đóng, mở lại; `word-box-on-reopened.png` ghi `AB = CD = 16cm` còn liền. Tất cả 115 cây toán của output Toán cuối khớp cây toán của probe `on` trước Word save.

**Word bỏ toàn bộ 110 property `noBreak` khi lưu ở cả hai spelling, giữ đủ 110 box.** Hiển thị sau mở lại ở các probe vẫn liền. Không khẳng định property được giữ nguyên, hoặc mọi công thức vẫn không ngắt sau mọi kiểu sửa. Word hiển thị tổng trang 3 ở probe, baseline là 4; đây chưa phải kiểm định phân trang nguồn/output. Không chứng nhận toàn bộ trang chỉ từ ảnh công thức.

tn019 chưa hoàn thành UI: Mac khóa lại khi đang vào công thức ở probe TN. Ghi `not_run/incomplete`, không suy rộng kết quả từ AB. Không có Writer UI edit/save/reopen mới trong đợt này.

## Writer và HTML kiểm tra giới hạn

Writer headless render output cuối Toán có 4 trang, text và cả 4 PNG trang trùng byte với baseline trước box. TN cuối có 4 trang, trùng text/PNG với probe spelling `1`; đây chỉ là tương đương hai spelling, chưa có so sánh TN trước box trong đợt này. Không thấy ký tự lỗi `¿` trong text của hai PDF. Không dùng quét text làm chứng nhận mọi glyph, hoặc ảnh headless làm UI acceptance. Kết quả trong `writer-final-comparison.json`.

Xuất HTML bằng JAR cuối cho baseline và Toán cuối: **115/115 MathML subtree giống nhau**, gồm node, thuộc tính, text và thứ tự. Đây là regression export có phạm vi, chưa kiểm render trình duyệt hoặc các đề khác. `html-comparison.json` lưu kết quả.

## Còn mở

- Xác nhận tn019 và các trường hợp rộng/bảng/phân trang trên Word UI; cần xem toàn trang, không chỉ số công thức.
- Writer DOCX vẫn có giới hạn quan hệ đầu và mũi tên; tuyến Math riêng còn căn lề hệ và các UI chưa chạy. OLE được giữ có thể hiển thị thiếu ở Writer ngay từ nguồn.
- Chưa làm lại ledger 265 occurrence theo từng ứng dụng trên snapshot cuối. Không dùng tổng failed/needs_review lịch sử làm số nghiệm thu hiện tại; accepted vẫn 0.
- Claude chưa review các sửa root/assertion cuối. Bản review hiện có cùng bằng chứng mới sẵn để review tiếp.

`verification.json`, `checkpoint.md`, log Maven/gate/corpus/HTML và ảnh QA trong thư mục work ghi kết quả, phạm vi và giới hạn. Không đăng mô tả PR hoặc thay trạng thái PR trong đợt này.
