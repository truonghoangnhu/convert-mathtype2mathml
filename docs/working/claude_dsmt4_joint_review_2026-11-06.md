# Handoff Claude cho Codex: review noBreak cuối, ledger và Toán#15 (2026-11-06)

Tôi chỉ đọc file. Không chạy test, render, UI, shell hay git; không sửa file nào. Mọi nhận định dưới đây dựa trên mã và tài liệu hiện có.

## 1. Bản sửa root inline noBreak cuối

**Kết luận: sửa đúng, không thấy lỗi P1/P2 mới. Còn hai lỗ hổng test P3 nên vá, kèm hai ghi chú không cần sửa.**

Những điểm đã kiểm và đạt:
- **Namespace và loại root:** `buildInlineMath` (`XmlBeansOmmlInjector.java:518-549`) từ chối root sai namespace, root chỉ là fragment như `m:r`/`m:f`, `oMathPara` có 0 hoặc nhiều hơn 1 `oMath`, phần tử lạ, và text không rỗng nằm trực tiếp trong `oMathPara`. Không còn lỗi lấy công thức đầu rồi bỏ phần còn lại, hay bỏ wrapper của fragment. Lỗi này có từ trước, nay đã đóng ở tuyến inline.
- **Single path không làm hỏng paragraph:** exception ném ra ở dòng 157, trước `editParagraph`, rồi `inject` bắt và trả `false` (dòng 59). Paragraph thật chưa bị chạm vào.
- **Multi path là atomic:** exception ném trong lambda khi đang sửa bản sao (dòng 89-90), trước bước đưa thay đổi vào paragraph thật (dòng 202+). Test ở `DocxMathPatchWorkflowTest.java:1756-1758` đặt root sai ở object **đầu**. Vì segment được sắp ngược thứ tự tài liệu (dòng 73), object b được thay trên bản sao trước, rồi a mới lỗi. Tức là test có chạy đúng tình huống "đã sửa một phần rồi thất bại".
- **`oMathPara` một công thức:** trả về chính `oMath` con. `insertBefore` tự gỡ nó khỏi `oMathPara` cha, còn `oMathParaPr` bị bỏ. Với inline như vậy là hợp lý vì `jc` không có nghĩa ở đó.
- **Không phải lỗi tiềm ẩn:** tuyến production luôn sinh `<oMath>` đúng namespace (`mml2omml.xsl:17-21`), và output rỗng hoặc chỉ có text trần đã bị chặn trước ở `DocxMathPatchMain.java:326` (`ommlRejectionReason`).

| Mức | File:dòng | Nội dung | Mới hay có trước |
|---|---|---|---|
| P3 (test) | `DocxMathPatchWorkflowTest.java:1769-1783` | Test `oMathPara` một công thức chỉ kiểm số box = 1 và text của `e` = `x+1`. Nếu dòng 544 bị đổi thành `keepInlineObjectTogether(...); return importedMath;`, paragraph sẽ chứa nguyên một `m:oMathPara` giữa chữ (Word coi là display), nhưng test **vẫn xanh**. Nên thêm assert: `count(oMathPara)=0`, `count(oMathParaPr)=0`, `oMath` là con trực tiếp của `w:p`, `noBreak/@val='on'`, và run `"Cho "` còn đứng trước. | Mới (lỗ hổng của test vừa thêm) |
| P3 (test) | cùng file, `:1733-1767` | Ca từ chối không kiểm `oMathPara` chứa một phần tử ngoài namespace math, ví dụ `<m:oMathPara><w:r/><m:oMath>…</m:oMath></m:oMathPara>`. Mã hiện tại vẫn từ chối đúng (dòng 538); chỉ là chưa có regression giữ hành vi này. | Mới |
| Ghi chú, không cần sửa | `XmlBeansOmmlInjector.java:531-535` | Node không phải element được bỏ qua. Riêng CDATA có nội dung, ví dụ `<m:oMathPara><![CDATA[x]]><m:oMath>…`, sẽ được nhận và mất `x`. XSLT/Saxon không sinh CDATA nên tuyến production không gặp. | Biên |
| Đã biết, có trước | `XmlBeansOmmlInjector.java:497-516` (`buildMathPara`, block) | Root `<m:f>` bị làm phẳng thành `oMath>fPr,num,den`, root `<m:r>` mất wrapper, không kiểm namespace. Production không gặp. Checkpoint đã ghi "not a block-root fix". Nếu muốn đồng bộ: tách chung một hàm kiểm root và dùng cho block, nhưng giữ nguyên `oMathPara` hợp lệ có nhiều công thức. Ưu tiên thấp. | Có trước |

Ghi chú về việc Word bỏ `noBreak` khi lưu: có thể vì `on` là giá trị mặc định của `boxPr/noBreak` nên Word không ghi lại. Đây là giả thuyết, tôi chưa đối chiếu ECMA-376 §22.1.2. Nếu đúng thì việc Word bỏ thuộc tính là vô hại, nhưng đừng ghi vào tài liệu trước khi đối chiếu.

Lưu ý về artifact: trong `work/codex-dsmt4-nobreak-2026-11-06/` vẫn còn ba file khóa `~$an_TQB_HN_Lx-box-ui-saved.docx`, `~$an_TQB_HN_Lx-box-on-saved.docx`, `~$-THPT-2026-box-probe.docx`. Có thể Word vẫn đang mở các file này, hoặc khóa còn sót lại. Cần xác nhận đã đóng trước khi coi file saved là bản cuối, và không đưa file `~$` vào commit.

## 2. Gap ledger/bằng chứng có thể đóng bằng dữ liệu sẵn có

Các tổng sau đều là **lịch sử, không phải trạng thái hiện tại**:
- Ledger 265: 46 failed, tính trên `out/dsmt4-finalization-corpus-2026-11-05/patched/`.
- Overlay sau đợt fences: 14 failed / 251 needs_review.
- Overlay sau đợt degree: 13 failed / 252 needs_review.

Cả ba đều tính trên OMML của snapshot cũ, trước khi có box và trước khi guard inline boundary giữ thêm OLE.

| Mức | Gap | Ví dụ cụ thể | Đóng bằng dữ liệu nào |
|---|---|---|---|
| **P2** | Overlay 13 failed còn tính li002 và li010 là Word failed (chữ dính liền). Trong output hiện tại, cả hai đã là **OLE giữ lại** (`codex_dsmt4_inline_boundary_2026-11-06.md:32`). Ngoài ra li003, li011, li012 còn các kết quả `pass` cho một OMML không còn tồn tại. | li002 `p,khối`, li010 `ptheo` | Gắn tag `retained_ole_policy` cho 5 ca này. Coi verdict OMML cũ là "đã bị thay thế", không phải pass hay fail. Không đếm là bản chuyển đổi sửa được. Writer hiển thị khung OLE rỗng là giới hạn có sẵn từ nguồn. |
| **P2** | Chưa có cột cho biết OMML đã chấm có còn tương đương với output hiện tại không. | Mọi `pass` của Word/Writer trong ledger | Dựng một cột cho 265 ca từ các diff đã có: `identical_mod_box` (đã chứng minh cho 2.215 inline so với inline-boundary-final), `letterlike_changed` (diff của symbol-scope), `now_retained_ole` (5 ca trên), `native_unchanged` (18). Verdict cũ chỉ được mang sang khi có tag. **Writer:** box chỉ được chứng minh trung tính với Toán (PNG trùng byte). Với Hóa, Lý, TN chỉ được mang `fail` sang, không được mang `pass`. |
| P2 | Bằng chứng lưu Word cho snapshot hiện tại đã có trong file nhưng chưa được dùng | toan078 (ℝ) và 115 ca Toán | So sánh cây toán của `Toan_TQB_HN_Lx-box-on-probe.docx` với `…-box-on-saved.docx`, bỏ qua `noBreak`. (1) Xác định ℝ của toan078 còn `m:scr=double-struck` sau khi Word lưu. (2) Liệt kê thay đổi text/cấu trúc, ví dụ U+2212→`-` như từng gặp ở Lý. Đây là bằng chứng mức artifact cho `word.save_preservation`, không phải UI. |
| P3 | toan086 `word.page_break`: chuyển fail → needs_review (có phạm vi) | Probe có cây toán khớp output cuối, sau sửa/lưu/mở lại vẫn liền | Không nâng lên pass vì baseline hiển thị **4 trang** còn probe chỉ **3 trang**, chưa giải thích được, trong khi Writer cuối vẫn 4 trang. Cần giải thích chênh lệch này trước khi dùng làm bằng chứng phân trang. Có thể ghi `word.edit_save_reopen = pass (probe)` cho toan086. |
| P3 | toan078, tn017, tn020 `word.save_preservation` | Bản sửa letterlike đã qua UI cho toan078 và tn017; tn020 chỉ có kiểm tra artifact (`m:scr=script`) | Chuyển fail → needs_review, ghi rõ tn020 là kiểm tra XML, không phải quan sát UI. |
| P3 | Tài liệu cũ | `docs/dsmt4_migration_acceptance.md:167` vẫn ghi "Latest boundary… 109 Java" trong khi nobreak đã 114. `:66-68` nói Word căn trái đúng các hàng của Toán #15 trên output **trước box**. | Cập nhật số test. Kiểm XML xem toan015 trong output cuối có nằm trong box không, và `mcJc` còn sau khi Word lưu không. |

Nếu chấp nhận các chuyển trạng thái trên, overlay suy ra sẽ còn **7 failed**: hoa037, hoa042, hoa066, hoa067, hoa068, hoa086 (Word/Writer mũi tên, nội dung, lưu DOCX) và toan015. Accepted vẫn 0, mọi ca còn lại là needs_review. Con số 7 này phụ thuộc vào tag tương đương ở trên và không phải một đợt nghiệm thu mới.

## 3. Toán#15: căn hàng hệ phương trình ở tuyến LibreOffice Math riêng

Những gì đã có:
- **Candidate:** `out/dsmt4-degree-followup-2026-11-06/mathml/toan015.mathml` là `mfenced{` → `mtable columnalign="left"` → 3 hàng phẳng chỉ gồm mi/mn/mo. Adapter không đổi gì (G không chạy vì `mfenced` chỉ có một con), chỉ ghi `table_alignment` (`prepare_libreoffice_mathml.py:206-210`).
- **LO bỏ qua `columnalign`:** đặt ở mtable, mtr hay mtd đều không có tác dụng (followup §2). Chỉ annotation StarMath có `alignl` mới căn trái được. Bỏ annotation thì mất `alignl` và nhóm sai.
- **Lệnh StarMath do LO sinh ra** (`work/codex-dsmt4-ui-followup-2026-11-06/math-toan015-reopened-ax.txt:25`): `left lbrace matrix{ { x = 2 + 5 t } ## { y = 2 + 2 t } ## { z = - 1 - 3 t } } right none`. Mỗi ô đã là một nhóm `{…}`, nên chèn `alignl` là việc rất cục bộ.

**Probe hẹp có thể làm ngay (headless, chỉ trên bản QA):**
1. **Control quyền ưu tiên:** MathML có presentation `x=1`, annotation `StarMath 5.0` là `x = 9`. Render và ghi LO hiển thị theo nguồn nào. Nếu theo annotation thì annotation là nguồn quyết định, và mọi annotation sinh ra phải tương đương nội dung với presentation. Đây là rủi ro an toàn chính của hướng này.
2. **Candidate probe:** giữ nguyên presentation của toan015, bọc `<semantics>` và thêm annotation `left lbrace matrix{ alignl { x = 2 + 5 t } ## alignl { y = 2 + 2 t } ## alignl { z = - 1 - 3 t } } right none`. Annotation phải được sinh bằng một serializer chỉ nhận đúng hình dạng S, không chép tay:
   - root không thuộc tính → `mfenced open="{" close="" separators=""` → `mtable` chỉ có `columnalign="left"` → `mtr`/`mtd` không thuộc tính;
   - lá chỉ gồm `mi` một chữ ASCII, `mn` chỉ chữ số ASCII, `mo` ∈ {`=`, `+`, `−`, `-`}.
3. **Đỏ→xanh, đo từ bbox chữ trong PDF, không suy từ ảnh preview hay fingerprint:**
   - **Đỏ (candidate hiện tại):** tọa độ x trái của glyph đầu (x, y, z) ở 3 hàng lệch nhau quá 0,5pt.
   - **G1:** x trái của 3 hàng bằng nhau trong khoảng 0,5pt, trong khi mép phải khác nhau.
   - **G2:** text theo từng hàng giống hệt các lá presentation (`x=2+5t`, `y=2+2t`, `z=−1−3t`).
   - **G3:** lưu ODT rồi mở lại vẫn đạt G1/G2. `content.xml` có đủ 3 `alignl`, và presentation do LO xuất lại có cùng chuỗi lá theo từng hàng.
   - **G4:** sửa trong UI (thêm `q`), lưu/đóng/mở lại vẫn giữ `alignl`. Giữ `not_run` cho tới khi Codex làm UI.
4. **Nếu xanh:** thêm rule "A" vào `prepare_libreoffice_mathml.py`, chỉ áp cho hình dạng S. Test phản ví dụ gồm `columnalign` center/right/thiếu, thuộc tính lạ, `mtd` có msup/mfrac, `mi` nhiều chữ, ký tự ngoài whitelist, `mn` có dấu phẩy, `open`/`close` khác, input đã có `semantics`. Chạy lại phải giữ nguyên output (lần chạy sau đi vào nhánh metadata, byte-identical). Status vẫn `needs_review`, `application_acceptance=not_run`. Kiểm từng ca toan013, toan014, toan016: ca nào không đúng hình dạng S thì vẫn chỉ cảnh báo.
5. **Nếu đỏ, hoặc control cho thấy annotation có thể làm lệch nội dung mà không phát hiện được:** giữ `lo_row_alignment=failed` cho toan015, ghi lý do là importer của LO 26.8.0.3 không đọc căn lề từ MathML, còn annotation là một bộ chuyển StarMath ngoài phạm vi. Không dùng padding, ảnh, hay sửa normalized MathML của Word.

## Đề xuất ưu tiên duy nhất cho Codex

**Làm overlay theo snapshot hiện tại bằng dữ liệu (mục 2), trước probe Toán#15.** Lý do: con số đang công bố (13 failed / 252 needs_review) còn chứa 2 ca đã đổi trạng thái và 3 ca có `pass` cho OMML không còn tồn tại. Sửa việc này không cần UI hay sửa mã production. Phần việc gồm:
- thêm cột tương đương snapshot;
- gắn tag `retained_ole_policy` cho li002, li003, li010, li011, li012;
- so sánh cây toán `box-on-probe` với `box-on-saved` cho Toán.

Sau đó mới chạy probe toan015 ở mục 3.

## Chưa kiểm

- Chưa chạy test, Maven, render, UI hay XML diff nào. Các mệnh đề về hành vi lấy từ đọc mã và tài liệu của Codex.
- Chưa mở `report.json`, `verification.json`, `ledger.json`, các DOCX probe hay ODT. Chưa kiểm toan015 trong output cuối là inline hay block, có nằm trong box không.
- Chưa đối chiếu ECMA-376 về giá trị mặc định của `noBreak`.
- Chưa xác minh tn019, ca rộng/bảng/phân trang trong Word, Writer với Hóa/Lý/TN có box, hay tác động của box tới Writer DOCX.
- Phạm vi giữ nguyên: FULL_END_ONLY unsupported; 108 safety skip và 2 OLE Lý ¶91 không mở rộng; OLE giữ lại không phải bản chuyển đổi sửa được; accepted vẫn 0.
