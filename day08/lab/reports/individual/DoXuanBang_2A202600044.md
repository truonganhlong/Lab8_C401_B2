# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** \***\*Đỗ Xuân Bằng\*\***  
**Vai trò trong nhóm:** Retrieval Owner
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này tôi chủ yếu đảm nhận Sprint 1 — xây dựng toàn bộ Indexing Pipeline trong file `index.py`. Cụ thể, tôi đã implement ba thành phần chính:

- **Preprocess (`preprocess_document`):** Viết logic parse metadata từ header của mỗi tài liệu (Source, Department, Effective Date, Access) bằng cách duyệt từng dòng đầu file, tách phần header ra khỏi nội dung chính và normalize text (loại bỏ dòng trống thừa, bỏ tiêu đề viết hoa).

- **Chunking (`chunk_document` + `_split_by_size`):** Thiết kế chiến lược chunking 2 tầng — ưu tiên chia theo section heading `=== ... ===` trước, nếu section quá dài (vượt 1600 ký tự ≈ 400 tokens) thì chia tiếp theo paragraph `\n\n`, fallback sang `\n` nếu không có paragraph rõ ràng.

- **Embedding + Vector Store:** Tích hợp Jina Embeddings v5 (`jina-embeddings-v5-text-small`) qua REST API để tạo vector, lưu trữ vào ChromaDB với cosine similarity. Mỗi chunk được gắn đầy đủ 5 metadata fields: `source`, `section`, `department`, `effective_date`, `access`.

Kết quả cuối: index thành công 5 tài liệu, tổng cộng 30 chunks, sẵn sàng cho Sprint 2.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Concept tôi hiểu rõ nhất sau lab này là **chiến lược chunking ảnh hưởng trực tiếp đến chất lượng retrieval**. Trước khi làm lab, tôi nghĩ chunking đơn giản chỉ là cắt text theo số ký tự cố định. Nhưng thực tế khi áp dụng cách cắt cứng, các chunk bị đứt giữa điều khoản — ví dụ một nửa nội dung "Điều 3: Điều kiện áp dụng" rơi vào chunk trước, nửa còn lại sang chunk sau. Khi retrieval gặp câu hỏi "Sản phẩm kỹ thuật số có được hoàn tiền không?", chunk trả về có thể chỉ chứa phần đầu của điều khoản mà thiếu danh sách ngoại lệ.

Giải pháp tôi học được là **ưu tiên ranh giới ngữ nghĩa tự nhiên** (section heading → paragraph → dòng) thay vì ranh giới số lượng. Cách chia theo `=== Section ===` trước, rồi fallback theo `\n\n` giúp mỗi chunk giữ được ngữ cảnh hoàn chỉnh của một chủ đề, từ đó cải thiện đáng kể context recall khi retrieve.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều ngạc nhiên là **metadata trong ChromaDB chỉ hỗ trợ kiểu primitive** (str, int, float, bool). Nếu truyền vào list hoặc dict thì ChromaDB sẽ raise error mà không có warning rõ ràng. Tôi phải thêm một bước ép kiểu `safe_meta` để convert mọi giá trị không phải primitive sang string trước khi upsert.

Ngoài ra, việc chọn embedding model cũng mất thời gian cân nhắc giữa chạy local (Sentence Transformers — miễn phí nhưng chậm) và gọi API (Jina v5 — nhanh, hỗ trợ task-specific adapter nhưng cần API key). Cuối cùng nhóm chọn Jina v5 vì tận dụng được task adapter `retrieval.passage` / `retrieval.query` cho hai pha index và search.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q03 — "Ai phải phê duyệt để cấp quyền Level 3?"

**Phân tích:**

Đây là câu hỏi ở mức **medium** thuộc category Access Control, yêu cầu retrieve đúng tài liệu `access_control_sop.txt` và trích xuất thông tin cụ thể về quy trình phê duyệt.

**Về phía Indexing:** Chiến lược chunking theo section heading hoạt động tốt ở đây. Nội dung về Level 3 nằm trọn trong section `=== Section 2: Phân cấp quyền truy cập ===`, bao gồm đầy đủ thông tin 3 cấp level (Level 1, 2, 3) với người phê duyệt tương ứng. Chunk không bị cắt ngang.

**Về phía Retrieval (dự kiến Sprint 2):** Với dense retrieval dùng Jina v5, câu hỏi "cấp quyền Level 3" có semantic similarity cao với nội dung chunk chứa "Level 3 — Elevated Access". Metadata `department: IT Security` cũng có thể hỗ trợ re-rank hoặc filter nếu cần.

**Rủi ro tiềm ẩn:** Nếu chunk size quá nhỏ, thông tin Level 3 có thể bị tách khỏi ngữ cảnh Level 1 và Level 2, khiến model thiếu bức tranh tổng thể để so sánh và trả lời chính xác. Chiến lược giữ nguyên 1 section = 1 chunk giúp tránh được rủi ro này.

**Expected answer:** "Level 3 (Elevated Access) cần phê duyệt từ Line Manager, IT Admin, và IT Security" — nằm hoàn toàn trong chunk, kỳ vọng baseline sẽ trả lời đúng ở Sprint 2.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

1. **Thử nghiệm Hybrid Retrieval (Sprint 3):** Kết quả chunking cho thấy một số tài liệu chứa mã lỗi, tên viết tắt (ví dụ "ERR-403-AUTH", "P1", "Level 3") mà dense embedding có thể không capture tốt. Tôi sẽ thử kết hợp BM25 sparse search với dense search để cải thiện recall cho các query chứa keyword/mã cụ thể.

2. **Thêm metadata `chunk_index` và `total_chunks`:** Giúp downstream (generation step) biết chunk đang đọc nằm ở vị trí nào trong tài liệu gốc, từ đó cải thiện grounded prompting bằng cách cung cấp context ngữ cảnh rộng hơn.

---

_Lưu file này với tên: `reports/individual/[ten_ban].md`_
_Ví dụ: `reports/individual/nguyen_van_a.md`_
