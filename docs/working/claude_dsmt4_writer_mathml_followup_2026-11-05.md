# DSMT4: Writer/MathML follow-up — Claude, 2026-11-05

> Đích dự kiến khi Codex copy: `docs/working/claude_dsmt4_writer_mathml_followup_2026-11-05.md`.
> Mọi đường dẫn `scratch:` dưới đây tương đối với
> `/Users/truonghoangnhu/.claude/jobs/f431a462/tmp/followup/`
> (đích repo: scripts/ + checkpoint → `work/claude-writer-mathml-followup/`, out/ →
> `out/dsmt4-writer-mathml-followup-2026-11-05/`).

**Trạng thái:** corpus `needs_review`; **0 occurrence accepted**. Chưa sửa production, chưa
commit/push. GUI: Claude **not_run** (không có công cụ UI hợp lệ). Bằng chứng UI duy nhất của
đợt này là của Codex (mục 1.4), ghi đúng phạm vi.

**Guard:** `Write work/claude-writer-mathml-followup/checkpoint.md` bị chặn: "This background
session hasn't isolated its changes yet. Call EnterWorktree first…". Không EnterWorktree, không
đổi setting, không dùng shell để ghi vào repo. Mọi file ở scratch (Codex xác nhận cách này).

Môi trường: LibreOffice **26.8.0.3**, build `bce0998afefdbc355585ca324285661a2170ba77`
(khác commit upstream đã ghim `218f0be8…`), headless, mỗi lượt soffice một profile mới, output
không ghi đè. Nguồn: 265 sidecar MathML của 5 đề; hash cả 265 khớp ledger cũ (`manifest.json`).

## Findings theo mức

| Mức | Case | Finding | Tuyến |
| --- | --- | --- | --- |
| **failed** | Hóa #68 ¶148 | Writer lưu DOCX làm mất nhóm rỗng: dựng từ MathML adapter, mở lại DOCX vẫn `> {150}^{°}"C"` → `¿150°C`. Tuyến DOCX→Writer OMML vẫn failed như cũ. | Writer DOCX |
| **failed** | Toán #13–#16 ¶11 | Hàng hệ phương trình bị căn giữa ở **mọi** tuyến LibreOffice đã thử; nguồn căn trái. Không có dạng MathML/OMML nào đã thử cho hàng căn trái. | Math, Writer ODT, Writer DOCX |
| **failed** | 21 Toán có `mfenced separators=""` `( )` | Tuyến MathML→Math **sai nội dung mà không có `¿`**: `M(2);)2);)1)`, `∫(2)f)(x))−)1)dx`. Kiểm `¿` là không đủ. | Math, Writer ODT |
| **failed** | Toán #11, #69 | `mover accent=true` + `→`: Math bỏ mũi tên vectơ (`u→` → `u`) ở mọi biến thể. | Math |
| **failed** | 14 ca khác | Sau adapter vẫn lỗi parse: chỉ số chỉ có toán tử (`^{2+}`, `^+`: Hóa #23–#26/#58/#65/#85), khoảng nửa mở `[a;b)` (Toán #46–#50), `mline` (TN #20), `t(^°C)` (TN #22). Ngoài phạm vi adapter. | Math |
| major | 183/265 | MathML nhiều con trực tiếp dưới `<math>` bị Math tách mỗi con thành một dòng (`newline`), kéo theo `¿` ở 87 ca (vd. Li #18 `B ¿ 3,5`). | Math |
| info | Hóa #98/#100, #99 | `→` đứng riêng nhập đúng; `NaOH→` lỗi sau khi nối dòng, rule T sửa được. | Math |

Không ca nào chuyển từ OK sang lỗi khi bật adapter (0 regression trên 265, `out/p1d-265`).

## 1. Ưu tiên 1: quan hệ ở đầu và adapter riêng cho LibreOffice Math

### 1.1 Ma trận probe (đã xem render)

`scratch:out/p1-matrix` (thăm dò, adapter v0; input `.mml` từng biến thể còn trên đĩa),
`out/p1b-adapter`, **`out/p1c-adapter-final`** (34 ca + 7 control biên), `out/p1d-265`
(cả 265 nguồn: raw và WLT), `out/p1e-mfenced` (39 nguồn có mfenced: raw, WLT, WLTF).
Mỗi ca: nhập `.mml` → `.odf`, PDF, resave/reopen `.odf`, PDF sau reopen, xuất MathML, so token
lá và vị trí slot (msup/mfrac…) với nguồn. Contact sheet đã xem:
`out/p1-matrix/sheets/p1-0{1..5}.png`, `out/p1e-mfenced/sheets/sel-01.png`.

| Biến thể | Kết quả trên LibreOffice 26.8.0.3 |
| --- | --- |
| raw | nhiều con → mỗi con một dòng; `< > ≤ ≥ =` đầu, `x =`, `x >` → `¿` |
| W (bọc 1 `mrow`) | hết tách dòng; quan hệ đầu vẫn `¿`; `NaOH→` thành `NaOH→¿` |
| + L (`<mrow/>` trước quan hệ đầu) | `< > ≤ ≥ = →` đầu, cả lồng trong msup/mfrac/msqrt và `mrow` có sẵn: đúng |
| + T (`<mrow/>` sau quan hệ cuối) | `x =`, `x >`, `NaOH→`: đúng |
| chỉ toán tử (`>`, `=`, `+`, `> =`) | lỗi ở mọi biến thể, **không có rule** (unsupported) |
| unary `− - + ±`, nhị phân `a>b` `x=2` `a+b` `a≤b` | đúng sau W; L/T không chạm |
| `≠` đầu, `mstyle` chứa quan hệ đầu | vẫn lỗi → báo `untested`, **không sửa** |
| MathML không namespace | Math nhập ra **rỗng** → adapter không nhận, phải namespace ở normalizer |
| `semantics` + annotation StarMath | Math dùng annotation, bỏ presentation → adapter không vào |
| root ngoại lai / `mo` ngoại lai trong `mrow` | Math không nhập; adapter trả nguyên byte |

Sau resave/reopen, annotation StarMath ổn định ở mọi ca. ASCII `-` được LibreOffice xuất thành
`−` ở mọi biến thể; adapter không gây ra việc này.

### 1.2 Adapter đề xuất (prototype, chưa production)

`scratch:scripts/lo_math_adapter.py`. Chỉ dùng cho đầu vào của MathML importer của LibreOffice
Math, **không** áp vào MathML chuẩn hóa dùng cho OMML/Word. Mặc định `rules="WLT"`:

- **W:** `<math>` có >1 con MathML thì bọc vào một `mrow`. Không bọc nếu có con ngoại lai hoặc `semantics`/`annotation`.
- **L:** chỉ áp cho `LEAD_REL = < > ≤ ≥ = →` trong `mrow`/`msqrt`. Con đầu là `mo`, sau nó có
  anh em khác rỗng: chèn `<mrow/>` trước.
- **T:** chỉ áp cho `TRAIL_REL = = > →` trong `mrow`: chèn `<mrow/>` sau quan hệ cuối.
- **Không bao giờ:** sửa chuỗi chỉ có toán tử (kiểm trước L/T), unary, phần tử khác namespace
  của root, `semantics`/`annotation(-xml)`, input không namespace. Ký tự/container khác chỉ
  báo `untested`. Nếu không rule nào chạy thì trả **nguyên chuỗi gốc** (không serialize lại).
- **F (opt-in, `rules="WLTF"`, không nằm trong mặc định):** `mfenced separators=""` với
  `open/close ∈ ( )`, không thuộc tính khác → mở rộng theo MathML 3 §3.3.8
  (`mrow`, `mo fence=true`). Đã chứng minh trên 35 instance `( )`: hết 21 ca `uoper`, render
  đúng, ổn định sau reopen. Loại `|`: Writer chuyển thành `lrline`, hiển thị và xuất DOCX là chữ
  `lrline` (Toán #62). Loại `{`/close rỗng: LibreOffice từng tự thêm ngoặc đóng (mục 2).

Không thêm ký tự, operand, thuộc tính hay spacing. Nhóm rỗng là đúng dạng `{ }` mà helper
upstream `lcl_AddMissingOperands` (ooxmlimport) chèn.

Regression đề xuất: `scratch:scripts/test_lo_math_adapter.py`, **25 test đạt**
(`out/adapter-tests/green.log`). Gồm hai phản ví dụ Codex: (1) `urn:foreign` root và `mo` ngoại
lai trong `mrow`; (2) `> =` chỉ có toán tử. Thêm biên namespace-free, `semantics`/`annotation-xml`,
thuộc tính `tr:`, container/ký tự chưa thử, và rule F. Bằng chứng đỏ: phiên bản lỗi đã bị ghi đè
nên không lưu được, vì vậy `scripts/mutation_check.py` đưa lại từng lỗi vào bộ nhớ: bỏ ranh giới
namespace → 7 test fail; kiểm operator-only sau L/T → 2 fail; vào semantics → 1 fail
(`out/adapter-tests/mutation.log`).

Kết quả 265 nguồn (`out/p1d-265`, `out/ledger-delta.json`): raw **87** ca có `¿`, **183** ca tách
dòng. Adapter (WLT, cộng F với mfenced): còn **14** ca có `¿`, **0** tách dòng, **0** regression.
Có 17 ca `failed` ở tiêu chí `lo_math_mathml_import`: 14 lỗi parse kể trên, 2 mất mũi tên vectơ,
1 `|x+2|` (Toán #62). 248 ca `needs_review`: không có `¿`, token khớp (bỏ qua ngoặc), annotation
ổn định. Tiêu chí này không kiểm spacing/font/căn hàng và không thay nghiệm thu.

### 1.3 Writer trong tài liệu (headless)

`scratch:out/p3b-writer-embed`: ODT có 9 ca × {raw, WLT, WLTF}, mỗi object chỉ chứa MathML
(không annotation) để Writer chạy importer khi mở. Đã xem PDF Writer
(`writer-p-1.png`, `writer-p-2.png`) và PDF sau DOCX→mở lại (`docxrt-p-1.png`).

- Writer ODT: ra giống probe Math (`>150°C`, `NaOH→`, `B=3,5.10⁻⁵T` đúng với WLT; Toán #10/#54/#11
  chỉ đúng với F; #11 vẫn mất mũi tên; #15 hàng căn giữa).
- ODT→ODT headless chép **nguyên byte** storage object chưa sửa (27/27), nên không phải roundtrip
  công thức. Bằng chứng reopen chỉ là render PDF của bản đã lưu.
- **Writer lưu DOCX → mở lại:** Hóa #68 WLT/WLTF lại thành `¿150°C` (OMML xuất `>150°C`, khi nhập
  thiếu operand trái). Li #18 raw mất `=` khi xuất. #62 WLTF xuất chữ `lrline`. Tuyến DOCX không
  thừa hưởng được sửa của adapter.
- `out/p3-writer-embed` (lượt đầu) có khung cố định 4×0,6 cm nên glyph méo. Chỉ dùng nội dung
  text, không dùng làm bằng chứng hình học.

### 1.4 Bằng chứng UI của Codex (không phải lượt GUI của Claude)

`work/codex-writer-adapter-ui/verification.json`: Codex mở bản sao `WL/odf/real-hoa068.odf`
(sha256 `9427bf9e…d920d008`, trùng file scratch `out/p1-matrix/WL/odf/real-hoa068.odf`) trong
LibreOffice Math 26.8.0.3, thêm `q` ở command editor, lưu ODF, đóng, mở lại: `>150°Cq`, không
placeholder (`fb9959e1…24c80`, StarMath `{ { } > 150 ^ ° "C" }q`). Phạm vi: **chỉ ODF đứng riêng**,
không chứng nhận DOCX OMML hay bố cục toàn tài liệu. Lúc đọc vẫn còn file lock
`.~lock.hoa68-adapter-ui.odf#`; Claude không đụng tới GUI/file đó.

### 1.5 Phạm vi

- **Đã chứng minh** (LibreOffice 26.8.0.3, headless): W/L/T với các ký tự/container nêu trên đúng
  nội dung, không lỗi, ổn định sau reopen ở Math đứng riêng và object Writer ODT. Ca
  Hóa #68 chỉnh UI trên ODF đứng riêng đạt (Codex).
- **Chưa chứng minh:** UI edit/save/reopen trong Writer ODT, bố cục/spacing trong đề gốc, ký
  tự/container ngoài danh sách, phiên bản LibreOffice khác, Word. **Không** có tuyên bố hỗ trợ chung.
- **Vẫn failed:** DOCX→Writer OMML và Writer→DOCX của quan hệ ở đầu. Thành công trên ODF
  đứng riêng không dùng để đánh dấu DOCX accepted.

## 2. Ưu tiên 2: hệ phương trình Toán #13–#16 ¶11

- **OMML/DOCX (Writer):** `out/p2-omml-toan15`. V0 là OMML hiện tại (`m:d{` + `m:m`, mcJc=left),
  V1 thay bằng `m:eqArr`, V2 `m:m` không ngoặc. Writer nhập thành `matrix{…}` / `stack{…}`,
  không có `alignl`. Xuất lại DOCX thì mất `mPr`/`mcJc`. Render đã xem (`page1-crop.png`): cả ba
  căn giữa, dấu `.` nằm cạnh hàng giữa. `eqArr` không tốt hơn, nên **không** đề xuất đổi `m:m`
  sang `eqArr`. Một run `x=2+5t` nguyên hàng được nhập thành text có ngoặc kép (`x"="2"+"5t`).
- **MathML (Math):** `out/p2-mathml`. `columnalign=left` trên `mtable`, `mtr`, `mtd` đều bị bỏ
  qua, hàng căn giữa.
- **StarMath `alignl`:** `out/p2-alignl`. Chỉ sửa annotation để chẩn đoán, không phải output đề
  xuất. Hàng căn trái đúng (`compare3.png`: trái raw, giữa alignl). LibreOffice xuất
  `<mtd columnalign="left">` kèm annotation. Bỏ annotation rồi nhập lại thì **mất alignl, nhóm
  lại sai** (`{x = {2+5}} t`) và **thêm ngoặc đóng thừa** (`right lbrace`; xem `noann-page.png`).
- Upstream đã ghim (`ooxmlimport.cxx`): `handleM`/`handleEqArr` không đọc thuộc tính căn chỉnh.
  Commit này chưa được xác minh khớp binary đang cài; ở đây chỉ dùng để giải thích kết quả thực nghiệm.

**Kết luận:** không có prototype hẹp nào giữ hàng căn trái mà vẫn chỉnh sửa được qua MathML hoặc
OMML trên LibreOffice 26.8.0.3. Hướng duy nhất thấy được là sinh annotation StarMath có `alignl`.
Đó là một bộ chuyển MathML→StarMath mới, phạm vi lớn, chưa làm và không đề xuất ở lượt này.
`lo_row_alignment=failed` ghi cho #13–#16 (đã xem #15; #13/#14/#16 cùng cấu trúc). Word: not_run.
Policy OLE giữ không đổi.

## 3. Ledger delta và case checklist

- `scratch:out/ledger-delta.json`: 265 object, base
  `out/dsmt4-r1-corpus-2026-11-05/acceptance-ledger-five-exams.json`. Chỉ thêm tiêu chí mới
  `lo_math_mathml_import` (phạm vi ghi trong từng bản ghi) và `lo_row_alignment` (#13–#16).
  Không ghi lại ledger cũ. Kết quả: 17 failed, 248 needs_review, 0 accepted.
- `scratch:out/case-checklist.json`: nhóm `inline`(237), `display_left`(2), `display_centerGroup`(3),
  `display_table`(10), `fraction`(14), `fraction_skew`(2), `scripts`(108), `arrow`(4),
  `arrow_labelled`(3), `matrix_or_system`(4), `font_style`(9), `spacing`(31), `fenced`(39),
  `retained_ole`(13). Mỗi nhóm có danh sách occurrence và số đếm theo tiêu chí. Tiêu chí
  `historical_*` chép từ audit cũ trên **snapshot output cũ hơn** và chưa kiểm lại; `word_*`
  not_run ở mọi nhóm. Bằng chứng Word đã có là của Codex (`work/codex-word-acceptance/`).
- Còn thiếu theo nhóm: labelled arrows (kích thước nhãn, Word), skew fraction (Writer vẽ phân
  số đứng, chưa kiểm lại), font/spacing (`C H₃`, `N a O H`: sidecar tách mỗi chữ một `mi`; Math
  cũng vẽ nghiêng/tách), display/table trong ngữ cảnh gốc, Word cho mọi nhóm.

## 4. Đề xuất cho Codex (theo thứ tự)

1. Nếu sẽ có tuyến MathML→LibreOffice Math: tích hợp `lo_math_adapter.py` (WLT) thành bước
   **riêng** của tuyến đó, kèm 25 regression. F chỉ bật cho `( )` nếu chấp nhận bằng chứng
   p1e/p3b. Không đưa vào MathML/OMML của Word.
2. Ghi rõ trong policy: quan hệ ở đầu **failed** trên Writer DOCX (cả nhập lẫn lưu), hàng hệ
   phương trình căn giữa trên mọi tuyến LibreOffice.
3. GUI cần chạy (not_run): Writer mở `out/p3b-writer-embed/writer-embed.odt`, vào object
   `hoa068 [WLT]` và `toan054 [WLTF]`, thêm `q` cuối công thức, lưu ODT, đóng, mở lại, đọc editor
   và chụp ảnh. Lặp lại, lần này lưu DOCX rồi mở lại (kỳ vọng Hóa #68 hỏng theo p3b). Word: mở
   bản patched Toán, kiểm hàng #15 có căn trái theo mcJc hay không.
4. Các lỗi Math còn lại (chỉ số chỉ có toán tử, khoảng nửa mở, accent vectơ, `|…|`): mỗi lỗi cần
   probe riêng trước khi thêm rule. Không mở rộng danh sách mà không có bằng chứng.

## Tái lập

Chạy từ repo root (đường dẫn sidecar trong case list là tương đối với repo). `$S` là scratch root.

```bash
S=/Users/truonghoangnhu/.claude/jobs/f431a462/tmp/followup
python3 -I $S/scripts/inventory_operators.py work/claude-five-exam-acceptance/ledger.json $S/out/operator-inventory.json
python3 -I $S/scripts/make_cases_p1.py $S/out/operator-inventory.json $S/out/cases-p1.json
python3 -I $S/scripts/probe_math.py $S/out/cases-p1b.json <new_out> --variants raw,WLT
python3 -I $S/scripts/probe_math.py $S/out/cases-265.json <new_out> --variants raw,WLT
python3 -I $S/scripts/probe_math.py $S/out/cases-mfenced.json <new_out> --variants raw,WLT,WLTF
python3 -I $S/scripts/p2_omml_probe.py out/dsmt4-r1-corpus-2026-11-05/patched/Toan_TQB_HN_Lx-omml.docx <new_out>
python3 -I $S/scripts/p2_alignl_probe.py $S/out/p2-mathml/raw/odf/toan015-raw.odf <new_out>
python3 $S/scripts/writer_embed_probe.py $S/out/cases-writer.json raw,WLT,WLTF <new_out>
python3 $S/scripts/contact_sheet.py <matrix_dir> <out_prefix> '<glob>' raw/pdf WLT/pdf ...   # cần Pillow
(cd $S/scripts && python3 -m unittest -v test_lo_math_adapter && python3 mutation_check.py)
python3 -I $S/scripts/make_ledger_delta.py $S && python3 -I $S/scripts/make_manifest.py $S
```

Manifest gồm tool, input repo, hash 265 sidecar và hash mọi file: `scratch:manifest.json`.
