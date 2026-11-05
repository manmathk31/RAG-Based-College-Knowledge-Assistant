"""Retrieval evaluation benchmark measuring Recall@K, Precision@K, and MRR for Dense vs Hybrid."""

import pytest

from app.retrieval.models import RetrievalCandidate
from app.retrieval.rrf import reciprocal_rank_fusion

# ------------------------------------------------------------------------------
# Synthetic Benchmark Dataset
# ------------------------------------------------------------------------------

BENCHMARK_CHUNKS = {
    "c_att": "Students must maintain a minimum of 75% attendance in lectures and practical sessions to be eligible to appear in end-semester examinations.",
    "c_ref": "Tuition refund policy: 100% refund if withdrawn within 15 days of admission, 50% within 30 days, and 0% thereafter.",
    "c_cs102": "Course CS102 Data Structures and Algorithms. Prerequisite: CS101 Introduction to Programming with a minimum grade C.",
    "c_app": "Grade re-evaluation requests must be submitted to the Controller of Examinations within 10 days of result announcement.",
    "c_lib": "Central Library hours are Monday to Friday 8:00 AM to 8:00 PM. Overdue book fines are $1 per day per volume.",
    "c_hostel": "Campus hostel curfew is 10:00 PM for all undergraduate resident students.",
    "c_sports": "Annual athletic sports meet is held in February with inter-department competitions.",
    "c_med": "Campus health medical clinic provides first aid and outpatient care between 9:00 AM and 5:00 PM.",
}

# 5 Synthetic Student Questions with Ground Truth relevant chunk ID
EVALUATION_QUERIES = [
    {
        "query": "What is the minimum attendance requirement for semester exams?",
        "ground_truth_id": "c_att",
        # Simulated dense rank list (semantic overlap)
        "dense_ranking": ["c_att", "c_app", "c_hostel"],
        # Simulated keyword rank list (exact token match on attendance, semester, exams)
        "keyword_ranking": ["c_att", "c_sports", "c_ref"],
    },
    {
        "query": "What are the course codes and prerequisites for CS102 Data Structures?",
        "ground_truth_id": "c_cs102",
        # Dense might place generic course info higher
        "dense_ranking": ["c_att", "c_cs102", "c_lib"],
        # Keyword search strongly matches exact code "CS102" at rank 1
        "keyword_ranking": ["c_cs102", "c_hostel", "c_app"],
    },
    {
        "query": "How much tuition fee is refunded if I withdraw within 15 days?",
        "ground_truth_id": "c_ref",
        "dense_ranking": ["c_ref", "c_att", "c_lib"],
        "keyword_ranking": ["c_ref", "c_cs102", "c_med"],
    },
    {
        "query": "How many days do I have to submit a grade re-evaluation request?",
        "ground_truth_id": "c_app",
        "dense_ranking": ["c_att", "c_app", "c_cs102"],
        "keyword_ranking": ["c_app", "c_ref", "c_sports"],
    },
    {
        "query": "What are the central library hours and overdue book fines?",
        "ground_truth_id": "c_lib",
        "dense_ranking": ["c_hostel", "c_lib", "c_att"],
        "keyword_ranking": ["c_lib", "c_med", "c_cs102"],
    },
]


def create_candidate_list(chunk_ids, source):
    return [
        RetrievalCandidate(
            chunk_id=cid,
            document_id="doc-eval",
            document_name="Handbook.pdf",
            document_version=1,
            content=BENCHMARK_CHUNKS[cid],
            rank=idx + 1,
            score=1.0 - (idx * 0.1),
            retrieval_source=source,
        )
        for idx, cid in enumerate(chunk_ids)
    ]


def compute_metrics(rankings, k=3):
    """Compute Recall@K, Precision@K, and Mean Reciprocal Rank (MRR)."""
    recalls = []
    precisions = []
    reciprocal_ranks = []

    for item in rankings:
        top_k_ids = [c.chunk_id for c in item["results"][:k]]
        gt = item["ground_truth_id"]

        if gt in top_k_ids:
            recalls.append(1.0)
            precisions.append(1.0 / k)
            rank = top_k_ids.index(gt) + 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            recalls.append(0.0)
            precisions.append(0.0)
            reciprocal_ranks.append(0.0)

    avg_recall = sum(recalls) / len(recalls)
    avg_precision = sum(precisions) / len(precisions)
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)

    return {
        "recall_at_k": round(avg_recall, 4),
        "precision_at_k": round(avg_precision, 4),
        "mrr": round(mrr, 4),
    }


def test_retrieval_evaluation_benchmark():
    """Execute comparative benchmark evaluating Dense-only vs Hybrid (RRF) retrieval."""
    dense_eval_runs = []
    hybrid_eval_runs = []

    for item in EVALUATION_QUERIES:
        gt = item["ground_truth_id"]
        dense_cands = create_candidate_list(item["dense_ranking"], source="dense")
        keyword_cands = create_candidate_list(item["keyword_ranking"], source="keyword")

        # Dense-only
        dense_eval_runs.append({"ground_truth_id": gt, "results": dense_cands})

        # Hybrid with RRF
        hybrid_fused = reciprocal_rank_fusion(
            dense_candidates=dense_cands,
            keyword_candidates=keyword_cands,
            k=60,
            top_k=3,
        )
        hybrid_eval_runs.append({"ground_truth_id": gt, "results": hybrid_fused})

    dense_metrics = compute_metrics(dense_eval_runs, k=3)
    hybrid_metrics = compute_metrics(hybrid_eval_runs, k=3)

    print("\n" + "=" * 50)
    print("RETRIEVAL EVALUATION BENCHMARK RESULTS (K=3)")
    print("=" * 50)
    print(f"Dense-Only Retrieval : Recall@3={dense_metrics['recall_at_k']:.2f}, MRR={dense_metrics['mrr']:.2f}")
    print(f"Hybrid (Dense + FTS) : Recall@3={hybrid_metrics['recall_at_k']:.2f}, MRR={hybrid_metrics['mrr']:.2f}")
    print("=" * 50)

    # Invariants
    assert hybrid_metrics["recall_at_k"] >= dense_metrics["recall_at_k"]
    assert hybrid_metrics["mrr"] >= dense_metrics["mrr"]
    assert hybrid_metrics["recall_at_k"] == 1.0  # All ground truth items retrieved in top 3
    assert hybrid_metrics["mrr"] == 1.0  # Hybrid fusion placed all ground truth items at rank 1

