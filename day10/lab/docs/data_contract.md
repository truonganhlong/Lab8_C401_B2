# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `data/raw/policy_export_dirty.csv` | Batch CSV export từ lớp staging trước khi publish | Duplicate chunk, thiếu `effective_date`, `doc_id` lạ, `effective_date` không ISO | `raw_records`, `quarantine_records`, cảnh báo nếu `quarantine_records > 0` |
| `data/docs/policy_refund_v4.txt` | Canonical text file để đối chiếu policy refund khi clean và eval retrieval | Chunk stale nói `14 ngày làm việc` thay vì bản v4 là `7 ngày làm việc` | Expectation `refund_no_stale_14d_window`, eval `hits_forbidden` cho `q_refund_window` |
| `data/docs/hr_leave_policy.txt` | Canonical text file cho HR policy | Export kéo nhầm bản cũ 2025 (`10 ngày phép năm`) thay vì policy 2026 | Quarantine reason `stale_hr_policy_effective_date`, expectation `hr_leave_no_stale_10d_annual` |
| `data/docs/sla_p1_2026.txt` và `data/docs/it_helpdesk_faq.txt` | Canonical knowledge docs cho IT Helpdesk / SLA | Sai mapping `doc_id`, thiếu metadata thời gian export, drift nội dung khi re-export | `no_empty_doc_id`, freshness theo `latest_exported_at`, review manifest theo `run_id` |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | ID ổn định sinh từ `doc_id + seq + hash(chunk_text)` sau clean |
| doc_id | string | Có | Phải thuộc allowlist hiện tại: `policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy` |
| chunk_text | string | Có | Không rỗng, tối thiểu 8 ký tự sau clean; duplicate bị đưa vào quarantine |
| effective_date | date | Có | Chuẩn hóa về `YYYY-MM-DD`; dòng parse lỗi hoặc thiếu ngày bị quarantine |
| exported_at | datetime | Có | Dùng để ghi nhận độ mới của export và đưa vào manifest freshness |

---

## 3. Quy tắc quarantine vs drop

Record bị flag không bị xóa âm thầm. Pipeline ghi toàn bộ vào `artifacts/quarantine/quarantine_<run-id>.csv` để giữ bằng chứng quan sát được theo từng lần chạy.

Các trường hợp hiện tại đi quarantine:

- `unknown_doc_id`
- `missing_effective_date`
- `invalid_effective_date_format`
- `stale_hr_policy_effective_date`
- `missing_chunk_text`
- `duplicate_chunk_text`

Chỉ cleaned dataset mới được publish sang bước validate và embed. Việc merge lại dữ liệu quarantine phải do owner data pipeline hoặc owner nghiệp vụ tương ứng xác nhận:

- CS/Operations owner với `policy_refund_v4`
- HR owner với `hr_leave_policy`
- IT Helpdesk owner với `sla_p1_2026` và `it_helpdesk_faq`

Trong Sprint 1, policy đơn giản là "quarantine trước, không auto-merge lại trong cùng run".

---

## 4. Phiên bản & canonical

Source of truth cho refund policy là `data/docs/policy_refund_v4.txt`, tương ứng `doc_id=policy_refund_v4`, effective date `2026-02-01`. Nếu raw export còn câu nói `14 ngày làm việc` thì coi là dữ liệu stale từ bản sync cũ và phải bị fix hoặc fail expectation.

Source of truth cho HR leave là `data/docs/hr_leave_policy.txt`, với cutoff version tối thiểu `2026-01-01`. Dòng HR mang effective date cũ hơn mốc này không được publish vào cleaned dataset.

Canonical docs hiện tại:

- `data/docs/policy_refund_v4.txt`
- `data/docs/hr_leave_policy.txt`
- `data/docs/sla_p1_2026.txt`
- `data/docs/it_helpdesk_faq.txt`
