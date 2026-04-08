# question_bank_docx_ingest_module_architecture_spec.md

## Mục tiêu

Tài liệu này mô tả kiến trúc tích hợp project convert DOCX hiện tại vào repo `question_bank`
theo hướng:

- không trộn thẳng logic convert vào lõi bank/exam
- tận dụng app `importer` làm staging/review pipeline
- hỗ trợ hai mode:
  1. `strict_omml`
  2. `assisted_convert`

Mục tiêu cuối:
- upload DOCX
- convert/parse/review
- commit vào question bank
- từ bank sinh đề chốt sẵn hoặc đề ngẫu nhiên

---

## Quyết định kiến trúc

### Giữ 2 mode import trong `importer`

#### 1. `strict_omml`
Dùng cho DOCX sạch:
- chỉ chấp nhận OMML
- fail fast nếu có MathType/OLE/preview
- import nhanh

#### 2. `assisted_convert`
Dùng cho DOCX thực tế:
- có MathType/OLE/hình/layout phức tạp
- chạy converter hiện tại
- sinh HTML + MathML + assets + QA
- review thủ công
- rồi mới commit vào bank

---

## Vị trí tích hợp trong repo

### Backend

```text
backend/
  importer/
    apps.py
    models.py
    serializers.py
    urls.py
    views.py
    tasks.py
    services/
      strict_docx_import/
      assisted_docx_convert/
        orchestration/
        convert/
        parser/
        qa/
        review_patch/
        commit/
        publish/
```

### Frontend

```text
frontend/src/feature-module/importer/
  pages/
  components/
  hooks/
  services/
  types/
```

---

## Vai trò từng lớp backend

## 1. `orchestration/`
Chịu trách nhiệm:
- nhận explicit input
- single-pass deterministic
- lock theo input
- cache hash
- chống recursive discovery
- log lý do bắt đầu convert
- gọi converter + parser + QA theo pipeline 1 chiều

### Service chính
- `DocxIngestOrchestrator`

### Hàm chính
- `start_job(import_job_id)`
- `run_conversion(import_job_id)`
- `run_parser(import_job_id)`
- `run_qa(import_job_id)`
- `finalize_preview(import_job_id)`

---

## 2. `convert/`
Bọc project convert hiện tại.

Chịu trách nhiệm:
- gọi shell wrapper / Java / Python tools
- sinh:
  - `*-transpect.html`
  - thư mục assets
  - QA thô
  - log convert

### Service chính
- `DocxConvertService`

### Output contract
```json
{
  "html_path": "...",
  "asset_base_path": "...",
  "qa_json_path": "...",
  "qa_md_path": "...",
  "conversion_log_path": "...",
  "converter_version": "..."
}
```

---

## 3. `parser/`
Chịu trách nhiệm:
- parse HTML đã convert
- sinh object trung gian:
  - `exam_bundle`
  - `question_bank_items`
- map sections/questions/assets/math fragments
- đổ preview vào staging tables

### Service chính
- `ExamHtmlParser`
- `QuestionBankPreviewBuilder`

### Output chính
- `exam_bundle.json`
- `question_bank_items.json`
- `parser_report.json`

---

## 4. `qa/`
Chịu trách nhiệm:
- tổng hợp QA
- publish gates
- parser warnings
- figure placement warnings
- unresolved preview/object flags
- metrics phục vụ review UI

### Service chính
- `DocxIngestQaService`

### Trạng thái nên kết luận
- `pass`
- `needs_review`
- `blocked`

---

## 5. `review_patch/`
Chịu trách nhiệm:
- áp patch người dùng lên preview
- keep/suppress image
- đổi role `context-figure` / `essential-figure`
- sửa stem_html/solution_html/answer_key
- re-render preview đã patch nếu cần

### Service chính
- `PreviewPatchService`

---

## 6. `commit/`
Chịu trách nhiệm:
- commit preview đã duyệt vào bank chính
- tạo:
  - `question`
  - `question_version`
  - `question_choice`
  - `question_short_answer_key`
  - `question_interaction`
  - `stimulus*` nếu cần

### Service chính
- `QuestionBankCommitService`

---

## 7. `publish/`
Chịu trách nhiệm:
- sanitize output publish
- strip debug attrs
- layout polish cuối
- không đụng logic bank chính

### Service chính
- `PublishOutputService`

---

## Luồng dữ liệu tổng thể

```text
Upload DOCX
-> import_docx_job created
-> orchestrator starts
-> convert
-> parser
-> QA
-> preview staging written
-> reviewer edits/patches
-> approve
-> commit to question bank
-> optional create exam snapshot
```

---

## Models / bảng nên dùng

Repo đã có sẵn staging khá tốt. Kiến trúc này giả định tiếp tục dùng:

- `import_docx_jobs`
- `import_docx_preview_questions`
- `import_docx_assets`
- `import_docx_issues`

### Mở rộng đề xuất cho `import_docx_jobs`
Thêm hoặc chuẩn hóa các field:

- `mode`: `strict_omml` | `assisted_convert`
- `source_filename`
- `source_hash`
- `source_docx_path`
- `convert_html_path`
- `asset_base_path`
- `qa_json_path`
- `qa_md_path`
- `parser_report_path`
- `conversion_log_path`
- `status`
- `publish_gate_status`
- `review_required`
- `started_at`
- `finished_at`

### Mở rộng đề xuất cho `import_docx_preview_questions`
- `section_code`
- `question_number_display`
- `question_type_guess`
- `stem_html`
- `choices_json`
- `subquestions_json`
- `answer_key_json`
- `solution_html`
- `source_map_json`
- `parse_confidence`
- `review_status`

### Mở rộng đề xuất cho `import_docx_assets`
- `preview_question_id`
- `asset_src`
- `asset_role`
- `placement`
- `mime_type`
- `qa_flags_json`
- `keep_or_suppress`
- `is_restored`
- `trim_applied`

### Mở rộng đề xuất cho `import_docx_issues`
- `severity`
- `issue_code`
- `target_type`
- `target_id`
- `message`
- `suggested_fix`
- `resolved`

---

## Commit mapping vào bank chính

### Với câu độc lập
- tạo `question`
- tạo `question_version`
- tạo `question_interaction`
- tạo `question_choice` hoặc `question_short_answer_key`

### Với nhóm câu dùng chung ngữ cảnh
- tạo `stimulus`
- tạo `stimulus_version`
- tạo `stimulus_item`
- tạo `stimulus_asset`

### Rule commit
- không commit nếu question preview chưa `approved`
- không commit nếu còn `blocked` QA issue
- commit phải idempotent theo preview id + revision

---

## Trạng thái job đề xuất

### `import_docx_jobs.status`
- `uploaded`
- `queued`
- `converting`
- `converted`
- `parsing`
- `preview_ready`
- `reviewing`
- `approved_for_import`
- `imported`
- `failed`

### `import_docx_preview_questions.review_status`
- `parsed`
- `needs_review`
- `reviewed`
- `approved`
- `rejected`
- `imported`

---

## API backend đề xuất

## 1. Upload + create job
- `POST /api/importer/docx/jobs`
- input:
  - file
  - subject
  - mode
  - metadata

## 2. Start/Restart convert
- `POST /api/importer/docx/jobs/{id}/start`
- `POST /api/importer/docx/jobs/{id}/retry`

## 3. Job detail
- `GET /api/importer/docx/jobs/{id}`

## 4. Preview questions
- `GET /api/importer/docx/jobs/{id}/preview-questions`

## 5. Preview assets
- `GET /api/importer/docx/jobs/{id}/assets`

## 6. Issues
- `GET /api/importer/docx/jobs/{id}/issues`

## 7. Apply patch
- `POST /api/importer/docx/jobs/{id}/patches`

## 8. Approve question
- `POST /api/importer/docx/preview-questions/{id}/approve`

## 9. Commit import
- `POST /api/importer/docx/jobs/{id}/commit`

## 10. Optional create exam snapshot after import
- `POST /api/importer/docx/jobs/{id}/create-exam`

---

## Frontend importer module

## 1. Pages
### `ImportJobListPage`
- danh sách file import
- trạng thái
- QA verdict
- actions

### `ImportJobDetailPage`
- tabs:
  - Summary
  - Preview Questions
  - Assets
  - QA Issues
  - Logs

### `QuestionReviewPage`
- source context
- preview HTML
- patch editor
- asset controls
- answer/solution editor

### `ImportCommitPage`
- tổng kết trước commit
- số câu approved/rejected
- số issue còn lại

---

## Frontend components

- `DocxUploadForm`
- `ImportJobStatusCard`
- `PreviewQuestionCard`
- `PreviewAssetPanel`
- `QaIssueList`
- `QuestionPatchEditor`
- `FigureRoleSelector`
- `KeepSuppressToggle`
- `CommitSummaryPanel`

---

## Hook/service frontend đề xuất

### Services
- `importer.api.ts`
- `importerReview.api.ts`
- `importerCommit.api.ts`

### Hooks
- `useImportJobs`
- `useImportJobDetail`
- `usePreviewQuestions`
- `usePreviewAssets`
- `useApplyPatch`
- `useCommitImport`

---

## Patch model đề xuất

Patch nên lưu dạng JSON có target rõ:

```json
{
  "patches": [
    {
      "target_type": "question",
      "target_id": "preview_q_001",
      "field": "stem_html",
      "action": "replace",
      "value": "<p>...</p>"
    },
    {
      "target_type": "asset",
      "target_id": "preview_asset_12",
      "field": "asset_role",
      "action": "set",
      "value": "context-figure"
    },
    {
      "target_type": "asset",
      "target_id": "preview_asset_12",
      "field": "keep_or_suppress",
      "action": "set",
      "value": "keep"
    }
  ]
}
```

---

## Exam integration

Sau khi commit vào bank, có 2 hướng:

### 1. Đề chốt sẵn
- chọn `question_version`
- snapshot vào `exam`, `exam_block`, `exam_block_item`

### 2. Đề ngẫu nhiên
- dùng `blueprint`, `exam_mix_job`
- chọn từ bank
- sinh `exam`
- học sinh làm trên `exam` snapshot

### Rule quan trọng
- học sinh không làm trực tiếp trên preview
- học sinh không làm trực tiếp trên bank live object
- luôn làm trên `exam` snapshot

---

## Operational invariants

Module `docx_ingest` phải tuân thủ:

1. single explicit input by default
2. recursive discovery only by opt-in
3. outputs excluded from discovery
4. one canonical input = one active conversion job
5. hash + toolchain fingerprint cache
6. QA/cleanup must not retrigger convert
7. every conversion logs exactly why it started

---

## Publish-output boundary

`importer` internal preview có thể giữ:
- debug attrs
- provenance
- QA metadata

Nhưng `publish` hoặc `exam snapshot` user-facing nên:
- strip debug attrs không cần
- giữ HTML/MathML sạch
- giữ class/layout semantic cần cho frontend

---

## Tách trách nhiệm với app khác

### `importer`
- upload
- convert
- preview
- review
- commit

### `content_bank`
- source of truth của câu hỏi

### `exams`
- snapshot đề thi
- phát đề

### `attempts`
- làm bài
- chấm bài

### `taxonomy`
- topic/tag/learning objective

---

## Migration strategy

### Giai đoạn 1
- giữ nguyên strict importer hiện có
- thêm `assisted_convert` mode
- đổ preview vào staging tables hiện tại

### Giai đoạn 2
- thêm UI review patch
- commit chuẩn vào question bank

### Giai đoạn 3
- nối trực tiếp từ imported questions sang exam generator

---

## Quyết định cuối

Repo này nên tích hợp project convert hiện tại như một subsystem:

**`importer.services.assisted_docx_convert`**

với boundary rõ:
- converter không chạm trực tiếp vào `question` live
- mọi thứ đi qua staging/review
- commit mới tạo dữ liệu chính thức trong bank

## Chốt một câu
**`question_bank` đã có sẵn khung rất phù hợp; việc đúng nhất là tích hợp project hiện tại vào app `importer` dưới mode `assisted_convert`, dùng staging/review hiện có, rồi commit sang `content_bank` và `exams`.**
