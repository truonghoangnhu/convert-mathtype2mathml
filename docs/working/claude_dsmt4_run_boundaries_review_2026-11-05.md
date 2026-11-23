# Review read-only: sửa ranh giới run letterlike DSMT4

**Kết luận:** P1 trước đó (gộp token liền kề) đã được sửa đúng. Còn **1 finding P2** vì cổng an toàn chỉ kiểm 4 ký tự, hẹp hơn nhiều so với tập ký tự mà XSLT xếp là letterlike. Thêm 3 finding P3 về phạm vi, chẩn đoán và test. Corpus vẫn ở trạng thái `needs_review`; không được hiểu là đã nghiệm thu.

## Phần đã xác minh đúng (đọc mã)

- **Ranh giới run:** `mml2omml.xsl:491` và `:562` dùng chung `m:IsLetterlikeMtext` (`:811-815`) với FNor (`:801`). Vì vậy hai mtext khác loại normal/letterlike luôn bị tách. Nhánh `otherwise` ở `:674` chỉ chạy khi không có phần tử nào làm ngắt run, nên cũng không gộp sai.
- Test `adjacentNormalTextAndLetterlikeTokensKeepSeparateRunKinds` (`XsltMathmlToOmmlConverterTest.java:201-211`) phủ cả hai ranh giới x→ℝ và ℝ→kg. `red.log` cho thấy trước sửa ra 1 run, đúng với lỗi cũ.
- **Mixed `xℝ` được fail-closed:** cổng ở `MathmlContent.java:49-55` → lỗi ở `DocxMathPatchMain.java:322-329` → `OMML_CONVERSION_FAILED` → giữ OLE. Test ở `DocxMathPatchWorkflowTest.java:22-36` kiểm output trùng từng byte với nguồn và chỉ ghi vào thư mục temp, không động vào fixture.
- **Giá trị m:nor:** khi không có `m:val`, cổng coi là bật, đúng mặc định OMML. Các giá trị `0`, `false`, `off` được miễn đúng như yêu cầu: ℝ khi đó nằm trong math run, Word giữ được.
- `<m:sty m:val="p">` trong `probes-after.txt` dùng đúng namespace.

## Findings

**P2 — Cổng chỉ chặn 4 code point, trong khi XSLT xếp cả khối U+2100–214F và U+1D400–1D7FF là letterlike**
- Vị trí: `MathmlContent.java:53-54` so với `mml2omml.xsl:814`.
- Ca tái hiện:
  ```xml
  <math xmlns="http://www.w3.org/1998/Math/MathML"><mtext>z ∈ ℂ</mtext></math>
  ```
  1. Token này là mixed nên FNor=1, ra run `m:nor` với text `z ∈ ℂ`.
  2. ℂ (U+2102) không nằm trong {211D, 2124, 2115, 2113}, nên cổng cho qua và object bị vá.
- Ca tương tự: `tập ℚ`, `ⅆx`, `𝐯 = 2`, `ℋ`.
- Hệ quả (suy ra, chưa kiểm trên Word): theo cơ chế đã thấy với ℝ/ℤ/ℕ/ℓ, Word có thể lưu thành C/Q/d/v. Lý do: schema OMML không cho `m:nor` đi cùng `m:scr`/`m:sty`. Trên Word chỉ mới kiểm 4 ký tự đó.
- Hướng sửa: dùng một tập ký tự chung cho XSLT, Java và vector test. Có thể mở rộng cổng ra cả hai khối; như vậy chỉ tăng số OLE được giữ lại, không làm mất dữ liệu. Sau đó chạy lại 32 đề để xem số object bị giữ thay đổi thế nào.

**P3 — Phân loại "pure letterlike" rộng hơn bằng chứng Word**
- Vị trí: `mml2omml.xsl:814`.
- `probes-after.txt:13-16` cho thấy `<mtext>℃</mtext>` và `<mtext>𝑥</mtext>` giờ thành math run `sty=p`.
- ℃, №, ™, ℅ không phải chữ toán, trước đây ở `m:nor` vẫn an toàn.
- Với `𝑥` (italic sẵn trong ký tự), `sty=p` mâu thuẫn với kiểu của ký tự. Word có thể đổi thành x đứng; chưa được kiểm.
- 32 đề không bị ảnh hưởng (theo báo cáo của Codex là canonical trùng nhau). Cần thu hẹp tập ký tự hoặc probe Word cho ký tự đại diện của từng nhóm.

**P3 — Lý do từ chối không phân biệt được**
- Vị trí: `DocxMathPatchMain.java:323` và `:328`.
- Thông báo gộp 3 nguyên nhân thành một câu, và skip reason chung là `OMML_CONVERSION_FAILED`.
- Khi rà corpus, không tách được object bị giữ vì letterlike với object bị giữ vì rỗng hoặc thiếu base. Nên trả về nguyên nhân cụ thể.

**P3 — Thiếu test**
- `MathmlContentVectorTest` không có ca `m:nor` nào: thiếu `val` = absent/`1`/`on` (phải chặn) và `0`/`false`/`off` (phải cho qua). Nhánh miễn trừ hiện chưa có test, và XSLT không bao giờ sinh `val`.
- `DocxMathPatchWorkflowTest.java:33` chỉ kiểm `unresolved()==1`, không kiểm `skipBreakdownCount(OMML_CONVERSION_FAILED)`. Test có thể vẫn xanh nếu object bị giữ vì lý do khác.
- Chưa có ca ℂ/ℚ (sẽ lộ P2) và ca NBSP. Ví dụ `<mtext>ℝ&#xA0;</mtext>`: normalize-space không bỏ NBSP, nên token không còn là pure và bị giữ OLE. Kết quả vẫn an toàn nhưng làm giảm số công thức được chuyển.

**Không phải regression, chỉ ghi nhận:** khoảng trắng trong mtext bị mất do normalize-space (`probes-after.txt:9-10`: ` = ` thành `=`). Lỗi này đã có trước bản sửa và cũng xảy ra khi tách các mtext liền kề.

## Giới hạn

- Chỉ đọc mã, test, các file `docs/working` được chỉ định và các artifact `probes-after.txt`, `red.log`, `verification.json`.
- Tôi **không chạy** Maven, Python, gate, converter hay corpus, và **không mở Word/Writer**. Các con số 97/116/4, gate 4/4, kết quả so sánh 32 đề và quan sát Word lưu/đóng/mở lại đều là số liệu Codex báo cáo, tôi chưa chạy lại. Tôi chưa đối chiếu hash của `word-run-boundaries.docx`.
- Hành vi Word với ℂ/ℚ/𝑥/℃ là suy luận, chưa quan sát.
- FULL_END_ONLY vẫn unsupported, các OLE bị giữ lại vẫn chưa được mở rộng xử lý. DSMT4 chưa hoàn tất.
- Không sửa file, không commit, push, merge hay đăng lên GitHub.
