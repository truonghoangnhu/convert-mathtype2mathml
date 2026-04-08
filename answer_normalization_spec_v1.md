# answer_normalization_spec_v1.md

## Mục tiêu

Tài liệu này định nghĩa cách chuẩn hóa đáp án và rubric ngay trong gói convert/parser,
để đầu ra JSON trở thành canonical source of truth cho:

- import vào `question_bank`
- tạo đề thi
- chấm bài
- review/audit

Nguyên tắc cốt lõi:
- không để logic đáp án/rubric sống ở dạng formatting cue của Word
- không bắt `question_bank` phải parse lại gạch chân, tô đỏ, `[A]`, `R.`
- mọi câu hỏi sau parse phải có canonical answer model rõ ràng

---

## Phạm vi

Áp dụng cho các loại câu:
1. trắc nghiệm 1 lựa chọn đúng
2. đúng/sai theo ý `a)/b)/c)/d)`
3. trả lời ngắn
4. tự luận có rubric

Không áp dụng cho:
- grading AI
- classify topic/difficulty
- OCR
- sửa nội dung học thuật mơ hồ

---

## Nguyên tắc bất biến

1. formatting cue trong source chỉ là **source cues**
   - underline
   - font color
   - marker `[A]`
   - marker `R.`
   - marker `[R]`

2. output JSON phải lưu **meaning**, không lưu formatting như logic chính

3. nếu parser không xác định được chắc chắn:
   - gắn issue
   - chuyển `needs_review`
   - không đoán bừa

4. `question_bank` không được parse lại source cues để quyết định đáp án/rubric

---

## Canonical answer model

Mỗi câu sau parse phải có một trong các mode sau:

```json
{
  "answer_key": {
    "mode": "single_choice | multiple_select | boolean | short_answer | rubric | none"
  }
}
```

### Mapping
- trắc nghiệm 1 lựa chọn đúng -> `single_choice`
- đúng/sai -> `boolean` trong từng subquestion
- trả lời ngắn -> `short_answer`
- tự luận có rubric -> `rubric`
- chưa xác định được -> `none` + issue/review flag

---

## 1. Multiple Choice Normalization

### Input convention
Người soạn đánh dấu đáp án đúng bằng:
- gạch chân ký tự `A/B/C/D`
- hoặc tô đỏ ký tự `A/B/C/D`

### Detection scope
Parser phải kiểm tra:
- label của choice (`A`, `B`, `C`, `D`)
- formatting cue áp dụng lên label hoặc vùng rất gần label
- không chỉ dựa vào nội dung phương án

### Canonical output
```json
{
  "question_type": "multiple_choice",
  "choices": [
    {"choice_id": "q1_A", "label": "A", "content_html": "<p>...</p>"},
    {"choice_id": "q1_B", "label": "B", "content_html": "<p>...</p>"}
  ],
  "answer_key": {
    "mode": "single_choice",
    "correct_choice_ids": ["q1_B"]
  }
}
```

### Source cue capture
```json
{
  "answer_detection": {
    "source_cues": [
      {"type": "underline", "target": "choice_label_B"},
      {"type": "font_color", "value": "#ff0000", "target": "choice_label_B"}
    ],
    "confidence": 0.98,
    "parser_notes": []
  }
}
```

### Validation rules
- phải có đúng 1 đáp án đúng
- nếu 0 đáp án đúng -> `missing_correct_choice`
- nếu >1 đáp án đúng -> `multiple_correct_choices_detected`
- nếu confidence thấp -> `needs_review`

---

## 2. True/False Normalization

### Input convention
- mỗi ý bắt đầu bằng:
  - `a)`
  - `b)`
  - `c)`
  - `d)`
- ý nào đúng:
  - label được gạch chân
  - hoặc label được tô đỏ
- không mark -> coi là sai

### Canonical output
```json
{
  "question_type": "true_false",
  "subquestions": [
    {
      "subquestion_id": "q4_a",
      "label": "a",
      "content_html": "<p>...</p>",
      "answer": {
        "mode": "boolean",
        "value": true
      }
    },
    {
      "subquestion_id": "q4_b",
      "label": "b",
      "content_html": "<p>...</p>",
      "answer": {
        "mode": "boolean",
        "value": false
      }
    }
  ]
}
```

### Source cue capture
```json
{
  "answer_detection": {
    "source_cues": [
      {"type": "underline", "target": "subquestion_label_a"}
    ],
    "confidence": 0.95,
    "parser_notes": []
  }
}
```

### Validation rules
- mỗi label `a/b/c/d` phải map được thành 1 subquestion
- mỗi subquestion phải có `answer.value = true|false`
- nếu label/formatting cue mơ hồ -> `ambiguous_true_false_marker`
- nếu số lượng ý bất thường -> `true_false_structure_warning`

---

## 3. Short Answer Normalization

### Input convention
Đáp án có dạng:
- `[A] <đáp án>`
- `A. <đáp án>`

Ở đây `A` là marker “answer”, không phải choice label.

### Detection scope
- tìm marker `[A]` hoặc `A.`
- chỉ chấp nhận marker trong vùng answer/solution phù hợp
- không nhầm với choice `A.` của câu trắc nghiệm

### Canonical output
```json
{
  "question_type": "short_answer",
  "answer_key": {
    "mode": "short_answer",
    "accepted_answers": [
      {
        "raw": "12,5",
        "normalized": "12.5"
      }
    ]
  }
}
```

### Normalization policy
Cho mỗi đáp án, lưu tối thiểu:
- `raw`
- `normalized`

Chuẩn hóa có thể bao gồm:
- trim whitespace
- normalize dấu phẩy thập phân -> dấu chấm nếu policy cho phép
- normalize case cho text answer nếu policy cho phép
- chuẩn hóa spacing

### Source cue capture
```json
{
  "answer_detection": {
    "source_cues": [
      {"type": "marker", "value": "[A]"}
    ],
    "confidence": 0.96,
    "parser_notes": []
  }
}
```

### Validation rules
- nếu không có marker -> `missing_short_answer_marker`
- nếu span đáp án không rõ -> `ambiguous_short_answer_span`
- nếu nhiều marker mâu thuẫn -> `multiple_short_answer_markers_conflict`

---

## 4. Essay Rubric Normalization

### Input convention
Rubric bắt đầu bằng:
- `R.`
- `[R]`

Rubric có thể:
- kéo dài nhiều dòng
- không lặp lại marker `R`
- hoặc lặp lại `R.`/`[R]` ở đầu từng block

### Canonical output
```json
{
  "question_type": "essay",
  "answer_key": {
    "mode": "rubric"
  },
  "rubric": {
    "mode": "analytic",
    "rubric_html": "<div><p>...</p></div>",
    "blocks": [
      {
        "order": 1,
        "content_html": "<p>Ý 1 ...</p>",
        "points": null
      },
      {
        "order": 2,
        "content_html": "<p>Ý 2 ...</p>",
        "points": null
      }
    ]
  }
}
```

### Detection scope
- marker mở đầu `R.` hoặc `[R]`
- gom tất cả các block rubric liên tiếp cho đến:
  - hết câu
  - câu tiếp theo
  - section tiếp theo
  - block boundary rõ ràng khác

### Rubric grouping rules
- marker đầu tiên mở rubric section
- các dòng sau không cần lặp marker vẫn thuộc cùng rubric nếu nằm trong vùng liên tiếp
- nếu lặp `R.` nhiều lần, có thể:
  - tạo block mới trong `rubric.blocks[]`
  - hoặc coi là continuation nếu rule context cho thấy vậy

### Source cue capture
```json
{
  "rubric_detection": {
    "source_cues": [
      {"type": "marker", "value": "R."}
    ],
    "confidence": 0.94,
    "parser_notes": []
  }
}
```

### Validation rules
- tự luận có thể thiếu rubric nếu policy cho phép, nhưng phải gắn `missing_rubric`
- rubric boundary mơ hồ -> `ambiguous_rubric_boundary`
- rubric parse fail -> `needs_review`

---

## 5. Question-type specific invariants

### Multiple choice
- phải có `choices[]`
- phải có `answer_key.mode = single_choice`
- phải có đúng 1 `correct_choice_id`

### True/false
- phải có `subquestions[]`
- mỗi subquestion phải có `answer.mode = boolean`

### Short answer
- phải có `accepted_answers[]`

### Essay
- phải có `answer_key.mode = rubric`
- nên có `rubric_html` và/hoặc `rubric.blocks[]`

---

## 6. Answer/rubric QA issues

### Multiple choice
- `missing_correct_choice`
- `multiple_correct_choices_detected`
- `choice_label_structure_warning`

### True/false
- `ambiguous_true_false_marker`
- `true_false_structure_warning`

### Short answer
- `missing_short_answer_marker`
- `ambiguous_short_answer_span`
- `multiple_short_answer_markers_conflict`

### Essay
- `missing_rubric`
- `ambiguous_rubric_boundary`
- `rubric_parse_incomplete`

### Generic
- `answer_detection_low_confidence`
- `answer_mode_unknown`
- `source_cue_conflict`

---

## 7. Severity policy

### Blocker
- multiple choice nhưng không xác định được đúng 1 đáp án
- multiple choice phát hiện nhiều đáp án đúng mâu thuẫn
- answer mode không xác định được cho câu mà policy yêu cầu auto-parse chính xác

### Warning
- thiếu rubric ở câu tự luận nhưng hệ thống cho phép nhập tay sau
- true/false parse được nhưng confidence thấp
- short answer parse được nhưng normalized answer cần review

### Info
- có source cue dư thừa nhưng canonical answer vẫn rõ

---

## 8. Review status policy

### Auto-approved
Cho phép nếu:
- answer/rubric parse rõ
- confidence >= threshold
- không có blocker

### Needs review
Nếu:
- confidence thấp
- boundary mơ hồ
- source cue conflict
- rubric incomplete

### Rejected from auto-import
Nếu:
- blocker issue tồn tại
- answer mode không canonical hóa được

---

## 9. Subject-aware thresholds

Parser quality gate có thể chỉnh threshold theo môn, nhưng canonical answer model phải giữ chung.

Ví dụ:
- Chemistry/Physics/Math có thể khác confidence threshold
- nhưng output answer model không đổi

---

## 10. JSON fields bắt buộc nên có

Mỗi question sau normalization nên có thêm:

```json
{
  "answer_key": {...},
  "answer_detection": {
    "source_cues": [],
    "confidence": 0.0,
    "parser_notes": []
  },
  "rubric_detection": null,
  "qa_flags": []
}
```

Nếu là essay:
```json
{
  "rubric": {...},
  "rubric_detection": {
    "source_cues": [],
    "confidence": 0.0,
    "parser_notes": []
  }
}
```

---

## 11. Runtime placement in pipeline

Normalization phải chạy sau:
- question segmentation
- question type inference sơ bộ

và trước:
- exam_bundle serialization
- question_bank_items serialization
- publish QA finalization

Pipeline:
```text
DOCX
-> HTML/MathML/assets
-> section/question segmentation
-> question type inference
-> answer_and_rubric_normalization
-> answer/rubric QA gate
-> JSON contract output
```

---

## 12. Không được làm

- không để `question_bank` parse lại underline/red color để quyết định đáp án
- không để frontend tự suy luận `[A]` hoặc `R.`
- không đoán đáp án khi source cue mơ hồ
- không dùng plain text mất formatting làm nguồn duy nhất cho answer detection

---

## 13. Quy tắc authoring guideline tương ứng

### Multiple choice
- mark đúng 1 choice label bằng underline hoặc đỏ

### True/false
- dùng `a)/b)/c)/d)`
- mark label của ý đúng

### Short answer
- dùng `[A]` hoặc `A.`

### Essay
- dùng `R.` hoặc `[R]`

Nếu không theo convention:
- parser vẫn cố gắng đọc
- nhưng có thể rơi vào `needs_review` hoặc `blocker`

---

## 14. Success criteria

Spec này được coi là triển khai đúng khi:
- mọi câu sau parse có canonical answer/rubric model rõ
- downstream không phải suy luận lại từ formatting cues
- QA có thể chặn các case mơ hồ
- review UI có đủ evidence (`source_cues`, `confidence`, `notes`) để người dùng xác minh
- import vào database có logic xuyên suốt, không cần kiểm tra lại bằng rule khác

---

## 15. Chốt ngắn

Formatting của Word như:
- gạch chân
- tô đỏ
- `[A]`
- `R.`

chỉ là **dấu hiệu nguồn**.

Gói convert/parser phải biến các dấu hiệu đó thành:
- `correct_choice_ids`
- `boolean true/false`
- `accepted_answers`
- `rubric.blocks`

để toàn hệ thống về sau dùng một logic thống nhất.
