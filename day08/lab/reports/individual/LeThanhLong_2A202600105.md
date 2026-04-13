# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Lê Thanh Long  
**Vai trò trong nhóm:** Tech Lead  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi giữ vai trò **Tech Lead**, nên phần việc chính của tôi là chốt hướng kỹ thuật chung cho cả pipeline thay vì chỉ làm một module riêng lẻ. Tôi cùng nhóm thống nhất kiến trúc từ `Raw Docs -> Index -> ChromaDB -> Dense Retrieval -> Optional Rerank -> Grounded Answer`, đồng thời chia việc theo sprint để tránh bị chồng chéo giữa indexing, retrieval, documentation và evaluation. Về mặt quyết định, tôi ưu tiên baseline trước với dense retrieval, `chunk_size=400`, `top_k_search=10`, `top_k_select=3`, model `gpt-5.4-mini`, rồi mới tuning sau khi có scorecard đầu tiên. Khi baseline cho thấy `Context Recall = 5.0/5` nhưng completeness còn yếu, tôi chốt hướng thử **rerank** làm biến duy nhất cho variant.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu rõ hơn rằng làm Tech Lead trong một bài toán RAG không phải là chọn càng nhiều kỹ thuật càng tốt, mà là **xác định đúng tầng đang gây lỗi**. Trước đây tôi khá dễ bị cuốn vào suy nghĩ “cứ thêm hybrid retrieval hay prompt phức tạp thì hệ thống sẽ mạnh hơn”. Nhưng khi nhìn vào kết quả thực tế, tôi thấy baseline đã đạt recall rất cao, nghĩa là bài toán không nằm ở chuyện không tìm thấy tài liệu. Vấn đề nằm ở chỗ evidence nào được đẩy vào prompt và model có giữ đúng kỷ luật grounded khi trả lời hay không. Điều này làm tôi hiểu sâu hơn về giá trị của A/B rule: chỉ đổi một biến mỗi lần để biết chính xác điều gì tạo ra cải thiện.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất với tôi không phải là viết thêm code, mà là **kiềm chế việc đổi quá nhiều thứ cùng lúc**. Với một corpus nhỏ và chỉ có 10 câu hỏi eval, việc thay đồng thời chunking, top-k, retrieval strategy và prompt rất dễ tạo cảm giác “có tiến bộ”, nhưng lại làm mất khả năng giải thích kết quả. Đây là chỗ tôi phải giữ vai trò điều phối: baseline chưa đủ tốt thì phải chấp nhận điều đó, đọc kỹ failure mode rồi mới quyết định bước tiếp theo. Điều làm tôi ngạc nhiên là chỉ một thay đổi khá nhỏ, bật `jina-reranker-v3`, đã cải thiện rõ `Completeness` từ `4.40` lên `4.70`. Nhưng đồng thời, một vài câu vẫn không tốt hơn.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?

**Phân tích:**

Tôi chọn `q02` vì đây không phải là một lỗi “sai hoàn toàn”, mà là một case rất điển hình cho việc **đúng ý nhưng chưa chắc đúng chuẩn**. Ở baseline, câu trả lời đạt `Completeness = 5/5` nhưng `Faithfulness = 4/5`. Sang variant bật rerank, `Faithfulness` tăng lên `5/5` nhưng `Completeness` lại giảm xuống `4/5`. Cả hai phiên bản đều có `Context Recall = 5/5`, nên có thể khẳng định lỗi không nằm ở indexing hay retrieval.

Điểm đáng chú ý là model đang xử lý một fact tưởng đơn giản nhưng có nuance về cách diễn đạt: baseline thiên về câu trả lời gần với đáp án mong đợi là `7 ngày làm việc`, trong khi variant lại bám sát một phrasing ngắn hơn là `7 ngày`. Nhìn từ góc độ Tech Lead, đây là tín hiệu quan trọng: khi hệ thống trả lời policy question chứa mốc thời gian hoặc điều kiện, chỉ “gần đúng” là chưa đủ. Vì vậy, tôi xem `q02` là bằng chứng rằng sau khi retrieval đã ổn, nhóm cần tăng kiểm soát ở bước answer synthesis.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ ưu tiên một lớp **answer guardrail cho factual policy questions**. Với các câu có mốc thời gian hoặc điều kiện, prompt nên ép model giữ nguyên qualifier từ context, ví dụ `ngày` hay `ngày làm việc`. Tôi cũng muốn thử một bước hậu kiểm đơn giản cho các fact dạng số, để nếu answer làm rơi mất qualifier quan trọng thì hệ thống sẽ sinh lại thay vì trả ra ngay.

---
