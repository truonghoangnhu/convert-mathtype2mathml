# core-vs-subject mapping + codex run spec

Tài liệu này là **một nguồn duy nhất** để Codex chạy và theo dõi tiến độ sửa lỗi, nhằm tránh tình trạng không rõ cái gì đã fix và cái gì chưa.

Mục tiêu:
- tách lỗi phổ biến chung vào `core`
- tách lỗi riêng vào `subject spec`
- dùng cùng một file làm **mapping + chỉ thị chạy**
- buộc Codex xuất QA trước/sau để theo dõi tiến độ

---

## 1) Cách dùng file này trong Codex

Dùng file này làm **source of truth**.

Mỗi lần chạy Codex:
1. đọc file này trước
2. xác định `subject=<generic|math|physics|chemistry|biology>`
3. chỉ sửa trong phạm vi được phép
4. cập nhật QA trước/sau
5. báo rõ:
   - lỗi nào thuộc `core`
   - lỗi nào thuộc `subject spec`
   - lỗi nào đã fixed
   - lỗi nào còn unresolved

---

## 2) Quy tắc chung cho Codex

### Bắt buộc
- giữ nhánh transpect hiện tại
- không redesign pipeline từ đầu
- không migrate sang pipeline generation khác ở giai đoạn này
- không hy sinh chất lượng MathML hiện đang tốt
- không để rule của môn này ảnh hưởng sang môn khác
- mọi thay đổi phải đo được bằng QA before/after

### Khi cần thêm package mới
Tìm theo thứ tự này:
1. upstream repo / dependency hiện đang dùng
   - transpect
   - Apache POI
   - dependency hiện có
2. registry chính thức
   - Maven Central
   - npm
   - PyPI
3. maintained GitHub repo
4. community fork
5. last resort

Ưu tiên:
- open source
- tương thích với nhánh hiện tại
- ít phá kiến trúc hiện có

---

## 3) Mapping lỗi: đưa vào core hay subject spec

# A. CORE — lỗi phổ biến chung, sửa một lần cho nhiều môn

Những lỗi sau phải nằm ở `core`, không đẩy xuống từng môn.

### CORE-1. Object classification chung
Áp cho mọi môn.

Đưa vào core:
- classifier theo `progId`
- classifier theo extension
- classifier theo alt text
- classifier theo surrounding context
- output object class chuẩn:
  - `equation`
  - `diagram`
  - `chart`
  - `chemical-diagram`
  - `generic-image`
  - `unknown-preview`

Ví dụ chung:
- `Equation.DSMT4` -> `equation`
- `Visio.Drawing.15` -> `diagram` hoặc `chart`
- `ChemDraw*.Document.*` -> `chemical-diagram`

### CORE-2. Preview fallback handling
Đưa vào core:
- detect preview còn sót
- count preview theo loại
- unresolved object list
- fallback tracking
- mapping asset -> fallback type

Ví dụ lỗi thuộc core:
- `Embedded equation preview`
- `.emf` / `.wmf` preview còn sót
- object có alt/label sai bản chất

### CORE-3. HTML cleanup chung
Đưa vào core:
- không để ảnh dính vào text sau
- chuẩn hóa inline vs display math
- cleanup paragraph/table/image boundaries
- sửa alt/class sai kiểu “equation preview” cho diagram
- giảm DOM nặng, bẩn, không semantic

Ví dụ lỗi thuộc core:
- `<img ...>Câu 5`
- `div.math-block` chèn sai trong luồng câu
- diagram nhưng alt vẫn là equation preview

### CORE-4. CSS nền dùng chung
Đưa vào core:
- `math-inline`
- `math-block`
- `docx-table`
- `inline-image`
- image block classes
- base spacing/line-height an toàn

### CORE-5. QA framework chung
Đưa vào core:
- QA JSON schema
- QA Markdown summary
- per-exam summary
- unresolved object report
- before/after diff summary

Field QA chung tối thiểu:
- total MathML formulas
- total previews
- count by progId/type
- emf count
- wmf count
- unresolved objects
- per exam/de issue counts

### CORE-6. Cache + batch conversion
Đưa vào core:
- persistent hash-based cache
- sidecar MathML cache
- deduplicate repeated assets
- batch conversion strategy
- skip reconversion when hash already exists

### CORE-7. Safe global normalization only
Chỉ các rule cực an toàn mới được nằm ở core:
- whitespace cleanup
- encoding cleanup cơ bản
- HTML entity cleanup
- normalization cực hiển nhiên, không phụ thuộc môn

Không được đặt ở core:
- rewrite công thức hóa học
- rewrite chỉ số vật lý
- rewrite ký hiệu toán học
- rewrite notation sinh học

---

# B. SUBJECT SPEC — lỗi riêng theo môn

## B1. MATH SPEC
Chỉ giữ các rule đặc thù Toán.

Đưa vào math spec:
- notation toán inline/display
- vector
- log
- tích phân
- ma trận
- khoảng `[a;b)`
- tọa độ, hình học giải tích
- bảng ghép nhóm của toán thống kê
- graph/diagram placement đặc thù toán nếu cần

Không được cho Chemistry/Physics rule chạm vào:
- chỉ số toán
- số mũ toán
- ký hiệu hàm
- ký hiệu tập hợp, giới hạn, đạo hàm

## B2. PHYSICS SPEC
Đưa vào physics spec:
- `Visio.Drawing.15` semantics cho mechanics/electric/lab diagrams
- graph/chart semantics cho đồ thị vật lý
- physics unit cleanup
- physics corruption dictionary
- physics-safe inline indices

Ví dụ lỗi riêng của Lý:
- đồ thị/sơ đồ thí nghiệm/mạch điện bị coi là equation
- `điện trờ`
- `thừi điềm`
- `Mpa`
- `c m²`
- chỉ số vật lý kiểu `v₀`, `x₁`, `U₀`, `I₀`

Physics spec không được:
- chemistry hóa các chỉ số vật lý
- biến mọi sub/sup thành `<sub>/<sup>` kiểu công thức hóa

## B3. CHEMISTRY SPEC
Đưa vào chemistry spec:
- chemical inline notation
- ChemDraw branch
- chemistry unit/symbol normalization
- ion / oxidation-state handling
- chemistry suspicious numeric QA
- chemistry corruption dictionary

Ví dụ lỗi riêng của Hóa:
- công thức inline Unicode sub/sup bị đẩy lên cùng một hàng, nhìn không tự nhiên
- `ChemDraw_x64.Document.6.0`
- `ChemDraw.Document.6.0`
- ion và điện tích hiển thị xấu
- `mol·L⁻¹` / `mol.L-1` / `mol·L^-1`
- numeric corruption kiểu `211,8*0 = 8472`
- text corruption như `Trọng giai đoạn`, `T lag`, `Có 2 tố thí nghiệm`

Chemistry spec phải ưu tiên:
- công thức hóa học ngắn inline -> semantic HTML `<sub>/<sup>`
- ChemDraw -> SVG hoặc PNG
- không áp dụng rule này ngoài `subject=chemistry`

## B4. BIOLOGY SPEC
Để dành sau, nhưng nguyên tắc:
- gene/protein/chromosome notation riêng
- không dùng chemistry rules mù
- không dùng math rules mù

---

## 4) Mapping lỗi phổ biến đã quan sát

### Nhóm lỗi phổ biến chung -> CORE
- preview fallback còn sót
- unresolved asset
- alt/class sai
- html cleanup chưa sạch
- image-text boundary lỗi
- block/inline math boundary lỗi
- QA không đồng nhất
- cache/batch chưa tối ưu

### Nhóm lỗi riêng Toán -> MATH SPEC
- notation toán
- interval/table notation
- vector/log/integral safety
- không cho chemistry/physics rewrite chạm vào

### Nhóm lỗi riêng Lý -> PHYSICS SPEC
- visio/mechanics/electric/lab diagrams
- chart semantics
- physics units
- text corruption dictionary riêng
- physics inline variable indices

### Nhóm lỗi riêng Hóa -> CHEMISTRY SPEC
- chemical inline notation
- ChemDraw
- chemistry units / ion / oxidation states
- suspicious numeric corruption
- chemistry text normalization riêng

---

## 5) Chỉ thị chạy cho Codex

Dùng nguyên văn phần này khi chạy.

```text
Read this file as the single source of truth.

Task:
- separate shared fixes into Global Core
- separate subject-specific fixes into the correct subject spec
- preserve the current good MathML quality
- do not let one subject’s rules affect another subject
- classify every unresolved object into:
  equation / diagram / chart / chemical-diagram / generic-image / unknown-preview
- implement fixes only in the right layer:
  core vs selected subject profile
- produce a before/after QA report so we can track what is fixed and what is still unresolved

Current subject: <generic|math|physics|chemistry|biology>

Required outputs:
1. summary of issues mapped to core
2. summary of issues mapped to the selected subject spec
3. code changes
4. before/after QA JSON
5. before/after QA markdown summary
6. unresolved object list
7. explicit list:
   - fixed now
   - still unresolved
   - deferred to another subject spec

Constraints:
- keep the current transpect branch
- do not redesign the pipeline from scratch
- do not migrate pipeline generation now
- if a new package is needed, search in this order:
  1. current upstream repos/dependencies
  2. Maven Central / npm / PyPI
  3. maintained GitHub repos
  4. community forks
  5. last resort

Execution order:
1. identify shared issues -> core
2. identify subject-specific issues -> selected subject spec
3. implement core-safe fixes first
4. implement selected subject fixes second
5. rerun QA
6. report exactly what changed
```

---

## 6) QA format bắt buộc

Codex phải xuất ít nhất:

### QA JSON
- subject
- total_mathml_formulas
- total_previews
- count by preview/object type
- emf_count
- wmf_count
- text_fix_count
- chemistry_inline_fix_count if subject=chemistry
- unresolved_objects
- per_exam summary

### QA Markdown
Phải có:
- overall result
- what was fixed in core
- what was fixed in subject spec
- what remains unresolved
- publish verdict

---

## 7) Nguyên tắc để không mất dấu tiến độ

Mỗi lần chạy Codex phải ghi rõ 3 mục:

### Fixed now
Các lỗi đã sửa xong trong lần chạy này

### Still unresolved
Các lỗi còn tồn tại sau QA

### Deferred
Các lỗi không thuộc subject hiện tại hoặc không thuộc core, sẽ xử lý ở profile khác

Ví dụ:
- chemistry inline notation thấy trong file physics -> deferred, not fixed here
- visio diagram issue thấy trong chemistry file -> core or deferred depending on classification

---

## 8) Phán quyết triển khai

Đề nghị “scan kỹ để tách lỗi phổ biến chung vào core, lỗi riêng vào spec” là **hợp lý và nên làm**.

Lý do:
- giúp không bị lẫn cái gì đã fixed
- giúp Codex báo tiến độ rõ
- tránh sửa Hóa làm hỏng Lý/Toán
- giúp QA theo dõi được ở mức core vs subject
- phù hợp với cách dùng Codex/GPT-5.4: một source-of-truth rõ + một lệnh chạy ngắn, chặt
