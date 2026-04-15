# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Observability

**Tên nhóm:** C401_B2  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Đỗ Việt Anh | Tech Lead, Group Report | vietanh201004@gmail.com |
| Đỗ Xuân Bằng | Ingestion Owner (Sprint 1) | doxuanbang14122005@gmail.com |
| Lê Thanh Long | Cleaning & Quality Owner (Sprint 2) | lethanhlong9a1819@gmail.com |
| Trương Anh Long | Embed & Evaluation Owner (Sprint 3) | truonganhlong.1209@gmail.com |
| Lã Thị Linh | Monitoring / Docs Owner (Sprint 4) | lalinhkhmt@gmail.com |

**Ngày nộp:** 15/04/2026  
**Repo:** `truonganhlong/Lab8_C401_B2`  
**Độ dài khuyến nghị:** 600–1000 từ

---

## 1. Pipeline tổng quan (150–200 từ)

Nhóm xây dựng ETL pipeline cho Knowledge Base IT Helpdesk với mục tiêu: (1) **Data Integrity** (ngăn dữ liệu stale/sai lọt vào vector store), (2) **Data Observability** (mỗi lần chạy truy vết được bằng `run_id`, log, manifest và artifact đầu ra). Nguồn raw là `day10/lab/data/raw/policy_export_dirty.csv` (kèm file inject để test).

Luồng end-to-end:
1) **Ingest**: đọc raw, gắn `run_id`, log `raw_records`.  
2) **Transform & Clean**: chuẩn hoá `effective_date` (YYYY-MM-DD) và `exported_at` (ISO datetime), allowlist `doc_id`, loại duplicate, quarantine stale/draft marker và các conflict thời gian (temporal logic). File: `day10/lab/transform/cleaning_rules.py`.  
3) **Quality Gate (Expectations)**: chạy suite expectation theo severity (halt/warn) để chặn dữ liệu rủi ro trước khi publish. File: `day10/lab/quality/expectations.py`.  
4) **Publish & Embed**: embed/upsert vào ChromaDB, ghi manifest + log. File: `day10/lab/etl_pipeline.py`.

Evidence run mẫu: `day10/lab/artifacts/logs/run_sprint2_v2_final.log` có `run_id`, đường dẫn `cleaned_csv`, `quarantine_csv`, và `manifest_written`.

---

## 2. Cleaning & expectation (150–200 từ)

Nhóm chốt hướng làm theo “publish boundary”: dữ liệu chỉ được publish nếu qua **clean + expectation**. Các cleaning rule chính nằm ở `day10/lab/transform/cleaning_rules.py`:
- Allowlist `doc_id` (quarantine `unknown_doc_id`).
- Chuẩn hoá `effective_date` và quarantine nếu thiếu/sai format.
- Chuẩn hoá `exported_at` và quarantine nếu thiếu/sai format.
- Quarantine conflict timeline: `effective_date_after_exported_at`.
- Quarantine duplicate chunk_text.
- Fix nội dung stale refund (14 → 7 ngày) cho `policy_refund_v4` và đánh dấu `[cleaned: stale_refund_window]`.
- Quarantine stale/draft markers (ví dụ “bản sync cũ”, “lỗi migration”, “draft”…).

Expectation evidence theo run `sprint2_v2_final` (log: `day10/lab/artifacts/logs/run_sprint2_v2_final.log`): các check “halt” đều OK (như `refund_no_stale_14d_window`, `effective_date_iso_yyyy_mm_dd`, `it_no_hr_leakage`) và check “warn” vẫn có metric (`min_retention_60pct`).

---

## 3. Before / after ảnh hưởng retrieval (200–250 từ)

Nhóm dùng inject corruption + eval CSV để chứng minh cleaning/gate tác động thật lên retrieval.

**Before (Bad):** `day10/lab/artifacts/eval/eval_bad.csv` cho câu hỏi `q_refund_window` trả về preview chứa “**14 ngày làm việc**” và `hits_forbidden=yes` → chunk stale lọt vào retrieval.

**After (Good):** `day10/lab/artifacts/eval/eval_good.csv` cho `q_refund_window` trả về “**7 ngày làm việc**” và `hits_forbidden=no` → policy đúng được retrieve sau clean/gate.

Ngoài refund, `eval_good.csv` còn cho thấy các câu SLA/lockout/leave policy đều retrieve đúng `doc_id` kỳ vọng (`sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy`) với `contains_expected=yes`.

---

## 4. Freshness & monitoring (100–150 từ)

Nhóm đặt Freshness SLA 24h để phát hiện “snapshot cũ” (vấn đề upstream). Với `run_id=sprint2_v2_final`, log ghi:
`freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.921, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}`
(`day10/lab/artifacts/logs/run_sprint2_v2_final.log`).  
Nhóm coi đây là incident dữ liệu: cần escalation cho data owner để refresh export, và runbook xử lý đã được viết ở `day10/lab/docs/runbook.md`.

---

## 5. Liên hệ Day 09 (50–100 từ)

Sau Day 09 (multi-agent), Day 10 tập trung “đúng dữ liệu trước, rồi mới RAG”. Pipeline Day 10 tạo ra collection/DB đã clean + có manifest theo `run_id`, giúp hệ retrieval/agent ở Day 09 (hoặc triển khai helpdesk) tránh bị trả lời sai do dữ liệu stale và có đường truy vết khi cần debug.

---

## 6. Rủi ro còn lại & việc chưa làm

- Freshness hiện đang log FAIL nhưng pipeline vẫn có thể `PIPELINE_OK`; cần nâng thành “block publish” (hoặc chỉ cho phép khi chạy mode `--allow-stale` để demo).
- Cần tự động hoá incident response (Slack/Teams) kèm `run_id`, manifest và quarantine để giảm thời gian xử lý upstream.
