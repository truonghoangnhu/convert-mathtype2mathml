# answer_reconciliation_spec_v1.md

## Mục tiêu

Tài liệu này định nghĩa cách hợp nhất các nguồn đáp án/lời giải khác nhau thành một
`answer_key` canonical duy nhất cho mỗi câu, đồng thời phát hiện conflict và quyết định
khi nào auto-pass, khi nào needs_review, khi nào blocker.

Nguồn có thể bao gồm:
1. local answer cues trong từng câu
2. answer summary ở cấp đề
3. solution / hướng dẫn giải
4. rubric tự luận

---

## Nguyên tắc cốt lõi

1. không có nguồn nào được phép overwrite mù quáng nguồn khác
2. mọi hợp nhất phải qua reconciliation
3. canonical answer cuối phải có:
   - `answer_key`
   - `answer_sources`
   - `reconciliation`
4. nếu các nguồn conflict mà không có rule rõ để giải quyết, phải `needs_review` hoặc `blocker`

---

## Các nguồn đầu vào

## 1. Local answer extraction
Nguồn từ:
- underline/red choice labels
- underline/red true/false labels
- `[A]` / `A.`
- `R.` / `[R]`

Đây là nguồn gần câu nhất.

## 2. Answer summary extraction
Nguồn từ:
- bảng đáp án
- bảng đúng/sai
- danh sách đáp án
- mixed summary block

Đây là nguồn ở cấp đề.

## 3. Solution extraction
Nguồn từ:
- lời giải
- hướng dẫn giải
- block kết luận đáp án
- rubric essay

Đây là nguồn giải thích/chứng minh, không phải lúc nào cũng là answer source chính.

---

## Canonical reconciliation output

Mỗi question sau reconcile phải có structure tối thiểu:

```json
{
  "answer_key": {...},
  "answer_sources": [
    {"source": "local_formatting", "confidence": 0.88},
    {"source": "answer_summary_table", "confidence": 0.99}
  ],
  "reconciliation": {
    "status": "resolved | conflict | needs_review | blocked",
    "chosen_source": "answer_summary_table",
    "notes": []
  }
}
```

Nếu là essay:
```json
{
  "answer_key": {"mode": "rubric"},
  "rubric": {...},
  "answer_sources": [
    {"source": "rubric_marker", "confidence": 0.95}
  ],
  "reconciliation": {
    "status": "resolved",
    "chosen_source": "rubric_marker"
  }
}
```

---

## Source priority model

Nguồn không phải lúc nào cũng có độ ưu tiên tuyệt đối.
Ưu tiên phụ thuộc vào loại câu và độ rõ ràng của evidence.

### Base priority đề xuất
1. local structured answer with high-confidence evidence
2. answer summary with high-confidence mapping
3. solution-derived answer cue
4. fallback inference / weak evidence

### Quy tắc quan trọng
- nguồn gần câu hơn không tự động thắng nếu confidence thấp
- summary không tự động thắng nếu conflict với local high-confidence
- solution chỉ nên override khi kết luận đáp án cực rõ ràng

---

## Reconciliation by question type

## 1. Multiple choice

### Sources có thể có
- local formatting cue trên choice label
- answer summary entry
- solution conclusion (“chọn B”)

### Rule
#### Case A
Local high-confidence + summary same
-> `resolved`
-> chosen source may be `local+summary`

#### Case B
Local missing/weak + summary clear
-> use summary
-> `resolved`
-> chosen_source = `answer_summary`

#### Case C
Local clear + summary clear but different
-> `conflict`
-> do not auto-pick unless policy explicitly allows
-> default `needs_review` or `blocked`

#### Case D
Only solution says “chọn B”, local and summary absent
-> allowed as fallback only if solution cue is explicit
-> mark lower confidence
-> likely `needs_review` unless policy says acceptable

### Blocker examples
- multiple choice with multiple different candidate answers
- local says B, summary says A, solution says D

---

## 2. True/False

### Sources có thể có
- local underline/red on a/b/c/d labels
- summary boolean table
- solution per subpart

### Rule
Reconcile per subquestion:
- `a`, `b`, `c`, `d` individually

#### Case A
Local and summary agree on all subparts
-> `resolved`

#### Case B
Some subparts missing locally, summary fills them
-> `resolved_with_fill`

#### Case C
Any subpart conflicts
-> `needs_review` or `blocked` depending on count/severity

### Blocker examples
- summary says `a=true`, local says `a=false`
- multiple subparts unresolved with no strong source

---

## 3. Short answer

### Sources có thể có
- local `[A]` / `A.`
- summary answer table
- solution final numeric/text result

### Rule
#### Case A
Local and summary normalize to same answer
-> `resolved`

#### Case B
Local missing, summary present
-> `resolved`

#### Case C
Local raw and summary raw differ but normalized values match
-> `resolved_normalized_equivalent`

#### Case D
Values differ materially
-> `needs_review` / `blocked`

### Note
If numerical tolerance policy exists:
- values inside tolerance may be `resolved_with_tolerance`

---

## 4. Essay

### Sources có thể có
- rubric marker block
- solution block
- rubric summary table (rare)

### Rule
- rubric source is primary
- solution text may enrich rubric but should not replace missing rubric automatically unless policy allows
- if essay has no rubric but has a solution:
  - `missing_rubric`
  - likely `needs_review`

### Chosen source
Usually:
- `rubric_marker`
- or `rubric_block_group`

---

## Reconciliation status meanings

### `resolved`
Canonical answer derived confidently and consistently.

### `resolved_with_fill`
Main source resolved, secondary source filled missing fields.

### `resolved_normalized_equivalent`
Raw values differ, normalized values equivalent.

### `conflict`
Multiple strong sources disagree.

### `needs_review`
Not safe to finalize automatically.

### `blocked`
Cannot continue to auto-import/publish due to severe ambiguity.

---

## Conflict detection rules

Flag conflict when:
- two strong sources produce different canonical answers
- summary references impossible question mapping
- solution contradicts both local and summary in explicit ways
- short answer has multiple incompatible normalized answers
- rubric boundary overlaps another question/section

### Conflict issue codes
- `answer_source_conflict`
- `summary_vs_local_conflict`
- `summary_vs_solution_conflict`
- `local_vs_solution_conflict`
- `boolean_subanswer_conflict`
- `short_answer_value_conflict`
- `rubric_source_conflict`

---

## Confidence-aware rules

Reconciliation must consider:
- source type
- confidence
- cue quality
- structural consistency
- question-type policy

### Suggested heuristics
- if one source has confidence >= 0.95 and others are weak/missing -> may resolve automatically
- if two sources both >= 0.85 and disagree -> conflict
- if only weak sources exist -> needs_review

---

## Per-question `answer_sources` structure

```json
{
  "answer_sources": [
    {
      "source": "local_formatting",
      "confidence": 0.91,
      "details": {
        "cue_types": ["underline", "font_color"]
      }
    },
    {
      "source": "answer_summary_table",
      "confidence": 0.98,
      "details": {
        "summary_type": "table"
      }
    }
  ]
}
```

Possible `source` values:
- `local_formatting`
- `answer_summary_table`
- `answer_summary_list`
- `solution_explicit`
- `rubric_marker`
- `rubric_block_group`
- `manual_override`

---

## Reconciliation notes

`reconciliation.notes[]` should be short audit lines, for example:
- `summary filled missing local answer`
- `local and summary normalized to same value`
- `conflict: local=B summary=A`
- `rubric inferred from repeated [R] markers`

---

## QA issues and severity

### Info
- `answer_summary_redundant_but_consistent`
- `solution_confirms_existing_answer`

### Warning
- `answer_resolved_from_summary_only`
- `answer_resolved_from_solution_only`
- `resolved_with_tolerance`
- `rubric_present_but_structure_weak`

### Blocker
- `answer_source_conflict`
- `canonical_answer_missing`
- `boolean_subanswer_conflict`
- `rubric_unusable`
- `summary_mapping_invalid`

---

## Auto-pass rules

Question can be auto-approved only if:
- reconciliation status is one of:
  - `resolved`
  - `resolved_with_fill`
  - `resolved_normalized_equivalent`
- no blocker issue
- confidence passes parser quality gate
- answer_key is canonical and complete

---

## Needs-review rules

Question must go to review if:
- reconciliation status is `needs_review`
- or any blocker/warning policy so requires
- or answer derived only from weak evidence
- or source conflict exists
- or essay rubric incomplete/ambiguous

---

## Runtime placement in pipeline

Pipeline:
```text
DOCX
-> HTML/MathML/assets
-> question segmentation
-> local answer normalization
-> answer summary extraction
-> solution extraction
-> answer reconciliation
-> answer QA gate
-> JSON contract serialization
```

---

## Overrides

If an override manifest exists, it may:
- force chosen source
- replace answer_key
- suppress misleading summary entry
- confirm rubric boundary

When override is applied:
- add `manual_override` to `answer_sources`
- add audit note
- do not erase original source evidence

---

## Không được làm

- không để summary overwrite local answer trực tiếp
- không để solution overwrite answer_key trực tiếp mà không qua reconciliation
- không bỏ evidence sources sau khi reconcile
- không auto-resolve conflict mạnh chỉ vì cần “cho chạy qua”

---

## Success criteria

Spec này được coi là triển khai đúng khi:
- parser tách riêng local answers, answer summary, and solution
- reconciliation sinh ra canonical `answer_key` có audit trail
- conflict được phát hiện thay vì bị che đi
- review UI có thể giải thích rõ vì sao một answer được chọn
- import/publish chỉ nhận câu đã qua reconciliation rõ ràng
