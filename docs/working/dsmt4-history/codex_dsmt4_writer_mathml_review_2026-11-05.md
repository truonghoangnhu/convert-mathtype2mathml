# Codex review: Writer/MathML follow-up, 2026-11-05

Đã nhận và review bàn giao Claude `f431a462`. **Giữ adapter ở mức prototype, chưa tích hợp production. Corpus vẫn `needs_review`; không occurrence nào được nghiệm thu đầy đủ trong đợt này.** Không commit/push/merge hoặc thay trạng thái Draft PR #4.

## Phát hiện độc lập và quyết định

1. **Lỗi ở F opt-in:** bản bàn giao mở rộng `mfenced` trước khi kiểm tra ranh giới `semantics` và `annotation-xml`. Hai phản ví dụ độc lập làm thay đổi presentation/metadata dù hợp đồng adapter nói không đi vào chúng. Mặc định WLT không có lỗi này. Log đỏ: `work/claude-writer-mathml-followup/codex-opt-in-boundary-red.log`.
2. Bản sửa riêng `work/codex-writer-adapter-ui/candidate-v2/lo_math_adapter.py` đưa kiểm tra ranh giới lên trước F. **6 regression độc lập + 25 test Claude đạt**; log trong cùng thư mục. Bản bàn giao gốc được giữ nguyên. Đây vẫn là bản thử; không suy phạm vi F sang mọi cặp ngoặc hoặc container chưa được probe.
3. Đã xem độc lập ảnh `p3b-writer-embed/docxrt-p-1.png`: Hóa #68 WLT/WLTF trở lại ký hiệu lỗi `¿` khi qua DOCX, dù ODT hiển thị dấu `>` đúng. Adapter MathML cho Math **không sửa được tuyến DOCX OMML của Writer**.
4. Đã xem `p2-alignl/compare3.png`: mẫu hệ #15 căn giữa ở bản raw, annotation StarMath `alignl` mới căn trái; bỏ annotation rồi nhập lại cho kết quả hỏng. Không có cơ sở đổi `m:m` sang `m:eqArr` hoặc thêm bộ sinh StarMath trong đợt này. #13/#14/#16 chưa được Codex xem riêng; không coi cấu trúc giống nhau là bằng chứng render từng ca.

## Kiểm tra giao diện thực tế

LibreOffice Writer 26.8.0.3; thao tác bằng `cua_repl`, chỉ sửa bản QA riêng.

| Mẫu | Thao tác và kết quả | Phạm vi |
| --- | --- | --- |
| Hóa #68, `hoa068 [WLTF]`, Object 3 trong `writer-embedded-ui.odt` | Vào Math editor, thêm `q`, thoát object, lưu ODT, đóng, mở lại, vào editor: `{ { } > 150 ^ ° "C" }q`; ảnh giao diện hiển thị `>150°Cq`, không `¿`. | Object nhúng trong ODT thử; F không áp dụng vào công thức này. Không gọi nhầm là Object 2/WLT. |
| Toán #54, WLTF trong `toan054-embedded-isolated.odt` | Tạo ODT một đoạn từ bản thử Claude, mở editor, thêm `q`, lưu ODT, đóng, mở lại. Editor: `{ int csup 2 csub 0 { { ( { 2 f { ( x ) } - 1 } ) } d x } }q`; ảnh giao diện giữ đúng ngoặc ngoài, ngoặc `f(x)`, cận 0/2 và `q`. | Một công thức trong tài liệu thử; không phải bố cục đề gốc. |

Đường dẫn hai bản QA và JSON kiểm chứng ở `work/codex-writer-adapter-ui/`. Bản Hóa UI save đã serialize lại 20 storage object, gồm các object không sửa; **không có tuyên bố bảo toàn byte hoặc nội dung của mọi object sau lượt UI save này**. Chỉ xác nhận nội dung và edit/reopen của mẫu đã quan sát. Các thao tác điều hướng chưa lưu sau đó được bỏ, không đưa vào kết quả.

Không chạy lại UI xuất DOCX trong đợt này; bằng chứng DOCX thất bại ở trên là render headless của Claude đã được Codex xem độc lập. Word căn hàng hệ #15 chưa chạy trong follow-up này. Không suy kết quả Word từ Writer hoặc XML.

## Bằng chứng và giới hạn

- Bàn giao gốc: `docs/working/dsmt4-history/claude_dsmt4_writer_mathml_followup_2026-11-05.md`; ảnh/log/ledger: `out/dsmt4-writer-mathml-followup-2026-11-05/`. Bản copy đã đối chiếu SHA với scratch; đây là kiểm tra vận chuyển artifact, không phải nghiệm thu công thức.
- Test độc lập: `work/codex-writer-adapter-ui/test_candidate_boundaries.py`; log xanh candidate-v2: `independent-green.log`, `claude-tests-green.log`.
- UI Hóa: `embedded-ui-verification.json`; UI Toán: `toan054-ui-verification.json` trong cùng thư mục.
- Ledger Claude 17 failed / 248 needs_review / 0 accepted chỉ mô tả tiêu chí nhập MathML vào Math ở prototype; không thay ledger nghiệm thu Word/Writer của corpus.
- Mũi tên vectơ/nhãn, căn hàng, font, spacing và bố cục toàn đề vẫn còn giới hạn. Không tích hợp WLT/F chỉ dựa trên hết `¿`, token hoặc số đếm.
- Mã chính và MathML chuẩn hóa/OMML Word không đổi trong follow-up này. Không chạy lại Maven/gate toàn bộ vì không có sửa production; mốc trước đó 92 Java test và gate 4/4 vẫn là bằng chứng của snapshot trước, không phải test mới.

Đợt theo dõi Claude và review prototype đã bàn giao xong. Bước sản phẩm kế tiếp cần là một tuyến xuất MathML/ODT dành riêng cho LibreOffice có hợp đồng rõ ràng và kiểm tra bố cục trong đề gốc; tuyến DOCX hiện vẫn phải báo lỗi/needs_review ở các ca nêu trên. `FULL_END_ONLY` và các OLE đang giữ nguyên không được mở rộng phạm vi.
