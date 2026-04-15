# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Đỗ Xuân Bằng  
**Vai trò:** Embed
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** 400–650 từ

---

## 1. Tôi phụ trách phần nào?

Trong Day 10, tôi phụ trách phần kết nối giữa cleaned dataset và vector store, tập trung vào việc chuẩn hóa runtime embedding để bước publish sang ChromaDB dùng đúng model. Các file tôi làm nhiều nhất là `etl_pipeline.py`, `embeddings.py`, `eval_retrieval.py`, `grading_run.py`, cùng cấu hình `.env` / `.env.example`. Công việc của tôi bắt đầu từ đầu ra `cleaned_csv` do phần cleaning tạo ra, sau đó bảo đảm pipeline có thể embed, query và grading bằng cùng một embedding runtime thay vì để index và query dùng hai model khác nhau.

Phần này kết nối trực tiếp với cleaning/quality owner vì tôi dùng `artifacts/cleaned/*.csv` và manifest làm “publish boundary”. Nó cũng nối với docs/eval owner vì sau khi embed xong thì `eval_retrieval.py` và `grading_run.py` mới đọc đúng collection. Bằng chứng rõ nhất là `artifacts/logs/run_sprint1.log` có `embedding_runtime=provider=jina model=jina-embeddings-v5-text-small` và `embed_upsert count=6 collection=day10_kb`.

---

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật quan trọng nhất của tôi là không để ChromaDB tự fallback về default embedding local, mà buộc toàn bộ pipeline dùng embedding runtime theo `.env`. Lý do là nhóm đã dùng Jina v5 (`jina-embeddings-v5-text-small`) từ Day 08 và Day 09. Nếu Day 10 lại để Chroma hoặc script eval tự dùng `all-MiniLM-L6-v2`, hệ sẽ sinh ra hai không gian vector khác nhau và lỗi chỉ lộ ra khi chạy thật ở bước upsert hoặc query.

Vì vậy tôi tách logic sang `embeddings.py`, phân biệt rõ `embed_passages()` và `embed_queries()`, rồi cho `etl_pipeline.py`, `eval_retrieval.py` và `grading_run.py` cùng đọc `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL`. Tôi cấu hình `CHROMA_DB_PATH=./chroma_db_jina` để tách index Jina khỏi index cũ. Trade-off là Jina API chậm hơn local model và phụ thuộc API key, nhưng đổi lại index/query nhất quán hơn và dễ debug hơn qua `run_id`, manifest và log runtime.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly đáng nhớ nhất tôi xử lý là lỗi lệch dimension giữa collection cũ và embedding mới. Triệu chứng là pipeline đã đi qua phần ingest, clean và expectation thành công, nhưng vỡ ở bước embed với lỗi kiểu “Collection expecting embedding with dimension of 384, got 1024”. Điểm khó là log data quality vẫn xanh, nhưng lỗi thật lại nằm ở serving/index layer.

Check giúp tôi định vị là `artifacts/logs/run_sprint1.log`: các expectation đều `OK`, nhưng runtime embed ghi rõ Jina v5. Từ đó tôi suy ra collection cũ được tạo bằng model khác, còn run hiện tại đang gửi vector 1024 chiều. Cách fix của tôi là: tách embedding runtime thành module riêng, để query và index dùng chung provider; ghi `embedding_provider` và `embedding_model` vào manifest; và thêm logic rebuild collection nếu phát hiện dimension mismatch trong `etl_pipeline.py`. Sau khi chỉnh, `run_sprint1.log` đã đi tới `embed_upsert count=6` và `PIPELINE_OK`.

---

## 4. Bằng chứng trước / sau

Tôi dùng evidence tương đương từ manifest và eval CSV. Ở `artifacts/manifests/manifest_sprint2-sample.json`, `run_id=sprint2-sample` ghi `cleaned_records=5` và `quarantine_records=5`, cho thấy pipeline đã siết chặt hơn so với `run_id=sprint1` (`cleaned_records=6`, `quarantine_records=4`) để loại thêm chunk refund stale. Sau khi publish sang index đã verify, `artifacts/eval/sprint2_hashing_eval.csv` cho thấy câu `q_refund_window` có `contains_expected=yes`, `hits_forbidden=no`, còn `q_leave_version` có `top1_doc_expected=yes`. Với tôi, đó là bằng chứng dữ liệu sau clean và bước embed/query nhất quán thực sự cải thiện retrieval.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ tự động hóa collection naming bằng `provider + model + dimension` trong `CHROMA_COLLECTION` hoặc metadata bắt buộc, để khi đổi embedding model thì pipeline tự tạo namespace mới thay vì chờ đến lúc upsert mới phát hiện lỗi. Cách này sẽ giảm rủi ro rerun sai DB và làm idempotency dễ quan sát hơn trong runbook.

