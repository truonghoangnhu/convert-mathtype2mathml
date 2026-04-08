# Phase G - DOCX Export Hardening And Parity Review

## Mục tiêu

Phase G chốt phần `teacher_exam` DOCX export prototype theo hướng:

- harden failure policy
- review parity giữa HTML source và DOCX exported output
- tạo regression target riêng cho exporter
- chuẩn bị note cho styling/template phase kế tiếp

Đây là phase ổn định chất lượng, không phải phase mở thêm mode export mới.

## Kết quả đã hoàn tất

### 1. Parity review

Đã thêm parity checker ở:

- [`scripts/export/docx_export_parity.py`](/Users/truonghoangnhu/Desktop/transpect-branch-project/scripts/export/docx_export_parity.py)

Nó so sánh:

- `exam_bundle.json`
- HTML source tương ứng
- DOCX export output

Các điểm đang kiểm:

- question count
- section titles
- math presence
- image presence
- answer summary presence
- solution cue presence
- openability / zip integrity

### 2. Failure policy hardening

Đã harden policy trong exporter ở:

- [`scripts/export/docx_exporter.py`](/Users/truonghoangnhu/Desktop/transpect-branch-project/scripts/export/docx_exporter.py)

Hiện trạng:

- math/image degradation có ngưỡng rõ ràng
- `answer_summary_zone_missing` được xét theo ngữ cảnh
- zip integrity là blocker
- openability check là blocker theo policy mặc định

### 3. Regression target riêng cho DOCX export

Đã thêm bộ regression riêng:

- [`regression_set/docx_export_inventory.json`](/Users/truonghoangnhu/Desktop/transpect-branch-project/regression_set/docx_export_inventory.json)
- [`scripts/regression/run_docx_export_regression.py`](/Users/truonghoangnhu/Desktop/transpect-branch-project/scripts/regression/run_docx_export_regression.py)

Coverage:

- OMML-clean sample
- real sample với images và answer summary
- harder sample nhiều math/OLE/preview hơn

### 4. Styling readiness note

Đã thêm note:

- [`docs/docx_export_styling_readiness_v1.md`](/Users/truonghoangnhu/Desktop/transpect-branch-project/docs/docx_export_styling_readiness_v1.md)

Nội dung chốt:

- built-in WordprocessingML styles first
- template support để v2 sau
- giữ layout deterministic trước khi đi sâu vào theme/template

## Kết quả kiểm chứng thực tế

Regression run gần nhất:

- [`out/docx-export-regression-20260408-132014/docx_export_regression_report.json`](/Users/truonghoangnhu/Desktop/transpect-branch-project/out/docx-export-regression-20260408-132014/docx_export_regression_report.json)
- [`out/docx-export-regression-20260408-132014/docx_export_regression_report.md`](/Users/truonghoangnhu/Desktop/transpect-branch-project/out/docx-export-regression-20260408-132014/docx_export_regression_report.md)

Tóm tắt:

- `passed_count = 0`
- `needs_review_count = 3`
- `failed_count = 0`
- regression verdict = `passed`

Parity result:

- OMML-clean: `parity_ok`
- Math sample: `parity_ok`
- Hard OLE sample: `parity_ok`

Điểm quan trọng:

- `question_count` parity đã khớp trên cả 3 case
- `zip_integrity` pass
- content parity không còn mismatch thực chất

## Lưu ý môi trường

`soffice`/LibreOffice headless round-trip đang abort trên máy này.

Hệ quả:

- openability check vẫn là blocker trong policy mặc định
- regression target dùng override hẹp để tách lỗi môi trường khỏi lỗi nội dung

Điều này không đổi thiết kế policy, chỉ giúp kiểm parity vẫn chạy được trong workspace hiện tại.

## File / artifact chính

- [`docs/docx_export_parity_report_v1.md`](/Users/truonghoangnhu/Desktop/transpect-branch-project/docs/docx_export_parity_report_v1.md)
- [`docs/docx_export_failure_policy_v1.md`](/Users/truonghoangnhu/Desktop/transpect-branch-project/docs/docx_export_failure_policy_v1.md)
- [`docs/docx_export_regression_target_v1.md`](/Users/truonghoangnhu/Desktop/transpect-branch-project/docs/docx_export_regression_target_v1.md)
- [`scripts/export/docx_export_report_schema_v1.json`](/Users/truonghoangnhu/Desktop/transpect-branch-project/scripts/export/docx_export_report_schema_v1.json)
- [`regression_set/docx_export_failure_policy_regression.json`](/Users/truonghoangnhu/Desktop/transpect-branch-project/regression_set/docx_export_failure_policy_regression.json)

## Kết luận

Phase G đã đạt mục tiêu hardening + parity review cho DOCX export prototype.

Hiện trạng:

- export prototype vẫn là `teacher_exam` only
- parity giữa HTML source và DOCX export đã được đo và đạt trên bộ regression nhỏ
- failure policy rõ hơn và có thể điều chỉnh theo môi trường
- regression target riêng đã có
- styling/template phase tiếp theo có đầu vào rõ ràng hơn

