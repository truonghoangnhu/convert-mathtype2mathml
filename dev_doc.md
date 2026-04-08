# DEV DOC — Tóm tắt chức năng chính đã làm (trạng thái hiện tại)

Tài liệu này tóm tắt nhanh các chức năng đã có trong package hiện tại, dựa trên code đang chạy trong repo.

## 1) Mục tiêu hệ thống

- Convert `DOCX -> HTML` cho ngân hàng đề.
- Giữ chất lượng công thức:
  - OMML -> MathML trực tiếp.
  - MathType WMF/BIN -> MathML sidecar (qua transpect).
- Có QA định lượng sau convert để chốt publish/cleanup.

## 2) Thành phần chính

### Java core converter
- CLI entry: [DocxToHtmlCli.java](/Users/truonghoangnhu/Desktop/transpect-branch-project/src/main/java/com/example/docxmath/DocxToHtmlCli.java)
- Engine chính: [DocxToHtmlConverter.java](/Users/truonghoangnhu/Desktop/transpect-branch-project/src/main/java/com/example/docxmath/DocxToHtmlConverter.java)
- OMML transformer: [OmmlToMathmlTransformer.java](/Users/truonghoangnhu/Desktop/transpect-branch-project/src/main/java/com/example/docxmath/OmmlToMathmlTransformer.java)
- Sidecar registry: [MathmlSidecarRegistry.java](/Users/truonghoangnhu/Desktop/transpect-branch-project/src/main/java/com/example/docxmath/MathmlSidecarRegistry.java)

### Subject profile layer
- Subject detect/factory/rules:
  - [SubjectDetector.java](/Users/truonghoangnhu/Desktop/transpect-branch-project/src/main/java/com/example/docxmath/SubjectDetector.java)
  - [SubjectProfileFactory.java](/Users/truonghoangnhu/Desktop/transpect-branch-project/src/main/java/com/example/docxmath/SubjectProfileFactory.java)
  - [SubjectRules.java](/Users/truonghoangnhu/Desktop/transpect-branch-project/src/main/java/com/example/docxmath/SubjectRules.java)
- Profile theo môn:
  - [GenericProfile.java](/Users/truonghoangnhu/Desktop/transpect-branch-project/src/main/java/com/example/docxmath/GenericProfile.java)
  - [PhysicsProfile.java](/Users/truonghoangnhu/Desktop/transpect-branch-project/src/main/java/com/example/docxmath/PhysicsProfile.java)
  - [ChemistryProfile.java](/Users/truonghoangnhu/Desktop/transpect-branch-project/src/main/java/com/example/docxmath/ChemistryProfile.java)
  - [MathProfile.java](/Users/truonghoangnhu/Desktop/transpect-branch-project/src/main/java/com/example/docxmath/MathProfile.java)
  - [BiologyProfile.java](/Users/truonghoangnhu/Desktop/transpect-branch-project/src/main/java/com/example/docxmath/BiologyProfile.java)

### Pipeline scripts
- Wrapper convert end-to-end: [run_docx_with_transpect.sh](/Users/truonghoangnhu/Desktop/transpect-branch-project/scripts/transpect/run_docx_with_transpect.sh)
- Generate sidecar MathML: [generate_sidecars.sh](/Users/truonghoangnhu/Desktop/transpect-branch-project/scripts/transpect/generate_sidecars.sh)
- QA audit bundle: [audit_exam_bundle.py](/Users/truonghoangnhu/Desktop/transpect-branch-project/scripts/qa/audit_exam_bundle.py)
- Batch runner: [run_subject_batch.py](/Users/truonghoangnhu/Desktop/transpect-branch-project/scripts/batch/run_subject_batch.py)
- Cleanup generated artifacts: [cleanup_generated_artifacts.py](/Users/truonghoangnhu/Desktop/transpect-branch-project/scripts/cleanup/cleanup_generated_artifacts.py)

## 3) Chức năng đã implement trong converter

### 3.1 Math conversion
- OMML -> MathML qua XSLT `omml2mml.xsl`.
- Hỗ trợ sidecar MathML cho MathType assets từ manifest TSV.
- Render inline/display MathML + MathJax (có option `--native-mathml-only`).

### 3.2 OLE/object classification + asset handling
- Phân loại object theo equation/diagram/chemical-diagram/generic.
- Ưu tiên dùng MathML cho equation nếu có sidecar.
- OLE preview fallback chỉ dùng khi không convert được.
- Có xử lý Visio/ChemDraw/MathType theo nhánh riêng trong render object.

### 3.3 Text normalization theo môn
- Generic normalization (lỗi encoding phổ biến, đơn vị cơ bản).
- Physics: fix lỗi đơn vị và corruption phổ biến (`cm²`, `cm³`, `mol⁻¹`, `MPa`, typo tiếng Việt).
- Chemistry: fix glyph legacy (mũi tên, dấu), unit/inline chemistry, một số lỗi số liệu/pattern đã quy định.
- Math: cleanup glyph/text residual của đề Toán.

### 3.4 Chemistry inline notation + script normalization
- Chuẩn hóa token hóa học inline (`sub/sup`) và ký hiệu electron/charge.
- Chuẩn hóa nhiệt độ dạng `^0C -> °C` ở ngữ cảnh phù hợp.
- Giữ MathML đúng, tránh rewrite semantics rộng tay.

### 3.5 Core HTML cleanup / publish sanitize
- Loại leakage Word field code (`INCLUDEPICTURE`, `MERGEFORMAT...`).
- Cleanup empty paragraph chain quanh table/math/image.
- Cleanup flow math-block bị lỗi.
- Suppress ảnh standalone blank/invisible.
- Suppress nonessential standalone context image theo rule bảo thủ + có cơ chế restore context image cần giữ.
- Sanitization output publish (đếm leakage debug attrs/namespace qua QA).

### 3.6 Image/diagram policy
- Rasterize EMF/WMF sang PNG khi cần (ưu tiên external tool, fallback POI).
- Có cache raster để tránh convert lặp.
- Generic inline-image trim tracking (`trim-candidate`, `trim-applied`, bad-crop guard).
- Chính sách web-safe image được QA theo dõi (`.emf/.wmf/.gif placeholder`, violations).

### 3.7 Figure placement policy
- Tách role `context-figure` vs `essential-figure`.
- Context figure: layout text-left/image-right (responsive mobile stack) trong nhánh phù hợp.
- Essential figure: render centered block, không ép vào side-cell hẹp.
- Rule essential table-figure đã được mở rộng reusable ở core cho non-math cases.

### 3.8 Metrics và timing tích hợp
- Converter trả `ConversionSummary` gồm:
  - counters chuyển đổi, fallback, fix count, suppression count.
  - timing theo stage (docx load, omml, mathtype, image render, cleanup, build, sanitize, write).

## 4) Orchestration invariant đã có

Trong wrapper [run_docx_with_transpect.sh](/Users/truonghoangnhu/Desktop/transpect-branch-project/scripts/transpect/run_docx_with_transpect.sh):

- Explicit single input `.docx` (không nhận output artifacts làm input).
- Per-input lock theo canonical path, có stale-lock recovery.
- Cache key theo input hash + toolchain fingerprint + args.
- Cache hit thì skip convert, không chạy lại vô ích.
- Log rõ lý do start conversion (`start reason`), run id, input hash.
- Ghi timing TSV cho từng run.

Trong batch [run_subject_batch.py](/Users/truonghoangnhu/Desktop/transpect-branch-project/scripts/batch/run_subject_batch.py):

- Mặc định không recursive discovery.
- Recursive scan chỉ chạy khi có `--allow-recursive-discovery`.
- Exclude `out/`, `work/`, `_files/` khỏi discovery.
- Hỗ trợ reuse theo fingerprint để tránh reconvert.

## 5) QA/reporting đã có

Script [audit_exam_bundle.py](/Users/truonghoangnhu/Desktop/transpect-branch-project/scripts/qa/audit_exam_bundle.py) xuất JSON/MD gồm:

- Totals: MathML, preview, corruption, inline issues.
- Count-by-type: `Equation.DSMT4`, `Visio`, `ChemDraw`, `.emf`, `.wmf`.
- Unresolved objects list có classification + fallback metadata.
- Publish verdict (`safe to publish` / `still needs cleanup`).
- Metrics mở rộng:
  - chemistry/physics/math residual counters
  - word field leakage
  - generic inline image trim/bad crop
  - web-safe asset violations
  - chemical-diagram quality metrics

## 6) Cleanup vận hành

Script [cleanup_generated_artifacts.py](/Users/truonghoangnhu/Desktop/transpect-branch-project/scripts/cleanup/cleanup_generated_artifacts.py):

- Dọn `work/` và `out/` run dirs cũ theo tuổi.
- Dọn orphan assets không còn được HTML tham chiếu.
- Có mode `dry-run` và `--apply`.
- Có `keep_latest` để giữ lại các run gần nhất.
- Có xuất report JSON để audit dọn dẹp.

## 7) Output artifacts chuẩn

Mỗi run thường tạo:
- `*-transpect.html`
- `*_files/` assets
- `*.conversion.log`
- `*.qa.json`
- `*.qa.md`
- `run.timings.tsv`

## 8) Ghi chú trạng thái

- Project hiện tối ưu theo hướng pipeline thực dụng cho dữ liệu đề thực tế nhiều nguồn.
- Trọng tâm hiện tại là ổn định publish output, giữ fidelity MathML, và có QA đủ chi tiết để đóng vòng fix.
