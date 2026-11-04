# Bàn giao review DSMT4 cho Claude Code

Trạng thái: đã chuẩn bị, **chưa giao/chạy Claude Code**. Session Codex không có
connector Claude Code và không tìm thấy lệnh `claude` trong PATH.

## Nhiệm vụ

Review độc lập, chỉ đọc mã và dữ liệu. Tìm lỗi có thể làm mất/sai nội dung,
vị trí, khả năng sửa hoặc hiển thị công thức; kiểm tra xem kết luận trong báo
cáo có vượt quá bằng chứng hay không. Không triển khai sửa lỗi trong lượt review.

Repo: `/Users/truonghoangnhu/Desktop/convert-mathtype2mathml`.
Base HEAD: `1a1ed5d8e93346575e937014f7c237d36ef1e8a8`.
Các thay đổi **chưa commit**, gồm cả tệp untracked. Review working tree thực tế,
không chỉ HEAD hoặc `git diff` của các tệp đã tracked.

## Đọc trước

1. `docs/support_scope_policy.md`
2. `docs/dsmt4_real_corpus_2026-11-03.md`
3. `docs/dsmt4_migration_acceptance.md`
4. `git diff` và các tệp mới dưới `fixtures/dsmt4/`.

Bản kê SHA-256 của tệp đầu vào review được lưu cục bộ tại
`work/claude-review/review-input-manifest.json`. Nếu tệp đã đổi khi bắt đầu
review, ghi rõ phiên bản thực tế đã xem; không quy kết finding cho snapshot cũ.

## Bối cảnh cần giữ đúng

- 32 DOCX, 2.617 lần xuất hiện Equation.DSMT4, 27 OMML native, 10 OLE khác.
- Đã parse trực tiếp 2.100 BIN MathType khác nhau, tương ứng 1.934 hash MTEF.
- Đã tạo 2.508 ứng viên OMML; 109 MathType còn giữ nguyên.
- Một FULL_END_ONLY chưa có body để chuyển; không có recovery được chứng minh.
- Toàn corpus vẫn `needs_review`. Đếm đủ/parse được/XML hợp lệ không chứng minh
  đúng công thức hoặc hiển thị đúng. Không nâng thành `accepted` từ các số trên.
- Đã thử sửa/lưu/mở lại mẫu mũi tên trong Word và LibreOffice Math. Writer đã
  save ODT/reopen/render; chưa thử sửa tương tác embedded formula trong Writer.
- Mũi tên ngắn hơn và nhãn có khác biệt khoảng cách so với OLE preview.

## Phạm vi mã ưu tiên

- `src/main/java/com/example/docxmath/word/XmlBeansOmmlInjector.java`:
  tách run trước/sau object; oMath phải dưới w:p; giữ rPr, drawing, text,
  dấu ngắt trang; rollback có khôi phục đầy đủ khi lỗi giữa chừng không?
- `src/main/java/com/example/docxmath/word/PoiMathSourceDetector.java`:
  block chỉ được sở hữu paragraph chỉ chứa object; không xoá đơn vị,
  nhãn đáp án, field, bookmark, ảnh hoặc cấu trúc paragraph khác.
- `src/main/java/com/example/docxmath/word/DocxMathPatchMain.java`:
  exception, sidecar hỏng/rỗng, OMML rỗng/bare text phải giữ OLE; báo rõ trạng thái.
- `src/main/java/com/example/docxmath/word/BasicMathmlNormalizer.java`,
  `src/main/java/com/example/docxmath/MathmlContent.java`,
  `scripts/transpect/mathml_content.py`,
  `scripts/transpect/generate_sidecars.sh`,
  `src/main/java/com/example/docxmath/DocxToHtmlConverter.java`:
  namespace, metadata/phantom, khoảng trắng, content bị bỏ một phần và nhất quán
  giữa Java/Python/HTML/cache/manifest. Gate có nội dung không phải semantic validator.
- `src/test/java/com/example/docxmath/word/DocxMathPatchWorkflowTest.java`,
  `tests/test_mathml_content.py`, `tests/test_dsmt4_corpus_audit.py`:
  test có bắt lỗi thực hay chỉ kiểm tra dấu hiệu XML/số lượng?

## Bằng chứng để tự đối chiếu

Các thư mục `in/`, `tools/`, `work/`, `out/` bị gitignore nhưng có trong máy này.
Không coi việc chúng không xuất hiện trong git diff là thiếu dữ liệu tại chỗ.

- `out/dsmt4-real-corpus/source_inventory.json`: nguồn/hash/vị trí/XML occurrence.
- `out/dsmt4-real-corpus/mtef_inventory.json`: kết quả parse BIN theo từng object.
- `out/dsmt4-real-corpus/batch_report.json`: output và preservation checks.
- `out/dsmt4-real-corpus/patched/`: DOCX candidates cuối cùng.
- `out/dsmt4-real-corpus/chemistry-arrow-evidence/application_evidence.json`.
- `fixtures/dsmt4/chemistry-arrows/` và `fixtures/dsmt4/full-end-only/`.
- `work/dsmt4-real-corpus/repatch_verify.py`, `probe_all_bins.py` và
  `out/dsmt4-real-corpus/bin_payload_probe.jsonl`: phương pháp audit tại chỗ.

Chọn vài ca đối kháng cụ thể để đối chiếu trực tiếp DOCX nguồn/output; đừng chỉ
tin `all_preservation_checks_pass`. Đặc biệt kiểm tra phần mà audit chưa đo:
run properties, tab/break, field, drawing placement, headers/footers và văn bản
trong textbox. Phân biệt lỗi mới, lỗi tồn tại trước, và khoảng trống bằng chứng.

## Cách làm và giới hạn phối hợp

- Không sửa mã, fixture, đề gốc, output hiện có hoặc trạng thái git.
- Không commit, reset, stash, clean, cài dependency hoặc đổi runtime.
- Có thể tạo script/bằng chứng riêng trong `work/claude-review/`.
- Chưa chạy lại batch hoặc generator ghi đè `out/`/`work/dsmt4-real-corpus/`.
- Nếu cần build/test, báo trước để tránh tranh chấp `target/` với agent triển khai.
  Test Python có một ca cũ phụ thuộc manifest modern-output đã sinh sẵn trong out/.
- Không giả định mọi Equation.DSMT4 cùng cấu trúc; phân loại bằng MTEF thực tế.
- Không suy công thức từ preview/fingerprint hoặc khẳng định FULL_END_ONLY đã giải mã.

## Kết quả cần trả

Ghi vào `docs/working/claude_dsmt4_review.md`:

1. Findings theo P0/P1/P2: file + dòng, trigger, tác động, bằng chứng/tái hiện,
   đề xuất sửa và test cần thêm. Nếu không có finding actionable, nói rõ.
2. Những kết luận báo cáo đã kiểm chứng độc lập và những kết luận chưa đủ bằng chứng.
3. Các lệnh/ca đã kiểm tra và giới hạn còn lại.
4. Ba việc tiếp theo theo ưu tiên. Tách rõ review với triển khai chưa được làm.

Không cần lặp lại toàn bộ diff hoặc tạo báo cáo dài nếu không có finding.

## Sau review

Codex tiếp nhận findings, tái hiện lỗi, thêm regression rồi sửa và chạy gate.
Việc triển khai kế tiếp ưu tiên là độ dài mũi tên/khoảng cách nhãn trên mẫu Hóa.
Một nhiệm vụ phân tích riêng sau đó là phân nhóm 108 object chưa patch bởi điều
kiện an toàn, giữ FULL_END_ONLY ở trạng thái unsupported. Không giao hai agent
cùng sửa injector/XSLT hoặc cùng điều khiển Word/Writer trong một lượt.
