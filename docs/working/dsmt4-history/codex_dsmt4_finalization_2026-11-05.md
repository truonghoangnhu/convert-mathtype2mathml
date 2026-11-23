# DSMT4: hoàn thiện phạm vi đã kiểm chứng — 2026-11-05

**Đã bổ sung lệnh chuẩn bị MathML riêng cho LibreOffice Math, gia cố cổng nội dung và đưa hồi quy vào CI. Corpus vẫn `needs_review`; chưa nghiệm thu đầy đủ 265 occurrence.** Không commit/push/merge hoặc đổi Draft PR #4.

## Mã và hợp đồng

- `scripts/transpect/prepare_libreoffice_mathml.py` tạo file MathML mới dành cho LibreOffice Math với ba quy tắc W/L/T đã probe: gom các con trực tiếp của `math` vào một `mrow`, thêm nhóm rỗng quanh các quan hệ đầu/cuối thuộc danh sách đã đo. Không thêm toán hạng có nội dung; không đổi nguồn hoặc MathML dùng cho OMML Word. F vẫn experimental, không tích hợp.
- JSON/exit: **needs_review/0** khi chuẩn bị candidate; **unsupported/2** khi không có nội dung MathML hiển thị hợp lệ; **failed/1** khi XML/DOCTYPE/I/O lỗi hoặc đích đã tồn tại. Không có accepted; `application_acceptance=not_run`. Nguồn và đích có sẵn không bị ghi đè.
- Tuyến LibreOffice chỉ tính nội dung có namespace MathML. Nếu chỉ có token ngoài namespace thì không tạo candidate. Nếu còn nội dung MathML nhưng XML trộn namespace hoặc chứa semantics/annotation, trả nguyên chuỗi byte-identical và báo `untested`, không áp dụng W/L/T. Tránh mất `xmlns=""` hoặc binding dùng trong QName khi serialize.
- Java/Python từ chối công thức chỉ chứa CGJ U+034F hoặc variation selector; vẫn giữ base+selector, toán tử vô hình đi cùng nội dung và dấu kết hợp thông thường. Không loại mọi Mn. Cơ sở: [Unicode variation sequences](https://www.unicode.org/faq/vs.html), [Unicode display guidance](https://unicode.org/faq/unsup_char.html). Đây là cổng nội dung hẹp, không chứng nhận font của mọi ký tự khác.
- Test openability-failure của gate dùng manifest/report trong thư mục tạm của chính test; không còn phụ thuộc hoặc ghi đè file `out/` cũ. Gate production không bị làm yếu.
- CI nay chạy Java tests khi build, Python/workflow tests trước generated-output gate; path filters bao gồm mã/test mới. **Chưa chạy GitHub CI cho các thay đổi chưa push.**

## Đỏ → xanh và review

Log trong `work/dsmt4-finalization-2026-11-05/`: `visibility-{java,python}-red.log`, `clean-gate-{red,green}.log`, `lo-command-{red,green}.log`, `lo-mixed-namespace-{red,green}.log`, `lo-serialization-{red,green}.log` và các log suite cuối.

Reviewer độc lập `/root/review_dsmt4` tìm hai P2 namespace và kiểm lại sau sửa: không còn finding quan trọng; 13 focused tests đạt. Reviewer không sửa mã. CI path-filter omission cũng đã được bổ sung.

## Kiểm chứng cuối

| Kiểm tra | Kết quả và phạm vi |
| --- | --- |
| `mvn -q -o package` | **93 tests**, 0 failure/error/skip; `maven-final.log` |
| `python3 -m unittest discover -s tests` | **116 đạt**, gồm 9 command-level tests cho preparation; `python-tests-final.log` |
| Workflow unittest | **4 đạt**; `workflow-tests-final.log` |
| Generated-output gate | **4/4**, 0 structural failed checks; `out/dsmt4-finalization-modern-gate-2026-11-05/`. ZIP/XML, không phải mở ứng dụng. |
| Chạy JAR mới trên 32 đề | `out/dsmt4-finalization-corpus-2026-11-05/`: hash nguồn khớp baseline; tập package parts và nội dung canonical từng part trùng snapshot R1 trước. Không render lại 32 đề; không ghi đè output cũ. |
| Preparation MathML | Khớp W/L/T đã review trên **37 probe**; 4 probe không hợp lệ bị từ chối. Chuẩn bị **265 candidate** riêng ở `out/dsmt4-finalization-lo-mathml-2026-11-05/`; kiểm lại bằng mã cuối: output không đổi. Không có accepted. |

Word không đổi số liệu: **2.417 chèn = 71 block + 2.346 inline; 200 DSMT4 và 10 OLE khác giữ nguyên; 27 OMML nguồn → 2.444 OMML output**. Bộ 5: **252 candidate + 13 OLE giữ nguyên + 18 native OMML**. Con số 265 MathML chuẩn bị cho Math khác với 252 OMML chèn theo kiểm tra an toàn vị trí Word.

## Ứng dụng

**Word 16.114.3 (16.114.26102720):** mở `work/dsmt4-finalization-2026-11-05/word-toan15-variants.docx`, bản QA từ probe Claude Toán #15. Đã xem ảnh UI trước và sau Save → Close → Reopen: V0 `m:d+m:m`/`mcJc=left` giữ các hàng x/y/z căn trái. V1 eqArr và V2 matrix-only cũng đã quan sát. Không đổi converter sang eqArr. Không sửa ký tự trong hệ ở lượt này; không suy full-exam placement/editability. Đóng riêng bản QA; không sửa/lưu đề Tin học của người dùng. Ảnh đã quan sát trong tool trace của chat; không có file screenshot Word riêng của lượt này.

**LibreOffice Math 26.8.0.3:** Hóa #68 từ mã preparation mới được nhập ODF rồi xuất PDF bằng profile headless riêng. Đã xem `out/dsmt4-finalization-lo-render-2026-11-05/hoa068.png`: giữ `>150°C`, không `¿`. Không kết luận font/spacing chính xác. Phép sửa/lưu/đóng/mở lại ODT ở lượt trước giữ phạm vi riêng trong `codex_dsmt4_writer_mathml_review_2026-11-05.md`.

## Giới hạn nghiệm thu

- Không tuyên bố mọi DSMT4 giải mã được theo ProgID. `FULL_END_ONLY` vẫn unsupported; không suy nội dung từ preview/fingerprint.
- Không mở rộng 108 skip gốc, hai OLE Lý ¶91 hoặc các OLE giữ bởi safety guard.
- Writer DOCX còn lỗi quan hệ đầu và căn hàng hệ. Tuyến Math còn vấn đề mfenced, mũi tên vectơ/nhãn, font/spacing, phân số và cấu trúc ngoài W/L/T. Preparation không biến các lỗi đó thành thành công.
- Chưa đủ kiểm nội dung/bố cục và edit-save-reopen trong cả hai ứng dụng cho từng occurrence của 265 object; bold/italic và khoảng cách trong đề gốc chưa được chứng nhận toàn diện. Giữ ledger needs_review cùng các tiêu chí failed/not_run đã có.

Mã và kiểm tra của đợt này đã có bằng chứng. Mục tiêu nghiệm thu toàn bộ DSMT4 theo nội dung, khả năng sửa và bố cục vẫn chưa đạt; không dùng số test hoặc số công thức để tuyên bố hoàn tất mục tiêu đó.
