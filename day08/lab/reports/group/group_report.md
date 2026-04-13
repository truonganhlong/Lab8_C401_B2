# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** C401_B2
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Lê Thành Long | Tech Lead, Eval Owner | lethanhlong9a1819@gmail.com |
| Đỗ Việt Anh | Retrieval Owner, Group Report | vietanh201004@gmail.com |
| Trương Anh Long | Retrieval Owner | truonganhlong.1209@gmail.com |
| Đỗ Xuân Bằng | Indexing Owner | doxuanbang14122005@gmail.com |
| Lã Thị Linh | Documentation Owner | lalinhkhmt@gmail.com |

**Ngày nộp:** 13/04/2026  
**Repo:** [truonganhlong/Lab8_C401_B2](https://github.com/truonganhlong/Lab8_C401_B2)  
**Độ dài khuyến nghị:** 600–900 từ

---

## 1. Pipeline nhóm đã xây dựng (150–200 từ)

Nhóm đã xây dựng một hệ thống Full RAG Pipeline tập trung vào tính chính xác (groundedness) và khả năng trích dẫn nguồn (citation).

**Chunking decision:**
Nhóm sử dụng chiến lược **Heading-based Chunking** kết hợp fallback đa tầng. Quy trình như sau: ưu tiên tách theo section headers (`=== ... ===`) để giữ nguyên ngữ cảnh của một điều khoản. Nếu section dài vượt quá 1600 ký tự (~400 tokens), hệ thống fallback sang tách theo paragraph (`\n\n`) và cuối cùng là dòng (`\n`). Cách tiếp cận này giúp giảm thiểu việc thông tin quan trọng bị cắt đôi ở giữa điều khoản, đảm bảo mỗi chunk là một đơn vị ngữ nghĩa hoàn chỉnh.

**Embedding model:**
Hệ thống sử dụng model `jina-embeddings-v5-text-small` qua Jina AI API. Chúng tôi tận dụng tính năng task-specific adapter của Jina v5: dùng `retrieval.passage` khi indexing và `retrieval.query` khi truy vấn để tối ưu hóa không gian vector cho túi dữ liệu chính sách.

**Retrieval variant (Sprint 3):**
Nhóm chọn **Dense Retrieval + Reranking** làm variant chính. Sau khi Dense Retrieval (top-10) lấy về các ứng viên tiềm năng, chúng tôi áp dụng `jina-reranker-v3` để chấm điểm lại mức độ liên quan giữa query và từng chunk (Cross-Encoder style). Điều này giúp khắc phục nhược điểm "lost in the middle" và đảm bảo 3 chunks quan trọng nhất được đưa vào prompt generator.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Sử dụng **Reranking** làm phương pháp tối ưu hóa thay vì Hybrid Search hay Query Transformation.

**Bối cảnh vấn đề:**
Khi đánh giá Baseline (Sprint 2) với Dense Retrieval đơn thuần, nhóm đạt điểm tuyệt đối về **Context Recall (5.0/5)** nhưng điểm **Completeness lại thấp (4.40/5)**, đặc biệt là thất bại nặng ở câu `q06` (điểm 1/5). Qua phân tích, chúng tôi nhận thấy vấn đề không phải là "không tìm thấy tài liệu", mà là "chọn sai đoạn". Bi-Encoder (Dense) đã tìm đúng file `sla_p1_2026.txt`, nhưng đoạn chứa thông tin về "auto-escalate 10 phút" lại có score thấp hơn đoạn mô tả "quy trình audit", dẫn đến việc thông tin quan trọng bị đẩy ra khỏi top-3 context đưa vào LLM.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Hybrid (BM25 + Dense) | Cải thiện recall cho các mã lỗi (ERR-403) | Không giải quyết được bài toán ưu tiên đúng đoạn trong cùng một tài liệu có semantic tương đồng. |
| Rerank (Cross-Encoder) | Chấm điểm sâu mối quan hệ (Query, Chunk), sửa lỗi selection | Tăng latency do phải gọi thêm API/load model nặng. |
| Query Transform | Xử lý alias (P1, VIP) | Phức tạp và có thể gây nhiễu nếu model transform sai ý định người dùng. |

**Phương án đã chọn và lý do:**
Nhóm chọn **Rerank** vì đây là giải pháp trực diện nhất cho Failure Mode quan trọng nhất của nhóm (Evidence Selection). Vì Recall đã đạt 5.0, việc thêm Hybrid Search là thừa thãi. Rerank giúp hệ thống "đọc kỹ" lại 10 kết quả đầu tiên để chọn lọc 3 kết quả thực sự trả lời đúng câu hỏi.

**Bằng chứng từ scorecard/tuning-log:**
Tại câu `q06`, sau khi bật Rerank, điểm Completeness tăng vọt từ **1/5 lên 5/5**. Cross-Encoder đã nhận diện chính xác đoạn text về Escalation Time và đẩy nó lên vị trí Top 1.

---

## 3. Kết quả grading questions (100–150 từ)

Dựa trên kết quả chạy thử nghiệm và scorecard variant:

**Ước tính điểm raw:** 88 / 98

**Câu tốt nhất:** ID: `q01`, `q03` — Lý do: Đây là các câu hỏi tra cứu thông tin trực tiếp (SLA và Access Cấp 3). Nhờ chiến lược chunking theo section, thông tin trả về rất cô đọng, model `gpt-5.4-mini` dễ dàng trích xuất fact và citation chính xác.

**Câu fail:** ID: `q10` — Root cause: **Generation (Hallucination)**. Câu hỏi hỏi về trường hợp hoàn tiền "khẩn cấp/VIP" vốn không có trong docs. Dù retriever lấy về policy refund (đúng file), nhưng model thay vì báo "không biết" hoàn toàn thì lại cố gắng diễn giải "tùy trường hợp" dẫn đến vi phạm tính Faithfulness (điểm 1/5).

**Câu gq07 (abstain):** Pipeline xử lý rất tốt. Với prompt "Answer only from retrieved context" và logic hậu xử lý `abstain_keywords`, model đã trả lời "Tôi không biết" khi tra cứu mã lỗi không tồn tại, danh sách sources trả về rỗng, đạt điểm groundedness tối đa.

---

## 4. A/B Comparison — Baseline vs Variant (150–200 từ)

**Biến đã thay đổi (chỉ 1 biến):** Bật `use_rerank=True` với model `jina-reranker-v3`.

| Metric | Baseline | Variant | Delta |
|--------|---------|---------|-------|
| Faithfulness | 4.50 | 4.50 | 0.00 |
| Relevance | 4.90 | 4.80 | -0.10 |
| Context Recall | 5.00 | 5.00 | 0.00 |
| Completeness | 4.40 | 4.70 | +0.30 |

**Kết luận:**
Variant **tốt hơn rõ rệt** về mặt Completeness. Việc tăng 0.3 điểm trung bình cho thấy hệ thống đã ổn định hơn trong việc chọn lựa evidence. Mặc dù Relevance giảm nhẹ 0.1 (do model đôi khi trích dẫn quá chi tiết dẫn đến câu trả lời dài hơn), nhưng sự đánh đổi này là xứng đáng để giải quyết triệt để các câu hỏi yêu cầu độ bao phủ thông tin cao như `q06`.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Lê Thành Long | Tech Lead, Review kiến trúc, Quản lý tiến độ, Eval Owner | All |
| Đỗ Xuân Bằng | Indexing Pipeline (Preprocessing, Semantic Chunking) | 1 |
| Đỗ Việt Anh | Baseline RAG, Grounded Prompt engineering, Abstention logic, Group Report | 2 |
| Trương Anh Long | Tuning (Rerank implementation) | 3 |
| Lã Thị Linh | Documentation, Tuning Log, Architecture Diagram | 4 |

**Điều nhóm làm tốt:**
- Phối hợp nhịp nhàng giữa các Sprint: Index của Bằng rất sạch giúp Việt Anh implement baseline nhanh chóng.
- Phân tích Failure Mode cực kỳ kỹ lưỡng: Việc Linh xây dựng checklist giúp nhóm xác định đúng Rerank là "vũ khí" cần thiết thay vì lãng phí thời gian vào Hybrid search.

**Điều nhóm làm chưa tốt:**
- Quản lý Quota API: Nhóm gặp sự cố với Gemini API giữa chừng, gây mất thời gian chuyển đổi sang OpenAI.
- Chưa xử lý triệt để lỗi Hallucination (q10) dù đã có prompt hướng dẫn.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

Nhóm sẽ tập trung vào **Answer Guardrails**. Thay vì chỉ dựa vào prompt, chúng tôi sẽ thêm một bước "Validation" (Self-Correction): cho model tự kiểm tra lại câu trả lời của chính mình so với context trước khi output. Mục tiêu là triệt tiêu điểm 1/5 về Faithfulness ở các câu hỏi ngoại lệ (q10), đảm bảo hệ thống tuyệt đối không bịa đặt thông tin khi tài liệu không đề cập tới.

---
