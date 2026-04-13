"""
run_grading.py — Chạy pipeline với grading_questions và xuất log
=================================================================
Chạy: python run_grading.py

Input:  test.json (10 grading questions)
Output: logs/grading_run.json
"""

import json
from datetime import datetime
from pathlib import Path
from rag_answer import rag_answer

# === Đường dẫn ===
GRADING_QUESTIONS_PATH = Path(__file__).parent / "test.json"
LOG_DIR = Path(__file__).parent / "logs"
LOG_PATH = LOG_DIR / "grading_run.json"

# === Config — dùng cấu hình TỐT NHẤT của nhóm ===
BEST_CONFIG = {
    "retrieval_mode": "dense",      # hoặc "hybrid" nếu đã implement
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": True,             # bật rerank nếu đã implement
}


def main():
    print("=" * 60)
    print("Chạy Grading Questions")
    print("=" * 60)

    # Load questions
    with open(GRADING_QUESTIONS_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)
    print(f"Loaded {len(questions)} grading questions\n")

    # Chạy pipeline từng câu
    log = []
    for i, q in enumerate(questions, 1):
        qid = q["id"]
        question = q["question"]
        points = q.get("points", "?")
        print(f"[{i}/{len(questions)}] {qid} ({points}đ): {question[:60]}...")

        try:
            result = rag_answer(
                query=question,
                retrieval_mode=BEST_CONFIG["retrieval_mode"],
                top_k_search=BEST_CONFIG["top_k_search"],
                top_k_select=BEST_CONFIG["top_k_select"],
                use_rerank=BEST_CONFIG["use_rerank"],
                verbose=False,
            )
            entry = {
                "id": qid,
                "question": question,
                "answer": result["answer"],
                "sources": result["sources"],
                "chunks_retrieved": len(result["chunks_used"]),
                "retrieval_mode": result["config"]["retrieval_mode"],
                "use_rerank": result["config"]["use_rerank"],
                "timestamp": datetime.now().isoformat(),
            }
            print(f"  → OK | Sources: {result['sources']}")
            print(f"  → Answer: {result['answer'][:120]}...")

        except Exception as e:
            entry = {
                "id": qid,
                "question": question,
                "answer": f"PIPELINE_ERROR: {e}",
                "sources": [],
                "chunks_retrieved": 0,
                "retrieval_mode": BEST_CONFIG["retrieval_mode"],
                "use_rerank": BEST_CONFIG["use_rerank"],
                "timestamp": datetime.now().isoformat(),
            }
            print(f"  → ERROR: {e}")

        log.append(entry)
        print()

    # Lưu log
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print(f"Hoàn thành! Log đã lưu tại: {LOG_PATH}")
    print(f"Tổng: {len(log)} câu | Thành công: {sum(1 for e in log if not e['answer'].startswith('PIPELINE_ERROR'))}")
    print("=" * 60)


if __name__ == "__main__":
    main()
