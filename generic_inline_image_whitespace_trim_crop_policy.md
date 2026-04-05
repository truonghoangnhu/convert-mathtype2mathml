# generic_inline_image_whitespace_trim_crop_policy.md

## Mục tiêu

Task này xử lý riêng nhánh:

**generic inline-image whitespace trim/crop policy**

Mục tiêu là sửa các ảnh `inline-image` kiểu generic còn:
- canvas trắng quá lớn
- nội dung thật rất nhỏ ở giữa
- nhìn như ảnh bị phóng to “khủng khiếp”
- chưa được trim/crop đúng như `chem-diagram`

Task này là **core image pipeline task**, không phải chemistry-only, dù đang được kiểm trên cụm Hóa.

---

## Source of truth

Đọc các tài liệu sau trước khi sửa:

- `core_vs_subject_mapping_and_codex_run.md`
- `subject_profiles_spec_v1.md`
- `core_omml_mathtype_image_policy.md`
- latest HTML / QA / DOCX / asset bundle của cụm đang test
- latest before/after diff
- latest unresolved object reports nếu có

Current validation subject: `chemistry`
Layer classification: **CORE**

---

## Problem statement

Hiện có các ảnh đi theo nhánh:

- `class="inline-image"`

thay vì:

- `class="chem-diagram"`

Một số case đã convert ra PNG/SVG thành công nhưng:
- vùng trắng bao quanh quá lớn
- nội dung thật nằm giữa rất nhỏ
- HTML nhìn như ảnh quá to, dù thực chất là canvas bị dư whitespace
- chemical diagram branch đã có trim riêng, nhưng generic inline-image branch chưa có

Đây là vấn đề của:
- generic image bounding box
- generic image whitespace trim
- generic display sizing

Không phải vấn đề:
- MathML
- OMML equation conversion
- MathType equation conversion
- chemistry arrow normalization

---

## What this task must solve

1. detect generic inline-images with excessive whitespace
2. trim/crop outer whitespace safely
3. preserve actual visual content
4. avoid fake “full-size giant image” appearance
5. keep final HTML web-safe and stable
6. add QA so the problem is measurable and cannot hide

---

## Classification rule

Task này áp cho ảnh được classify là:

- `generic-image`
- `inline-image`

Nó **không** nhắm trực tiếp vào:
- `equation`
- `chem-diagram`
- `physics-diagram`
- `chart`

Tuy vậy, nếu logic trim/crop là generic và tái sử dụng an toàn, hãy đặt trong **core/images** để các role khác có thể opt-in sau.

---

## Root cause model

Vấn đề thường đến từ một trong các nguyên nhân sau:

1. PNG/JPEG canvas có lề trắng rất lớn
2. SVG `viewBox` quá rộng so với nội dung thật
3. asset được export theo canvas gốc của tài liệu thay vì content bbox
4. HTML sizing không sai, nhưng asset nguồn gần như toàn whitespace

Vì vậy chỉ sửa CSS là thường không đủ.

---

## Policy decision

### Allowed
- trim/crop **outer whitespace only**
- trim theo actual content bounding box
- chỉnh SVG `viewBox`
- crop raster theo safe non-white / non-empty bbox
- áp dụng sizing riêng sau khi trim

### Forbidden
- crop mù bằng CSS `overflow:hidden`
- cắt vào nội dung thật
- đổi semantic classification
- đẩy generic image vào MathML/equation pipeline

---

## Rendering and crop policy

### A. For SVG inline-images
Ưu tiên:
1. inspect `viewBox`
2. compute actual content bbox nếu có thể
3. shrink oversized whitespace margins
4. emit trimmed SVG
5. preserve all actual strokes/text/content

Nếu SVG đã có bbox hợp lý thì không sửa.

### B. For PNG/JPEG inline-images
Ưu tiên:
1. inspect raster bounds
2. detect non-background bounding box
3. crop only outer whitespace
4. preserve content fully
5. export trimmed raster asset

Background detection phải conservative:
- support white / near-white backgrounds
- không crop mất nét mờ nhưng có ý nghĩa
- không trim mất nhãn, mũi tên, ký hiệu, trục, annotation

### C. Display sizing after trim
Sau khi trim asset:
- không để ảnh nhìn như full-width giả
- vẫn responsive
- ưu tiên centered block cho figure độc lập
- cap chiều rộng theo trải nghiệm question-bank

Hướng khuyến nghị:
- `display: block`
- `margin: 0.5rem auto`
- `width: auto`
- `max-width` hợp lý cho container câu hỏi
- tránh dùng `max-width: 100%` vô điều kiện nếu sau trim vẫn cho cảm giác quá to

---

## QA requirements

Thêm hoặc cập nhật các metric core sau:

- `generic_inline_image_count`
- `generic_inline_image_trim_candidate_count`
- `generic_inline_image_trim_applied_count`
- `generic_inline_image_oversized_whitespace_count`
- `generic_inline_image_bad_crop_count`
- `generic_inline_image_blank_count`
- `generic_inline_image_near_white_count`

Nếu phù hợp, thêm:
- `generic_inline_image_svg_trim_applied_count`
- `generic_inline_image_raster_trim_applied_count`

Per-exam reporting phải cho thấy:
- nơi nào oversized whitespace vẫn còn
- nơi nào trim đã áp dụng
- nơi nào trim bị skip vì lý do an toàn

---

## Required HTML/output policy

Final published HTML phải thỏa:

- generic inline-image không còn nhìn như khổng lồ do canvas trắng dư
- asset reference trỏ tới output đã trim nếu trim được áp dụng
- class rõ ràng:
  - `inline-image`
  - có thể thêm `inline-image-trimmed`
- không dùng class diagram/equation sai bản chất

Metadata tùy chọn hữu ích:
- `data-trim-applied="true"`
- `data-trim-type="svg-viewbox|raster-bbox"`
- `data-trim-safe="true"`

---

## Package/tool policy

Nếu cần thêm package/tool, tìm theo thứ tự:

1. current upstream repos/dependencies already used by the project
2. Maven Central / npm / PyPI
3. maintained GitHub repos
4. community forks
5. last resort

Selection criteria:
- open source
- headless
- batch-friendly
- integrates with current branch
- safe bbox/viewBox trimming
- low risk of damaging content

Ưu tiên:
- thư viện xử lý ảnh/SVG đã có sẵn trong stack
- Java-friendly integration trước
- sidecar nhỏ chỉ khi thật sự cần

---

## Codex execution directive

```text
Read this file and the latest mapping/spec files as the source of truth.

Current validation subject: chemistry
Layer classification: CORE

Task:
- identify generic inline-image assets with excessive whitespace/canvas
- implement safe whitespace trim/crop for generic inline-images
- keep chemistry diagram logic unchanged unless shared trim code can be reused safely
- do not touch MathML / OMML / MathType equation paths
- do not crop blindly
- preserve actual image content fully
- rerun QA and report progress

Priority order:
1. detect oversized whitespace in generic inline-images
2. implement safe SVG viewBox trim
3. implement safe raster bbox trim
4. apply display sizing improvements after trim
5. rerun QA
6. report exact before/after impact

Required outputs:
1. summary of fixes mapped to core
2. code changes
3. before/after QA JSON
4. before/after QA markdown summary
5. list of generic inline-images trimmed
6. explicit list:
   - fixed now
   - still unresolved
   - deferred
```

---

## Success criteria

Task này chỉ được coi là thành công nếu:

- generic inline-images không còn nhìn như khổng lồ do whitespace-heavy canvas
- trim/crop an toàn, không làm mất nội dung thật
- oversized whitespace count giảm rõ rệt
- bad crop count giữ ở 0
- MathML quality không đổi
- chemistry diagram fixes không bị regress
- final HTML nhìn tự nhiên hơn cho question-bank usage

---

## Final note

Đây nên được coi là một **core asset-cleanup policy** tái sử dụng được cho question-bank ingestion, không phải hack riêng cho Hóa.