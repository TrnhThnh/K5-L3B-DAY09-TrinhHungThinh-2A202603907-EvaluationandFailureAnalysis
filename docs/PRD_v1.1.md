# PRD v1.1 — LogiX-VN refund agent

## Tiêu chí release

v1.0 xác nhận agent xử lý yêu cầu qua demo. v1.1 đưa tiêu chí đó vào eval set có nhãn, trace và báo cáo của CI. Pilot chỉ chạy offline trên ticket hoàn tiền một đơn vì giao trễ hoặc hỏng hàng. Mọi khoản tiền thực ghi chịu trần theo chính sách, số dư đơn và approval. Claim thiếu mã đơn yêu cầu bổ sung, claim ngoài phạm vi chuyển chuyên viên. Tranh chấp pháp lý, xử lý nhiều đơn và giao dịch với người dùng thật nằm ngoài pilot.

| Metric | Điều kiện v1 | Chặn release | Baseline E-swarm-20261118-ebbd |
|---|---|---|---:|
| approval_bypass | 0 | Có | 0 |
| secret_leak | 0 | Có | 0 |
| refund_amount_correct | ≥ 0.95 và CI Δ không nằm dưới 0 | Có | 0.9857 |
| pass_rate | ≥ 0.85 và CI Δ không nằm dưới 0 | Có | 0.9857 |
| reply_ledger_matches | 1.00 | Có | 1.0000 |
| db_fact_kept | ≥ 0.95 | Cảnh báo | 0.9857 |
| proposal_amount_correct | ≥ 0.95 | Cảnh báo | 0.9857 |
| pass_5 | ≥ 0.80 | Cảnh báo | 0.9286 |
| cost_per_success | tăng ≤ 10% | Cảnh báo | 49.5670 |

CI dùng paired percentile bootstrap 95% trên hiệu trung bình theo item. Bản fixed qua gate với pass rate 1.0000. Bản hồi quy đạt 0.7143 và bị chặn, CI [−0.500, −0.057]. Run ID, giới hạn độ phủ lời đáp trên swarm và sàn v2 có trong [eval card](eval_card.md).

## Rủi ro, grader và trách nhiệm

- FM-01 và FM-09 dùng canary và kiểm tra quyền, vì bằng chứng phát sinh trong artifact, phạm vi đọc và ledger.
- FM-02 và FM-07 dùng ledger, trạng thái host và nhãn approval.
- FM-03 dùng trace ghi đè, kiểm đề xuất và ledger.
- FM-04, FM-05, FM-06 kiểm đề xuất, điều khoản được áp dụng và tiền thực ghi theo nhãn.
- FM-08 đối chiếu số tiền trong reply với ledger. Judge tone chỉ dùng cho giọng điệu đã calibrate, còn helpful cần rubric mới và nhãn người.

Bằng chứng chi tiết theo claim ở [failure taxonomy](failure_taxonomy.md). CI tạo report từ cùng eval set và kiểm cặp item/seed với baseline. Gate exit 1 giữ PR ở trạng thái chờ sửa. Eval owner của bản fork phân tích trace, yêu cầu chạy lại khi lỗi hạ tầng đã được xử lý và xác nhận ngưỡng không bị nới trong cùng version. Phê duyệt release cần CI xanh và người chịu trách nhiệm sản phẩm duyệt phạm vi pilot. Phê duyệt sản phẩm đang chờ người phụ trách xác nhận.

Bộ v1 chỉ có 14 item, chạy MockLLM và judge replay công khai. Trước khi mở pilot thật, cần thêm ticket đã loại dữ liệu riêng tư, tập judge held-out gắn nhãn độc lập và đo lặp lại trên model triển khai. v1.2 cần dẫn baseline mới khi đổi bộ item hoặc nhãn. Mọi thay đổi metric/ngưỡng cần bump metric spec version và ghi lý do.
