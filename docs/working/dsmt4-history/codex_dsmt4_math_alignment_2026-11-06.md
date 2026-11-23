# DSMT4: căn trái hệ ba hàng trong LibreOffice Math — 2026-11-06

Đã sửa lỗi căn giữa hàng của toan015 ở tuyến **LibreOffice Math riêng**, trong phạm vi cấu trúc có kiểm chứng. Rule A chỉ thay ba candidate toan013–015; 262 candidate còn lại trùng byte với bộ degree follow-up. Toan016 là bảng lồng, tiếp tục giữ nguyên và báo cần review. Corpus vẫn `needs_review`, không tăng accepted, không commit/push/merge hoặc đổi PR.

## Bằng chứng trước khi tích hợp

Presentation của toan015 đã có `columnalign="left"` nhưng importer vẫn căn giữa các hàng. Prototype giữ presentation MathML, sinh annotation StarMath có `alignl`. Đo PDF baseline thấy mép trái ba hàng lệch 5,6 pt; prototype 0 pt, cả trước và sau save/reopen headless. Control cố ý có presentation `x=1`, annotation `x=9`: runtime hiển thị **x=9** và xuất lại presentation cũng thành x=9. Vì vậy annotation phải được sinh từ đúng nội dung đã kiểm; không được ghép lệnh tùy ý rồi coi presentation là đủ bảo toàn.

UI đã hoàn tất trên QA standalone Math: mở `ui-toan015-alignl.odf`, thêm `q` trong hàng thứ ba thành `z=−1−3tq`, Save As sang `ui-toan015-alignl-q-saved.odf`, đóng rồi mở lại. Ảnh `ui-math-reopened.png` ghi đủ ba hàng căn trái và q. Artifact có ba `alignl`, presentation đủ `x=2+5t`, `y=2+2t`, `z=−1−3tq`. Chỉ gõ qua Commands editor sau xác minh focus. `setValue` ban đầu không cập nhật command; file Save As chưa có q được giữ làm artifact thử không tính vào evidence. Dùng selectText + paste đã cập nhật đúng công thức trước lượt lưu cuối.

Đây là standalone Math, **không phải** UI edit của embedded Writer ODT, DOCX, hoặc toàn đề. Output toan015 do code production mới sinh **trùng byte** với MathML đầu vào của prototype đã qua UI. Không chạy lại cùng UI chỉ để tăng số ca, và không suy rộng sang toan013/014 chưa sửa tương tác.

## Giới hạn rule A

`scripts/transpect/prepare_libreoffice_mathml.py` nhận đúng whole-shape:

```text
math (không thuộc tính)
  mfenced(open="{", close="", separators="")
    mtable(columnalign="left")
      đúng 3 × mtr → mtd, không thuộc tính
```

Mỗi cell chỉ có lá không thuộc tính/con: `mi` một chữ ASCII, `mn` chữ số ASCII, `mo` trong `= + - −`. Grammar là một biến lhs, equals, RHS có thể bắt đầu bằng minus, rồi term với binary plus/minus. Term là một số nguyên có tối đa một chữ theo sau, hoặc một chữ. Không chấp nhận hai số/chữ liên tiếp, chained equals, toán tử đầu/cuối không hợp lệ, double operator, style, nội dung lồng, mixed text hoặc whitespace Unicode không phải XML whitespace.

Gate namespace/metadata chạy trước A. Input đã có annotation không bị sửa; chạy lại output A giữ nguyên byte. Presentation node/thuộc tính/text/thứ tự giữ nguyên, được bọc trong `semantics`; thêm annotation `encoding="StarMath 5.0"`. Chỉ cú pháp command đổi Unicode minus thành ASCII hyphen, presentation không đổi ký tự này. Record A ghi command và phiên bản đo ưu tiên annotation. Không chạy các rule khác tiếp trên output A; với hình dạng này không rule W/L/T/G/C/I/B/D nào cần chạy.

Các shape ngoài phạm vi đi qua adapter cũ và diagnostics như trước. Không phải bộ chuyển MathML→StarMath tổng quát, không áp rule lên normalized MathML/OMML Word. Hướng `alignl` dựa trên [tài liệu Math của LibreOffice](https://help.libreoffice.org/latest/en-GB/text/smath/01/03090700.html); hành vi importer và kết quả số đo ở đây chỉ được kiểm trên LibreOffice 26.8.0.3 đang cài.

## Test, review và xử lý finding

Kế hoạch ngắn ghi trong [alignment plan](./dsmt4_math_alignment_plan_2026-11-06.md). Test CLI mới đỏ trước code A vì chưa phát annotation (`alignment-cli-red-verified.log`: sáu subcase failure). Test rỗng 0 hàng ban đầu kỳ vọng sai exit 0; đã chỉnh về `unsupported`/exit 2 trước lượt đỏ cuối. Sau code, đầy đủ **141 Python test đạt** (`python-alignment-reviewed.log`). Bao phủ command chính xác, presentation không đổi, status needs_review/not_run, idempotence, LHS/RHS sai, attrs, namespace/metadata, số hàng, nested table thực của toan016 và mixed text. Không thêm fixture hoặc sửa nguồn.

Cùng **một** Claude session `2fdbb5a4-0d12-417c-a96c-304c0bdbdc80` đã review ba lượt trong đợt joint, chỉ Read/Glob/Grep. [Review lượt A](./claude_dsmt4_alignment_review_2026-11-06.md) không thấy lỗi P1/P2 trong parser/integration. Có P2 ở phép đo cũ: chỉ lấy từ đầu mỗi hàng, bỏ thiếu `t` cuối. Codex sửa extractor để gom **mọi word trong dải y của hàng**, giữ bbox từng word và so toàn chuỗi với presentation nguồn/sau lưu. `measurement-complete.json` và `verification-complete.json` khắc phục finding này cho cả PDF đầu và PDF sau reopen. Không dùng record `first_words` làm full-row-content pass.

Các P3 LHS/command assert/report command đã bổ sung. Grammar sản phẩm không thay đổi sau review; chỉ thêm report metadata và test/cách đo đầy đủ. Chưa có vòng Claude thứ tư, không nói reviewer đã tự chạy test/render/UI. Review P2 mapping từ lượt trước đã được xử lý trong script ledger; ledger mới không nhập pass/fail lịch sử thành verdict hiện tại.

## Chạy trên dữ liệu thật

Output cuối: `out/dsmt4-alignment-followup-v2-2026-11-06/`.

| ID | Nội dung ba hàng sau save | Lệch mép trái đầu/reopen | UI riêng |
| --- | --- | --- | --- |
| toan013 | x=5+2t; y=2+2t; z=−3+t | 0 / 0 pt | not_run |
| toan014 | x=2+5t; y=2+2t; z=1−3t | 0 / 0 pt | not_run |
| toan015 | x=2+5t; y=2+2t; z=−1−3t | 0 / 0 pt | standalone edit/save/close/reopen, input byte-identical |

Ảnh PNG trang đầu và sau reopen trùng byte; đã xem trang sau reopen, mỗi candidate giữ đủ nội dung, ngoặc và ba hàng. Cả ba giữ annotation có ba alignl, presentation sau lưu khớp từng hàng nguồn, toàn bộ text render gồm `t` cuối được đối chiếu. Không có chỉ số số đếm thay thế cho các kiểm tra này. 265 nguồn MathML giữ nguyên hash; full preparation bằng code cuối cho kết quả đúng byte với 265 file đã sinh/render. Toan016 vẫn có diagnostic `table_alignment`, không bị đưa vào A.

Lượt output đầu dừng vì script dự đoán có bốn ca thay đổi. Đọc dữ liệu thật cho thấy toan016 có thêm outer table; guard đã từ chối đúng. Giữ output/log lượt đầu nguyên vẹn, chạy v2 với ba ca đúng; không nới rule để làm con số dự đoán khớp. Candidate Word/32 đề không đổi, vẫn 2.286 chèn / 331 DSMT4 giữ + 10 OLE khác, 27 native → 2.313 OMML. 114 Java và gate 4/4 của joint snapshot vẫn là kết quả kiểm chứng đường Word; thay đổi này chỉ ở Python Math preparation, không dựng lại JAR hoặc lặp render Word.

`current-ledger.json` hiện trỏ đúng bộ Math mới; ba ca thêm evidence scoped cho isolated ODT render/roundtrip, toan015 thêm UI standalone. Các verdict lịch sử vẫn tách riêng. `current_failed_total=null` vì chưa chấm lại mọi tiêu chí trên toàn bộ snapshot; không có nghĩa 0 failed. Accepted promotions vẫn 0. Không công bố lại tổng failed lịch sử hoặc số suy từ việc chỉ sửa một tiêu chí.

## Bằng chứng và phần còn mở

- `work/dsmt4-joint-followup-2026-11-06/math-alignment-probe/ui-verification.json`, ảnh UI và file ODF q-saved.
- `out/dsmt4-alignment-followup-v2-2026-11-06/preparation.json`, `verification-complete.json`, PDF/PNG đầu và sau save/reopen.
- `alignment-current-report-audit.json`: code cuối sinh đúng từng payload, source hash và report A/diagnostics.
- `verification.json`, current ledger, log Python, kế hoạch và các report review nối kết evidence; file trial không được coi là production pass.

Vẫn cần nghiệm thu Writer DOCX (leading relation/mũi tên), nested table toan016, full-exam placement/font/spacing, ca rộng và UI chưa chạy. Không dùng kết quả Math riêng để chứng nhận chúng. FULL_END_ONLY unsupported; 108 safety skip ban đầu và hai OLE Lý ¶91 giữ nguyên. Không sửa in/, ZIP, fixture hoặc output lịch sử; không thay trạng thái PR.
