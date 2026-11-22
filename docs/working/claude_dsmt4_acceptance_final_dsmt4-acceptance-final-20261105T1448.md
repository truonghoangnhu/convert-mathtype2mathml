# Nghiệm thu DSMT4 — Claude, run `dsmt4-acceptance-final-20261105T1448`

**Chưa hoàn tất DSMT4. 265 occurrence: accepted 0, needs_review 219, failed 46, unsupported 0.**
Có một lỗi mới thuộc mã dự án: Word làm mất `ℝ ℤ ℕ ℓ` khi lưu.
Lỗi đã được sửa ở local và đã kiểm lại bằng UI Word. Bản sửa chưa commit hay push.
Sửa–lưu–mở lại qua UI đã chạy cho các mẫu sau, còn lại là `not_run`:
- Word: 14 mẫu, cộng 2 mẫu trên output đã sửa.
- Writer DOCX: 2 mẫu.
- LibreOffice Math/ODT: 2 mẫu.

Không commit, push, merge, không đổi trạng thái Draft hay auto-merge của PR #4.
Không sửa `in/`, ZIP, fixture, output hoặc bằng chứng cũ.
Mọi output mới nằm trong `work/dsmt4-acceptance-final-20261105T1448/` và `out/dsmt4-acceptance-final-20261105T1448/`.

## 0. Snapshot và công cụ

- Mã nguồn: HEAD `467370f` cùng working tree chưa commit.
  `manifest_before.json` / `manifest_after.json` có hash diff, hash nguồn, ZIP, output, 265 MathML LO và JAR.
- Kiểm trước và sau khi chạy: ZIP, 5 đề nguồn, 5 output baseline và 265 MathML LO **không đổi**.
- JAR được build lại vì có bản sửa ở mục 2.
- Phiên bản ứng dụng:
  - Word 16.114.3 (16.114.26102720).
  - LibreOffice 26.8.0.3; headless dùng profile riêng `qa/lo-profile-*`.
  - pdftoppm 26.10.0, OpenJDK 25.0.2, Python 3.13.5.
- Cách điều khiển UI: dùng công cụ computer-use. Ở nền dùng `app_*` cho menu và chụp màn hình. Ở toàn màn hình, gõ phím và click chỉ sau khi người dùng duyệt.
  Không dùng AppleScript, osascript hay System Events.
  Chỉ sửa bản QA trong `qa/`. Các cửa sổ Writer đang mở của người dùng không bị đụng tới.

## 1. Đã kiểm trực tiếp

**Word, render đề đầy đủ.** Word *Save As PDF (Best for printing)* cho bản QA của nguồn và output của Lý, Toán, TN, Hóa (`qa/word-render/*.pdf`).
- Đề Công nghệ có output trùng byte với nguồn nên không render lại.
- Mỗi đề được cắt theo neo “PHẦN/Câu”, nguồn đặt trên, output đặt dưới (`renders/word-segments`, `word-sheets`, `word-zoom`).
- **Đã xem toàn bộ phân đoạn chứa 265 occurrence** của 4 đề. Ghi chú nằm trong `evidence/visual_word_*.json`.
- MT Extra không cài trên máy này, chỉ có “MT Extra Tiger”. Vì vậy preview nguồn vẽ sai các glyph MT Extra (⇌ hiện thành `à à ã`).
  Với những glyph này, tham chiếu là MathML và bản ghi text WMF.

**Word, kiểu chữ tự động.** So multiset (chữ, nghiêng, đậm) giữa bản ghi LOGFONT của WMF preview và thuộc tính run OMML (`evidence/style_compare.json`).
- Kết quả: **252/252 khớp**.
- Khác biệt hệ thống: font Cambria Math thay cho Times New Roman.

**Writer DOCX.** Render headless 4 đề, nguồn và output (`renders/writer`).
- Đã xem Hóa (câu 1, 2, 7, 8, 11–13, 16; PII câu 4; PIII câu 1), Lý (câu 7, 8, 16), TN (PIII) và Toán (câu 2–4, 12).
- Quét toàn văn bản tìm glyph lỗi: chỉ còn một `¿`.
- Quét XML 252 OMML: 0 đối số rỗng.
- Occurrence không thuộc phân đoạn đã xem được ghi `writer_visual = not_viewed (scan-only)`.

**LibreOffice Math.** Nhập cả 265 MathML đã chuẩn bị (W/L/T) vào ODT nhúng, rồi render PDF (`qa/lo-math-embed-all`). **Đã xem cả 8 trang.**
Có thêm một ODT 20 mẫu đã lưu lại headless (`qa/lo-math-embed`).
Lưu ý: khi lưu headless, LibreOffice chỉ serialize lại những object đã nạp (20/265), nên annotation của các object khác không dùng làm bằng chứng.

**Sửa–lưu–đóng–mở lại trong Word:** 14 occurrence, chèn `q` vào bên trong công thức (`evidence/ui_roundtrip.json`).

| Cấu trúc | Occurrence | Đường dẫn của `q` sau lưu | Hiển thị sau mở lại |
| --- | --- | --- | --- |
| inline hóa | hoa001 | `oMath/r` | đã xem |
| block trong ô bảng | hoa014 | `oMathPara/oMath/sSub/e/r` | XML; ảnh lần mở đầu |
| block căn trái | hoa021 | `oMathPara/oMath/r` | đã xem |
| nhãn ⇌ (`groupChr`) | hoa037 | `oMath/groupChr/e/r` | đã xem; ⇌ vẫn không giãn |
| nhãn → trong block | hoa042 | `oMathPara/oMath/groupChr/e/r` | đã xem; mũi tên vẫn giãn |
| `>` đầu công thức | hoa068 | `oMath/sSup/e/r` | đã xem |
| hai mũi tên có nhãn | hoa086 | `oMathPara/oMath/r` (cơ sở “Zn”) | đã xem |
| phân số trong căn | li004 | `rad/e/f/num/r` | đã xem |
| `sPre` ¹⁴₆C | li008 | `sPre/e/r` | đã xem |
| phân số nghiêng | li009 | `f/den/r` | đã xem |
| vectơ | toan011 | `oMath/r` | đã xem |
| hệ `{` | toan013 | `d/e/m/mr/e/r` | đã xem |
| tích phân, ngoặc | toan054 | `nary/e/d/e/r` | đã xem |
| P′(t) | toan077 | `d/e/r` | đã xem |

**Writer DOCX qua UI** (`qa/writer-ui/wui-Hoa_Ha_Noi_L1.docx`). Các bước: mở trình sửa Math, chèn `q`, lưu DOCX (Keep Word format), đóng, mở lại.
- hoa001 giữ `C2H5OHq` (`oMath/r`).
- Nhãn hoa042 giữ `t^{qo},p`. Writer đổi `groupChr` thành `limLow`, và mũi tên vẫn tí hon.
- Việc Writer lưu cả tài liệu đã **làm hỏng các công thức không sửa**:
  - hoa068 mất `>`;
  - hoa037 và hoa086 bị dẹt thành ký tự rời.
- Chữ ngoài công thức không đổi.

**LibreOffice Math/ODT qua UI** (`qa/lo-math-ui/lomath-ui.odt`, MathML đã chuẩn bị).
- li004 → `{ v = sqrt { frac { { 3q p } } { ρ } } . }`;
- hoa042 → `csup { t ^ o ,q p }`.

Sau khi lưu ODT, đóng và mở lại, cả hai đều giữ ký tự sửa và hiển thị đúng; mũi tên hoa042 vẫn ngắn.

- Sau khi Word lưu, mọi công thức khác của 3 đề vẫn giữ nguyên: Hóa 100, Lý 18 kèm 3 OLE, Toán 115.
  Ngoại lệ duy nhất là cách Word lưu: `−`→`-`, `′`→`'`, ký hiệu letterlike → `m:scr`.
- Chữ ngoài công thức không đổi.
- Thao tác lỡ: hai lần `q` rơi ra ngoài vị trí định sửa. Cả hai đã được hoàn tác trước khi lưu và đã kiểm lại.

## 2. Lỗi mới, lỗi đã sửa, trước/sau

**Lỗi mới thuộc mã dự án, đã sửa ở local.**
- Hiện tượng: `mtext` chỉ chứa ký hiệu letterlike được xuất thành run `m:nor`. Word 16.114 lưu `ℝ ℤ ℕ ℓ` trong run `m:nor` thành chữ thường `R Z N l`, nên ký hiệu bị mất ngay lần lưu đầu.
- Quan sát trực tiếp: toan078 `(a∈ℝ)` sau khi lưu thành `R`.
- Probe Word `qa/probes/word-probe-1/2(-saved).docx` cho kết quả:
  - với `m:nor`, cả 4 ký hiệu đều mất;
  - với run toán, có hoặc không có `m:sty=p`, Word lưu đúng thành `m:scr` (double-struck/script).
- Phạm vi toàn corpus: 23 ℝ, 19 ℤ, 1 ℕ, 8 ℓ. Trong bộ 5 đề: toan078, tn017, tn020.
- Sửa hẹp trong `mml2omml.xsl` (`FNor`): một `mtext` **chỉ gồm** ký tự U+2100–214F hoặc U+1D400–1D7FF không còn là `m:nor`; nó nhận `m:sty=p` để giữ dáng đứng. Chữ thường và `mtext` lẫn ký tự khác vẫn là `m:nor`.
- Test hồi quy trong `XsltMathmlToOmmlConverterTest`:
  - đỏ trước khi sửa: `logs/letterlike-red.log`, `ℝ ==> expected <0> but was <1>`;
  - xanh sau khi sửa: `letterlike-green.log`.
- Toàn bộ test Java sau sửa: **95 đạt, 0 fail/error** (93 + 2).
- Output 32 đề mới nằm ở `out/dsmt4-acceptance-final-20261105T1448/corpus/`. So với snapshot finalization:
  - chỉ `word/document.xml` của 12 file đổi;
  - 48 công thức có chữ giữ nguyên; 51 run letterlike chuyển sang `m:sty=p`, 0 run letterlike còn `m:nor`;
  - số công thức, vị trí và OLE không đổi.
- Writer headless lưu lại DOCX vẫn giữ `a∈ℝ`, `ℓ=35,0`, `|ec|=Bℓv`.
- **Đã kiểm bằng UI Word trên output đã sửa** (`qa/word-ui-fix/`), mỗi file đều qua sửa, lưu, đóng, mở lại:
  - toan078 `(aq∈ℝ)` được lưu là `R` + `m:scr=double-struck` và hiển thị ℝ;
  - tn017 `ℓ=q35,0` và tn020 `Bℓv` được lưu là `l` + `m:scr=script` và hiển thị ℓ;
  - các công thức khác không đổi.

**Lỗi mới, chưa sửa (tuyến LibreOffice Math, MathML đã chuẩn bị).** 36 occurrence failed khi nhập:
- 20 ngoặc `mfenced separators=""` thành `)` lạc (`uoper`), ví dụ `M(2;2;1)`;
- 5 khoảng `[2,7;3,0)` thành `¿`;
- `|x+2|` và `|e_c|`;
- ion `X²⁺`, `Li⁺`, `H⁺`: dấu `+` cuối chỉ số trên nuốt phần sau;
- `t(°C)`;
- hệ toan015 lệch hàng.

Đây là giới hạn của quy tắc W/L/T. F vẫn experimental nên không mở rộng adapter trong đợt này.

**Lỗi Word đã thấy trong render, chưa sửa**, kèm probe trong `word-probe-1`:
- Mũi tên mẫu rỗng của hoa066/067 thành `→` ngắn. Probe cho thấy `⟶` vẽ dài, nhưng đổi ký tự là quyết định trình bày, cần chủ dự án chốt.
- ⇌ có nhãn (hoa037) không giãn. Probe `groupChr` và `limUpp` đều không giãn: đây là giới hạn của Word.
- li002 `p,khối` và li010 `ptheo`: chữ dính liền sau công thức. Nguồn không có dấu cách; khoảng hở thuộc về ảnh OLE.
- toan086: Word ngắt `AB = | CD = 16cm` qua cả dòng lẫn trang. tn019 và toan011 bị ngắt dòng giữa công thức.
- `S.ABCD` / `3,5.10` thành `S. ABCD`. Probe: một run `.` riêng có `m:nor` sẽ khít, nhưng sửa phải tách run trong logic gộp token, nên chưa làm.
- Phân trang lệch ở cả 4 đề dù số trang giữ nguyên (`pagination_word.json`, `pagination_writer.json`).
- Phân số và tích phân inline bị Word vẽ ở cỡ text-style. OMML không có thuộc tính nào cho inline display.

**Writer DOCX** (không đổi so với các đợt trước):
- hoa068 hiện `¿150°C`;
- 5 mũi tên (hoa037, 042, 066, 067, 086);
- toan015 lệch hàng;
- chữ trong công thức bị giãn cách.
- Mới quan sát qua UI: Writer lưu DOCX làm hỏng các công thức không được sửa. hoa068 mất `>`; mũi tên của hoa037 và hoa086 bị dẹt thành ký tự rời.

Các lỗi đã sửa ở những đợt trước được xác nhận lại trên đề đầy đủ: li008 C còn, toan054 không còn `fleft`, không còn ô placeholder.

## 3. Số liệu

| Tuyến | failed | needs_review | accepted |
| --- | ---: | ---: | ---: |
| Word | 9 | 256 | 0 |
| Writer DOCX | 7 | 258 | 0 |
| LibreOffice Math | 36 | 229 | 0 |
| **Tổng occurrence** | **46** | **219** | **0** |

- Theo đề: Lý 2/16, Toán 28/87, TN 3/29, Hóa 13/87 (failed/needs_review).
- 13 OLE giữ nguyên ở trạng thái needs_review.
- 18 OMML nguồn giữ nguyên XML.
- Với bản sửa local: toan078 và tn020 vẫn failed do tuyến Math; tn017 thành needs_review.

Chi tiết từng tiêu chí: `work/dsmt4-acceptance-final-20261105T1448/ledger.json`, `ledger.csv`, `ledger-summary.md`. Bản sao nằm trong `out/…/`.

## 4. Chưa chạy và lý do

Màn hình Mac khóa hai lần trong phiên, nên số mẫu UI bị giới hạn. Các mục chưa chạy:

- Writer DOCX, sửa–lưu–đóng–mở lại: `not_run` cho 250/252 OMML (chỉ chạy hoa001, hoa042).
- Writer DOCX, lưu toàn tài liệu qua UI: mới chạy cho đề Hóa; ba đề còn lại `not_run`.
- LibreOffice Math, sửa–lưu ODT–mở lại: `not_run` cho 263/265 (chỉ chạy li004, hoa042). Bằng chứng UI trước đây của Codex: hoa068, toan054.
- Word: 238 occurrence chưa thử sửa. Không suy rộng từ 14 mẫu.
- Word: chưa thử lưu toàn tài liệu cho đề TN ngoài bản output đã sửa.
- Writer: chưa xem trực quan từng occurrence ngoài các phân đoạn đã liệt kê (`not_viewed`).
- Không suy kết quả Writer từ ODT, và không suy kết quả Word từ XML.

## 5. Việc cho Codex review / UI

1. Review và tích hợp bản sửa `FNor` (letterlike). Test và UI Word trên output đã sửa đều đạt; cần review mã và chạy CI sau khi push.
2. Writer DOCX UI cho các mẫu còn lại: hoa021, li004, li008, toan013, toan054, cùng một lượt lưu toàn tài liệu cho Lý, Toán, TN.
   Với mỗi ca: sửa trong Math editor, lưu DOCX (Keep format), đóng, mở lại.
   Đã biết: Writer lưu làm hỏng hoa068, hoa037 và hoa086.
3. LibreOffice Math UI trên `qa/lo-math-embed/lo-math-embed.odt` cho toan015, tn004, toan053, li008. Với mỗi ca: sửa, lưu ODT, đóng, mở lại.
4. Các quyết định cần chủ dự án chốt:
   - mũi tên mẫu rỗng → `⟶`;
   - tách run `.` với `m:nor`;
   - `m:box noBreak` (hoặc chính sách khác) để Word không ngắt công thức;
   - chấp nhận phân trang lệch và font Cambria Math;
   - xử lý li002/li010 (không thêm ký tự giả).
5. Tuyến Math: probe quy tắc cho `+` cuối chỉ số, `|…|`, khoảng `[a;b)`, rồi mới quyết định có mở rộng ngoài W/L/T hay không.

## Chạy lại

```bash
cd work/dsmt4-acceptance-final-20261105T1448
python3 -I scripts/structure.py ../.. evidence/structure.json
python3 scripts/segments.py qa/word-render renders/word-png renders/word-segments word 150
python3 -I scripts/locate.py ../.. evidence/structure.json renders/word-segments/index.json evidence/structure_located.json
python3 -I scripts/style_compare.py ../.. evidence/structure_located.json evidence/style_compare.json
python3 -I scripts/adjacency.py ../.. evidence/structure_located.json evidence/adjacency.json
python3 scripts/pagination.py qa/word-render evidence/pagination_word.json
python3 scripts/lo_math_embed.py ../.. <ids> qa/<new-dir>
python3 scripts/repatch_compare.py ../.. ../../out/<new-run>/corpus
python3 -I scripts/build_ledger.py .
```

Kiểm tra tự động trên working tree hiện tại: `mvn -o -q package` (95 Java), `python3 -m unittest discover -s tests` (116), workflow (4), generated-output gate 4/4 tại `out/dsmt4-acceptance-final-20261105T1448/modern-gate/`. Log nằm trong `logs/`. **CI của PR #4 không kiểm chứng các thay đổi local này.**
