# codex_chemistry_fix_directive.md

## Mục tiêu

Tài liệu này là chỉ thị triển khai cho Codex để sửa nhánh hiện tại theo kết quả scan mới nhất của **môn Hóa**.
Mục tiêu là sửa đúng chỗ, không phá chất lượng convert công thức hiện có, và giúp theo dõi rõ cái gì đã fixed, cái gì chưa.

---

## Source of truth

Khi chạy task này, hãy dùng các tài liệu sau làm nguồn sự thật:

1. `core_vs_subject_mapping_and_codex_run.md`
2. `subject_profiles_spec_v1.md`
3. kết quả QA hiện tại của môn Hóa
4. HTML, DOCX, asset bundle, conversion log hiện tại

Nếu có mâu thuẫn:
- ưu tiên **mapping core vs subject**
- sau đó ưu tiên **subject profile chemistry**
- cuối cùng mới tới heuristic cục bộ

---

## Phạm vi task hiện tại

**Current subject: `chemistry`**

Chỉ sửa:
- `core` nếu đó là lỗi thật sự dùng chung
- `chemistry spec` nếu đó là lỗi đặc thù Hóa

Không được:
- sửa rule của Toán hoặc Lý trong task này trừ khi đó là lỗi hạ tầng `core`
- redesign pipeline từ đầu
- migrate sang pipeline generation khác
- hy sinh chất lượng MathML hiện có

---

## Kết quả scan cần bám theo

### 1. Chemical diagram / ChemDraw còn unresolved nhiều
QA hiện tại cho thấy:
- còn nhiều preview/fallback unresolved
- nhóm object nổi bật gồm:
  - `ChemDraw.Document.6.0`
  - `ChemDraw_x64.Document.6.0`
  - `ACD.ChemSketch.20`
  - `ChemWindow.Document`

Ý nghĩa:
- nhánh chemistry diagram hiện chưa đủ tốt
- nhiều ảnh hiện là fallback PNG từ EMF/WMF/OLE, chưa được xem là “resolved cleanly”
- có hiện tượng người dùng thấy **nền trắng / tưởng như mất hình**

### 2. Mũi tên phản ứng còn lỗi trong plain text
Mũi tên trong MathML khá ổn, nhưng mũi tên trong:
- plain text
- lời giải
- đoạn mô tả phản ứng
vẫn có thể bị ra:
- ký tự lạ
- glyph lỗi
- mất ký hiệu
- symbol bị thay thế không đúng

### 3. Đơn vị và ký hiệu hóa học chưa chuẩn hoàn toàn
Các nhóm còn cần kiểm:
- `10^12` bị tách mũ sai
- `80°C` / `80^0C` / `80⁰C`
- `mol·L⁻¹` và các biến thể
- ký hiệu nhiệt hóa như `ΔfH°298`, `ΔrH°298`
- điện tích ion
- số oxi hóa
- formatter đôi khi semantic hóa sai, ví dụ nhóm hóa học bị biến thành điện tích

### 4. Có nguy cơ lỗi số liệu / lời giải
Cần flag QA các trường hợp như:
- số bị cụt
- biểu thức bị méo
- ví dụ kiểu `M = 29` trong ngữ cảnh đáng ra phải lớn hơn nhiều
- biểu thức số học/hóa học có dấu hiệu mất ký tự

---

## Mapping: cái gì vào core, cái gì vào chemistry spec

# A. CORE FIXES (chỉ sửa nếu thật sự dùng chung)

Các lỗi sau chỉ đưa vào `core` nếu implementation của chúng dùng chung được cho nhiều môn:

### CORE-1. Unresolved preview reporting
Cần:
- đếm unresolved preview chính xác
- phân loại unresolved theo object type
- map asset -> fallback type
- đưa unresolved vào QA chung

### CORE-2. Generic fallback/image handling
Cần:
- asset fallback web-safe
- HTML alt/class cleanup cho image/preview
- không để object đã classified là diagram vẫn bị dán nhãn “equation preview”

### CORE-3. HTML cleanup chung
Cần:
- tách ảnh khỏi text sau
- cleanup paragraph/image boundaries
- cleanup inline vs display math boundary
- giữ HTML semantic và nhẹ

### CORE-4. QA improvements
Cần:
- before/after QA JSON
- before/after QA markdown
- unresolved object list
- fixed now / still unresolved / deferred

**Không đưa vào core:**
- chemistry inline notation
- chemistry arrow normalization
- chemistry unit normalization
- chemistry-specific suspicious numeric heuristics
- ChemDraw/ChemSketch/ChemWindow semantics

# B. CHEMISTRY SPEC FIXES (bắt buộc sửa ở chemistry layer)

### CHEM-1. Chemical diagram branch
Mở rộng chemistry object handling cho toàn bộ các ProgID sau:
- `ChemDraw.Document.6.0`
- `ChemDraw_x64.Document.6.0`
- `ACD.ChemSketch.20`
- `ChemWindow.Document`

Yêu cầu:
- classify đúng là `chemical-diagram`
- không để chúng đi nhầm vào equation branch
- render sang SVG nếu được
- fallback PNG nếu cần
- HTML class phải rõ ràng, ví dụ:
  - `chem-diagram`
- alt phải rõ ràng, ví dụ:
  - `Chemical structure diagram`
  - `Chemical reaction scheme`

Không được để alt kiểu:
- `Embedded object preview (...)`
- `Embedded equation preview (...)`

### CHEM-2. Chemical inline notation
Fix các công thức ngắn inline theo semantics Hóa:
- phân tử
- ion
- số oxi hóa
- đồng vị
- nồng độ
- đơn vị hóa học

Ưu tiên:
- dùng `<sub>` / `<sup>` semantic HTML
- không ép toàn bộ sang MathML nếu chỉ là notation ngắn inline

Ví dụ cần chuẩn hóa:
- `H2SO4` -> `H<sub>2</sub>SO<sub>4</sub>`
- `SO4^2-` -> `SO<sub>4</sub><sup>2−</sup>`
- `Al3+` -> `Al<sup>3+</sup>`
- `mol·L^-1` -> `mol·L<sup>−1</sup>`

### CHEM-3. Reaction arrow and chemistry symbol normalization
Phải thêm nhánh normalize riêng cho Hóa để xử lý:
- mũi tên phản ứng
- dấu cộng ion
- dấu trừ điện tích
- mũi tên trong lời giải plain text
- các glyph lỗi thay cho arrow/symbol

Yêu cầu:
- nếu symbol nằm trong MathML đúng rồi thì không đụng vào
- nếu symbol nằm trong plain text bị lỗi thì normalize về dạng đúng
- ưu tiên dùng ký hiệu chuẩn Unicode/HTML thống nhất

Ví dụ cần cover:
- `→`
- `⇌`
- `↑`
- `↓`
- điện tích `+`, `−`
- mũi tên phản ứng trong text thường

### CHEM-4. Chemistry unit normalization
Kiểm tra và chuẩn hóa các dạng sau:
- `mol·L⁻¹`
- `mol.L-1`
- `mol·L^-1`
- `80°C`
- `10^12`
- `ΔfH°298`
- `ΔrH°298`

Yêu cầu:
- không semantic hóa sai
- không tách mũ thành nhiều `<sup>` rời khi phải là một cụm
- không để `80^0C` nếu có thể chuẩn hóa thành `80°C`

### CHEM-5. Suspicious numeric corruption QA
Không tự sửa bừa các số liệu đáng ngờ.

Phải:
- detect
- flag vào QA
- liệt kê trong report

Ví dụ cần flag:
- số bị cụt
- biểu thức có dấu hiệu mất ký tự
- lời giải có quantity sai bất thường

---

## Must-fix now

Các việc này phải ưu tiên ngay trong lần chạy hiện tại:

1. mở rộng nhánh chemical diagram cho:
   - ChemDraw
   - ChemDraw x64
   - ChemSketch
   - ChemWindow

2. bỏ nhãn preview sai bản chất trong HTML
   - không để chemical diagram bị gắn preview label mơ hồ

3. thêm chemistry arrow/symbol normalization cho plain text
   - nhất là phản ứng hóa học trong lời giải

4. chuẩn hóa chemistry inline notation
   - không để chỉ số trên/dưới bị đẩy lên cùng một hàng thiếu tự nhiên

5. chuẩn hóa đơn vị/ký hiệu Hóa quan trọng
   - `mol·L⁻¹`
   - `°C`
   - `10^n`
   - ký hiệu nhiệt hóa

6. tăng QA cho unresolved chemistry objects và suspicious numeric corruption

---

## Nice-to-fix later

Các việc sau có thể để sau nếu lần này chưa đủ chắc:

- cải thiện renderer để ưu tiên SVG hơn PNG cho chemical diagrams
- làm đẹp layout chemical diagrams theo context câu hỏi/lời giải
- mở rộng dictionary text corruption riêng cho Hóa
- tối ưu cache riêng cho chemical diagram assets

---

## Chỉ thị chạy cho Codex

```text
Read this file, `core_vs_subject_mapping_and_codex_run.md`, and `subject_profiles_spec_v1.md` as the source of truth.

Current subject: chemistry

Task:
- preserve the current good MathML quality
- separate shared fixes into Global Core
- implement chemistry-specific fixes only in the chemistry layer
- do not let chemistry rules affect physics or math
- focus on unresolved chemical diagrams, reaction-arrow/plain-text symbol corruption, chemistry inline notation, and chemistry unit normalization
- keep a strict before/after QA trail

Required classification:
- equation
- diagram
- chart
- chemical-diagram
- generic-image
- unknown-preview

Priority order:
1. classify unresolved chemistry objects correctly
2. fix chemistry diagram handling
3. fix reaction arrows / chemistry symbols in plain text
4. fix chemistry inline notation
5. fix chemistry unit normalization
6. rerun QA and report exact progress

Required outputs:
1. summary of issues mapped to core
2. summary of issues mapped to chemistry spec
3. code changes
4. before/after QA JSON
5. before/after QA markdown summary
6. unresolved object list
7. explicit progress list:
   - fixed now
   - still unresolved
   - deferred

Constraints:
- keep the current transpect branch
- do not redesign the pipeline from scratch
- do not migrate pipeline generation
- if a new package is needed, search in this order:
  1. current upstream repos/dependencies
  2. Maven Central / npm / PyPI
  3. maintained GitHub repos
  4. community forks
  5. last resort
```

---

## QA bắt buộc sau khi chạy

### QA JSON
Phải có thêm hoặc cập nhật:
- `subject`
- `total_mathml_formulas`
- `total_previews`
- `equation_dsmt4_preview_count`
- `chemdraw_preview_count`
- `chemwindow_preview_count` nếu có
- `chemsketch_preview_count` nếu có
- `emf_count`
- `wmf_count`
- `chemistry_inline_fix_count`
- `chemistry_arrow_symbol_fix_count`
- `chemistry_unit_fix_count`
- `suspected_numeric_corruption`
- `unresolved_objects`
- `per_exam`

### QA Markdown
Phải có:
- overall chemistry result
- what was fixed in core
- what was fixed in chemistry spec
- remaining unresolved chemistry diagrams
- remaining plain-text symbol issues
- remaining unit/notation issues
- publish verdict

---

## Cách báo tiến độ để không mất dấu

Bắt buộc chia kết quả thành 3 phần:

### Fixed now
Những gì lần này đã sửa xong

### Still unresolved
Những gì còn tồn tại sau QA

### Deferred
Những gì không nên sửa trong task chemistry hiện tại hoặc cần task khác

---

## Phán quyết

Task này là hợp lý và nên ưu tiên.

Lý do:
- lỗi lớn nhất hiện tại của Hóa không còn nằm ở MathML chính mà nằm ở:
  - chemical diagram unresolved
  - reaction arrows / plain-text symbols
  - chemistry unit/notation normalization
- nếu không tách riêng chemistry spec thì rất dễ làm hỏng Toán/Lý
- dùng một task chemistry-focused với QA before/after sẽ giúp theo dõi rõ hơn cái gì đã fixed và cái gì chưa