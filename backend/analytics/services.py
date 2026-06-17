"""
analytics.services — pure aggregation functions over StudentResult / QuestionResponse.

All functions accept Django model instances and return plain dicts.
No HTTP concerns here; called by views and tests directly.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Optional


# ---------------------------------------------------------------------------
# Bucket helpers
# ---------------------------------------------------------------------------

_BUCKETS = [
    ("0-20%",   0.0,   20.0),
    ("21-40%",  20.0,  40.0),
    ("41-60%",  40.0,  60.0),
    ("61-80%",  60.0,  80.0),
    ("81-100%", 80.0, 100.0),
]


def _score_pct(score, max_score) -> float:
    """Return score% (0–100). Guard max_score == 0 → 0.0."""
    if not max_score:
        return 0.0
    return float(score) / float(max_score) * 100.0


def _bucket_for(pct: float) -> str:
    """Return the bucket label for a score percentage."""
    # The first bucket includes 0%, last bucket includes 100%.
    # Boundaries: 0-20% → pct ≤ 20; 21-40% → 20 < pct ≤ 40; etc.
    for label, lo, hi in _BUCKETS:
        if label == "0-20%":
            if pct <= hi:
                return label
        elif label == "81-100%":
            if pct > 80.0:
                return label
        else:
            if lo < pct <= hi:
                return label
    return "81-100%"


# ---------------------------------------------------------------------------
# Option mapping helper
# ---------------------------------------------------------------------------

def _printed_to_original(printed_label: str, question_id: int, option_order: dict) -> str:
    """
    Map a PRINTED option label to the ORIGINAL (underlying) option label.

    option_order[str(question_id)] is a list of ORIGINAL labels in printed order.
    The printed label at printed index i corresponds to original label option_order[...][i].

    So: printed label at printed position i is the LETTER (chr(ord('A') + i)).
    We need to convert the printed label letter → its printed index → look up original.

    Parameters
    ----------
    printed_label : str
        A printed option label, e.g. 'A', 'B', 'C', 'D'.
    question_id   : int
        The underlying question id.
    option_order  : dict
        OmrSheet.option_order — {str(question_id): [original labels in printed order]}.

    Returns
    -------
    str — the original option label.
    """
    key = str(question_id)
    if key not in option_order:
        # No shuffle info — treat as identity
        return printed_label

    printed_order = option_order[key]   # list of original labels in printed order
    # The printed letter 'A' → printed index 0, 'B' → 1, etc.
    printed_index = ord(printed_label) - ord('A')
    if 0 <= printed_index < len(printed_order):
        return printed_order[printed_index]
    # Out of range — fall back
    return printed_label


# ---------------------------------------------------------------------------
# test_summary
# ---------------------------------------------------------------------------

def test_summary(test) -> dict:
    """
    Build the test-level analytics summary dict.

    Parameters
    ----------
    test : assessments.Test

    Returns
    -------
    dict matching the Phase-5 plan shape.
    """
    from results.models import StudentResult, QuestionResponse
    from assessments.models import Question

    results = list(
        StudentResult.objects.filter(test=test)
        .select_related("student", "omr_sheet")
        .prefetch_related("responses")
    )

    n_students = len(results)
    graded = len(results)          # all persisted StudentResults are considered graded
    needs_review_count = sum(1 for r in results if r.needs_review)

    # ---- Scalar stats ----
    if not results:
        return {
            "test": _test_block(test),
            "n_students": 0,
            "graded": 0,
            "needs_review_count": 0,
            "average": None,
            "median": None,
            "max": None,
            "min": None,
            "max_score": None,
            "distribution": [{"bucket": b, "count": 0} for b, *_ in _BUCKETS],
            "toppers": [],
            "hardest_questions": [],
            "option_distribution": [],
        }

    scores = [float(r.score) for r in results]
    max_scores = [float(r.max_score) for r in results]

    average = sum(scores) / len(scores)
    sorted_scores = sorted(scores)
    n = len(sorted_scores)
    if n % 2 == 1:
        median = sorted_scores[n // 2]
    else:
        median = (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2.0

    max_val = max(scores)
    min_val = min(scores)
    max_score_val = max(max_scores) if max_scores else 0.0

    # ---- Distribution ----
    bucket_counts = {b: 0 for b, *_ in _BUCKETS}
    for r in results:
        pct = _score_pct(r.score, r.max_score)
        label = _bucket_for(pct)
        bucket_counts[label] += 1
    distribution = [
        {"bucket": b, "count": bucket_counts[b]}
        for b, *_ in _BUCKETS
    ]

    # ---- Toppers (top 5 by score desc) ----
    sorted_results = sorted(results, key=lambda r: float(r.score), reverse=True)
    toppers = []
    for r in sorted_results[:5]:
        student = r.student
        if student:
            roll = student.roll_number
            name = student.full_name or ""
        else:
            roll = ""
            name = ""
        toppers.append({
            "student": {"roll": roll, "name": name},
            "score": float(r.score),
            "max_score": float(r.max_score),
        })

    # ---- hardest_questions ----
    # Group QuestionResponses by underlying question_id;
    # count wrong answers per question (is_correct=False, not blank).
    # n = total responses for that question across all students.
    q_stats: dict[int, dict] = {}   # question_id → {wrong, n}

    for r in results:
        for resp in r.responses.all():
            q_id = resp.question_id
            if q_id is None:
                # Fallback: try resolving via question_order
                if r.omr_sheet and r.omr_sheet.question_order:
                    try:
                        q_id = r.omr_sheet.question_order[resp.q_pos]
                    except (IndexError, TypeError):
                        continue
                else:
                    continue

            if q_id not in q_stats:
                q_stats[q_id] = {"wrong": 0, "n": 0}
            q_stats[q_id]["n"] += 1
            if not resp.is_correct and resp.marked_options:
                # Non-blank wrong answer
                q_stats[q_id]["wrong"] += 1

    hardest_questions = []
    if q_stats:
        q_objs = {
            q.id: q
            for q in Question.objects.filter(id__in=q_stats.keys())
        }
        for q_id, stat in q_stats.items():
            q_obj = q_objs.get(q_id)
            wrong_rate = stat["wrong"] / stat["n"] if stat["n"] else 0.0
            hardest_questions.append({
                "question_id": q_id,
                "order_index": q_obj.order_index if q_obj else 0,
                "text": q_obj.text if q_obj else "",
                "wrong_rate": wrong_rate,
                "n": stat["n"],
            })
        hardest_questions.sort(key=lambda x: x["wrong_rate"], reverse=True)

    # ---- option_distribution ----
    # Per question: map each printed marked label → original via option_order;
    # count per original label across all student responses.
    opt_counts: dict[int, dict[str, int]] = {}  # q_id → {orig_label: count}

    for r in results:
        omr_sheet = r.omr_sheet
        option_order = omr_sheet.option_order if omr_sheet else {}

        for resp in r.responses.all():
            q_id = resp.question_id
            if q_id is None:
                if omr_sheet and omr_sheet.question_order:
                    try:
                        q_id = omr_sheet.question_order[resp.q_pos]
                    except (IndexError, TypeError):
                        continue
                else:
                    continue

            if q_id not in opt_counts:
                opt_counts[q_id] = defaultdict(int)

            for printed_label in resp.marked_options:
                original_label = _printed_to_original(printed_label, q_id, option_order)
                opt_counts[q_id][original_label] += 1

    option_distribution = []
    if opt_counts:
        from assessments.models import Option
        q_objs_od = {
            q.id: q
            for q in Question.objects.filter(id__in=opt_counts.keys())
            .prefetch_related("options")
        }
        for q_id, label_counts in opt_counts.items():
            q_obj = q_objs_od.get(q_id)
            if q_obj is None:
                continue
            # All original labels for this question
            all_options = list(q_obj.options.order_by("label"))
            correct_labels = [o.label for o in all_options if o.is_correct]
            options_list = [
                {"label": o.label, "count": label_counts.get(o.label, 0)}
                for o in all_options
            ]
            option_distribution.append({
                "question_id": q_id,
                "text": q_obj.text,
                "options": options_list,
                "correct": correct_labels,
            })
        # Sort by question order_index for stable output
        option_distribution.sort(
            key=lambda e: q_objs_od[e["question_id"]].order_index
            if e["question_id"] in q_objs_od else 0
        )

    return {
        "test": _test_block(test),
        "n_students": n_students,
        "graded": graded,
        "needs_review_count": needs_review_count,
        "average": average,
        "median": median,
        "max": max_val,
        "min": min_val,
        "max_score": max_score_val,
        "distribution": distribution,
        "toppers": toppers,
        "hardest_questions": hardest_questions,
        "option_distribution": option_distribution,
    }


def _test_block(test) -> dict:
    return {
        "id": test.id,
        "title": test.title,
        "subject": getattr(test, "subject", ""),
        "attempt_number": test.attempt_number,
    }
