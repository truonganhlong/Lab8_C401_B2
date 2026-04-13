# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trương Anh Long 
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi đảm nhận vai trò Retrieval Owner, tập trung chủ yếu vào Sprint 3 — Tuning Tối Thiểu. Sau khi baseline dense retrieval từ Sprint 2 đã chạy ổn định, tôi phân tích output để chọn variant phù hợp nhất cho corpus. Tôi quyết định chọn **Rerank** thay vì Hybrid hay Query Transform, dựa trên quan sát rằng dense đã retrieve đúng document nhưng ranking trong top-K chưa chính xác — cụ thể câu hỏi về Level 3 trả về chunk bắt đầu từ Level 1. Tôi implement hàm `rerank()` sử dụng CrossEncoder `ms-marco-MiniLM-L-6-v2` từ thư viện `sentence-transformers`, tích hợp vào pipeline `rag_answer.py`, và chạy `compare_retrieval_strategies()` để so sánh kết quả với baseline. Công việc của tôi kết nối trực tiếp với phần indexing của Sprint 1 (chunk metadata) và phần eval của Sprint 4 (scorecard).

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Concept tôi hiểu rõ nhất sau lab là sự khác biệt giữa **BiEncoder và CrossEncoder**. Trước lab, tôi nghĩ embedding là đủ để tìm đúng câu trả lời — embed query, embed chunk, so cosine similarity là xong. Sau khi implement rerank, tôi mới hiểu tại sao BiEncoder có giới hạn: nó embed query và chunk **độc lập**, không thấy được mối quan hệ giữa hai bên. CrossEncoder nhận cả cặp `(query, chunk)` cùng lúc, hiểu được ngữ cảnh đầy đủ hơn nên chấm điểm chính xác hơn. Đánh đổi là CrossEncoder chậm hơn — không thể dùng để search toàn bộ corpus, chỉ dùng để rerank top-K sau khi BiEncoder đã lọc sơ. Đây chính là lý do pipeline cần funnel: retrieve rộng (top-20) → rerank (top-6) → select (top-3).

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất là quyết định chọn variant nào trong 3 phương thức: Hybrid, Rerank, hay Query Transform. Cả 3 đều có lý do hợp lệ với corpus chính sách nội bộ này. Điểm mấu chốt giúp tôi quyết định là nhìn vào retrieval score: câu Level 3 có score chỉ 0.559 — dense tìm đúng file nhưng chunk trả về bắt đầu từ Level 1, không phải Level 3. Đây là dấu hiệu rõ ràng của ranking noise, không phải missing keyword. Rerank với CrossEncoder giải quyết đúng vấn đề này — chấm lại từng cặp (query, chunk) để đẩy đúng đoạn lên top mà không cần thay đổi indexing. Ngoài ra, một khó khăn thực tế khác là thư viện `sentence-transformers` khá nặng khi cài đặt, làm chậm quá trình setup — nhóm đã cân nhắc chuyển sang **Jina Rerank** như một giải pháp nhẹ hơn, gọi qua API thay vì load model xuống máy.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** "Ai phải phê duyệt để cấp quyền Level 3?"

**Phân tích:**

Baseline dense trả lời đúng về mặt nội dung — "cần phê duyệt của Line Manager, IT Admin và IT Security" — nhưng context recall chỉ ở mức trung bình vì chunk được retrieve (score 0.559, thấp nhất trong 3 câu thành công) bắt đầu từ mô tả Level 1, phải đọc qua toàn bộ Level 1 và Level 2 mới đến thông tin Level 3. Lỗi nằm ở **retrieval** — cụ thể là ranking: dense không phân biệt được đoạn nào trong chunk liên quan trực tiếp đến query, chỉ match theo semantic similarity tổng thể của cả chunk.

Sau khi áp dụng rerank với CrossEncoder, chunk mô tả Level 3 được đẩy lên top vì cross-encoder chấm điểm từng cặp `(query, chunk)` và nhận ra đoạn Level 3 liên quan trực tiếp hơn. Answer sau rerank đầy đủ và chính xác hơn, context recall tăng lên rõ rệt. Đây là bằng chứng rõ nhất cho thấy rerank hiệu quả với corpus có cấu trúc phân cấp như policy document.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ implement đầy đủ 2 variant còn lại là Hybrid và Query Transform để so sánh kết quả trực tiếp với Rerank. Cụ thể, tôi sẽ implement RRF thật sự cho Hybrid thay vì fallback về dense, và viết `transform_query()` để expand alias như "P1" → "Priority 1", "Level 3" → "Level 3 Admin Access". Sau đó chạy `compare_retrieval_strategies()` với cả 3 variant trên cùng bộ test questions, đo điểm RAGAS cho từng cái để có bằng chứng số liệu rõ ràng — thay vì chỉ chọn theo lý thuyết như sprint này. Mục tiêu là hiểu rõ variant nào thật sự phù hợp nhất với corpus chính sách nội bộ này.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*