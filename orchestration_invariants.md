# orchestration_invariants.md

## Mục tiêu

Tài liệu này chốt các **invariants** cho lớp orchestration của pipeline convert, nhằm ngăn:
- convert lặp vô tận
- nhiều thread/process xử lý cùng một input
- scan ăn lại chính output do hệ thống sinh ra
- QA/cleanup vô tình kích lại convert

Phạm vi:
- wrapper chạy 1 file
- batch entrypoint
- cache / lock / discovery
- không bàn về logic convert nội dung

---

## 1. Single-input invariant

Mỗi lần convert chuẩn chỉ được xử lý **một input DOCX mục tiêu**.

### Rule
- wrapper single-file chỉ nhận **1 DOCX explicit**
- không tự scan thư mục
- không tự tìm thêm việc
- không tự ăn output vừa sinh

### Cấm
- implicit recursive discovery
- process-all-files-in-dir mặc định
- watch mode mặc định

---

## 2. Explicit-discovery invariant

Discovery recursive chỉ được phép khi **opt-in rõ ràng**.

### Rule
- batch mode phải yêu cầu flag explicit, ví dụ:
  - `--allow-recursive-discovery`
- nếu không có flag này, orchestration phải từ chối scan rộng

### Mặc định
- `--input-docx <file>` là đường đi chuẩn

---

## 3. Output-exclusion invariant

Output không bao giờ được coi là input mới.

### Bắt buộc exclude khỏi discovery
- `out/`
- `work/`
- `*_files/`
- file `*-transpect.html`
- QA JSON / QA markdown
- diff reports
- temp artifacts
- publish artifacts
- cache directories

### Rule
- mọi pass discovery phải có output exclusion rõ ràng
- output của run hiện tại và run trước đều không được đưa lại vào queue input

---

## 4. One-input-one-job invariant

Một input canonical path chỉ được phép có **1 conversion job active** tại một thời điểm.

### Rule
- dùng per-input lock
- dedupe theo canonical path
- nếu input đang có run active:
  - từ chối job mới
  - trả exit code rõ ràng
  - log rõ lý do

---

## 5. Cache invariant

Nếu input hash và toolchain fingerprint không đổi, orchestration phải **skip convert**.

### Rule
- cache key tối thiểu gồm:
  - canonical input path
  - input content hash
  - toolchain/config fingerprint
- nếu output hiện tại còn hợp lệ:
  - trả cache hit
  - không convert lại

### Cấm
- rerun convert chỉ vì có QA/debug artifacts mới
- rerun convert chỉ vì output folder có file mới

---

## 6. QA non-trigger invariant

QA/cleanup/sanitization **không được kích hoạt một conversion pass mới**.

### Rule
- convert -> qa -> cleanup là flow một chiều
- QA chỉ đọc output hiện có
- cleanup chỉ xử lý output hiện có
- nếu thiếu artifact, phải báo lỗi rõ ràng, không tự convert lại ngầm

---

## 7. Logging invariant

Mỗi conversion run phải log **duy nhất một lý do bắt đầu**.

### Phải log
- input canonical path
- run id
- start reason
- cache miss / cache hit reason
- lock refusal nếu có

### Ví dụ reason hợp lệ
- `no cache key present`
- `input hash changed`
- `toolchain fingerprint changed`

### Không được
- log mơ hồ kiểu “starting conversion” mà không nói vì sao

---

## 8. Cleanup invariant

Cleanup chỉ được xóa **generated trash an toàn**, không bao giờ xóa input hoặc output hiện hành còn được tham chiếu.

### Không được xóa
- source DOCX
- current final HTML
- current asset bundle đang được HTML tham chiếu
- current QA deliverables
- cache đang còn hợp lệ
- spec/policy/config files

### Được xóa nếu an toàn
- stale temp dirs
- orphaned debug artifacts
- output cũ không còn được tham chiếu
- stale lock files đã xác minh không còn process sống

---

## 9. Stale-lock invariant

Lock phải tự bảo vệ trước crash.

### Rule
- lock nên chứa:
  - PID
  - timestamp
  - input path
- nếu process không còn sống hoặc lock quá hạn hợp lý:
  - cho phép stale-lock recovery
  - phải log rõ hành động recovery

---

## 10. Deterministic-run invariant

Cùng một input, cùng toolchain/config, cùng output target:
- hoặc convert 1 lần
- hoặc cache hit
- nhưng không được có hành vi ngẫu nhiên/dao động

---

## 11. Required behavior summary

Pipeline orchestration đúng phải thỏa:

1. explicit input by default
2. recursive discovery only by opt-in
3. outputs excluded from discovery
4. one canonical input = one active job
5. unchanged input/toolchain = cache hit
6. QA/cleanup never retrigger convert
7. every run has a clear logged start reason
8. stale locks recover safely
9. cleanup never deletes referenced current outputs

---

## 12. Rule cho Codex/dev

```text
When editing orchestration, preserve these invariants:

- single explicit input by default
- recursive discovery only by explicit opt-in
- never rediscover generated outputs as inputs
- one canonical input path = one active conversion job
- use per-input lock
- use hash + toolchain fingerprint cache
- QA/cleanup must never trigger convert again
- every conversion must log exactly why it started
- cleanup must be safe and must not delete current referenced outputs
```
