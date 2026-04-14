# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Đỗ Xuân Bằng  
**Vai trò trong nhóm:** Supervisor Owner  
**Ngày nộp:** 2026-04-14  

---

## 1. Tôi phụ trách phần nào?

Tôi chịu trách nhiệm chính cho **Sprint 1 — Supervisor Orchestrator**, tức là toàn bộ file `graph.py`. Cụ thể các function tôi trực tiếp implement:

- `supervisor_node()` — logic phân tích task và quyết định route
- `retrieval_worker_node()`, `policy_tool_worker_node()`, `synthesis_worker_node()` — wrapper nodes kết nối với worker thật
- `build_graph()` và `run_graph()` — entry point của toàn hệ thống

Ngoài ra, tôi cũng rebuild ChromaDB index từ đầu (collection `day09_docs`, 5 tài liệu) vì index ban đầu trống (`count=0`), và fix `workers/synthesis.py` để load đúng API key từ `.env`.

**Kết nối với nhóm:** `run_graph()` là hàm các thành viên khác (Sprint 2–4) gọi vào. Supervisor cũng định nghĩa state schema (`AgentState`) mà mọi worker đều đọc/ghi.

---

## 2. Quyết định kỹ thuật: Keyword-based routing thay vì LLM classifier

**Quyết định:** Dùng keyword matching để route thay vì gọi LLM để phân loại intent.

**Các lựa chọn đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Keyword matching (đã chọn) | Nhanh (~1ms), không tốn token, dễ debug | Cần maintain danh sách keyword thủ công |
| LLM classifier | Linh hoạt hơn, hiểu ngữ cảnh | Chậm (~800ms), thêm cost, thêm điểm lỗi |

**Lý do chọn keyword:** Lab có 5 tài liệu với domain rõ ràng — SLA/ticket, policy/refund, access control. Keyword đủ để phân biệt 3 loại task, không cần inference phức tạp.

**Bằng chứng từ trace** (`run_20260414_161107.json`):

```json
"supervisor_route": "retrieval_worker",
"route_reason": "SLA/incident/helpdesk keyword detected: ['p1', 'sla', 'ticket'] → retrieval_worker",
"latency_ms": 16887
```

Thời gian 16 giây là do LLM call ở synthesis — bản thân bước routing chỉ tốn < 2ms.

**Trade-off chấp nhận:** Nếu user hỏi bằng từ ngữ không nằm trong keyword list thì sẽ route về `retrieval_worker` theo default — chấp nhận được vì retrieval là fallback an toàn nhất, ít nhất vẫn có evidence để synthesis trả lời.

---

## 3. Lỗi đã sửa: OpenAI API key không được load → Synthesis trả về lỗi

**Lỗi:** Synthesis worker luôn in `[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env.` dù `.env` đã có key hợp lệ.

**Symptom:** Chạy `python graph.py` lần đầu, cả 3 query đều trả về cùng message lỗi đó. Confidence vẫn tính được (~0.53) nhưng `final_answer` không có nội dung thật.

**Root cause:** File `workers/synthesis.py` dùng `os.getenv("OPENAI_API_KEY")` nhưng không có `load_dotenv()` trước đó. Khi chạy trực tiếp qua `python graph.py`, biến môi trường từ `.env` chưa được load vào process.

**Cách sửa:** Thêm vào đầu `workers/synthesis.py`:

```python
# Trước khi sửa (synthesis.py dòng 19):
import os
WORKER_NAME = "synthesis_worker"

# Sau khi sửa:
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
WORKER_NAME = "synthesis_worker"
```

**Bằng chứng trước/sau:**

```
# Trước khi sửa:
Answer  : [SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env.

# Sau khi sửa (run_20260414_161107.json):
Answer  : Ticket P1 được tạo lúc 22:47, do đó:
          1. SLA deadline cho ticket P1 là 4 giờ sau khi tạo, tức là 02:47 ngày hôm sau.
          2. Người nhận thông báo là on-call engineer...
```

---

## 4. Tự đánh giá

**Làm tốt nhất:** Routing logic rõ ràng, có thứ tự ưu tiên (human_review > policy > SLA > default), `route_reason` luôn ghi rõ keyword nào trigger — đủ để trace đọc được mà không cần nhìn code.

**Làm chưa tốt:** Keyword list dùng cả tiếng Việt có dấu lẫn không dấu — dễ sót nếu user nhập theo cách khác. Chưa có unit test riêng cho `supervisor_node()` để verify routing đúng với 10 grading questions.

**Nhóm phụ thuộc vào tôi:** `run_graph()` và `AgentState` là interface trung tâm. Nếu tôi chưa xong Sprint 1, Sprint 2 không test được worker và Sprint 4 không chạy được `eval_trace.py`.

**Tôi phụ thuộc vào thành viên khác:** Cần Sprint 2 hoàn thiện `workers/policy_tool.py` để câu gq09 (cross-doc multi-hop) hoạt động đúng — hiện tại policy worker đã retrieve cả hai phần nhưng cần logic phân tích context phức tạp hơn.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ thêm **Parent-Child chunking** vào ChromaDB index. Nhìn trace `run_20260414_161107.json`, retrieval_worker trả về 3 chunks từ 3 file khác nhau với score thấp nhất chỉ 0.497 — tức là document `hr_leave_policy.txt` không liên quan gì đến câu hỏi P1 nhưng vẫn được kéo vào context. Nếu index theo chunk nhỏ hơn (paragraph-level thay vì toàn bộ file), relevance score sẽ chính xác hơn và LLM không bị nhiễu bởi nội dung không liên quan.
