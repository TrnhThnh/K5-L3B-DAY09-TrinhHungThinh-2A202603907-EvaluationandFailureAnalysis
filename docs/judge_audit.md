# Judge audit

Calibrate trên 100 nhãn replay mỗi tiêu chí, lấy FAIL làm lớp dương. Ngưỡng là κ ≥ 0.6, precision ≥ 0.8 và recall ≥ 0.7.

| Tiêu chí | TP / FP / FN / TN | κ | Precision | Recall | Tỉ lệ FAIL quan sát → Rogan–Gladen | Quyết định |
|---|---|---:|---:|---:|---|---|
| tone_ok | 24 / 4 / 6 / 66 | 0.757 | 0.857 | 0.800 | 28% → 30% | Đạt calibration cho giọng điệu |
| helpful | 9 / 0 / 21 / 70 | 0.375 | 1.000 | 0.300 | 9% → 30% | Loại khỏi gate |

## Audit bất đồng

| Case | Judge | Người | Phán quyết và thay đổi rubric |
|---|---|---|---|
| H-008 | PASS | FAIL | Người đúng. Cụm “anh check giúp em” cùng “rồi nha” quá thân mật theo chuẩn hỗ trợ. Thêm ví dụ để judge phân biệt lịch sự với suồng sã. |
| H-017 | PASS | FAIL | Người đúng theo chuẩn xưng hô của bộ replay. Đặt “anh/chị” làm mặc định và đưa ví dụ về cách gọi “bạn ơi” trong ngữ cảnh trang trọng. |
| H-029 | PASS | FAIL | Người đúng. “Không cần nhắn thêm” mang giọng gạt đi dù câu mở đầu có “Dạ”. Chấm toàn bộ lời đáp và đánh dấu mệnh lệnh làm khách khó tiếp tục trao đổi. |
| H-042 | FAIL | PASS | Người đúng. Câu ngắn vẫn lịch sự và nêu thời gian tiền về. Chỉ yêu cầu lời xin lỗi nếu ngữ cảnh có lý do cụ thể. |
| H-051 | FAIL | PASS | Người đúng. “Refund” là thuật ngữ được bộ phận hỗ trợ LogiX chấp nhận. Thêm danh sách thuật ngữ được phép. |
| HL-015 | PASS | FAIL | Người đúng. Lời đáp nói 55.000đ trong khi ledger ghi 40.000đ theo ghi chú nhãn. Tách khớp số tiền thành kiểm tra code trước khi chấm tính hữu ích. |
| HL-016 | PASS | FAIL | Người đúng. Lời xin lỗi dài vẫn đi kèm số tiền sai, 55.000đ thay vì 35.000đ. Rubric yêu cầu kiểm tra thông tin giao dịch trước khi chấm độ đầy đủ. |

Judge helpful bỏ sót 21/30 lỗi. Rogan–Gladen hiệu chỉnh tỷ lệ tổng thể trên dữ liệu replay và các ước lượng sensitivity/specificity hiện có. Quyết định từng case vẫn theo bằng chứng ledger hoặc nhãn người. Cần tập held-out mới có người gắn nhãn độc lập trước khi dùng judge để quyết định release.
