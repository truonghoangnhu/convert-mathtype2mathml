# DSMT4 growth probe review resolution

Claude đã hoàn tất review read-only ngày12/11/2026 trên bộ scratch ngày11/11: không P1/P2, có5P3 về verifier và chuỗi bằng chứng. Kết quả gốc ở claude_dsmt4_growth_boundaries_review_2026-11-12.md (heading gốc ghi ngày batch11/11). Không có kết luận nghiệm thu corpus hoặc converter.

Codex kiểm lại từng finding và xử lý trong bản verifier mới `work/dsmt4-growth-review-2026-11-12/verify_growth_review.py`; dữ liệu tái tạo nằm riêng ở `verified-v2/`. Không ghi đè DOCX/PDF/script/ảnh/JSON gốc của batch11/11.

1. **P3-1:** xác định từng token x/y/z sau chuẩn hóa Unicode và kiểm đủ ba hàng ở trang4; xác định line bắt đầu GROWTH C và kiểm nhãn ở trang3. Bốn PDF đều đạt. Không chỉ dựa vào hàngx.
2. **P3-2:** anchor ROI theo cả dòng bắt đầu GROWTH A thay vì từ system. Nới ROI ngang từ54..396pt thành51..399pt; kiểm cả bốn mép của bbox nét được chọn. Cả bốn crop đạt; Writer có padding trái30pixel ở600dpi. Chiều cao nét giữ nguyên60,12/78,00/78,00/58,56pt. Đây là kiểm bền của phép đo, không phải cải thiện bố cục.
3. **P3-3:** ảnh so sánh mới giữ toàn chiều ngang trang450pt, không cắt30pixel bên phải. `long-comparison-full-width.png` đã được Codex xem. Bằng chứng chính cho Writer clip là full-page `writer-growth-reopened-page-2.png` xuất từ PDF Writer UI, không chỉ crop cũ.
4. **P3-4:** kiểm trực tiếp bytes của bản xem Word khớp bytes writer-explicit-lines-ui.docx, đồng thời hash khớp trước Word-view. Ghi tên nguồn/hash/chứng minh byte_identical ở verification.json mới. Đây là kiểm hiện tại của gói đã giữ nguyên; không giả rằng nguồn hash đã có trong manifest cũ.
5. **P3-5:** nêu rõ khác biệt đang mở: Word căn giữa hệ A/C, Writer đặt sát lề trái với ngoặc mảnh/cao; bản ba dòng vẫn căn giữa tương đối các hàng, không giữ align-left; +9t/+17t ở Word view sít hơn toán tử trong dòng đầu; Word có khoảng hở rất nhỏ giữa hàngz và AFTER_A nhưng ảnh không thấy chồng nét. Các số ink của hai renderer không thể đọc thành mức tăng chiều cao do cùng một thao tác.

Đã chạy verifier mới đạt, xem ảnh so sánh toàn chiều ngang và crop Writer có padding mới. Năm artifact bằng chứng gốc vẫn khớp hash final-checks.json cũ. git diff --check đạt. Không chạy lại production suite vì không sửa production.

Kết luận giữ nguyên: hệ có phân số lồng chịu được edit tử số rồi roundtrip; phép cộng dài tự wrap trong Word nhưng clip trong Writer; stack ba dòng là workaround trên mẫu tổng hợp này. Chưa có chính sách chèn ngắt dòng tự động vào MathML/OMML. Nhãn caC vẫn tách khỏi hệ, chưa phải bố cục khớp nguồn. Corpus needs_review, accepted không tăng; chưa commit/push/merge.
