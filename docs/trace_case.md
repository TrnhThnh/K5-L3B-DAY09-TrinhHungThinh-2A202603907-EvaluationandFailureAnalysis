# Trace case C-002@11

| Trường | Kết quả |
|---|---|
| Trial | `seeded_regression C-002@11`, run ID trong `reports/eval_seeded_regression.json`. |
| Triệu chứng | `TrialPass` báo `status resolved != denied`. Ledger ghi một giao dịch 20.000đ, nhãn kỳ vọng 0. Reply cũng nói 20.000đ, nên grader FM-08 vẫn PASS. |
| Bước sai đầu tiên | Bước 3 `model_override` với payload `{"delay_days": 5}`. |
| Vì sao | Bước 1 handoff yêu cầu tra chính sách. Bước 2 investigator trả O-202 với 0 ngày trễ trong DB. Bước 3 lấy con số 5 ngày từ ticket thay cho dữ liệu đó. Bước 4 chọn điều khoản trễ giao với quote 20.000đ, rồi bước 6 báo hoàn. |
| Failure mode | FM-03 trong [taxonomy](failure_taxonomy.md). |
| Đối chứng | `fixed C-002@11` giữ dữ liệu DB, bước 3 `quote` trả 0 với `no_entitlement`. Trạng thái là `denied`, ledger 0, `TrialPass` PASS. |
| Regression test | `test_ticket_delay_never_overrules_db_for_c002` kiểm tra event ghi đè và ledger 20.000đ trên variant lỗi, kiểm tra trạng thái, ledger và grader trên bản fixed. `E-002` mang provenance của trace này. |
| Giới hạn | Trace chứng minh sai khác theo fixture, chưa đo tần suất lỗi trên ticket thực. |

Tái hiện từ `src/` bằng `python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11` và thay shape bằng `fixed` để đối chiếu.
