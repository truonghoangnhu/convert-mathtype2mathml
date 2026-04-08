# answer_summary_extraction_spec_v1.md

## Mục tiêu

Tài liệu này định nghĩa cách phát hiện và trích xuất **bảng đáp án / tóm tắt đáp án** ở cấp đề,
tách biệt khỏi:

- local answer cues trong từng câu
- solution / hướng dẫn giải
- rubric tự luận

Mục tiêu là sinh ra một lớp dữ liệu `answer_summary` rõ ràng để về sau:
- đối chiếu với đáp án parse từ từng câu
- hỗ trợ canonical answer reconciliation
- không nhầm bảng đáp án với lời giải

---

## Nguyên tắc cốt lõi

1. `answer_summary` là **nguồn đáp án ở cấp đề**, không phải lời giải.
2. `answer_summary` không thay thế tự động mọi local answer cue.
3. `answer_summary` phải được parse riêng trước khi reconcile.
4. nếu bảng/danh sách đáp án mơ hồ hoặc conflict, phải gắn issue thay vì đoán bừa.

---

## Phạm vi

Áp dụng cho các dạng:
1. bảng đáp án trắc nghiệm nhiều lựa chọn
2. bảng đúng/sai
3. bảng đáp án ngắn
4. danh sách text tóm tắt đáp án
5. các block “Đáp án”, “Bảng đáp án”, “Tóm tắt đáp án”

Không áp dụng cho:
- solution/rubric chi tiết
- local formatting cues trong từng câu
- grading AI

---

## Khái niệm

### `answer_summary_zone`
Một vùng trong tài liệu được nhận diện là nơi chứa tóm tắt đáp án ở cấp đề.

### `answer_summary_entry`
Một phần tử trong vùng đó, ánh xạ:
- question number
- answer value hoặc answer structure

### `answer_summary`
Object canonical ở cấp đề:

```json
{
  "answer_summary": {
    "present": true,
    "source_type": "table | list | mixed",
    "html": "<table>...</table>",
    "entries": []
  }
}
```

---

## Các dạng nguồn cần hỗ trợ

## 1. Bảng đáp án trắc nghiệm nhiều lựa chọn

Ví dụ:

| Câu | 1 | 2 | 3 | 4 |
|-----|---|---|---|---|
| ĐA  | A | C | D | B |

### Canonical output
```json
{
  "source_type": "table",
  "entries": [
    {"question_number": "1", "mode": "single_choice", "value": "A"},
    {"question_number": "2", "mode": "single_choice", "value": "C"}
  ]
}
```

---

## 2. Bảng đúng/sai

Ví dụ:

| Câu | a | b | c | d |
|-----|---|---|---|---|
| 1   | Đ | S | Đ | S |

hoặc:

| Câu | a | b | c | d |
|-----|---|---|---|---|
| 1   | T | F | T | F |

### Canonical output
```json
{
  "source_type": "table",
  "entries": [
    {
      "question_number": "1",
      "mode": "boolean_group",
      "subanswers": {
        "a": true,
        "b": false,
        "c": true,
        "d": false
      }
    }
  ]
}
```

---

## 3. Bảng đáp án ngắn

Ví dụ:

| Câu | Đáp án |
|-----|--------|
| 1   | 12,5   |
| 2   | 30     |

### Canonical output
```json
{
  "source_type": "table",
  "entries": [
    {
      "question_number": "1",
      "mode": "short_answer",
      "accepted_answers": [
        {"raw": "12,5", "normalized": "12.5"}
      ]
    }
  ]
}
```

---

## 4. Danh sách text tóm tắt đáp án

Ví dụ:
- 1.A
- 2.C
- 3.D

hoặc:
- Câu 1: A
- Câu 2: C

### Canonical output
```json
{
  "source_type": "list",
  "entries": [
    {"question_number": "1", "mode": "single_choice", "value": "A"},
    {"question_number": "2", "mode": "single_choice", "value": "C"}
  ]
}
```

---

## 5. Mixed summary blocks

Ví dụ:
- đầu là bảng trắc nghiệm
- sau đó là bảng trả lời ngắn
- hoặc trộn table + list

### Canonical output
```json
{
  "source_type": "mixed",
  "entries": [...]
}
```

---

## Detection strategy

## Bước 1: Detect answer summary zone
Tìm các block có dấu hiệu:
- heading chứa:
  - `Đáp án`
  - `Bảng đáp án`
  - `Tóm tắt đáp án`
  - `Đáp án tham khảo`
- table có header/cell pattern như:
  - `Câu`
  - `Đáp án`
  - `DA`
  - `a b c d`
- list pattern kiểu:
  - `1.A`
  - `1 - A`
  - `Câu 1: A`

## Bước 2: Classify source type
- `table`
- `list`
- `mixed`

## Bước 3: Extract entries
Tách từng entry theo question number và answer structure.

## Bước 4: Normalize answer values
Chuẩn hóa:
- choice label `A/B/C/D`
- boolean `Đ/S`, `Đúng/Sai`, `T/F`
- short answer raw/normalized

## Bước 5: Emit evidence + confidence
Mỗi summary nên có:
- `source_cues`
- `confidence`
- `parser_notes`

---

## Detection rules by type

## A. Table-based answer summary
Parser phải:
- nhận diện bảng có cấu trúc đáp án
- không nhầm bảng dữ liệu bài toán với bảng đáp án

### Signals mạnh
- header chứa `Câu`, `Đáp án`
- row/column values phần lớn là:
  - số câu
  - A/B/C/D
  - Đ/S
  - số ngắn
- bảng nằm gần cuối đề hoặc gần heading `Đáp án`

### Table exclusion rules
Không coi là answer summary nếu:
- bảng chứa dữ kiện bài toán
- bảng có đơn vị đo, số liệu dài, công thức, mô tả
- bảng xuất hiện trong thân câu hỏi

---

## B. List-based answer summary
Parser phải hỗ trợ pattern như:
- `1.A`
- `1) A`
- `1 - A`
- `Câu 1: A`

### Exclusion rules
Không coi là answer summary nếu:
- list nằm trong thân lời giải
- line chứa nội dung giải thích dài
- line không có mapping rõ question -> answer

---

## C. Boolean group summary
Parser phải hỗ trợ:
- `Đ/S`
- `Đúng/Sai`
- `T/F`
- `True/False`

Chuẩn hóa về:
- `true`
- `false`

---

## D. Short answer summary
Parser phải hỗ trợ:
- số
- text ngắn
- danh sách nhiều accepted answers nếu nguồn thể hiện rõ

### Normalization
- trim
- decimal comma -> decimal dot nếu policy cho phép
- collapse whitespace
- preserve `raw`

---

## JSON structure đề xuất

```json
{
  "answer_summary": {
    "present": true,
    "source_type": "table",
    "html": "<table>...</table>",
    "entries": [
      {
        "question_number": "1",
        "mode": "single_choice",
        "value": "A"
      },
      {
        "question_number": "2",
        "mode": "boolean_group",
        "subanswers": {
          "a": true,
          "b": false,
          "c": true,
          "d": false
        }
      },
      {
        "question_number": "3",
        "mode": "short_answer",
        "accepted_answers": [
          {"raw": "12,5", "normalized": "12.5"}
        ]
      }
    ],
    "detection": {
      "source_cues": [],
      "confidence": 0.0,
      "parser_notes": []
    },
    "qa_flags": []
  }
}
```

---

## QA issues

### Zone detection
- `answer_summary_zone_missing`
- `answer_summary_zone_ambiguous`

### Entry extraction
- `answer_summary_entry_parse_failed`
- `answer_summary_duplicate_question_number`
- `answer_summary_unknown_answer_mode`

### Content ambiguity
- `answer_summary_choice_value_invalid`
- `answer_summary_boolean_value_invalid`
- `answer_summary_short_answer_span_ambiguous`

### Structural mismatch
- `answer_summary_question_reference_unknown`
- `answer_summary_table_shape_unexpected`

---

## Severity policy

### Info
- summary present but redundant with local answers

### Warning
- summary parse partial
- some entries low confidence
- summary found but mixed-format ambiguous
- `answer_summary_zone_missing` khi local answer extraction yếu/mơ hồ hoặc còn unresolved câu objective

### Blocker
- malformed summary that appears authoritative but cannot be mapped safely
- duplicate conflicting entries for same question
- summary references impossible/nonexistent question ids in a way that breaks reconciliation

### Context-sensitive rule for `answer_summary_zone_missing`

Không phải đề nào cũng có bảng/list summary đáp án ở cuối.
Vì vậy cần tuning theo chất lượng local extraction:

- nếu local extraction mạnh và đầy đủ (objective questions được resolve rõ ràng, confidence cao):
  - hạ `answer_summary_zone_missing` xuống `info`
- nếu local extraction còn yếu/mơ hồ hoặc còn unresolved:
  - giữ `answer_summary_zone_missing` ở `warning`

Mục tiêu:
- không phạt quá mức các bundle sạch nhưng không có summary zone
- vẫn giữ tín hiệu review cho bundle còn rủi ro

---

## Confidence policy

Confidence should consider:
- strength of heading signal
- strength of table/list pattern
- consistency of question numbering
- consistency of answer values
- distance from end-of-exam / known answer section

Recommended output:
```json
{
  "detection": {
    "confidence": 0.94,
    "source_cues": [
      {"type": "heading", "value": "Đáp án"},
      {"type": "table_header", "value": "Câu/Đáp án"}
    ],
    "parser_notes": []
  }
}
```

---

## Output placement in contract

### `exam_bundle.json`
Store full `answer_summary` at exam level.

### `question_bank_items.json`
Do not copy the whole summary block to every question.
Only store per-question `answer_sources` when reconciliation uses summary data.

---

## Runtime placement in pipeline

Pipeline:
```text
DOCX
-> HTML/MathML/assets
-> section/question segmentation
-> answer_summary_extraction
-> local answer normalization
-> solution extraction
-> answer reconciliation
-> JSON contract output
```

---

## Không được làm

- không để bảng đáp án overwrite thẳng local answer mà không qua reconciliation
- không nhầm bảng đáp án với bảng dữ kiện câu hỏi
- không nhầm solution/rubric table với answer summary
- không suy đoán answer mode nếu summary mơ hồ

---

## Success criteria

Spec này được coi là triển khai đúng khi:
- parser phát hiện được summary zone ở các đề có bảng/danh sách đáp án
- summary entries được canonical hóa thành structure máy đọc được
- summary không bị nhầm với solution hoặc data table
- downstream có thể dùng summary như nguồn đối chiếu, không cần parse lại HTML thô
