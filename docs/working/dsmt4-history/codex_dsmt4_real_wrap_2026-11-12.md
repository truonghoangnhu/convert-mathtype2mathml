> Trạng thái mới nhất: đã hoàn tất Writer sửa–lưu–đóng–mở lại và xuất PDF; INT vẫn mất `=`. Đối chứng Word chỉ bỏ noBreak đã tự xuống dòng. Các mục bên dưới ghi diễn biến theo thời điểm; xem mục cuối để biết kết quả hiện tại. Chưa có sửa production hay tăng accepted.

# DSMT4 real formula wrapping spike

Scratch ngày 12/11/2026, chưa sửa production/chưa commit/push. Ba công thức lấy từ output snapshot có liên kết OLE Equation.DSMT4 thật: hàm mũ Toán Tạ Quang Bửu p64 math0; tích phân Toán Tuyên Quang p152 math2; bán phản ứng Hóa Bắc Ninh p142 math0. Plan.json ghi source/output hash, relationship và BIN hash. Đây chưa phải nội dung đã nghiệm thu theo nguồn: tích phân có operand đầu rỗng trong OMML, Hóa có electron plain 2e; các hạn chế này giữ nguyên.

## Thiết kế thử

`work/dsmt4-real-wrap-2026-11-12/build_real_probes.py` tạo sáu trang, mỗi dạng có baseline và eqArr ba hàng, text-width 180pt trong trang400pt. Chỉ cắt plain run tại ranh giới đã chọn: hàm mũ trước −5000 và +200000; tích phân trước dấu = thứ hai và tích phân cuối; Hóa trước +3H và →. Các subtree d/sSup/sSub/nary/f giữ cùng signature expanded XML names/attributes/text/children; chuỗi m:t đúng thứ tự. Đây là mapping thủ công cho ba ca, không phải bộ tách tự động. Ứng viên còn bỏ wrapper noBreak ngoài cùng; chưa có đối chứng chỉ bỏ wrapper nên không quy riêng toàn hiệu ứng cho eqArr.

Canonical render control sáu trang: INT/CHEM baseline tràn trang; ba ứng viên nằm trong cột. EXP baseline chỉ vượt text-margin khoảng2,3pt, chưa vượt trang. PDF text bbox không đo phần đã clip; ảnh fullpage mới là bằng chứng clip. Headless không phải UI roundtrip.

## Word UI đã chạy

EXP explicit sửa hằng số 200000→200001, lưu, đóng, mở lại; spoken equation xác nhận200001 và ba hàng, PDF xuất từ chính Word ở `word-real-reopened.pdf`. Sáu công thức cùng document roundtrip; chỉ EXP explicit có interactive edit. Đã xem contact sheet sáu trang: ứng viên còn ba hàng và sentinel dưới, INT/CHEM baseline tràn. Chưa đối chiếu full nguồn Word hoặc nghiệm thu semantic.

Một lần thao tác sai thay toàn EXP explicit thành1 và lưu trên QA. Bản lỗi giữ ở `word-failed-whole-equation-replacement.docx`; QA được khôi phục từ control bất biến, sửa lại đúng200001 và kiểm đủ sáu công thức trước lần đóng/mở lại được tính. Một thay đổi in-memory sau khóa máy đã được đóng Don’t Save trước khôi phục QA; không gán đó là thay đổi của người dùng. Nguồn/output cũ không bị sửa.

## Writer và lỗi mới

Writer EXP explicit Commands sửa200000→200001, lưu DOCX qua Use Word2010–365 và đóng. Mac khóa khi mở lại: **chưa có Writer UI reopen/PDF**. File lưu còn sáu công thức, EXP đúng200001, nhưng INT explicit hàng2 mất dấu = đầu dòng. `saved-structure-check.json` ghi unexpected content change, không normalize bỏ toán tử. Các ca khác chỉ document roundtrip, không interactive edit riêng.

`probe_leading_relation.py` kiểm bốn biến thể trên input control riêng bằng soffice headless/profile riêng. Baseline, m:nor trên run=, m:box cả hàng đều mất = sau DOCX export. Thêm delimiter group rỗng (beg/end/sepChr rỗng) trước = giữ đủ hai dấu =. Đây mới là headless structural result, không phải UI/render pass hoặc fix converter. File tự tạo, không dùng macro nguồn hoặc đổi cấu hình toàn cục.

Bản `writer-grouped-relation-ui.docx` đã chuẩn bị để kiểm UI riêng. Canonical render của empty-group sau headless roundtrip nằm ở `grouped-rt-render/`, cần xem ảnh trước kết luận. Operand tích phân rỗng vẫn needs_review dù = được giữ.

## Phần còn thiếu

Cần Mac mở khóa: Writer mở lại bản đã sửa, quan sát INT mất = và xuất PDF; thử grouped relation lưu–đóng–mở lại; Word mở bản sao Writer-save để kiểm nhóm rỗng không sinh ký hiệu/placeholder mới. Chưa kiểm render nguồn ba đề hoặc bố cục toàn đề. Corpus needs_review, accepted không tăng, FULL_END_ONLY unsupported và safety skips không đổi.

Claude được giao review phần bằng chứng hiện có, phải ghi rõ Writer reopen còn thiếu; không dùng review để lấp phần UI chưa chạy.

## Render rejected the empty-group trial

Codex đã xem grouped-rt-render/page-4.png: dù XML giữ đủ dấu =, render sinh thêm dấu đóng ngoặc `)` trước =. Vì vậy empty-group bị loại, không dùng writer-grouped-relation-ui như ứng viên sửa đạt. Điều này tái khẳng định token/count không đủ. Thử tiếp riêng `relation-trailing-equals.docx`: chuyển dấu = đầu hàng2 sang cuối hàng1, giữ toàn chuỗi toán và subtree; headless giữ dấu, render/UI còn cần xác nhận. Không thay input cũ hoặc production.

Codex đã xem trailing-rt-render/page-4.png và trailing-equals-result.json: Writer gộp hai hàng đầu khi dấu = nằm cuối hàng1. Chuỗi còn đủ nhưng chỉ còn2hàng và dòng đầu lại dài; thử này cũng bị loại về ngắt dòng. Không tiếp tục áp dụng mẹo vào converter khi chưa hiểu cách Writer tái tạo stack/quan hệ. Cần thử Math Commands với `{}` hoặc tuyến Math riêng dựa trên quan sát UI; không coi việc giữ dấu là thành công về bố cục.

## Claude review and Codex resolution

Claude read-only đã xong: khôngP1,3P2 và3P3, báo cáo riêng claude_dsmt4_real_wrap_review_2026-11-12.md. P2-1 chủ yếu là snapshot review đọc trước các addendum: trạng thái hiện tại đã loại cả empty-group lẫn trailing-equals. `review-v2/probe_controls.py` nay lưu generator và SHA đầu vào cho trailing-equals; kết quả xác nhận chỉ2hàng, không gọi đó làpass.

P2-2 đã kiểm lại bằng m:rPr đặt đầu run, chỉ một m:rPr, m:nor được thêm/giữ duy nhất. Kết quả đúng thứ tự này vẫn mất =; không dùng negative cũ làm bằng chứng độc lập. Đây là kiểm thứ tự cục bộ, chưa chạy validator schema toànDOCX.

P2-3 thêm `review-v2/unboxed-no-array.docx`: chỉ bỏ wrapper ba baseline, không thêm eqArr. Canonical Writer headless render trang3/5 đã xem, INT/CHEM vẫn tràn. **Chưa có Word render cho control này**; không quyết định bỏbox hayeqArr chung choWord. Đây vẫn là review debt trước thay sản phẩm.

P3 cập nhật verifier: ghi raw delta U+2212/hyphen riêng, UIreopen_done=false rõ choWriter, SHA file UI sau lưu; đường dẫn nguồn resolve từROOT tính theo script. Có kiểm sáu oMath và row count trong probev2. Con số EXP+2,3pt chỉ là LibreOffice headless; Word baseline vượt margin nhiều hơn, chưa đo số chính xác. Provenance BIN mới positional, chưa đối chiếu MTEF semantic trong lượt này. Không khái quát lỗi = thành mọi toán tử: −,+,→ vẫn giữ trong các mẫu này.

Các thay đổi verifier/probe saureview doCodex kiểm, không tự gán làClaude đã duyệt. UI còn chờMac mởkhóa như trên. git diff --check đạt; không sửaproduction/commit/push.

## Actual reopen and noBreak-only Word control completed

Sau khi người dùng mở khóa, Codex đã mở lại Writer QA qua UI. EXP Commands giữ stack ba hàng và200001; INT Commands sau mở lại thiếu = đầu hàng2. Xuất `writer-real-reopened.pdf` bằng Writer, kiểm tra file không rỗng và xem contact sheet đủ sáu trang: EXP/CHEM explicit còn ba hàng trong cột; INT explicit mất =; baseline INT/CHEM vẫn clip. Các câu trước nói chưa reopen là trạng thái lịch sử, nay đã đóng UI debt này. Đây vẫn là failure nội dung INT, không phải pass DOCX. Chỉ EXP có sửa tương tác riêng; năm công thức còn lại chỉ cùng tài liệu roundtrip.

Word đã mở `review-v2/unboxed-no-array.docx` và in PDF `word-unboxed-control.pdf`. Xem sáu trang: ba baseline chỉ bỏ outer box đã tự xuống dòng trong Word; không cần eqArr cho ba ca Word này. SHA DOCX khớp input được ghi trước UI, không sửa/lưu control. Đây là render-only control, chưa edit–save–reopen riêng. Cùng biến thể Writer headless vẫn tràn INT/CHEM. Không còn quy toàn hiệu quả Word cho eqArr.

`reopen-followup.json` ghi scope, PDF hash, quan sát UI/render và accepted_promotions=0. Verifier nay ghi actual_UI_reopen_done=true cho cả hai ứng dụng theo quan sát UI, không suy từ XML. Chưa sửa production; không commit/push. Vẫn thiếu căn cứ áp dụng chính sách wrap chung; cần điều tra cách Writer nhập/xuất quan hệ ở stack thay vì tiếp tục thêm delimiter giả.

## Reopen-delta review resolution

Claude bổ sung review tại `claude_dsmt4_real_wrap_reopen_review_2026-11-12.md`: không P1, hai P2 về báo cáo/phép đo. Đã xử lý: Word sau lưu đổi toàn bộ U+2212 thành ASCII hyphen-minus ở cả sáu công thức, kể cả điện tích HSO₄⁻. Verifier chỉ so tương đương dấu để tìm mất ký tự khác, không chứng minh stored content nguyên byte hoặc downstream equivalence. Raw delta giữ nguyên; ảnh Word không đủ kết luận mở sang Writer tương đương. Đây là hành vi Word-save quan sát được, chưa quy lỗi converter.

Probe unboxed cũ trong results.json đo formula4 (explicit), không phải baseline1/3/5; không dùng row đó để kết luận baseline mất =. Giữ log cũ để truy vết. Đã sửa generator để bỏ box tại đúng vị trí và assert thứ tự/chữ; `verify_unboxed_existing.py` kiểm các artifact cũ, không tạo lại DOCX: cả ba baseline có cùng signature expanded names/attrs/text/children sau bỏ wrapper và cùng chuỗi trước/sau Writer headless lưu. `unboxed-baseline-check.json` là bằng chứng đúng cho control. Phép đo signature tránh namespace-prefix/context của canonical XML và không suy layout.

Đã đóng riêng Word unboxed control qua UI không có Save prompt; SHA sau đóng vẫn `0d2db8863ff5076632be3385d084c349bf87fa05044d5faa08b4914d249ce594`. Không đóng tài liệu người dùng khác. Các SHA khác là snapshot sau lưu như đã ghi. Verifier đọc quan sát reopen từ reopen-followup.json, không tự suy từ DOCX; banner đầu báo cáo phân biệt trạng thái hiện tại và lịch sử.

Ở Word unboxed INT có ngắt trước = và tiếp tục ngắt bên trong phần đa thức ở các dòng sau; chưa kiểm edit–save–reopen riêng biến thể này hoặc fidelity với full đề. Các kiểm tra mở rộng chỉ hỗ trợ thiết kế thử kế tiếp. Cần điều tra Writer bằng control Commands trực tiếp, chưa có cách sửa đủ bằng chứng để tích hợp production.

## Commands trực tiếp: DOCX reimport hỏng, ODT giữ cú pháp (lượt tiếp theo)

Tạo riêng `writer-commands-leading-ui.docx` từ control, giữ nguồn/control/QA cũ. Trước sửa, Writer nhập INT explicit thành Commands `# = int ...` và AX Formula có ký hiệu lỗi ¿ ở vị trí đó. Như vậy lỗi đã xuất hiện khi nhập eqArr quan hệ đầu hàng, trước lần lưu làm rơi dấu; không còn quy toàn lỗi cho export.

Trong Commands chỉ thêm nhóm rỗng `{}` trước dấu = ở hàng2. Khi nhập lại toàn chuỗi chính xác, Formula hiển thị = và hết lỗi cú pháp tương ứng. Lưu DOCX, đóng, mở lại qua Recent Documents: DOCX XML vẫn đủ hai dấu = và ba hàng, cả sáu chuỗi toán không đổi so control. Tuy nhiên Commands sau mở lại trở về `# = int ...`, không còn `{}`, và render PDF `writer-commands-leading-reopened.pdf` trang4 vẽ dấu ¿ đỏ. Đã xem ảnh trang4. `writer-commands-leading-ui.docx.math4.xml` cho thấy export không có cấu trúc nhóm rỗng trước run=. Đây là quan sát ranh giới import/export, chưa audit mã nguồn LibreOffice để khẳng định hàm gây lỗi. Không coi việc XML giữ = là thành công.

Cùng Commands `{}` được khôi phục rồi Save As sang **ODF Text .odt mới**, không lưu đè DOCX. Đóng/mở lại bằng UI: Commands vẫn `# {} = int`, Formula không có ¿ tương ứng; PDF `writer-commands-leading-odt-reopened.pdf` trang4 hiển thị dấu = đúng và ba hàng. Annotation của Object4/content.xml giữ nguyên cú pháp này (`commands-odt-annotations.json`). Đây chỉ là đối chứng định dạng trên một công thức: operand rỗng ở tích phân đầu vẫn hiện □, semantic/fidelity/full-exam vẫn chưa đạt.

Mở DOCX Commands đã lưu bằng **Word**, xuất `word-commands-cross.pdf` rồi đóng không sửa/lưu. Đã xem trang4: Word hiển thị đủ = và ba hàng, không có lỗi ¿; DOCX SHA không đổi. Đây chỉ cross-render, không phải Word interactive edit/reopen mới.

Một lần nhập thử bằng typeText làm mất ký tự minus và thêm ngoặc thừa trong bộ nhớ QA. Không lưu trạng thái sai đó; thay toàn Commands bằng Home→Shift-End toàn văn bản và paste Unicode, xác nhận công thức/cú pháp đúng trước lưu. `verify_commands_control.py` kiểm cả sáu chuỗi toán của bản DOCX cuối trùng control, số hàng và annotation ODT; nó không suy nghiệm thu từ XML.

Kết luận hẹp: `{}` giải quyết cú pháp StarMath trong ODT của mẫu này, nhưng không tồn tại bền vững qua DOCX→Writer. Không tích hợp mẹo này vào normalized MathML/OMML hoặc giả định một dạng wrap chung. Tuyến Word/OMML và Writer/MathML→ODF cần kiểm độc lập theo chính sách đã có. Chưa thêm chính sách chuyển đổi tự động, accepted vẫn0; chưa commit/push.

## Commands review: further limits and captured original text

Claude review bổ sung lưu tại `claude_dsmt4_commands_odt_review_2026-11-12.md`. P2-1 hợp lệ: control headless ban đầu vẽ = bình thường, trong khi Math Commands/AX lúc kích hoạt chỉnh sửa hiện ¿. Chưa tách ảnh hưởng của đường mở/render với việc kích hoạt Math và khác biệt cấu trúc export, nên không khẳng định importer luôn render sai ngay khi mở tệp. Kết luận chính xác hiện tại: Commands được quan sát có quan hệ thiếu toán hạng và có lỗi parse; cách render còn phụ thuộc đường xử lý chưa cô lập.

P2-2 về khả năng quote mới được thêm cần đối chiếu lại capture CUA: biến originalCommand được đọc từ AX **trước thao tác nhập đầu tiên**, đã chứa S"=", "+"1 và "|". directCommand chỉ replace `# = int` bằng `# {} = int`. Đã chép chính xác hai chuỗi cùng pre-edit observation vào `commands-ui-observations.json`; không suy chuỗi Commands của Object4 từ Object3 vì dù token cùng nguồn, đường dựng/serialize từng object có thể khác. Full paste đã dùng để sửa lỗi nhập thử, nên phép kiểm chỉ khẳng định delta so với chuỗi AX đã capture, không khẳng định cấu trúc nguyên gốc OMML không đổi.

Tiếp tục đối chứng control chưa kích hoạt Math so với sau khi mở Commands, và lưu lần2 ở scratch riêng. Chưa có quyết định production.

## Fresh import control: binary-dependent relation rendering

Đã tạo `writer-import-control-ui.docx` byte-copy control, mở trong LibreOffice UI26.8.0.3, **xuất PDF trước khi kích hoạt Math**, rồi mở/thoát Commands không nhập gì và xuất PDF lần2. Cả hai ảnh trang4 đều có ký hiệu lỗi đỏ ở = hàng2. Đóng bằng Don’t Save; hash input không đổi. Vì vậy trên binary này lỗi render đã có trước khi sửa/kích hoạt Math.

Chạy thêm headless profile mới bằng chính `/Applications/LibreOffice.app/Contents/MacOS/soffice`26.8.0.3 cho control và Commands-DOCX: cả hai trang4 có lỗi đỏ giống UI. Chạy cùng control với soffice đóng gói trong runtime: phiên bản **LibreOfficeDev26.8.0.0.alpha0, build2c87e51eeaa2b413ff4ae097b2705eea1995d8e5**, ảnh trang4 hiển thị = sạch. Đã xem cả ba ảnh này. Đây là đối chiếu binary trên cùng input, giải thích khác biệt giữa render canonical cũ và UI26.8.0.3 trong phạm vi mẫu. Chưa xác định commit/hàm LibreOffice, chưa gọi đó là ma trận hỗ trợ phiên bản hay khuyến nghị nâng/hạ phiên bản. Cần ghi rõ binary/version khi dùng render làm bằng chứng; không suy render runtime tương đương app người dùng.

`import-version-comparison.json` ghi PDF hash, version và quan sát; `commands-ui-observations.json` lưu Commands trước/sau đã capture. Word cross PDF nay cũng được hash. File XML trích riêng để debug không phải fixture nguồn. Không thay cài đặt/default app, không sửa tệp người dùng.

Lưu lần2 bằng headless26.8.0.3 trên **bản sao mới**, không ghi đè Commands-DOCX: dấu = đầu hàng lại bị loại (hai dấu→một dấu), ba hàng còn. `commands-second-save-headless/result.json` lưu kết quả và stderr fontconfig. Đây là negative control headless, chưa chạy UI lần2; không mô tả là UI roundtrip.

## Final bounded review closure

Claude đã đóng hai P2 của Commands/ODT, không P1; báo cáo `claude_dsmt4_commands_resolution_review_2026-11-12.md`. Hai P3 còn lại được ghi rõ: các render cũ không lưu launch binary/version, nên việc quy canonical cũ cho binary đóng gói chỉ là suy luận từ kết quả tái hiện, không phải provenance đã lưu. `older-render-producers.json` bổ sung metadata Producer của PDF tìm được; metadata không thay thế launch record. Các kết quả mới có explicit binary/profile và version.

Quote của =,+,| do Writer nhập INT eqArr là một quan sát fidelity còn mở, dù đã xác nhận chúng có trong Commands trước sửa. Chưa cô lập quote do context eqArr hay split-run; không coi token-match là bảo toàn cách phân loại toán tử. Không đổi chính sách hỗ trợ trong lượt này.

Lượt điều tra này kết thúc ở bằng chứng phân biệt DOCX/ODT và binary. Bước riêng tiếp theo có thể thử MathML mtable→ODF trên cùng mẫu, ghi đúng phiên bản và kiểm UI, tuyệt đối chưa áp dụng shared OMML workaround. Check nguồn/control hash và diagnostic verification đã chạy, git diff --check đạt. Không chạy lại toàn bộ Maven/corpus khi không sửa production.
