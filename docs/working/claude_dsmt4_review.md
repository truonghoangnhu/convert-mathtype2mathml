# Review độc lập DSMT4 — kết quả

Phạm vi: review chỉ-đọc working tree thực tế (base HEAD `1a1ed5d`, gồm tệp untracked). Không sửa mã/fixture/`out/`/`work/dsmt4-real-corpus/`, không commit, không build lại, không chạy lại batch.
Snapshot: 31/31 tệp trong `work/claude-review/review-input-manifest.json` khớp SHA-256 lúc bắt đầu. `target/*.jar` (23:48) mới hơn mọi nguồn Java đã sửa (≤ 23:47), nên có thể dùng jar để tái hiện mà không cần build.
Bằng chứng riêng nằm trong `work/claude-review/` (script + DOCX tổng hợp). Mọi quan sát về hiển thị dưới đây là **bằng chứng XML tĩnh, chưa render trong Word/Writer**.

**Kết luận ngắn:** không có P0. Có 2 P1 (mất định dạng run của công thức inline; mất khoảng trắng `mspace`) và 4 P2. Các số đếm và kiểm tra bảo toàn trong báo cáo đúng khi đối chiếu độc lập; hai mô tả trong báo cáo vượt quá bằng chứng (xem mục 2).

---

## 1. Findings

> **Trạng thái xử lý:** P1-1 và P1-2 đã sửa (xem `docs/dsmt4_real_corpus_2026-11-03.md`, mục 3–4). Các P2 chưa xử lý. Chưa render lại trong Word/Writer.

### P1-1 — OMML inline làm mất toàn bộ định dạng run của object nguồn (cỡ chữ, màu, gạch chân, tô nền, đậm)
- Chỗ: `XmlBeansOmmlInjector.java:139-167` (`replaceObjectRun` chỉ clone `rPr` cho các run `before/after`, mà hai run này gần như luôn rỗng nên không được chèn), `:84-101` (`injectBlock` cũng bỏ run). Bộ chuyển `mml2omml.xsl` chỉ sinh `w:rFonts` Cambria Math cho `m:r`.
- Trigger: bất kỳ object inline có `w:rPr` trên run chứa nó.
- Tác động: Word lấy cỡ chữ của `m:r` từ `w:rPr` của chính nó, không kế thừa từ run chữ bên cạnh. Trong corpus:
  - 1.041/2.627 run object có `w:sz` tường minh; **1.031** trong số đó khác cỡ của style đoạn (mặc định 22 hoặc 24; chữ liền kề dùng cùng `sz` với object ở 987 trường hợp) → công thức sẽ nhỏ hơn chữ xung quanh.
  - Màu `0000CC`: 33; gạch chân: 25; tô nền (`highlight`): 20; đậm: 108 run object. Tất cả bị bỏ.
  - Mẫu `m:r` phổ biến nhất (9.437 `m:r` trong top-4 mẫu) chỉ có `rFonts`.
  - Đoạn mũi tên Hóa (`Hoa_NB_L3`, đoạn 135): chữ `sz=24`, mặc định tài liệu `22`, `m:r` không có `sz`. Đây là **giả thuyết** hợp lý cho “mũi tên ngắn hơn, nhãn lệch khoảng cách”; chưa kiểm chứng bằng render.
- Tái hiện: `work/claude-review/synth/make.py` đoạn P1 (run `sz=28`, đỏ, gạch chân) → output `['r[t]','oMath:x1+1']`, run định dạng biến mất. Báo cáo nói injector “retaining … run properties” — đúng cho run chữ khác, **sai cho chính run object**.
- Đề xuất: sao chép `w:sz/szCs/color/b/i/u/highlight` (và chỉ các thuộc tính Word math chấp nhận) của run object vào `w:rPr` của mọi `m:r` được chèn; với block, lấy từ run object hoặc `pPr/rPr`. Làm trước khi chỉnh độ dài mũi tên, để loại nhiễu do cỡ chữ.
- Test cần thêm: đoạn có run `sz=28`+màu → mọi `m:r` có `w:sz=28` và màu; so sánh trên fixture mũi tên thật (chữ 24, mặc định 22).

### P1-2 — `mspace` bị bỏ hoàn toàn khi đổi MathML → OMML
- Chỗ: `src/main/resources/mml2omml.xsl` không có template/chuỗi `mspace` nào (grep = 0); `omml2mml.xsl` mới có.
- Bằng chứng: 139 sidecar chứa `mspace` (283 phần tử; độ rộng `0.08em`×149, `0.16em`×65, `0.33em`×59, `1em`×10). Ví dụ `Li_TN_L2`: `I=10,0⟦0.33em⟧A`, `NA=6,02.10^23⟦0.33em⟧mol−1`, `1⟦0.33em⟧MeV=…` → số dính liền đơn vị. Mũi tên Hóa: MTEF nhúng TeX `\xrightarrow[,-H_2O,]{CH_3OH,\ HCl\ khan}`, fixture `arrow-1.mathml` có `mspace 0.16em`, output OMML là `→,−H2O,CH3OH,HClkhan` (mất khoảng trắng).
- Tác động: sai hiển thị/khoảng cách; có thể góp phần vào “nhãn có khác biệt khoảng cách” đã ghi nhận.
- **Test hiện tại ghi nhận lỗi này là đúng**: `DocxMathPatchWorkflowTest.retainsLabeledArrowContentFromRealChemistryMtefSidecars` assert `"CH3OH,HClkhan"` trong khi `provenance.json` có `expected_upper: "CH3OH, HCl khan"`. Chú thích trong test nói chuỗi “lấy từ preview nguồn” nhưng preview có khoảng trắng.
- Đề xuất: ánh xạ `mspace` theo ngưỡng (ví dụ ≥0.16em → `m:r` với `m:nor` hoặc U+2009/U+2005/U+2003 có `xml:space="preserve"`; 0.08em do MathType tự thêm có thể bỏ, cần quyết định có chủ ý), rồi sửa assert trong test thành có khoảng trắng.
- Test cần thêm: fixture mũi tên → upper label chứa khoảng trắng; `10,0 A` có khoảng trắng.

### P2-1 — Cổng nội dung (`MathmlContent.hasFormula` / `mathml_content.py`) chấp nhận “nội dung” chỉ là ký tự vô hình
- Chỗ: `MathmlContent.java:81-92`, `mathml_content.py:20-29`.
- Tái hiện (Java; Python giống trừ ghi chú): `<mi>U+2061</mi>`, `<mtext>U+200B</mtext>`, `<mi>U+00AD</mi>`, `<mn>&#x2062;</mn>` → **true**; `<mrow><mo>(</mo><mo>)</mo></mrow>` → true; `<mpadded width="0pt"><mi>x</mi></mpadded>` → true. Lệch Java/Python: U+0085 (Java true, Python false).
- Tác động: chính sách nói “khoảng trắng… không chứng minh chuyển đổi thành công” nhưng ký tự định dạng (Cf) lọt qua. Hiện corpus không có ca nào như vậy (quét 2.523 sidecar: 2 không dùng được = sidecar WMF rỗng `<math display="block"/>` và sidecar BIN của ca FULL_END_ONLY; không có ký tự PUA), nên là rủi ro tiềm ẩn.
- Đề xuất: coi Cf/Cc/Z* và PUA đã biết là rỗng ở cả hai cài đặt, dùng chung một bảng test vector Java/Python.

### P2-2 — Khối hóa (block) đổi căn lề của 21/80 đoạn
- Chỗ: `PoiMathSourceDetector.java:83-107` + `XmlBeansOmmlInjector.injectBlock`.
- Dữ liệu: 80 đoạn block; 59 có `jc=center`; **21 còn lại là `left` (6), `both` (3) hoặc không có `jc` (12)**; 47 nằm trong ô bảng; 9 có `w:ind`. `oMathPara` mặc định căn giữa nên các đoạn này đổi vị trí. Hành vi “đoạn rỗng chữ → block bất kể `numPr/ind`” đã có từ trước (không phải lỗi mới); tổng hợp synthetic P2 (đoạn có `numPr`, chỉ chứa object) → `oMathPara`.
- Đề xuất: đặt `m:oMathParaPr/m:jc` theo `jc` của đoạn, hoặc chuyển sang inline khi `jc` ≠ center / có `numPr`; thêm test `jc=left`.

### P2-3 — Phần “tách run” trong `replaceObjectRun` không bao giờ chạy với dữ liệu thật; một số kiểm thử vô hiệu
- `InlineSafetyEvaluator.java:50-73` chỉ cho phép run chứa `rPr` + đúng 1 `object`; run có `w:t`, `w:br`… bị bỏ qua (tái hiện P5, P6 trong synthetic: giữ nguyên OLE). Vì vậy các nhánh `hasBefore/hasAfter` là mã chết và báo cáo mục “Bugs … fixed #1” (tách run giữ text/drawing/page-break) không được kiểm chứng. Sửa thật chỉ là đưa `oMath` lên cấp `w:p`.
- `preservesShortUnitsAndAnswerLabelsBesideSingleEquation`: với nhãn `"."` và `" "`, `result.xml.contains(label)` luôn đúng (namespace URL có dấu chấm và khoảng trắng) → assert vô nghĩa. Nên so sánh chuỗi `w:t` đoạn trước/sau.
- Chưa có test cho rollback (`restoreParagraph`) hay cho nhánh `inject(MultiObjectPatchPlan)` bị lỗi giữa chừng. Tôi thử bằng DOCX tổng hợp (P3: object trực tiếp + object trong `w:hyperlink`): kết quả đúng — đoạn được khôi phục nguyên trạng và đếm vào `XML_MUTATION_ROLLBACK`. Lưu ý tiềm ẩn: `restoreParagraph` thay nút DOM nên `XWPFParagraph.getCTP()` bị tách khỏi cây; hiện không có mã nào dùng lại đoạn sau rollback.

### P2-4 — Bằng chứng/tài liệu: mô tả đường chuyển đổi và khoảng trống đo lường
- Cả 32 manifest chỉ chứa phần WMF (0 mục BIN); `generate.log`: “BIN parts required after WMF pass: 0”. Công thức đã chèn đến từ MTEF nhúng trong **WMF preview**, không từ BIN; việc parse 2.100 BIN là kiểm kê/đối chiếu. Chính sách ghi đường chuẩn `OLE → MTEF → …`. Tài liệu nên nêu rõ nguồn sidecar thực tế.
- Kiểm tra độc lập tôi làm (`bin_vs_sidecar.py`): với **2.616/2.616** sidecar, bội số ký tự ASCII chữ-số của các bản ghi `char` trong BIN **bằng** bội số trong MathML của WMF. Đây là bằng chứng tốt cho sự nhất quán BIN↔WMF nhưng chỉ ở mức đa tập, không chứng minh thứ tự, ký hiệu hay cấu trúc.
- Mục tiêu 265 object / 5 đề trong `support_scope_policy.md` và báo cáo corpus (“không coi là tập con”) chưa được hòa giải bằng bảng đối chiếu.
- Phụ: `scanned` không đếm object trong `w:sdt` (synthetic: 13 object, `scanned=12`, object trong `sdtContent` được giữ nguyên, không cảnh báo). Corpus thật không có ca này (mọi run object đều là con trực tiếp của `w:p`), nhưng đối chiếu “scanned = kiểm kê” sẽ không bắt được.

---

## 2. Kết luận báo cáo — đã kiểm chứng vs chưa đủ bằng chứng

**Đã kiểm chứng độc lập**
- 32 DOCX; 2.627 object = 2.617 `Equation.DSMT4` + 10 OLE khác (PBrush 6, ChemSketch 2, ChemWindow 2); 27 `m:oMath` nguồn; mọi object nằm trong `word/document.xml`, 124 trong bảng; không có trong textbox/header/footer/Fallback.
- 2.100 hash OLE khác nhau và 1.934 hash MTEF khác nhau (từ `mtef_inventory.json`; `bin_payload_probe.jsonl`: 2.100 `ok`, 6 lỗi `Equation Native` là OLE không phải MathType).
- 2.508 OMML chèn (80 block + 2.428 inline), output 2.535 `m:oMath`, **109** DSMT4 còn lại (tính lại từ output: 109). Sự phân bố các object giữ lại: đoạn nhiều object (3–17 object/đoạn) bị bỏ nguyên đoạn; 2 đoạn có OMML nguồn; 10 OLE khác.
- Bảo toàn: so sánh tuần tự mọi lá không-toán (kể cả `w:tab/br/sym/instrText/drawing/pict`) cùng `rPr` hiệu dụng giữa nguồn và output cho **mọi đoạn** của 32 tệp: 0 khác biệt sau chuẩn hóa khoảng trắng thuộc tính. Các phần khác bằng nhau về ngữ nghĩa XML trừ phần dưới. Lưu ý đây là cái “audit chưa đo” mà bàn giao nêu: **đã đo, đạt**.
- FULL_END_ONLY: SHA-256 DOCX/OLE/MTEF khớp fixture, 192 byte, vị trí đoạn 95 (đoạn này có 5 object, cả 5 đều bị giữ lại — 4 công thức dùng được bị giữ do quy tắc toàn-đoạn). WMF preview của nó (416 byte) cho sidecar rỗng `<math display="block"/>`, cổng loại đúng.
- Test ghi nhận: `surefire` 52/0/0; log Python 104 OK (không chạy lại).
- Namespace-free MathML nhiều phần tử anh em (`<math><mrow>…</mrow><mi>c</mi>…`) vẫn được chuyển đủ token (kiểm tra rủi ro `renameNode` trong `normalizeElementNamespaces`: không xảy ra).

**Chưa đủ bằng chứng / vượt quá**
- “Injector giữ run properties”: sai cho run object (P1-1). “Tách run…” (P2-3): mã chết.
- “Đã tạo OMML = chuyển đổi đúng”: chỉ ở mức token. Đối chiếu chuỗi TeX do MathType nhúng (`mt_comment`): 1.577/1.605 bản patch có TeX khớp sau chuẩn hóa; 28 chênh lệch tôi xem tay đều do bộ chuẩn hóa của tôi (giới hạn n-ary/căn/mũi tên có cận/delimiter không nằm trong `m:t`) trừ 1 ca `LI-12 … đoạn 123` mà TeX nhúng là `\ell` nhưng thân MTEF là `B=(m₂−m₁)g/(Iℓ)` — chú thích TeX có thể cũ, nên **không dùng TeX làm chân lý**; 998 object không có TeX nào để đối chiếu.
- Ràng buộc về “Word/LibreOffice/Writer”: tôi không chạy lại các ứng dụng; không đánh giá được.
- Không ghi “hiển thị đúng” cho bất kỳ ca nào; toàn corpus vẫn `needs_review`.

## 3. Lệnh và ca đã kiểm tra; giới hạn
- `preserve_check.py` (bảo toàn lá/`rPr` từng đoạn và các phần gói), `diff_detail.py`, `tex_oracle.py`, `preview_vs_bin.py` (TeX BIN có trong WMF: 1.619/1.619; 998 không có TeX), `bin_vs_sidecar.py`, các thống kê định dạng/`mspace`/block.
- DOCX tổng hợp `work/claude-review/synth/make.py` (13 object: run định dạng, `numPr`, `hyperlink`, `w:ins`, run hỗn hợp, `br`, bookmark/`proofErr`, field, nhiều run, `sdt`) chạy qua jar hiện có (`--patch-docx`), cộng bản MathML không namespace.
- `java/Gate.java` so sánh cổng Java với Python trên 14 vector.
- Hạn chế: không chạy `mvn`, Python test, Word, Writer; POI ghi lại mọi phần gói (chuẩn hóa xuống dòng trong thuộc tính, ví dụ `docPr@descr`, `o:gfxdata` base64 → dấu cách; `core.xml` bỏ `lastModifiedBy` rỗng; `[Content_Types].xml`, `_rels/.rels`, `word/_rels/document.xml.rels` khác về thứ tự/biểu diễn — tôi chưa đối chiếu từng quan hệ) — hành vi có từ trước của POI, 30 đoạn bị ảnh hưởng ở mức thuộc tính, chưa thấy tác động ngữ nghĩa. Corpus không có object ngoài `document.xml`, nên header/footer/textbox **chưa có bằng chứng**, không phải “đạt”. Thư mục `work/claude-review/` được tạo thêm, không sửa gì khác (trạng thái git không đổi).

## 4. Ba việc tiếp theo (chưa triển khai)
1. Sửa P1-1 và P1-2 (giữ `sz`/màu/gạch chân/tô nền; ánh xạ `mspace`) cùng test hồi quy, rồi mới đo lại độ dài mũi tên/khoảng cách nhãn trên mẫu Hóa trong Word/Writer — hai lỗi này có thể là nguyên nhân gốc của sai lệch đã thấy.
2. Quyết định căn lề block (P2-2), thắt cổng nội dung và bộ vector chung Java/Python (P2-1), sửa các assert vô nghĩa và thêm test rollback (P2-3); cập nhật tài liệu về nguồn sidecar WMF và hòa giải mục tiêu 265 object (P2-4).
3. Phân tích riêng 108 object chưa patch: hầu hết là đoạn nhiều object bị bỏ nguyên đoạn (`multi_skipped_ambiguous`=19 đoạn); cân nhắc patch từng object an toàn thay vì toàn đoạn. Giữ FULL_END_ONLY ở `unsupported`; chỉ ghi nhận rằng cả BIN lẫn WMF preview của nó đều không cho nội dung, không suy diễn thêm.
