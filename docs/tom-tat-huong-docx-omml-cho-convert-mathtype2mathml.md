# Tóm tắt chốt hướng mở rộng `.docx` / OMML cho repo `convert-mathtype2mathml`

## 1. Hiện trạng repo hiện tại

Repo `convert-mathtype2mathml` hiện **không phải** pipeline `MathML -> OMML -> DOCX`.

Nó đang là pipeline:

```text
DOCX -> HTML
```

với 2 luồng chính:

- **OMML native trong DOCX**: xử lý trong Java, có dùng `omml2mml.xsl` để đi theo chiều **OMML -> MathML**
- **MathType OLE / WMF**: dùng `transpect` để bóc ra **MathML sidecar**
- Sau đó Java **inject MathML vào HTML** để render bằng MathJax

### Những gì repo hiện đã làm được rất tốt

- quét `/word/media/*.wmf`
- quét `/word/embeddings/*.bin`
- sinh `work/transpect/mathml/*.mathml`
- sinh `manifest.tsv`
- match theo:
  - exact part name trước
  - fallback leaf-name nếu duy nhất

Đây là phần rất quý và nên **tái sử dụng nguyên vẹn**.

---

## 2. Kết luận kỹ thuật quan trọng

### Nếu gói của bạn đã chuyển được:

```text
OLE / MathType -> MathML
```

thì hoàn toàn có thể đi tiếp:

```text
MathML -> OMML -> DOCX
```

Đây là hướng đúng nếu đích cuối là Word editable equation.

### Điểm cần nhớ

- **OMML** là math native của Word
- **OLE/MathType** không phải OMML
- Vì vậy với OLE/MathType, hướng sạch nhất là:

```text
OLE/MathType -> MathML -> OMML -> inject vào DOCX
```

---

## 3. Hướng nên đi lâu dài

### Không nên lấy HTML làm trung gian cho nhánh DOCX mới

Nếu mục tiêu là đầu ra `.docx`, thì không nên đi:

```text
DOCX -> HTML -> DOCX
```

vì sẽ tăng tầng chuyển đổi và dễ mất fidelity.

### Hướng nên làm

Giữ nguyên nhánh HTML hiện có, và thêm **một nhánh mới song song**:

```text
DOCX source
  -> detect math source
     -> native OMML: giữ nguyên / copy
     -> OLE/WMF MathType: lấy sidecar MathML từ manifest
  -> MathML -> OMML
  -> inject lại vào DOCX
  -> output DOCX
```

---

## 4. Chiến lược đúng cho repo này

### Không phá nhánh hiện tại

Repo hiện tại vẫn tiếp tục phục vụ tốt cho:

```text
DOCX -> HTML + MathML
```

### Chỉ bổ sung nhánh mới

```text
DOCX -> DOCX(native OMML)
```

Vì repo của bạn đã có sẵn:
- `manifest.tsv`
- sidecar `*.mathml`
- exact match / leaf fallback

nên đây là nền rất tốt để patch ngược vào `.docx`.

---

## 5. Kiến trúc đề xuất thêm vào project

### Package mới nên thêm

```text
src/main/java/.../word/
  DocxMathPatchMain.java
  MathOccurrence.java
  MathSourceDetector.java
  MathSidecarRepository.java
  MathmlNormalizer.java
  MathmlToOmmlConverter.java
  OmmlInjector.java
  DocxWalker.java
```

### Resource mới nên thêm

```text
src/main/resources/
  mml2omml.xsl
```

Repo hiện đã có `omml2mml.xsl`, còn chiều ngược `mml2omml.xsl` là phần còn thiếu.

---

## 6. Vai trò từng module

### `MathSourceDetector`
Phân loại từng công thức trong `.docx`:
- `NATIVE_OMML`
- `OLE_BIN`
- `WMF_PREVIEW`
- `UNKNOWN`

### `MathSidecarRepository`
Đọc:
- `manifest.tsv`
- thư mục `mathml/*.mathml`

và trả về MathML theo part name.

### `MathmlNormalizer`
Chuẩn hóa MathML trước khi đổi sang OMML.

### `MathmlToOmmlConverter`
Chuyển:

```text
MathML -> OMML
```

nên ưu tiên triển khai bằng **XSLT + Saxon** để hợp với kiến trúc repo hiện tại.

### `OmmlInjector`
Chèn OMML vào `.docx` tại đúng vị trí object cũ.

### `DocxWalker`
Duyệt toàn bộ paragraph / table cell / các phần cần patch trong tài liệu.

---

## 7. Thuật toán tổng thể của nhánh mới

```text
input.docx
  -> mở bằng XWPFDocument
  -> duyệt paragraph / table cell
  -> detect math occurrence
       - native OMML: giữ nguyên
       - OLE_BIN / WMF_PREVIEW: lấy partName
  -> tra manifest.tsv
  -> lấy sidecar MathML
  -> normalize MathML
  -> convert MathML -> OMML
  -> thay object cũ bằng OMML
  -> ghi output.docx
```

---

## 8. Nguyên tắc thay thế object cũ

### Không sửa bên trong OLE object

Không cố chỉnh binary OLE.

### Cách đúng

Dùng OLE/WMF chỉ để:
- xác định vị trí công thức
- xác định part-name
- tìm sidecar MathML

Sau đó:
- xóa object cũ
- chèn OMML mới vào đúng vị trí trong Word

Tức là:

```text
[text trước] [OLE/WMF object] [text sau]
=>
[text trước] [OMML] [text sau]
```

---

## 9. Phân loại inline và block

### Inline
Nếu object nằm giữa text trong cùng paragraph.

### Block
Nếu paragraph gần như chỉ chứa object.

### Khuyến nghị triển khai

- **Giai đoạn 1**: chỉ patch **block equations**
- **Giai đoạn 2**: thêm **inline equations**

Lý do: block equations dễ và ít rủi ro hơn rất nhiều.

---

## 10. Thứ tự triển khai nên làm

### Giai đoạn 1 — MVP an toàn nhất
Chỉ patch **block equations**:
- detect object paragraph
- tra manifest
- lấy MathML
- đổi sang OMML
- thay cả paragraph

### Giai đoạn 2
Thêm inline equation:
- giữ text trước/sau
- xóa object run
- chèn `m:oMath` vào giữa paragraph

### Giai đoạn 3
Mở rộng:
- table cells
- header/footer
- grouped shapes
- cleanup style/spacings

---

## 11. Điều chốt về mặt kỹ thuật

### Chốt 1
Repo hiện tại đã giải được phần khó nhất:

```text
MathType/OLE -> MathML
```

### Chốt 2
Phần còn thiếu chỉ là:

```text
MathML -> OMML
```

và bộ injector đưa OMML vào `.docx`.

### Chốt 3
Không nên viết lại từ đầu.

Nên **tái sử dụng tối đa**:
- `generate_sidecars.sh`
- `manifest.tsv`
- sidecar MathML
- exact/leaf fallback logic

### Chốt 4
Kiến trúc tốt nhất là repo có 2 đầu ra song song:

```text
A. DOCX -> HTML + MathML
B. DOCX -> DOCX(native OMML)
```

---

## 12. Kết luận cuối cùng

Hướng mở rộng đúng nhất cho repo `convert-mathtype2mathml` là:

```text
Giữ nguyên nhánh HTML hiện tại
+ thêm nhánh patch DOCX dùng lại manifest sidecar
+ bổ sung MathML -> OMML
+ thay OLE/WMF bằng OMML native trong DOCX
```

Đây là hướng:
- ít phá code cũ
- tận dụng tối đa phần đã làm được
- đúng bản chất Word
- phù hợp lâu dài nếu đích cuối là `.docx`

---

## 13. Câu ngắn gọn nhất để nhớ

**Repo hiện tại đã đi được nửa đường rất khó. Việc hợp lý tiếp theo là không quay vòng qua HTML, mà dùng lại sidecar MathML hiện có để patch ngược OLE/MathType thành OMML native trong `.docx`.**
