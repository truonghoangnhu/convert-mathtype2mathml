# Codex tiếp nhận audit 5 đề và sửa converter

> Đợt mới: [R1 đã tái hiện trong Word và chặn bằng giữ OLE](./codex_dsmt4_r1_2026-11-05.md),
> 92 test Java và gate 4/4 đạt; số liệu corpus không đổi so với đợt prescript.

> Cập nhật mới: [sửa thứ tự prescript](./codex_dsmt4_prescript_order_2026-11-05.md).
> Kết luận cũ về `sPre` đúng nhưng Writer mất C đã được đính chính: lỗi thứ tự
> nằm ở converter và đã sửa, kiểm cả Word/Writer UI. Các mục dưới là các snapshot theo đợt.

Claude đã bàn giao audit trong
`claude_dsmt4_five_exam_acceptance_2026-11-05.md`: 265 occurrence có ledger,
12 object failed trong Writer trên output đã audit, 251 còn needs_review,
hai OLE giữ nguyên. Word và sửa ký tự qua UI Writer chưa chạy trong audit.
Đây là kết quả trên snapshot cũ, không phải số lỗi đã đo lại sau các sửa dưới.

## Kiểm chứng độc lập và sửa hẹp

Codex đã xem lại ảnh nguồn/output và xác nhận ô placeholder của Lý #1. Hai
finding khác có lỗi ở cấu trúc converter đã được tái hiện và sửa trước:

1. Toán TQB #54, đoạn 43: `mfenced separators=""` chứa `2`, `f`, `(x)`, `−`,
   `1` bị xuất thành năm đối số `m:e` của delimiter. Writer nhập sai thành
   chữ `left`/dấu `¿` và giữ chữ sai sau lưu. Với separators rỗng, converter
   nay tạo một `m:e` chứa cả biểu thức, giữ delimiter `(x)` bên trong. Các
   trường hợp separators mặc định hoặc có dấu phân cách giữ hành vi cũ.
2. Hóa Hà Nội #66/#67, đoạn 146/147: `mover(→, mrow rỗng)` tạo `limUpp` có
   đối số nhãn rỗng và in placeholder. Nhánh hẹp mới xuất mũi tên thường khi
   nhãn chính xác là `mrow` rỗng. Không thay cách xử lý nhãn có nội dung.

Hai test hồi quy đỏ đúng nguyên nhân trước sửa (5 đối số thay vì 1, một
`limUpp` thay vì 0). Sau sửa, `mvn -q -o package`: **85 test, 0 fail/error**.
Log: `work/codex-five-exam-fixes/converter-red.log`, `maven-green.log`.

## Kết quả Writer sau sửa

Chạy lại CLI thật cho cả 5 đề, dùng nguồn/manifest cũ không đổi. Output mới:
`out/dsmt4-converter-followup-2026-11-05/`. Không ghi đè output đã audit.

Đã render 5 output bằng Writer headless profile riêng và lưu lại chúng thành
DOCX ở thư mục `writer-resave/`. Codex xem Toán trang 2, Hóa trang 3/4:
biểu thức tích phân đọc được `(2f(x)−1)`, không có chữ `left`/`¿`; hai mũi tên
không còn ô nhãn rỗng phía trên. Sau lưu lại bằng Writer, text OMML của ba
ca này giống trước lưu. Bằng chứng:
`work/codex-five-exam-fixes/verification.json` và các PNG cùng thư mục.
Đây là roundtrip headless không sửa ký tự qua UI, chưa phải nghiệm thu Word.

## Word xác nhận thêm trên mẫu tách riêng

Codex đã mở `work/codex-word-acceptance/glyph-cases.docx` trong Word 16.114.3
và xem 20 mẫu OMML lấy nguyên từ output mới. Đây là mẫu tách riêng có nhãn
ca thử, không giữ ngữ cảnh đoạn/bảng; không dùng nó để nghiệm thu bố cục.

- Word cũng in placeholder ở Lý #1 và TN #27/#30. AX mô tả cơ sở là `empty`;
  ảnh có ô chấm cạnh chỉ số. Như vậy đây là lỗi converter thực ở cả hai ứng
  dụng, không chỉ là giới hạn Writer.
- Word giữ `C` trong tiền chỉ số của Lý #8 và dấu `>` của Hóa #68. Hai ca này
  khác Writer, nơi glyph mất/hỏng và bị mất khi lưu.
- Toán #54 sau sửa đọc được tích phân với `(2f(x)−1)`; Hóa #66 có mũi tên
  thường, không có đối số nhãn rỗng. Chưa sửa/save/reopen các ca này trong Word.
- Nhãn mũi tên hai chiều Hóa #37 vẫn cần xem kích thước; không tuyên bố các
  mũi tên có nhãn đạt chỉ vì có đủ ký tự trong XML.

Tệp `work/codex-word-acceptance/cases.json` ghi source/object/paragraph và
chuỗi trước kiểm; `observations.json` ghi phạm vi và kết quả quan sát. Còn
phải kiểm ngữ cảnh gốc và chỉnh sửa/mở lại. Quét cấu trúc: có ba script base
rỗng trong output bộ 5 đề; output 32 đề cũ có 54 đối số rỗng (không đồng nghĩa
54 object), cần xử lý theo hướng bảo toàn OLE hoặc chuẩn hóa có bằng chứng.

## Còn phải tiếp tục

- Kiểm trong Word các nhóm ca mà Claude liệt kê, ưu tiên đối số rỗng,
  tiền chỉ số, dấu `>` và sửa bên trong ngoặc của Toán #54.
- Writer UI sửa/save/close/reopen chưa chạy; một lần lưu headless không thay
  thế được việc này.
- Cơ sở rỗng ở Lý #1, TN #27/#30 đã được chặn theo mục dưới; Writer làm mất C trong tiền chỉ số Lý #8;
  dấu `>` Hóa #68 bị mất sau lưu; mũi tên có nhãn, hệ phương trình, spacing
  và kiểu chữ vẫn mở. Chưa cập nhật lại toàn bộ ledger sau sửa, không tự trừ
  ba ca khỏi tổng 12 failed để tuyên bố nghiệm thu.
- R1 của review căn lề (proofErr, run rỗng, khoảng trắng) cần Word kiểm.
- Chưa mở rộng hai OLE Lý đoạn 91; FULL_END_ONLY vẫn unsupported; không đổi
  policy của 108 safety skip cũ. Corpus vẫn needs_review.

Chưa commit/push/merge, chưa đổi Draft PR #4.

## Chặn cơ số script rỗng và bảo toàn OLE

Sau khi Word và Writer đều xác nhận placeholder, cổng OMML từ chối các
`m:sSup`, `m:sSub`, `m:sSubSup`, `m:sPre` thiếu `m:e` hoặc có cơ số không
chứa phần tử nội dung (chỉ `m:argPr` cũng bị từ chối). Không ghép chỉ số vào
ký tự bên cạnh bằng suy đoán. Tiền chỉ số có cơ số đầy đủ và các giới hạn
nary tùy chọn rỗng vẫn được chấp nhận. Đây là kiểm tra có phạm vi giới hạn,
không phải kiểm chứng toàn bộ ngữ nghĩa OMML.

Hồi quy bao gồm gate, mẫu degree/nuclide và đoạn nhiều object: nếu một công
thức không hợp lệ, giữ toàn bộ đoạn theo chính sách mutation nguyên tử.
Đã có vòng đỏ/xanh; `mvn -q -o package` đạt **89 test, 0 failure/error**.
Log: `work/codex-five-exam-fixes/script-base-red.log` và
`script-base-green.log`.

Output 5 đề mới, không ghi đè các snapshot trước:
`out/dsmt4-script-base-guard-2026-11-05/`. Có **252 công thức chèn, 13 OLE
giữ lại**, cộng 18 OMML nguồn thành 270 OMML output. Tăng 11 OLE giữ lại:
Lý đoạn 28 (1), TN đoạn 125 (6), TN đoạn 128 (4). Ba công thức cơ số rỗng
khiến tám object cùng đoạn được giữ lại theo chính sách nguyên tử; không
phải cả 11 công thức đều có lỗi cơ số. Hai OLE Lý đoạn 91 vẫn giữ nguyên.

Đã kiểm các đoạn giữ thêm giống nguyên bản, các OMML nguồn, nội dung/định
dạng run ngoài công thức, thuộc tính đoạn, số đoạn và byte embedding được
bảo toàn ở cả 5 tệp. Nguồn không đổi. Manifest và bằng chứng:
`out/dsmt4-script-base-guard-2026-11-05/manifest.json`,
`work/codex-five-exam-fixes/script-base-verification.json`.
Đây là kiểm chứng cấu trúc; output guard mới chưa được render/UI nghiệm thu.
Chưa chạy lại toàn bộ 32 đề sau guard, không thay số liệu corpus cũ bằng
suy diễn. Ledger audit cũ vẫn là snapshot riêng, chưa được nghiệm thu lại.

## Chặn UI và bàn giao tiếp tục

CUA báo Mac bị khóa và không tự mở khóa được. Đã yêu cầu người dùng mở khóa;
chưa thực hiện edit-save-close-reopen Word/Writer trên các mẫu mới. Không
thử vượt màn hình khóa. Sau khi mở khóa, tiếp tục các mẫu Toán #54, Lý #8,
Hóa #68 và bố cục R1 trong ngữ cảnh gốc; sau đó cập nhật ledger bằng kết quả
ứng dụng thực. Các giới hạn Writer, spacing/font và hệ phương trình vẫn
mở. Corpus vẫn `needs_review`; chưa commit/push/merge hoặc đổi Draft.
Heartbeat theo dõi dừng tại bàn giao này để không lặp kiểm tra khi chờ mở
khóa Mac; có thể tiếp tục trong chat sau khi người dùng báo đã mở khóa.

## UI tiếp tục sau khi người dùng mở khóa Mac — 2026-11-05

Người dùng đã mở khóa Mac; blocker khóa máy ở mục trên đã hết. Không khởi
tạo lại Claude hoặc heartbeat. Các tệp thử dưới đây là bản sao công thức
tách riêng, không phải bản đề gốc hay output giao nhận.

### Word: ba mẫu đã sửa, lưu, đóng và mở lại

Trong Word 16.114.3, đã thêm `q` bằng UI, lưu DOCX, đóng cửa sổ và mở lại:

- Toán #54: `q` nằm bên trong cặp ngoặc ngoài của tích phân; sau mở lại AX
  đọc được biểu thức và XML xác nhận `q` nằm trong `m:d/m:e`. Cấu trúc
  ngoặc lồng vẫn hiển thị đúng trong mẫu thử.
- Lý #8: sửa cơ số thành `Cq`, tiền chỉ số 14/6 và `Cq` còn sau mở lại.
- Hóa #68: thêm `q` sau `>`, cả `>q150°C` vẫn còn sau mở lại.

Bằng chứng lưu tại `work/codex-word-acceptance/word-ui-roundtrip.json` và
ba cặp `*-edit.before.docx` / `*-edit.docx`. Các lần đặt con trỏ ban đầu
chưa đúng đã được undo trước phép thử cuối; bằng chứng chỉ ghi thay đổi
cuối đã kiểm lại trong OMML. Không dùng các tệp có ký tự thử làm reference
nội dung nguồn.

### Writer: sửa được mẫu tích phân, hai ca mất nội dung được tái hiện

Chọn object bằng bàn phím, Enter vào Math editor; thêm `q` ở cuối công thức
trong editor đang focus, lưu ở định dạng DOCX, đóng và mở lại, Enter vào
Math editor kiểm tiếp:

- Toán #54 còn biểu thức tích phân với ngoặc lồng và ký tự mới `q`; không
  còn chữ `left` hoặc `¿` trong phần hiển thị. Đây là một phép sửa thật
  trong công thức, khác với roundtrip headless không chỉnh sửa trước đó.
- Lý #8: ngay khi nhập, Math editor là `<?> lsub {6} lsup {14}`, thiếu `C`.
  Sau sửa/lưu/mở lại vẫn là placeholder và thiếu `C`; DOCX có text `614q`.
- Hóa #68: trước lưu, editor có `> {150} ^ {°} "C"` nhưng hiển thị `¿150°C`.
  Sau sửa/lưu/mở lại, editor và DOCX đều mất `>`; còn `150°Cq`.

Hai ca sau **không đạt nội dung**, dù chỉnh sửa được và tệp mở lại được.
Word giữ hai glyph tương ứng. Chưa có sửa converter có bằng chứng khắc
phục việc nhập/xuất này của Writer; không đánh dấu accepted. Bằng chứng:
`work/codex-word-acceptance/writer-ui-roundtrip.json` và ba tệp
`*-writer-ui.docx`.

### R1: bốn đoạn có khoảng trắng cuối, chưa cần đổi policy

Đã tạo `work/codex-word-acceptance/r1-source-candidate.docx`, giữ nguyên các
đoạn nguồn 151/153/155/157 và các đoạn OMML tương ứng từ snapshot
`dsmt4-word-placement-2026-11-04`, kèm nhãn bên ngoài đoạn để đối chiếu.
Word mở ở Compatibility Mode: cả bốn OLE nguồn và bốn OMML inline có
khoảng trắng cuối đều ở lề trái. Không tái hiện lỗi tự căn giữa trên bốn
đoạn này, nên không đổi chính sách bằng suy đoán. Mẫu ghép không kiểm chứng
phân trang toàn đề; các biến thể proofErr/run rỗng còn phải thử riêng.

### Phạm vi còn mở

Đã hoàn thành UI roundtrip đại diện nêu trên, chưa hoàn tất nghiệm thu cả
265 occurrence, 18 OMML nguồn trong ngữ cảnh đề, hay toàn bộ nhóm ca ở bàn
giao Claude. Còn bố cục gốc/bảng/phân trang, nhãn mũi tên, hệ phương trình,
font/spacing, các biến thể R1 khác, và cập nhật lại ledger sau guard mới.
252 chèn/13 OLE giữ lại là số liệu output guard, không phải số accepted.
Corpus tiếp tục `needs_review`. Không sửa mã production trong lượt UI này;
không commit/push/merge, không thay đổi Draft PR #4.
