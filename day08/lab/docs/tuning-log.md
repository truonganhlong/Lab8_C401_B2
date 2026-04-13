# Tuning Log — RAG Pipeline (Day 08 Lab)

> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 13/04/2026  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens (~1600 ký tự)
overlap = không (paragraph-based chunking)
top_k_search = 10
top_k_select = 3
use_rerank = False
embedding = jina-embeddings-v5-text-small
llm_model = gpt-5.4-mini
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.50/5 |
| Answer Relevance | 4.20/5 |
| Context Recall | 5.00/5 |
| Completeness | 3.10/5 |

**Câu hỏi yếu nhất (điểm thấp):**
- **q06** (Escalation P1) — Completeness = 1/5. Pipeline trả lời về cấp quyền tạm thời (section 4 của access_control_sop) thay vì quy trình escalation thực sự (auto-escalate lên Senior Engineer sau 10 phút). Dense retrieval lấy chunk sai section.
- **q09** (ERR-403-AUTH) — Faithfulness = 1, Relevance = 1. Đây là câu abstain (không có dữ liệu), pipeline trả lời "Tôi không biết" ngắn gọn nhưng LLM-judge cho điểm thấp vì thiếu explanation.
- **q10** (VIP hoàn tiền khẩn cấp) — Relevance = 1/5. Pipeline đúng khi abstain (không có chính sách VIP đặc biệt), nhưng LLM-judge đánh giá thấp vì answer không trả lời trực tiếp câu hỏi.
- **q04** (Sản phẩm kỹ thuật số) — Completeness = 2/5. Expected answer là "Không, ngoại lệ không hoàn tiền" nhưng pipeline thêm điều kiện "trừ khi có lỗi do nhà sản xuất" — không hoàn toàn sai nhưng chưa khớp hoàn toàn.

**Giả thuyết nguyên nhân (Error Tree):**
- [x] Retrieval: Dense bỏ lỡ exact keyword / lấy chunk sai section (q06)
- [x] Generation: Abstain answer quá ngắn, thiếu explanation (q09)
- [ ] Indexing: Chunking cắt giữa điều khoản → Đã giải quyết bằng section-based chunking
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 13/04/2026  
**Biến thay đổi:** `use_rerank = True` (bật cross-encoder ms-marco-MiniLM-L-6-v2)  
**Lý do chọn biến này:**
> Baseline cho thấy q06 lấy chunk sai section — cross-encoder rerank sẽ đánh giá lại từng cặp (query, chunk) và ưu tiên chunk thực sự trả lời câu hỏi. Dự kiến sẽ cải thiện completeness ở các câu hỏi cần chunk chính xác.

**Config thay đổi:**
```
retrieval_mode = "hybrid"  # fallback về dense (BM25 chưa implement đầy đủ)
use_rerank = True          # BIẾN THAY ĐỔI DUY NHẤT
# Các tham số khác giữ nguyên
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.50/5 | 4.40/5 | −0.10 |
| Answer Relevance | 4.20/5 | 4.20/5 | 0.00 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 3.10/5 | 3.50/5 | **+0.40** |

### Per-Question Comparison

| Câu | Baseline (F/R/Rc/C) | Variant (F/R/Rc/C) | Kết quả |
|-----|---------------------|--------------------| --------|
| q01 | 5/5/5/3 | 5/5/5/**5** | **Variant tốt hơn** |
| q02 | 5/5/5/5 | 5/5/5/5 | Hòa |
| q03 | 5/5/5/5 | **4**/5/5/5 | Baseline nhỉnh hơn |
| q04 | 4/5/5/2 | 4/5/5/2 | Hòa |
| q05 | 5/5/5/5 | 5/5/5/5 | Hòa |
| q06 | 5/5/5/**1** | 5/5/5/**4** | **Variant tốt hơn rõ rệt** |
| q07 | 5/5/5/2 | 5/5/5/2 | Hòa |
| q08 | 5/5/5/5 | 5/5/5/**4** | Baseline nhỉnh hơn |
| q09 | 1/1/-/1 | 1/1/-/1 | Hòa (abstain) |
| q10 | 5/1/5/2 | 5/1/5/2 | Hòa |

**Nhận xét:**
> - **q06 cải thiện nhiều nhất** (Completeness: 1 → 4): Rerank giúp chọn đúng chunk về escalation process thay vì chunk về cấp quyền tạm thời. Cross-encoder hiểu được "escalation" liên quan đến quy trình tự động hơn là cấp quyền thủ công.
> - **q01 cải thiện** (Completeness: 3 → 5): Rerank chọn chunk chứa đầy đủ thông tin SLA bao gồm cả response time (15 phút) và resolution time (4 giờ).
> - **q03 giảm nhẹ** (Faithfulness: 5 → 4): Đây có thể do sự khác biệt nhỏ trong cách rerank sắp xếp chunks, không đáng kể.
> - **q08 giảm nhẹ** (Completeness: 5 → 4): Variant answer ngắn hơn baseline, thiếu 1 chi tiết phụ.

**Kết luận:**
> Variant (rerank) **tốt hơn baseline** ở metric quan trọng nhất: **Completeness (+0.40)**. Faithfulness giảm không đáng kể (−0.10), Relevance và Context Recall giữ nguyên. Rerank đặc biệt hiệu quả khi dense search trả về nhiều chunk tương tự — cross-encoder giúp chọn chunk chính xác nhất, cải thiện chất lượng generation.

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Completeness thấp (3.10/5) — pipeline trả lời đúng nhưng thiếu chi tiết. Root cause: dense retrieval chọn chunk "gần đúng" thay vì chunk chứa đúng thông tin cần trả lời.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Rerank (cross-encoder) có tác động lớn nhất đến Completeness (+0.40). Chunking strategy (section-based) là nền tảng — Context Recall đạt 5.00/5 chứng tỏ indexing pipeline hoạt động tốt.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Implement BM25 sparse search thực sự để hybrid kết hợp dense + sparse qua RRF. Kỳ vọng cải thiện thêm cho các câu chứa mã lỗi (ERR-403), tên riêng (P1), và alias (Approval Matrix). Ngoài ra, cải thiện grounded prompt để abstain answer có explanation rõ ràng hơn (hiện tại "Tôi không biết" quá ngắn).
