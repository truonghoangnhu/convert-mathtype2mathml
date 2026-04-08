# next_steps_roadmap.md

## Mục tiêu

Tài liệu này chốt các bước tiếp theo cho gói convert sau khi đã có:
- converter thực dụng chạy được
- subject profiles theo môn
- publish cleanup
- figure placement policies
- QA/reporting
- orchestration invariants
- performance/timing foundation

Mục tiêu của giai đoạn tiếp theo:
- khóa contract đầu ra
- khóa publish behavior
- giảm hồi quy
- chuẩn bị cho export linh hoạt và tích hợp về sau
- chưa gộp vào `question_bank` vội

---

## Nguyên tắc giai đoạn này

1. ưu tiên ổn định gói convert trước
2. không mở rộng tích hợp `question_bank` quá sớm
3. mọi thay đổi lớn phải có:
   - output contract
   - QA impact
   - regression coverage
4. tách rõ:
   - internal preview mode
   - publish output mode

---

## Priority 1 — khóa JSON output contract

### Mục tiêu
Chuẩn hóa output machine-readable để về sau:
- nhập vào `question_bank`
- review
- export sang định dạng khác
- test tự động

### Deliverables
- `manifest.json`
- `exam_bundle.json`
- `question_bank_items.json`
- `qa.json`

### Việc cần làm
- định nghĩa schema version
- khóa field bắt buộc/tùy chọn
- chuẩn hóa enum:
  - question types
  - asset roles
  - placements
  - QA severities
- đảm bảo mỗi run có thể sinh output contract ổn định

### Success criteria
- cùng một input và cùng toolchain cho ra output contract nhất quán
- parser/reviewer có thể dựa hoàn toàn vào JSON, không cần đọc HTML thô để hiểu cấu trúc câu

---

## Priority 2 — khóa internal mode vs publish mode

### Mục tiêu
Tách rõ output phục vụ dev/QA và output phục vụ người dùng cuối.

### Internal mode
Giữ:
- namespace nội bộ
- debug attrs
- provenance
- QA metadata
- source tracing

### Publish mode
Strip:
- debug attrs không cần
- namespace nội bộ không cần
- field leakage
- provenance lộ ra user-facing output

### Việc cần làm
- chốt cờ/chế độ chạy rõ ràng
- serializer/publish cleanup cuối
- QA riêng cho publish mode

### Success criteria
- internal preview vẫn giàu metadata cho dev
- publish output sạch, tối giản, không lộ chi tiết không cần thiết

---

## Priority 3 — khóa publish gates

### Mục tiêu
Không để output “gần đúng” được gắn `safe to publish` một cách mơ hồ.

### Việc cần làm
Chia rõ issue levels:
- `info`
- `warning`
- `error`
- `blocker`

### Gợi ý blocker
- unresolved equation/preview còn sót
- Word field leakage
- unresolved object còn tồn tại
- output publish còn placeholder rõ ràng
- critical image/content missing

### Gợi ý warning
- context figure layout chưa đẹp
- typography còn thô
- image chưa trim tối ưu nhưng vẫn đọc được

### Success criteria
- `publish_verdict` phản ánh đúng trải nghiệm thực tế
- QA không còn “đẹp hơn HTML thật”

---

## Priority 4 — core promotion workflow

### Mục tiêu
Ngăn vá lặp lại theo từng môn mãi mãi.

### Việc cần làm
Tạo thư mục docs:
```text
docs/core-promotion/
```

Mỗi lỗi lặp xuyên môn có 1 note:
- mô tả lỗi
- đã thấy ở môn nào
- hiện ở spec hay promote lên core
- QA impact
- phạm vi fix

### Rule
- thấy lại ở 2 môn trở lên -> mở note đề xuất promote
- thấy lại ở 3 môn -> gần như bắt buộc đưa vào core trừ khi có lý do rõ

### Success criteria
- giảm patch lặp
- boundary core/spec rõ hơn sau mỗi vòng fix

---

## Priority 5 — regression exam set

### Mục tiêu
Biến các case đã dùng để fix thành bộ regression chuẩn.

### Bộ regression đề xuất
- 2 đề Hóa
- 2 đề Lý
- 2 đề Toán
- 1 file OLE/preview khó
- 1 file OMML sạch

### Với mỗi file lưu:
- source DOCX
- output HTML chuẩn tham chiếu
- QA JSON tham chiếu
- note các vùng trọng điểm cần so

### Success criteria
- mọi thay đổi core đều được chạy qua regression set
- regression có thể phát hiện:
  - MathML giảm
  - preview tăng
  - image/layout regress
  - publish leakage quay lại

---

## Priority 6 — performance baseline

### Mục tiêu
Đo tốc độ theo nhóm đề và đặt ngưỡng chấp nhận được.

### Phân loại đề
- nhẹ
- trung bình
- nặng MathType/OLE
- nặng image/diagram

### Metrics cần theo dõi
- unzip/load
- omml conversion
- sidecar generation
- image rendering
- cleanup/publish sanitize
- parser build JSON
- write output

### Việc cần làm
- chốt file benchmark
- lưu timing before/after
- định nghĩa regression perf threshold

### Success criteria
- sửa đúng nhưng không chậm bất thường
- perf regress được phát hiện sớm

---

## Priority 7 — export `.docx` direction

### Mục tiêu
Chốt sớm chiến lược export ngược, dù chưa build full ngay.

### Quyết định kỹ thuật
- MathML là chuẩn nội bộ
- export DOCX = MathML -> OMML -> WordprocessingML -> `.docx`

### Việc cần làm
- chọn package theo stack
- viết decision note
- chốt export source:
  - `exam_bundle`
  - hoặc `question_bank_items`

### Success criteria
- không còn mơ hồ về hướng export
- đủ rõ để làm prototype exporter ở giai đoạn sau

---

## Priority 8 — parser stabilization

### Mục tiêu
Parser HTML -> JSON phải ổn định, không chỉ HTML preview.

### Việc cần làm
- khóa rule tách section/question/subquestion
- khóa mapping asset -> question
- khóa question type inference
- khóa answer extraction
- sinh parser report có confidence/warnings

### Success criteria
- parser đủ tin cậy cho preview/review
- giảm nhu cầu vá tay ở bước nhập bank

---

## Priority 9 — review/override policy

### Mục tiêu
Xử lý các ca edge-case mà rule chung không bao phủ hết.

### Việc cần làm
- định nghĩa patch/override manifest
- cho phép:
  - keep/suppress image
  - asset role override
  - placement override
  - text patch
  - publish exception

### Success criteria
- 95% xử lý bằng rule
- 5% xử lý bằng override có kiểm soát
- không phải vá code core cho từng ca hiếm

---

## Priority 10 — chỉ sau đó mới tích hợp vào `question_bank`

### Điều kiện trước khi tích hợp
- output contract đã khóa
- publish gates đã rõ
- regression set đã có
- perf baseline đã có
- parser đủ ổn
- override policy đã có
- export direction đã chốt

### Khi đó mới:
- build importer integration
- build review UI
- map JSON vào DB schema

---

## Đề xuất thứ tự thực thi thực tế

### Phase A
1. JSON output contract
2. internal vs publish mode
3. publish gates

### Phase B
4. regression exam set
5. performance baseline
6. parser stabilization

### Phase C
7. core promotion docs
8. override policy
9. export `.docx` direction note

### Phase D
10. integration planning with `question_bank`

---

## Milestone nên đạt

### Milestone M1
- output contract ổn
- publish mode ổn
- QA đáng tin

### Milestone M2
- regression ổn
- perf ổn
- parser ổn

### Milestone M3
- export direction chốt
- override policy ổn
- đủ tự tin để tích hợp

---

## Chốt ngắn

Gói convert bây giờ nên được phát triển như một:

**content normalization engine**

chứ chưa nên coi là một phần của `question_bank` lúc này.

Khi đạt đủ các milestone trên, việc tích hợp vào `question_bank` sẽ nhẹ hơn nhiều và rủi ro thấp hơn.

---

## Snapshot hiện tại (2026-04-07)

Đối chiếu theo `dev_doc.md`, hệ thống đã có:
- convert `DOCX -> HTML` ổn định với OMML + MathType sidecar
- subject profiles (generic/physics/chemistry/math/biology)
- publish cleanup quan trọng (field leakage, structural cleanup, image suppression)
- QA report chi tiết và publish verdict
- orchestration single-pass + lock + cache
- cleanup generated artifacts có dry-run/apply

Phần còn thiếu để “khóa gói”:
- JSON output contract chuẩn hóa versioned
- tách rõ internal mode vs publish mode ở mức contract
- publish gates chính thức hóa theo severity
- regression set chuẩn và perf threshold chính thức
- parser output contract đủ ổn để tích hợp importer

---

## Backlog thực thi 14 ngày (đề xuất)

### Track 1 — Contract & Gate (ưu tiên cao nhất)
1. Chốt `output_contract_v1.md`:
   - định nghĩa schema cho `manifest.json`, `exam_bundle.json`, `question_bank_items.json`, `qa.json`
   - định nghĩa enum cứng: question type, asset role, figure role, severity
2. Thêm `schema_version` vào tất cả artifact JSON.
3. Chuẩn hóa `publish_verdict` theo severity:
   - `safe_to_publish`
   - `needs_review`
   - `blocked`
4. Viết `publish_gates_matrix.md`:
   - điều kiện blocker/warning/info rõ ràng

### Track 2 — Regression & Perf
5. Dựng `regression_set/` tối thiểu 8 file như roadmap gốc.
6. Thêm script chạy regression 1 lệnh:
   - convert + QA + compare baseline (MathML, previews, unresolved, leakage)
7. Chốt `perf_baseline.md`:
   - phân nhóm đề
   - ngưỡng cảnh báo/regress

### Track 3 — Parser & Override
8. Chốt parser output tối thiểu:
   - section/question mapping
   - asset mapping
   - answer extraction confidence
9. Chốt override manifest v1:
   - keep/suppress image
   - role override
   - placement override
   - text patch

---

## Definition of Done theo giai đoạn

### DoD-M1 (Contract + Publish gate)
- Có `schema_version` và schema docs cho 4 JSON artifact.
- Publish verdict không còn mơ hồ; QA markdown phản ánh đúng gate.
- 3 bundle baseline (Hóa/Lý/Toán) chạy pass theo gate mới.

### DoD-M2 (Regression + Perf)
- Có regression set và baseline snapshot.
- Có script so sánh before/after tự động.
- Perf report có threshold và phát hiện regress.

### DoD-M3 (Parser + Override)
- Parser tạo JSON ổn định cho review.
- Override manifest xử lý được edge case mà không vá core.
- Có decision note rõ cho hướng export `.docx`.

---

## Lệnh vận hành đề xuất (chuẩn hóa cho team)

### Convert 1 file
```bash
scripts/transpect/run_docx_with_transpect.sh <input.docx> <output.html> \
  target/docx-html-math-1.0.0-jar-with-dependencies.jar \
  tools/calabash/extensions/transpect/mathtype-extension \
  tools/calabash/distro/xmlcalabash-1.4.1-100.jar \
  tools/calabash/distro/lib/Saxon-HE-10.8.jar \
  work/<run-id> tools/calabash/extensions/transpect/transpect-config.xml --subject <subject>
```

### QA 1 file
```bash
python3 scripts/qa/audit_exam_bundle.py <html> --asset-dir <asset_dir> \
  --conversion-log <conversion.log> --subject <subject> \
  --json-out <qa.json> --md-out <qa.md>
```

### Cleanup định kỳ
```bash
python3 scripts/cleanup/cleanup_generated_artifacts.py \
  --prune-work-runs --prune-out-runs --prune-orphan-assets \
  --keep-work-runs 6 --keep-out-runs 12 --min-age-hours 168 --apply
```

---

## Ghi chú điều phối

- Không mở rộng phạm vi sang tích hợp `question_bank` khi chưa đạt DoD-M2.
- Mọi thay đổi core phải kèm:
  - QA before/after
  - regression impact
  - note core-vs-subject mapping
- Không merge patch “subject-specific” vào core nếu chưa có bằng chứng lặp xuyên môn.
