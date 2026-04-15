# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability
**Họ và tên:** Trương Anh Long
**Vai trò:** Sprint 3 — Monitoring
**Ngày nộp:** 15/04/2026
**Độ dài yêu cầu:** 400–650 từ

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**
- `etl_pipeline.py` — chạy pipeline good run và bad run với các flag tương ứng
- `eval_retrieval.py` — chạy đánh giá retrieval, xuất `eval_good.csv` và `eval_bad.csv`
- `docs/quality_report.md` — viết báo cáo so sánh before/after với số liệu thực tế

**Kết nối với thành viên khác:**
Tôi nhận output từ Sprint 2 (dữ liệu đã clean, collection `day10_kb` đã embed) làm baseline cho Scenario A (good run). Kết quả 2 file eval và quality report được nhóm dùng làm bằng chứng cho phần grading Sprint 3.

**Bằng chứng (run_id thực tế):**
- Good run: `sprint2-good` → `artifacts/manifests/manifest_sprint2-good.json`
- Bad run: `inject-bad` → `artifacts/manifests/manifest_inject-bad.json`

---

## 2. Một quyết định kỹ thuật (100–150 từ)

**Chọn flag `--no-refund-fix --skip-validate` thay vì sửa tay dữ liệu**

Khi inject corruption cho Scenario B, tôi có hai lựa chọn: (1) sửa trực tiếp file CSV raw để chèn dữ liệu sai, hoặc (2) dùng flag `--no-refund-fix --skip-validate` có sẵn trong pipeline.

Tôi chọn cách (2) vì đảm bảo tính tái lập — bất kỳ thành viên nào cũng có thể reproduce bad run chỉ bằng một lệnh duy nhất mà không cần biết cách sửa CSV thủ công. Ngoài ra, cách này phản ánh đúng thực tế: lỗi trong production thường đến từ việc bỏ qua validation rule, không phải từ việc ai đó sửa tay dữ liệu. Flag `--skip-validate` còn cho phép pipeline tiếp tục embed dù expectation fail, giúp bad data thực sự được đẩy vào vector DB và ảnh hưởng rõ ràng đến kết quả retrieval.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** Sau khi chạy xong cả good run và bad run, hai file `eval_good.csv` và `eval_bad.csv` có kết quả giống hệt nhau — cột `hits_forbidden` đều trả về `no` cho `q_refund_window`, dù bad run phải trả về `yes`.

**Metric phát hiện:** So sánh thủ công 2 file CSV, cột `top1_preview` của `q_refund_window` ở cả hai đều chứa "7 ngày" — tức vector DB không phản ánh dữ liệu bẩn của bad run.

**Nguyên nhân:** Pipeline dùng `upsert` theo `chunk_id` cố định. Khi `chunk_id` không đổi, ChromaDB giữ nguyên nội dung cũ ("7 ngày") thay vì ghi đè bằng nội dung bẩn ("14 ngày").

**Fix:** Xóa collection cũ trước khi chạy bad run để force rebuild hoàn toàn, đảm bảo vector DB phản ánh đúng dữ liệu bẩn. Sau fix, `eval_bad.csv` ghi nhận `hits_forbidden=yes` cho `q_refund_window` — đúng như kỳ vọng của Sprint 3.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Hai dòng trích thẳng từ file eval thực tế:

**eval_bad.csv** (`run_id=inject-bad`) — Scenario B (corrupted):
```
q_refund_window,...,policy_refund_v4,
"Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc...",
yes,yes,,3
```
→ `hits_forbidden=yes`: retrieval trả về chunk chứa "14 ngày" ❌

**eval_good.csv** (`run_id=sprint2-good`) — Scenario A (clean):
```
q_refund_window,...,policy_refund_v4,
"Yêu cầu được gửi trong vòng 7 ngày làm việc...",
yes,no,,3
```
→ `hits_forbidden=no`: retrieval trả về chunk chứa "7 ngày" ✅

Câu `q_leave_version` đạt `top1_doc_expected=yes` ở good run, đủ điều kiện merit (`gq_d10_03`).

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ mở rộng file `data/test_questions.json` thêm ít nhất 3 câu hỏi mới bao phủ các policy khác, đồng thời thêm cột `scenario` vào output CSV của `eval_retrieval.py`. Điều này giúp nhóm phân tích kết quả theo từng nhóm policy thay vì chỉ nhìn tổng thể, dễ phát hiện loại corruption nào ảnh hưởng nặng nhất đến retrieval.