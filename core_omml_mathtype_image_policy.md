# core_omml_mathtype_image_policy.md

## Mục tiêu

Tài liệu này chốt policy kiến trúc cho `question_bank` và pipeline convert:

- lỗi nào thuộc **core**
- lỗi nào thuộc **subject spec**
- đặc biệt cho 3 nhóm xuyên môn:
  - `OMML`
  - `MathType`
  - `image/diagram`

Mục tiêu là tránh vá lặp lại theo từng môn cho các lỗi thực chất thuộc tầng nguồn công thức hoặc tầng render chung.

---

## Nguyên tắc tổng quát

Nếu lỗi thuộc về:

- **loại nguồn công thức**
- **loại object nhúng**
- **tầng render/chuyển đổi chung**
- **tầng QA chung**

thì đưa vào **core**.

Nếu lỗi thuộc về:

- ký hiệu chuyên ngành
- đơn vị chuyên ngành
- quy ước hiển thị theo môn
- semantic cleanup theo nội dung môn học

thì đưa vào **subject spec**.

---

## 1) OMML policy

### Đưa vào core

Các lỗi sau của OMML phải nằm ở `core`:

- parse OMML
- detect OMML runs/equations
- OMML -> MathML conversion
- OMML -> HTML wrapper generation
- grouping lỗi do converter OMML sinh ra
- superscript/subscript lỗi do nhánh OMML sinh ra
- spacing/baseline lỗi ở render wrapper chung của OMML
- cache/QA cho OMML equations
- thống kê số lượng OMML equations
- regression test cho OMML rendering

### Không đưa vào subject spec

Không nên sửa ở từng môn nếu lỗi thật sự nằm ở:
- parser OMML
- converter OMML
- HTML/CSS wrapper chung của OMML
- grouping exponent/subscript do OMML conversion tạo ra

### Chỉ giữ ở subject spec
Sau khi OMML đã convert xong, các phần sau mới thuộc từng môn:
- Hóa:
  - `80°C`
  - `ΔfH°298`
  - `ΔrH°298`
  - điện tích ion
  - số oxi hóa
- Lý:
  - `cm²`
  - `MPa`
  - `v₀`, `I₀`, `x₁`
- Toán:
  - vector
  - log
  - integral
  - interval
  - matrix

### Kết luận cho OMML
**OMML source parsing/conversion/render bugs -> core**
**subject semantics after OMML conversion -> subject spec**

---

## 2) MathType policy

### Đưa vào core

Các lỗi sau của MathType phải nằm ở `core`:

- detect `Equation.DSMT4`
- MathType source resolution:
  - WMF
  - BIN
  - OLE
  - sidecar MathML
- MathType -> MathML conversion
- MathType fallback policy
- preview/fallback handling
- cache theo hash
- batch conversion strategy
- QA count cho MathType equations
- unresolved MathType reporting

### Không đưa vào subject spec
Không nên vá theo từng môn nếu lỗi nằm ở:
- MathType extraction
- WMF/BIN selection
- sidecar generation
- preview fallback
- HTML wrapper chung cho MathType output

### Chỉ giữ ở subject spec
Sau khi MathType đã convert xong, phần subject spec chỉ nên làm:
- normalize notation theo môn
- sửa đơn vị/ký hiệu theo domain
- flag semantic corruption theo ngữ cảnh môn học

### Kết luận cho MathType
**MathType source parsing/conversion/render bugs -> core**
**subject semantics after MathType conversion -> subject spec**

---

## 3) Image / Diagram policy

### Đưa vào core

Các lỗi sau phải nằm ở `core`:

- object classification chung:
  - `equation`
  - `diagram`
  - `chart`
  - `chemical-diagram`
  - `generic-image`
  - `unknown-preview`
- preview fallback handling
- EMF/WMF source routing
- image render pipeline
- SVG/PNG output policy
- blank-image detection
- near-white detection
- tiny-image detection
- bad-crop detection
- oversized display detection framework
- HTML image wrapper chung
- alt/class cleanup chung
- per-object render QA
- unresolved object reporting

### Core object family mapping

Ít nhất phải support các mapping sau:

- `Equation.DSMT4` -> `equation`
- `Visio.Drawing.15` -> `diagram` hoặc `chart`
- `ChemDraw*.Document.*` -> `chemical-diagram`
- `ACD.ChemSketch.20` -> `chemical-diagram`
- `ChemWindow.Document` -> `chemical-diagram`
- `.emf` / `.wmf` -> resolve theo context và object family

### Không đưa vào subject spec
Không nên sửa theo môn nếu lỗi nằm ở:
- object classification
- fallback preview logic
- metafile rendering
- blank image
- placeholder policy
- generic image sizing framework

### Chỉ giữ ở subject spec
Phần subject spec chỉ nên làm:
- semantics của diagram theo môn
- styling/sizing riêng nếu cần
- domain-specific alt/label
- rule hiển thị riêng theo loại diagram

Ví dụ:
- Physics:
  - mechanics/electric/lab diagram semantics
- Chemistry:
  - chemical structure diagram semantics
  - reaction scheme semantics
- Math:
  - graph/coordinate figure semantics

### Kết luận cho image/diagram
**diagram/image classification/render bugs -> core**
**domain-specific diagram semantics/display tuning -> subject spec**

---

## 4) Subject spec policy

Subject spec chỉ nên xử lý:

### Math spec
- notation toán
- vector
- log
- integral
- matrix
- interval
- math-specific table/graph formatting

### Physics spec
- unit vật lý
- chỉ số vật lý
- chart semantics
- physics text corruption dictionary
- physics diagram semantics

### Chemistry spec
- chemical inline notation
- chemistry arrow/symbol normalization
- chemistry unit normalization
- chemistry numeric suspicion QA
- chemical-diagram display semantics
- chemistry text corruption dictionary

### Biology spec
- gene/protein/chromosome notation
- biology-specific symbol cleanup

---

## 5) Core modules đề xuất

Nên tách core thành các module theo source type và render type:

### Core source modules
- `core/omml/`
- `core/mathtype/`
- `core/objects/`
- `core/images/`
- `core/qa/`
- `core/html/`

### Core responsibilities

#### `core/omml`
- detect OMML
- parse OMML
- convert OMML
- emit HTML/MathML wrapper
- OMML QA metrics

#### `core/mathtype`
- detect Equation.DSMT4 / MathType assets
- resolve WMF/BIN/OLE
- sidecar MathML cache
- batch conversion
- MathType QA metrics

#### `core/objects`
- generic classifier
- ProgID mapping
- source family mapping
- unresolved object inventory

#### `core/images`
- render SVG/PNG
- blank/near-white/tiny/bad-crop checks
- image sizing framework
- placeholder policy

#### `core/html`
- wrapper generation
- image/text boundary cleanup
- inline/display math cleanup
- common CSS classes

#### `core/qa`
- JSON schema
- Markdown summary
- before/after diff metrics
- fixed / unresolved / deferred reporting

---

## 6) Decision rules cho Codex/dev

### Rule 1
If a bug can appear in **Math, Physics, Chemistry** because they share:
- OMML
- MathType
- image/diagram pipeline

=> put it in **core**

### Rule 2
If a bug appears only when:
- chemistry notation is semantically wrong
- physics units are wrong
- math notation is rewritten incorrectly

=> put it in **subject spec**

### Rule 3
Do not patch in subject spec if the bug lives in:
- converter
- parser
- wrapper
- classifier
- fallback policy
- generic QA

### Rule 4
Subject spec may only adjust after:
- source type is parsed
- object is classified
- shared render layer has completed

---

## 7) Ví dụ mapping cụ thể

### Case A: OMML exponent grouping lỗi
=> **core/omml**

### Case B: `80^0C` trong Hóa
If caused by generic OMML wrapper/converter:
=> **core/omml**

If OMML is already structurally correct and Chemistry needs nicer notation afterward:
=> **chemistry spec**

### Case C: MathType preview fallback lỗi
=> **core/mathtype**

### Case D: `Visio.Drawing.15` bị coi là equation
=> **core/objects** + **core/images**

### Case E: `ChemDraw.Document.6.0` bị blank image
=> **core/images** + **core/objects**
If later Chemistry wants special display sizing:
=> **chemistry spec**

### Case F: `CO` bị semantic hóa thành `CO⁻`
=> **chemistry spec**

### Case G: `v₀` bị chemistry rule chạm vào
=> bug của **subject isolation policy**
- core keeps the boundary
- fix in dispatcher / subject spec boundary

---

## 8) Policy cho question_bank

Với `question_bank`, không để runtime phụ thuộc trực tiếp vào:
- Word UI
- OpenOffice/LibreOffice như renderer chính
- patch ad-hoc theo từng câu

Question bank nên lưu theo asset model:

- `asset_type`
- `source_family`
- `render_status`
- `rendered_format`
- `qa_flags`
- `subject`

### Asset type ví dụ
- `equation_omml`
- `equation_mathtype`
- `diagram_physics`
- `diagram_chemistry`
- `generic_image`

### Source family ví dụ
- `omml`
- `mathtype`
- `visio`
- `chemdraw`
- `chemsketch`
- `chemwindow`

### Render status ví dụ
- `rendered`
- `fallback`
- `placeholder`
- `unresolved`

### Rendered format ví dụ
- `mathml`
- `svg`
- `png`

### QA flags ví dụ
- `blank`
- `near_white`
- `tiny`
- `bad_crop`
- `oversized_display`
- `suspicious_numeric`

---

## 9) Chỉ thị ngắn cho Codex

```text
Use this file as policy.

When a bug is reported, first classify it as one of:
- OMML source bug
- MathType source bug
- image/diagram pipeline bug
- subject semantics bug

Then apply this rule:
- OMML source bugs -> core
- MathType source bugs -> core
- image/diagram classification/render bugs -> core
- subject notation/semantics/unit cleanup -> subject spec

Do not patch source-type bugs inside chemistry/physics/math spec unless there is a very strong reason and it is explicitly documented as temporary.

Always report:
1. issue classification
2. why it belongs in core or subject spec
3. code area to change
4. QA impact
```

---

## 10) Phán quyết cuối

**Có, nếu OMML lỗi thì nên chuyển về core.**
**Có, nếu MathType lỗi thì cũng nên chuyển về core.**
**Có, nếu image/diagram classification/render lỗi thì cũng nên chuyển về core.**

Chỉ phần:
- notation theo môn
- đơn vị theo môn
- semantic cleanup theo môn

mới nên để ở `subject spec`.

Đây là cách đúng nhất để:
- tránh vá lặp theo từng môn
- giúp `question_bank` ổn định lâu dài
- theo dõi QA rõ ràng theo source type và subject layer