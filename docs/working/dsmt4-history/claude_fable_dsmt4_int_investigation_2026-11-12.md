# INT MathML→Writer: điều tra vì sao baseline import đã lỗi trước khi wrap (read-only)

**Kết luận ngắn:** nghi vấn số một là hai dấu `|` trần (`<mo>|</mo>`), được importer chuyển thành `mline` đứng ngoài cặp ngoặc; dấu `|` mở còn nằm chung `mstyle` với dấu tích phân. Chưa đủ bằng chứng để sửa adapter. Cần chạy Probe 1 trước, vì cả hai probe sau đều phụ thuộc kết quả của nó.

**Phạm vi:**
- Đã đọc lượt này: sidecar INT, `prepared-single.mathml`, toàn bộ `prepare_libreoffice_mathml.py`.
- Dùng lại từ các lượt trước trong session: `UI-annotations.json`, hai contact sheet INT (UI và bundled) tôi xem ở độ phân giải thấp, và các Commands của tuyến OMML.
- Tôi không chạy lệnh, không render, và không đọc mã nguồn LibreOffice. Mọi phát biểu về nguyên nhân phía LibreOffice dưới đây là giả thuyết.

## 1. Shape nghi vấn

Sidecar chỉ có một dòng: `…/mathml/wmf/f5b5582c….wmf.mathml:1`. `math` có 21 con trực tiếp; chỉ số tính từ 0.

**Shape A — dấu `|` mở nằm trong `mstyle` cùng dấu tích phân, dấu `|` đóng nằm ngoài:**

- `math/mstyle[2]`: `<mstyle displaystyle="true"><msubsup><mo>∫</mo><mn>0</mn><mn>2</mn></msubsup><mo>|</mo></mstyle>`
- `math/mo[10]`: `<mo>|</mo>`, ngang hàng ở top-level, sau `…+1`.

Hai dấu `|` là `mo` trần, không cân trong cùng một container, và cắt ngang ranh giới `mstyle`. Tích phân thứ nhất không có biểu thức dưới dấu tích phân nào được nhóm lại; thứ duy nhất đi cùng nó trong `mstyle` là dấu `|`.

**Shape B — hai tích phân sau, dùng làm đối chứng tốt:**

- `math/mstyle[14]` và `math/mstyle[18]`: `msubsup(∫)` kèm `<mrow><mo>(</mo>…<mo>)</mo></mrow>` trong cùng `mstyle`.

**Đã chứng minh bằng artifact:**

- **Commands importer sinh ra** cho prepared-single (chỉ áp W) trên 26.8.0.3 (`work/dsmt4-mathml-wrap-2026-11-12/UI-annotations.json:11`):
  `{ S = { int ^ 2 _ 0 mline } 2 x ^ 3 - 3 x ^ 2 + 1 mline d x = { int ^ 1 _ 0 { ( … ) } } d x + … }`
  - Mỗi `<mo>|</mo>` thành một `mline` trần.
  - Shape A thành `{ int ^ 2 _ 0 mline }`: importer lấy dấu `|` làm toán hạng của tích phân.
  - Shape B thành `{ int … { ( … ) } }`.
- **Vị trí ký hiệu lỗi.** Prepared-single không có bảng nhưng vẫn lỗi, trên cả UI 26.8.0.3 và bundled alpha. Trên contact sheet tôi thấy đúng hai ký hiệu đỏ, ở đúng hai vị trí dấu `|`: ngay sau `∫₀²` và ngay sau `+1`. Quanh hai tích phân Shape B không có ký hiệu nào.
- **Phạm vi lỗi.** Vì cả hai binary cùng lỗi, đây là lỗi theo input, không theo binary. Điểm này khác với ca leading-relation ở tuyến OMML.
- **Đối chứng chéo từ tuyến OMML.** Với cùng công thức, Writer nhập OMML thành `<?> "|" 2 {x} ^ {3} … "|"dx`: dấu `|` là văn bản trong ngoặc kép. Báo cáo DOCX khi đó chỉ ghi lỗi quan hệ đầu hàng, không ghi lỗi tại dấu `|` (`work/dsmt4-real-wrap-2026-11-12/commands-odt-annotations.json:14,38`).
- **Adapter hiện tại không có rule nào khớp shape này.**
  - B chỉ nhận `|msub(mi,mi)|=` ở đầu hàng (`prepare_libreoffice_mathml.py:276-287`).
  - G chỉ nhóm `mfenced` có sẵn (`:325-344`).
  - W chỉ bọc `mrow` (`:289-300`).
  - Docstring ghi nhận bung `mfenced` thành các `mo` thanh dọc thì mất thanh (`:326-328`) và cố ý không đưa rule F vào (`:16`).

**Giả thuyết, chưa chứng minh:**

- **H1:** `mline` trần ngoài `left … right` không hợp lệ với parser StarMath, mỗi cái sinh một ký hiệu lỗi. Bằng chứng mới là tương quan vị trí và số lượng trên ảnh độ phân giải thấp.
- **H2:** việc dấu `|` bị bắt làm toán hạng của `int` gây lỗi riêng, hoặc che một lỗi "tích phân thiếu toán hạng". Hiện không tách được với H1.
- **H3:** ở hai biến thể bảng, `mline` lỗi làm `matrix{…}` hỏng cú pháp, nên các hàng bị dàn thành một dòng và có thêm ký hiệu lỗi quanh `=` và `+`. Hiện mới chỉ là đồng xuất hiện; báo cáo wrap cũng ghi "chưa cô lập" (`docs/working/dsmt4-history/codex_dsmt4_mathml_odf_wrap_2026-11-12.md:19`).

## 2. Ba probe scratch, theo thứ tự

Điều kiện chung:
- thư mục scratch mới;
- binary hệ thống 26.8.0.3, headless, profile mới có assert vắng mặt; ghi version;
- input chỉ có MathML, không annotation;
- mỗi probe là một ODT gồm bản gốc và bản đổi đúng một biến;
- mọi biến thể ghi nhãn *diagnostic control, không phải repaired source conversion*;
- bằng chứng lấy từ Commands importer lưu, text PDF (đếm `¿`) và số `mo` còn lại trong presentation đã lưu. Không lấy từ số token.

**Probe 1 — loại token của dấu `|` (phân biệt H1)**

- **Biến đổi:** từ `prepared-single.mathml`, đổi tại chỗ đúng hai phần tử `<mo>|</mo>` thành `<mtext>|</mtext>`. Giữ nguyên vị trí, kể cả cái nằm trong `mstyle[2]`.
- **Kỳ vọng nếu H1 đúng:** Commands có `"|"` thay cho `mline`; số `¿` từ 2 về 0; đủ hai dấu `=` trong presentation lưu.
- **Tiêu chí loại H1:** vẫn còn `¿` tại vị trí dấu `|`, hoặc `¿` xuất hiện ở chỗ khác.
- **Lưu ý đọc kết quả:** nếu hết `¿` nhưng mất dấu `|` hoặc mất `=`, coi là thất bại, giống control raw-stripped trước đây.

**Probe 2 — vị trí dấu `|` so với `mstyle`/`int` (phân biệt H2 với H1)**

- **Biến đổi:** từ bản gốc, vẫn giữ `mo`, chỉ dời `<mo>|</mo>` ra khỏi `mstyle[2]` thành phần tử ngang hàng ngay sau nó.
- **Kỳ vọng:**
  - nếu vẫn đúng hai `¿` và Commands có `mline` nằm ngoài `{ int … }`, thì vị trí không phải nguyên nhân và H1 đủ giải thích;
  - nếu số hoặc vị trí `¿` thay đổi, thì việc bắt toán hạng có vai trò.
- **Biến phụ không tránh được:** tích phân sẽ rỗng toán hạng. Ghi riêng nó nhập thành `<?>` hay thành lỗi.
- **Tiêu chí loại:** chưa có kết quả Probe 1 thì không diễn giải Probe 2.

**Probe 3 — bảng có sụp vì `mline` không (phân biệt H3). Chỉ chạy nếu Probe 1 dương tính.**

- **Biến đổi:** từ `prepared-table.mathml` (đã có rule L), đổi đúng hai dấu `|` như Probe 1.
- **Kỳ vọng nếu H3 đúng:** render ba hàng, không `¿`, Commands `matrix{ … ## { { } = … } ## { + … } }`, đủ hai `=`.
- **Tiêu chí loại H3:** vẫn dàn một dòng hoặc còn `¿` quanh `=`/`+`. Khi đó còn một nguyên nhân khác trong bảng, ví dụ `mstyle` trong `mtd`, và cần probe riêng.
- **Giới hạn:** kể cả khi qua, đây vẫn chỉ là control chẩn đoán. Nó không phải bằng chứng wrap cho INT và không giải quyết căn trái.

## 3. Ứng viên sửa adapter: chưa nên sửa

Khuyến nghị: chưa viết code và chưa mở rộng `prepare()`.

**Lý do:**

- H1 chưa có đối chứng một biến.
- Cặp `|` ở đây cắt ngang ranh giới `mstyle`. Mọi cách "gom thành `mfenced`" đều phải dời nút qua `mstyle`, tức là ràng buộc lại toán hạng của tích phân. Đó là suy diễn cấu trúc nguồn, không còn là bước thích ứng cho importer.
- Sidecar này không cho biết biểu thức dưới dấu tích phân của MTEF gốc nằm ở đâu. `plan.json` của spike wrap đã ghi "do not silently repair operand binding".

**Nếu Probe 1 và Probe 3 dương tính, ứng viên hẹp nhất để bàn** là đổi `mo` thành `mtext` cho dấu `|` trần, không dùng annotation. Guard tối thiểu:

- chỉ `<mo>|</mo>` không thuộc tính, không tail;
- ngoài mọi `mfenced`;
- không trùng shape của rule B hay I;
- toàn công thức có **đúng hai** dấu `|`;
- không có `∣`, `‖`, `{`, `}` hay dấu `:` kiểu tập hợp.

**Phải reject:**

- số dấu `|` lẻ hoặc lớn hơn 2 (`|a|b|c|` mơ hồ);
- dấu `|` làm dấu phân cách (tập hợp, xác suất có điều kiện, "chia hết");
- dấu `|` có `stretchy`/`fence`/`form`;
- dấu `|` trong chỉ số hoặc phân số cao (mất co giãn);
- input có namespace lạ hoặc metadata; hiện đã được giữ nguyên byte (`prepare_libreoffice_mathml.py:412-416`).

**Rủi ro:**

- `mtext` làm mất vai trò toán tử/fence và khả năng co giãn với mọi trình đọc MathML khác. Chỉ được dùng trong candidate riêng cho LibreOffice, không đụng normalized MathML/OMML.
- Sau khi Writer lưu, presentation sẽ mang `mtext`. Cần kiểm reimport presentation-only như đã làm với rule L.
- Không sinh annotation StarMath cho shape này. Annotation có quyền quyết định trong importer đã đo, và chưa có cách chứng minh hai biểu diễn tương ứng.
- Provenance: mọi thay đổi phải ghi rule kèm path vào report; `status` vẫn là `needs_review`.
- Ô tích phân rỗng (□) là vấn đề nguồn riêng. Rule này không sửa nó, và không được coi là đã sửa.

## 4. Roadmap ưu tiên

1. **Chạy Probe 1, rồi Probe 2 và Probe 3 cho INT.** Chỉ sau đó mới quyết định có bàn rule cho dấu `|` hay xếp INT vào nhóm shape không hỗ trợ có lý do rõ ràng.
2. **GUI edit/save-close-reopen cho leading relation.** Dùng hai sidecar đã đo (`b=c=2,5`, `P=72/720=1/10`, biến thể rule L) trên Writer 26.8.0.3. Việc này đang bị chặn vì CUA Finder bị từ chối; headless không thay được. Cần:
   - bắt Commands trước và sau;
   - sửa một hằng;
   - lưu ODT, đóng, mở lại, xuất PDF;
   - kiểm nhóm rỗng `{ }` có sửa được bằng tay và có hiện placeholder không.
3. **Công thức dài thật, cao, sát mép trang, toàn đề.** Hai sidecar ngắn vốn vừa cột 180pt nên không phải bằng chứng wrap. Cần:
   - ít nhất một công thức thật sự tràn cột; EXP đã có UI nhưng chỉ ở dạng hàng nối bắt đầu bằng dấu một ngôi;
   - một hệ cao có phân số lồng;
   - một ca cuối trang;
   - sau đó đặt vào bố cục đề gốc.
   - Căn trái vẫn chưa giải được nếu không có annotation: `columnalign` bị bỏ khi nhập.
4. **Tách hẳn nhánh Word và Writer trong chính sách.**
   - Word/OMML: bỏ box để Word tự ngắt. Hiện mới có bằng chứng render-only; còn thiếu edit–save–reopen và đánh giá việc Word lưu U+2212 thành "-".
   - Writer/MathML→ODF: rule L cho quan hệ đầu hàng.
   - Ghi rõ "eqArr có hàng bắt đầu bằng quan hệ không an toàn với Writer qua DOCX trên 26.8.0.3".
   - Không có workaround dùng chung.
5. **Quy tắc promotion corpus.** Định nghĩa trước tiêu chí cho từng occurrence:
   - provenance OLE↔sidecar được kiểm ở mức MTEF, không chỉ theo vị trí;
   - baseline import sạch trên binary đã ghi;
   - roundtrip GUI;
   - đủ token quan hệ trong presentation lưu;
   - không dựa vào số token, hash hay số object.
   - Giữ nguyên cho tới khi tiêu chí được duyệt: accepted = 0, FULL_END_ONLY unsupported, safety skips và hai OLE Lý ¶91.

**Chưa kiểm:** nội dung ZIP của các ODT đã lưu, PDF/PNG gốc ở độ phân giải đầy đủ, mã nguồn LibreOffice, và ngữ nghĩa MTEF/BIN của công thức INT.

---

## Codex assessment of the handoff (not experiment results)

Fable completed on requested model claude-fable-5-2 in the existing session. Its proposed INT causes remain hypotheses, not established LibreOffice source-level causes. Failure on both measured binaries does not alone establish a binary-independent input defect; they may share importer behavior. Changing mo to mtext alters operator/fence semantics and is authorized only as an explicitly labelled diagnostic control; exactly two bars is not a sufficient production guard against conditional probability, divisibility, set-builder or other ambiguous usage. Moving the opening bar across mstyle also changes operand grouping and is a confounded control for integral binding; do not interpret it as a source-equivalent repair. No red marker is not content acceptance, especially in light of the earlier stripped-raw equals-loss control. Primary agent must run and visually verify any selected probe before proposing a converter rule. No probe, production fix, GUI acceptance or corpus promotion was performed in this planning/delegation turn.
