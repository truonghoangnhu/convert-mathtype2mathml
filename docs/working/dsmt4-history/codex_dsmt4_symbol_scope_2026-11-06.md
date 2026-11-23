# DSMT4: xử lý finding phạm vi symbol và diagnostic — 2026-11-06

## Thay đổi

- `src/main/resources/letterlike_policy.xml` là nguồn chung cho phạm vi symbol cần review của Java và tập pure symbol được XSLT chuyển thành math run. Chỉ bốn ký hiệu có bằng chứng Word ℝ/ℤ/ℕ/ℓ được chuyển; không còn tự đưa ℃, №, ™, ℅, 𝑥 hoặc ℂ sang `sty=p`.
- Normal-text run có symbol trong U+2100–214F hoặc U+1D400–1D7FF nay bị giữ để review khi m:nor bật. Đây là lựa chọn bảo toàn cho phạm vi chưa kiểm chứng, **không** kết luận Word làm mất mọi ký hiệu trong hai block. Có thể giữ OLE cho cả ký hiệu đơn vị không lỗi; đây là chi phí của phạm vi bảo thủ, chưa có bằng chứng để nới từng ký hiệu.
- `ommlRejectionReason` phân biệt `normal_text_symbol_requires_review`, `missing_script_base`, `empty_math_content`, invalid XML/root/parent và bare text. Patcher ghi lý do cụ thể; skip category vẫn `OMML_CONVERSION_FAILED` để tương thích telemetry. Chưa có candidate accepted nào được suy ra từ cổng này.
- Test phủ m:nor absent/1/on/true và 0/false/off, ℂ/ℚ/𝐯, ordinary units, NBSP, đúng skip reason và output package trùng byte khi giữ OLE.
- Converter cung cấp systemId của stylesheet để policy tương đối được nạp cả từ classes và packaged JAR. Chạy patch CLI thật và modern gate đã kiểm tra tuyến packaged JAR.

## Bằng chứng

`work/codex-dsmt4-symbol-scope-2026-11-06/`:

- `red.log`: guard/code cũ cho z ∈ ℂ được vá thay vì giữ; test thất bại.
- `final-java.log`: `mvn -q -o package`, **100 test Java đạt**, 0 failure/error.
- `pure-policy-red.log`/`pure-policy-green.log`: probe riêng thay classpath resource bằng policy rộng trước đó để tái hiện việc ℃ bị đổi sang math run. Resource production và output cũ không bị sửa cho phép thử này; policy mới giữ normal text và cổng giữ OLE.
- `python.log`: 116 tests; `workflow.log`: 4 tests; `gate.log`: modern generated-output gate 4/4, không phải nghiệm thu ứng dụng.
- Output mới `out/dsmt4-symbol-scope-2026-11-06/corpus/`: chạy lại 32 đề; `corpus-check.json` ghi tập part và nội dung canonical trùng snapshot run-boundaries trước. Không thêm OLE bị giữ trong corpus hiện có; không mở rộng bất kỳ safety skip cũ nào.

Không chạy UI Word/Writer mới trong đợt này. Các ký hiệu ngoài bốn mẫu không được tuyên bố đã kiểm chứng trên Word; chúng được giữ để tránh tự đổi kiểu chưa có bằng chứng. Ledger baseline vẫn 0 accepted / 219 needs_review / 46 failed; không tự cập nhật thành nghiệm thu mới.

Đã giao Claude review lại, chỉ đọc. Lần resume phiên trước bị CLI từ chối vì không có deferred marker; phiên đó kết thúc lỗi, không phải bị quota. Tạo phiên review mới với scope tương đương, metadata `claude-fresh-launch.json`; kết quả được lưu riêng khi hoàn thành. Không bypass guard, không dùng worktree mới.

Chưa commit/push/merge/đổi Draft hoặc đăng GitHub. Các lỗi Writer/Math và các phép UI chưa chạy vẫn còn; đợt sửa này không hoàn tất nghiệm thu DSMT4.

## Chốt sau review Claude

Claude đã hoàn tất review chỉ đọc: `claude_dsmt4_symbol_scope_review_2026-11-06.md`. Không còn finding P1/P2 về tính đúng của mã trong phạm vi đọc. Review chưa chạy test/UI độc lập, và còn nêu một P3 JSONL cùng các chỗ thiếu bằng chứng; đã xử lý tiếp như sau:

- Summary/JSONL có trường cộng thêm `conversion_diagnostics`, đếm các lần validation thất bại theo mã lý do. Nó không phụ thuộc log warnings và không đổi skip category cũ. Đây là số lần resolution đã thử, không nhất thiết bằng toàn bộ unresolved trong đoạn nhiều object. Các constructor PatchSummary cũ vẫn dùng được.
- Test trước bổ sung JSONL thất bại (`jsonl-red.log`); test workflow xác nhận đúng diagnostic và byte-identical OLE, test JSONL xác nhận trường thực sự được serialize dù không có warning log.
- Chạy mới `mvn -o package` không dùng `-q`: `final-java-verbose.log` có **Tests run: 101, Failures: 0, Errors: 0, Skipped: 0** và BUILD SUCCESS. Python vẫn 116, workflow 4.
- `packaged-policy-probe.log`: chạy SymbolPolicyProbe bằng class từ jar-with-dependencies, không override stylesheet/policy. Có mtext thật, nên kiểm tra được việc XSLT nạp policy từ JAR; không chỉ dựa vào gate modern không có mtext.
- Output cuối: `out/dsmt4-symbol-scope-2026-11-06/final-corpus/` và `final-modern-gate/`. File `final-corpus-check.json` đối chiếu với snapshot run-boundaries; trong khi log repatch_compare so với snapshot finalization cũ hơn nên vẫn ghi 48 phương trình đổi thuộc tính. Hai phép so sánh có baseline khác nhau, không mâu thuẫn.

Claude chưa review lại phần bổ sung telemetry JSONL sau kết luận trên. Không gọi review đó là chứng nhận phần bổ sung này hoặc nghiệm thu DSMT4 toàn bộ.
