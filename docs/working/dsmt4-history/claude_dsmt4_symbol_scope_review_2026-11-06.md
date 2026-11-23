## Review read-only: phạm vi symbol letterlike và nạp policy dùng chung

**Kết luận:** Không có finding P1/P2 nào về tính đúng của mã. Phần sửa P2 và P3 trước đó đúng về logic. Còn **1 finding P3 về chẩn đoán** và **2 chỗ hở bằng chứng**: số liệu 100 test và việc nạp policy từ JAR chưa kiểm được qua log. Corpus vẫn `needs_review`.

### Đã xác minh bằng đọc mã

- **Policy dùng chung** (`letterlike_policy.xml:5-6`):
  - XSLT chỉ đọc `verified-pure-class` (`mml2omml.xsl:10`, `:812-816`).
  - Java chỉ đọc `review-class` (`MathmlContent.java:22-30`).
  - 4 ký tự ℝℤℕℓ đều nằm trong khối U+2100–214F, nên hai tập không mâu thuẫn nhau:
    - mtext chỉ gồm 4 ký tự này → math run, không có `m:nor` → cổng cho qua.
    - mtext lẫn ký tự khác hoặc ký tự chưa kiểm (ℂ, ℃, 𝑥…) → `m:nor` → cổng giữ OLE.
- **Regex:**
  - Java `Pattern` xử lý đúng dải supplementary U+1D400–1D7FF vì làm việc theo code point.
  - `normalize-space` không bỏ NBSP, nên `ℝ\u00a0` bị giữ OLE. Workflow test có phủ ca này.
- **Giá trị `m:nor`** (`MathmlContent.java:64-70`): khi không có val, hoặc val là 1/on/true, cổng chặn; 0/false/off thì cho qua. Giá trị lạ (ví dụ `OFF`) bị coi là bật, tức là vẫn chặn. Như vậy là an toàn.
- **systemId** (`XsltMathmlToOmmlConverter.java:28-29`):
  - `document('letterlike_policy.xml')` được resolve theo base URI tĩnh của stylesheet.
  - Saxon 12.9 (theo `pom.xml:16`) có nhánh riêng để resolve base URI dạng `jar:`, nên cách làm này hợp lý cả với `target/classes` lẫn `jar-with-dependencies`. Điểm này tôi biết từ hiểu biết về Saxon, chưa chạy thử.
  - Nếu nạp hỏng: `document()` báo lỗi → `IllegalStateException` → `OMML_CONVERSION_FAILED` → giữ OLE. Tức là lỗi theo hướng an toàn, nhưng không ồn ào (xem mục hở bằng chứng 1).
  - Nếu `MathmlContent` thiếu resource: lỗi khởi tạo class là `Error`, không bị `catch (RuntimeException)` nuốt. Cả lượt chạy sẽ dừng ngay, rõ ràng.
- **Test** khớp mô tả:
  - `MathmlContentVectorTest.java:19-43`: ma trận 8 symbol × 7 giá trị val, ca đơn vị `20 km`, và 3 lý do từ chối riêng biệt.
  - `XsltMathmlToOmmlConverterTest.java:214-228`: ℃/№/™/℅/𝑥/ℂ vẫn ở `m:nor`; ca đơn vị và ca mixed.
  - `DocxMathPatchWorkflowTest.java:22-37`: 8 token, skip reason, output trùng từng byte với nguồn.
  - `final-java.log:64-71` có đúng 8 dòng `normal_text_symbol_requires_review`, khớp 8 token. Vậy các ca này bị giữ đúng lý do, dù test không assert chuỗi lý do.

### Finding

**P3: Lý do cụ thể bị mất khi chạy batch có JSONL**
- `DocxToHtmlCli.java:238-241` ép log level thành `SUMMARY` khi bật `--patch-summary-jsonl`.
- `warn()` chỉ in khi level là `WARNINGS` (`DocxMathPatchMain.java:345-347`).
- Phần detail có cấu trúc vẫn chỉ là `"failed: OMML conversion for <part>"` (`:329`).
- Hệ quả: khi rà corpus bằng JSONL, vẫn không tách được object bị giữ do review symbol với object bị giữ do rỗng hoặc thiếu base. P3 cũ mới được sửa một phần.
- Hướng sửa: đưa `rejection` vào phần detail của `SkipClassification`. Vẫn giữ nguyên category nên telemetry không bị ảnh hưởng.

### Hở bằng chứng (chưa phải lỗi mã)

1. **Tuyến nạp policy từ JAR chưa được chứng minh bằng gate.**
   - `out/dsmt4-symbol-scope-2026-11-06/modern-gate` không có `mtext` nào (grep ra 0 kết quả).
   - Theo hiểu biết của tôi, Saxon chỉ tính biến global khi được dùng lần đầu. Khi đó `document()` chỉ chạy lúc xử lý `mtext`, nên gate 4/4 không chứng minh policy nạp được từ JAR.
   - Bằng chứng gián tiếp chỉ có nếu lượt chạy 32 đề dùng JAR trên cây mã hiện tại: các ca ℝ/ℓ dạng mtext ra giống baseline. Tôi không xác nhận được điều kiện đó.
   - Nên thêm một test chạy bộ chuyển trong JAR với `<mtext>ℝ</mtext>`.
2. **Log chưa khớp với các con số báo cáo.**
   - `final-java.log` chạy bằng `mvn -q`, nên không có dòng `Tests run`. Con số "100 test" không kiểm được từ log; chỉ thấy không có `[ERROR]`.
   - Theo thứ tự thời gian sửa file mà Glob trả về (tôi suy ra là cũ trước, mới sau), `final-java.log`, `gate.log` và `corpus*` có vẻ được tạo trước `pure-policy-*.log`. Chưa chắc các lượt chạy đó đã bao gồm phần thu hẹp `verified-pure-class`.
   - `corpus.log` báo 12 file đổi `document.xml` (tổng 48 phương trình), trong khi `corpus-check.json` báo không có khác biệt. Rất có thể `corpus.log` so với file nguồn chứ không so với baseline, nhưng log không ghi rõ.
   - Nên chạy lại không có `-q` trên cây mã hiện tại.

### Mã đã chứng minh và hành vi Word chưa kiểm

- **Đã chứng minh bằng đọc mã:** chỉ ℝℤℕℓ đứng một mình được đổi thành math run. Mọi `m:nor` đang bật mà chứa ký tự thuộc hai khối đều bị giữ OLE.
- **Chưa kiểm trên Word:**
  - Word xử lý ℂ, ℃, №, ™, ℅, 𝑥, ℋ trong `m:nor` ra sao.
  - ℝ khi mtext có `mathvariant` khác (ra `sty` khác `p`).
  - Tác động thật lên đề có đơn vị như `25 ℃`: các đề này sẽ bị giữ OLE. Đây là chi phí cố ý của phạm vi bảo thủ. Theo báo cáo của Codex, 32 đề không phát sinh thêm OLE bị giữ; tôi chưa chạy lại.

### Giới hạn

- Chỉ đọc mã, test, các log và JSON trong `work/codex-dsmt4-symbol-scope-2026-11-06/`, cùng các doc `docs/working` liên quan.
- Không chạy Maven, Python, gate hay corpus; không mở Word/Writer.
- Không sửa file, không commit, push, merge hay đăng lên GitHub.
