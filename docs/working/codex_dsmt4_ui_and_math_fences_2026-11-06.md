# DSMT4 UI and LibreOffice Math follow-up 2026-11-06

Đã sửa hai điểm telemetry và bốn nhóm lỗi nhập MathML vào LibreOffice Math. **Chưa nghiệm thu DSMT4 toàn bộ.** Các phép thử dưới đây chỉ nâng bằng chứng cho nội dung/chỉnh sửa của từng công thức; font, spacing, vị trí trong đề và mọi lần lưu của Word/Writer vẫn cần được đối chiếu riêng. Không commit/push/merge hoặc đổi Draft PR #4.

## Mã và phạm vi đã sửa

- `conversion_diagnostics` nay có `conversion_exception` cho ngoại lệ trong pipeline chuẩn hóa/chuyển/kiểm tra. Lý do gate từ chối được đếm đúng một lần bằng nhánh return riêng. Map trong summary là snapshot bất biến, sắp khóa theo tên; không rò số đếm khi cùng patcher chạy tài liệu tiếp theo. Constructor cũ vẫn dùng map rỗng; constructor mới yêu cầu map khác null như các map inventory khác.
- **G:** `mfenced separators=""`, nhiều đối số, cặp `()` hoặc `||`, không có thuộc tính khác hoặc mixed text có nghĩa → gom đối số thành một `mrow`. Giữ nguyên `mfenced`, cặp ngoặc và ký tự. Không mở rộng thành các `mo` như F. L/T và I/B không chạy trên `mrow` bên trong `mfenced`, cả ở lần chuẩn bị lại, để tránh tự mở rộng phạm vi chưa probe. Chỉ XML whitespace ` \t\r\n` được coi là không có nội dung.
- **C:** chỉ `msup` với base `mi` một chữ ASCII; exponent `+`, hoặc `mrow(mn 2/3, mo +)` không có thuộc tính, thêm nhóm rỗng bên phải dấu cộng. Không đổi dấu cộng thành text, không đoán ion từ preview; không mở rộng sang `4+`, biểu thức `n+`, dấu âm hay script phức tạp.
- **I:** chỉ toàn bộ `mrow` gồm đúng `[`, hai `mn` số thập phân dấu phẩy dương, `;`, `)` không có thuộc tính → biểu diễn cùng nội dung bằng một `mfenced open="[" close=")" separators=""` có một nhóm con. Không áp dụng cho endpoint âm/biến hay cặp ngoặc khác.
- **B:** chỉ `mrow` bắt đầu bằng `|msub(mi,mi)|=...` (các `mi` là một chữ ASCII), các token bao không có thuộc tính → giữ operand nguyên và đưa cặp `|` vào `mfenced`. Không tìm cặp thanh tùy ý hoặc sửa quan hệ chia hết.

Mọi quy tắc trên thuộc `scripts/transpect/prepare_libreoffice_mathml.py`, tuyến Math riêng. Không áp dụng vào normalized MathML/OMML Word. Mixed namespace/metadata vẫn giữ nguyên byte và báo cần review. F vẫn ngoài production. Mọi candidate vẫn `needs_review`, không phải accepted.

## Bằng chứng render và nguồn

`out/dsmt4-math-compat-2026-11-06/mathml/` chứa 265 candidate mới được tạo **trực tiếp từ `source_mathml`** trong ledger gốc. So với 265 MathML đã chuẩn bị trước: đúng **34 file đổi, 231 file giữ nguyên byte**. Trong đó 21 G, 7 C, 5 I, 1 B. Script `generate_final.py` đối chiếu độc lập với các biến thể thử đã render; không dùng hàm production để tạo expected. Không sửa nguồn/ZIP/fixture/output cũ.

- 21 G: xem tất cả cặp raw/G trong hai trang `all21/render-*.png`, rồi chia batch nhỏ để có đủ **42/42 StarMath annotation** sau lưu. Batch 42 object đầu tiên chỉ serialize 20 object đang nạp; 22 storage còn nguyên MathML nên annotation null. Không coi null là đã đối chiếu annotation. Bản cũ được giữ để audit.
- 13 C/I/B: xem hết raw/trial trên `remaining-all13/render-1.png`. Quy tắc `form="postfix"` không sửa ion; nhóm rỗng sửa được. Phép thử chuyển base `(` của ký hiệu độ sang empty-base **vẫn lỗi**, không tích hợp.
- **Production thật:** nhập 34 MathML mới, xuất PDF, lưu ODT rồi xuất PDF sau mở lại theo batch 14/14/6. Xem ba ảnh `final-production/{1,2,3}/production-reopened-1.png`; **34/34 annotation có mặt**, ngoặc/giới hạn/chỉ số/điện tích đúng ở các lỗi đang sửa. Đây là bản công thức cô lập, không phải bố cục toàn đề.

Tất cả script, raw/trial, log, ảnh và ODT kiểm chứng ở `work/codex-dsmt4-math-fences-2026-11-06/`. Đường dẫn source/hash trong `out/dsmt4-math-compat-2026-11-06/preparation.json` dùng để định danh, không dùng làm bằng chứng đúng công thức.

## UI thực tế

Thao tác qua `cua_repl` trên bản QA riêng, thêm `q` **trong Math editor**, lưu, đóng, mở lại, vào editor và xem công thức:

| Tuyến | Ca mới | Kết quả và giới hạn |
| --- | --- | --- |
| Writer DOCX, công thức tách riêng từ OMML cuối | hoa021, li004, li008, toan013, toan054 | Giữ phản ứng/chỉ số, căn chứa phân số, ¹⁴₆C, ba dòng hệ, tích phân với ngoặc lồng và q sau mở lại. Không chứng minh vị trí trong đề. |
| Math trong ODT tách riêng | li008, toan015, toan053, tn004 | Nội dung và q giữ sau mở lại; toan015 vẫn căn giữa các dòng nên **layout vẫn failed**. `frac` trong command tn004 là cú pháp Math; ảnh hiển thị phân số đúng, không phải chữ “frac” trên trang. |
| Math trong ODT, G | toan062 | Hai thanh trị tuyệt đối, x+2, phần còn lại và q đúng sau mở lại. |
| Math trong ODT, C/I/B | hoa023, hoa058, toan046, tn020 | Giữ 2+/3+, H+, [2,7;3,0), |e_c| và ℓ sau mở lại. Đầu vào trial tương đương canonical với candidate production của cùng ca. |

Ảnh/AX của năm ca Writer và bốn Math đầu ở `work/codex-dsmt4-ui-followup-2026-11-06/`; G ở `all21/ui-toan062-*`; C/I/B ở `remaining-all13/ui-*-reopened*`.

Đã lưu–đóng–mở lại **toàn DOCX** Lý, Toán, TN qua Writer, thêm `QA ` trong phần chữ để buộc serialize. OMML lần lượt 18/115/22, OLE 3/0/10 giữ số lượng. Chữ ngoài toán chỉ khác tiền tố QA; tuyến tính toán chỉ khác li002 thêm q (`p,`→`p,q`). Đây là audit lexical, không bảo đảm cấu trúc/style/layout. li002 đã sửa trong editor, lưu và mở lại toàn đề; chưa xem trực tiếp vùng công thức đó sau mở lại (XML và PDF headless có q). OLE gốc đầu tiên trong Lý báo “General OLE error” khi thử kích hoạt; không mở rộng hỗ trợ OLE đó và không coi nó là lỗi OMML mới.

Mac khóa lại ở lần định xem lại li002, sau khi các ca UI nêu trong bảng đã xong. Không thao tác tài liệu cá nhân khác và không giả lập kết quả cho phần chưa xem.

## Test và review

- Java: `mvn -o package`, **102 test**, 0 lỗi; `java-package.log`.
- Python: **128 test**, 0 lỗi; `final-boundaries-green.log`.
- Workflow: **4 test**; `workflow.log`.
- Modern generated-output gate: **4/4**, output mới `out/dsmt4-math-compat-2026-11-06/modern-gate/`.
- Test đỏ trước sửa: `telemetry-red.log` ở thư mục UI; `cli-red.log`, `cascade-red-confirmed.log`, `remaining-cli-red-confirmed.log` ở thư mục Math. Không chạy lại toàn bộ audit BIN hoặc render 32 đề vì không có thay đổi vào tuyến nội dung OMML trong đợt Math này.

Claude đã review telemetry (không P1/P2; sửa thứ tự key và ngoại lệ) và G. Phát hiện cascade L/T của G đã có regression đỏ→xanh; kiểm nguồn thực và batch annotation đã làm bổ sung. Ghi chú “default separator render đúng” trong review không phù hợp ảnh probe `(xy)` mất dấu phẩy; giữ cảnh báo untested cho separator ngoài phạm vi. Review cuối C/I/B và G ở `claude_dsmt4_math_compat_final_review_2026-11-06.md`: không có lỗi chặn. Đã siết thêm I/B và L/T ở mọi ngữ cảnh bên trong fence, giữ bản chạy lại ổn định; chặn base rỗng/vô hình/ngoài mẫu chữ ASCII. Có test đỏ trước sửa cho các ranh giới này, toàn bộ 128 Python xanh sau sửa. Các path được ghi rõ là trên cây candidate; metadata C dùng `exponent`/`shape` thay vì suy đó là ion. Claude đọc snapshot 125-test, các guard/test cuối được Codex kiểm riêng. `current-policy-check.json` xác nhận 265/265 payload hiện tại giữ nguyên byte so với bộ đã render; không chạy lại render không cần thiết.

## Phần còn mở

Trong **36 lỗi nhập/render Math của ledger cũ**, lỗi đã nêu của 34 ca được giải quyết ở tuyến Math cô lập. Hai ca giữ lỗi: toan015 căn hàng hệ; tn022 `t(°C)` do script có base `(`. Không tuyên bố 34 ca đạt mọi tiêu chí nghiệm thu.

Ledger gốc 265 occurrence được giữ nguyên (`accepted 0 / needs_review 219 / failed 46`). Overlay mới chỉ thay các lỗi Math đã kiểm, giữ mọi trạng thái Word/Writer khác để không vô tình xóa finding. Word vẫn có spacing li002/li010, ngắt công thức toan086 và các câu hỏi font/phân trang; Writer DOCX vẫn có `>`/nhãn mũi tên. Hầu hết occurrence chưa được sửa–mở lại qua UI. FULL_END_ONLY unsupported, các safety skip/OLE giữ nguyên. Corpus vẫn needs_review.

Overlay ở `out/dsmt4-math-compat-2026-11-06/ledger-overlay.json` giữ finding Word/Writer của ledger cũ. Nếu chỉ áp dụng các sửa Math vừa kiểm: aggregate suy ra là **accepted 0 / needs_review 251 / failed 14 / unsupported 0**; riêng Math còn 2 failed. Đây là trạng thái suy ra từ overlay có phạm vi, không phải một lượt nghiệm thu mới 265 occurrence.

Đầu ra chẩn đoán C đã đổi tên trường thành `exponent` và thêm `shape`, report có `path_space: candidate_tree`. Không ghi đè preparation.json của snapshot trước; report schema hiện tại trong `current-policy-check.json`.
