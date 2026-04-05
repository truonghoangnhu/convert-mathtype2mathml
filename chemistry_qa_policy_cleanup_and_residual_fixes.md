# chemistry_qa_policy_cleanup_and_residual_fixes.md

## Mục tiêu

Task này xử lý 3 nhóm vấn đề còn lại của môn Hóa sau khi đã:
- loại blank chemical-diagram
- thay nhiều placeholder bằng SVG

Nhưng hiện vẫn còn các vấn đề sau:
1. QA policy chưa phản ánh đúng trạng thái đã render thành công
2. Một số `chem-diagram` đang hiển thị quá to, gần như full width
3. Chemistry text residual issues vẫn còn:
   - mũi tên phản ứng ra ký tự lạ
   - ký hiệu nhường/nhận electron ra glyph lỗi
   - một số đơn vị/ký hiệu hóa học còn sai

---

## Source of truth

Đọc các file sau trước khi sửa:
- `core_vs_subject_mapping_and_codex_run.md`
- `subject_profiles_spec_v1.md`
- `codex_chemistry_fix_directive.md`
- `blank_chemical_diagram_escalation_for_codex.md`
- `unsupported_chemical_diagram_placeholder_to_real_rendered_output.md`
- QA before/after mới nhất
- unresolved object report mới nhất
- HTML output mới nhất

Current subject: `chemistry`

---

## 1. Vấn đề hiện tại cần chốt

### A. QA policy chưa đúng
Hiện có nhiều `chem-diagram` đã:
- `render_attempted = true`
- `render_output_type = svg`
- `render_success = true`

nhưng QA vẫn tiếp tục đếm chúng như preview/unresolved.

Việc này làm khó theo dõi tiến độ vì:
- ảnh đã nhìn thấy được trên HTML
- nhưng QA vẫn báo giống như chưa xử lý xong

### B. Chemical diagram hiển thị quá to
Hiện CSS nền đang để:
- `.chem-diagram { max-width: 100%; height: auto; }`

Điều này an toàn về responsive, nhưng với cấu trúc hóa học nhỏ thì có thể bị kéo to gần full width container, nhìn không tự nhiên.

Task này phải sửa để:
- không còn chemical diagram phóng to vô lý
- vẫn responsive
- không crop mất nội dung quan trọng

### C. Chemistry text residual issues
Còn phải xử lý các lỗi text/glyph như:
- mũi tên phản ứng hóa học ra ký tự lạ
- ký hiệu nhường / nhận electron ra ký tự lỗi
- plain-text reaction arrow chưa normalize xong
- một số notation như `10^12`, `80°C`, `ΔfH°298`, điện tích ion còn có nguy cơ format chưa đúng

---

## 2. Mapping: cái gì vào core, cái gì vào chemistry spec

# A. CORE FIXES

### CORE-1. QA policy cleanup
Đưa vào core:
- phân biệt rõ:
  - `rendered-successfully`
  - `fallback-preview`
  - `placeholder`
  - `unresolved`
- object chemistry đã render SVG/PNG thành công thì không nên tiếp tục bị đếm như preview chưa xử lý

### CORE-2. Generic image sizing framework
Đưa vào core:
- khung sizing chung cho ảnh nhúng
- hỗ trợ image role–specific sizing
- không hardcode full width cho mọi diagram
- cho phép subject layer đặt class sizing riêng

### CORE-3. Generic crop/bounding-box QA
Đưa vào core:
- detect tiny image
- detect bad crop
- detect oversized display
- detect suspicious whitespace margin
- detect blank/near-white image

# B. CHEMISTRY SPEC FIXES

### CHEM-1. Chemical diagram display sizing
Đưa vào chemistry spec:
- rule hiển thị riêng cho `chem-diagram`
- không để cấu trúc hóa học nhỏ bị phóng to gần full width
- ưu tiên:
  - giới hạn chiều rộng hiển thị hợp lý
  - giữ tỷ lệ
  - căn giữa nếu là diagram độc lập
  - vẫn responsive trên màn hình nhỏ

Yêu cầu:
- không crop mất liên kết/nhánh cấu trúc
- không scale quá lớn khi ảnh gốc nhỏ
- nếu SVG có bounding box quá rộng do whitespace, cho phép trim/crop theo `viewBox` hoặc bbox hợp lý

### CHEM-2. Chemistry arrow/symbol normalization
Đưa vào chemistry spec:
- normalize plain-text reaction arrows
- normalize glyph lỗi trong đoạn nhường/nhận e
- không đụng vào MathML đã đúng

Phải cover các trường hợp như:
- `` -> `→`
- glyph lỗi của arrow
- dấu `+`, `−` cho ion/electron
- electron transfer text như:
  - `2Cl⁻ → 2e + Cl₂`
  - `Na⁺ + e → Na`
  - các dòng nửa phản ứng

Nếu là text thường, normalize về ký hiệu chuẩn.
Nếu là MathML đúng rồi thì bỏ qua.

### CHEM-3. Chemistry notation cleanup
Đưa vào chemistry spec:
- `10^12` không được bung thành nhiều `<sup>` rời
- `80^0C` nên chuẩn hóa thành `80°C`
- `ΔfH°298`, `ΔrH°298` phải giữ đúng cụm ký hiệu
- điện tích ion và số oxi hóa không được semantic hóa sai
- không biến nhóm hóa học thành điện tích giả

### CHEM-4. Suspicious semantic corruption QA
Đưa vào chemistry spec:
- detect các lỗi kiểu:
  - `M = 29`
  - `211,8*0 = 8472`
  - `CO` bị thành `CO⁻`
- flag vào QA, không tự sửa bừa nếu chưa chắc

---

## 3. Xử lý ảnh bị to / crop như thế nào

### Quyết định
**Có thể crop, nhưng chỉ crop theo bbox/viewBox an toàn, không crop mù bằng CSS overflow hidden.**

### Không nên làm
- không dùng CSS crop cứng kiểu cắt mất phần cấu trúc
- không ép width 100% cho mọi chemical diagram
- không scale cùng một rule cho mọi ảnh

### Nên làm
1. nếu là SVG:
   - kiểm tra `viewBox`
   - trim whitespace thừa nếu bbox quá rộng
   - giữ nội dung thật, bỏ lề trắng lớn
2. nếu là PNG:
   - detect bounding box vùng có nét vẽ
   - crop whitespace ngoài cùng nếu an toàn
3. khi hiển thị HTML:
   - dùng class sizing riêng cho chemistry diagrams
   - ví dụ giới hạn:
     - `max-width` vừa phải
     - `width: auto`
     - `display: block`
     - `margin: 0.5rem auto`
   - không mặc định phóng full width trừ khi ảnh thực sự lớn

### Mục tiêu
- cấu trúc hóa học nhìn tự nhiên như hình minh họa trong đề
- không chiếm full chiều ngang khi không cần
- không mất nhánh/nhóm chức
- vẫn responsive

---

## 4. Chỉ thị chạy cho Codex

```text
Read this file and the latest chemistry mapping/spec files as the source of truth.

Current subject: chemistry

Task:
- clean up QA policy so successfully rendered chemical diagrams are no longer counted as unresolved previews
- fix chemistry diagram display sizing so diagrams do not blow up to near full width unnecessarily
- add safe crop/trim logic for chemical diagrams when whitespace/viewBox is excessive
- fix residual chemistry plain-text symbol issues:
  - reaction arrows
  - electron transfer notation
  - ion/electron glyph corruption
- fix residual chemistry notation issues:
  - 10^12 grouping
  - 80°C formatting
  - ΔfH°298 / ΔrH°298 grouping
  - avoid false semantic conversion such as turning chemistry groups into charges

Rules:
- do not reclassify chemical diagrams as equations
- do not send chemical diagrams into MathML conversion
- do not regress current MathML quality
- do not regress blank-image fixes
- do not apply chemistry fixes to physics or math
- do not crop chemical diagrams blindly; crop only with safe bbox/viewBox logic

Priority order:
1. QA policy cleanup
2. chemical diagram display sizing
3. safe crop/trim for oversized whitespace
4. chemistry arrow/symbol normalization
5. chemistry notation grouping fixes
6. rerun QA

Required outputs:
1. summary of fixes mapped to core
2. summary of fixes mapped to chemistry spec
3. code changes
4. before/after QA JSON
5. before/after QA markdown summary
6. unresolved object list
7. explicit progress list:
   - fixed now
   - still unresolved
   - deferred
```

---

## 5. QA bắt buộc sau khi chạy

### QA JSON
Phải có hoặc cập nhật:
- `subject`
- `total_mathml_formulas`
- `total_previews`
- `chemical_diagram_rendered_svg_count`
- `chemical_diagram_rendered_png_count`
- `chemical_diagram_placeholder_count`
- `chemical_diagram_render_failed_count`
- `chemical_diagram_blank_image_count`
- `chemical_diagram_near_white_image_count`
- `chemical_diagram_tiny_image_count`
- `chemical_diagram_bad_crop_count`
- `chemical_diagram_oversized_display_count`
- `chemistry_arrow_symbol_fix_count`
- `remaining_chemistry_arrow_symbol_issues`
- `chemistry_unit_fix_count`
- `remaining_chemistry_unit_issues`
- `suspected_numeric_corruption`
- `unresolved_objects`
- `per_exam`

### QA Markdown
Phải có:
- overall chemistry result
- what changed in QA policy
- what changed in chemical diagram display sizing
- whether crop/trim was applied
- remaining arrow/symbol issues
- remaining notation/unit issues
- publish verdict

---

## 6. Success criteria

Task chỉ được coi là thành công nếu:
- MathML count không giảm
- chemical diagram blank images không quay lại
- chemical diagrams không còn bị phóng full width vô lý
- crop/trim không làm mất nội dung cấu trúc
- reaction arrows / electron transfer text giảm lỗi rõ rệt
- QA phản ánh đúng object nào đã render thành công thay vì tiếp tục gọi tất cả là unresolved preview

---

## 7. Phán quyết

Đây là task cần làm tiếp ngay sau chemical-diagram rendering.

Lý do:
- renderer đã khá hơn rõ rệt
- nhưng QA policy hiện còn làm mờ tiến độ thật
- chemical diagram display chưa đẹp
- chemistry text residual issues vẫn ảnh hưởng chất lượng publish
