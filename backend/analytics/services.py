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


# ---------------------------------------------------------------------------
# student_detail
# ---------------------------------------------------------------------------

def student_detail(student_result) -> dict:
    """
    Build the per-student analytics detail dict for a single StudentResult.

    Parameters
    ----------
    student_result : results.StudentResult

    Returns
    -------
    dict with keys:
        score, max_score, pct, correct, wrong, blank,
        per_question, topic_accuracy
    """
    score = float(student_result.score)
    max_score = float(student_result.max_score)
    pct = _score_pct(score, max_score)

    # Fetch all responses ordered by q_pos
    responses = list(
        student_result.responses
        .select_related("question")
        .order_by("q_pos", "id")
    )

    # Build per_question list
    per_question = []
    for resp in responses:
        q = resp.question
        if q is not None:
            order_index = q.order_index
            text = q.text
        else:
            # Fallback: use q_pos as order_index, empty text
            order_index = resp.q_pos
            text = ""
        per_question.append({
            "order_index": order_index,
            "text": text,
            "is_correct": resp.is_correct,
            "flagged": resp.flagged,
            "marked_options": list(resp.marked_options),
        })

    # Sort by order_index for stable output
    per_question.sort(key=lambda e: e["order_index"])

    # Build topic_accuracy: group by question.topic
    topic_stats: dict[str, dict] = {}  # topic → {correct: int, total: int}
    for resp in responses:
        q = resp.question
        if q is not None:
            topic = q.topic if q.topic else "Untagged"
        else:
            topic = "Untagged"
        if topic not in topic_stats:
            topic_stats[topic] = {"correct": 0, "total": 0}
        topic_stats[topic]["total"] += 1
        if resp.is_correct:
            topic_stats[topic]["correct"] += 1

    topic_accuracy = {
        topic: {
            "correct": stat["correct"],
            "total": stat["total"],
            "accuracy": stat["correct"] / stat["total"] if stat["total"] else 0.0,
        }
        for topic, stat in topic_stats.items()
    }

    return {
        "score": score,
        "max_score": max_score,
        "pct": pct,
        "correct": student_result.correct_count,
        "wrong": student_result.wrong_count,
        "blank": student_result.blank_count,
        "per_question": per_question,
        "topic_accuracy": topic_accuracy,
    }


# ---------------------------------------------------------------------------
# improvement (retest chain)
# ---------------------------------------------------------------------------

def _walk_to_root(test):
    """Walk parent_test links to the root test. Return the root."""
    visited = set()
    current = test
    while current.parent_test_id is not None:
        if current.id in visited:
            # Cycle guard
            break
        visited.add(current.id)
        current = current.parent_test
    return current


def _collect_chain(root):
    """
    Collect the full retest chain starting from root, ordered by attempt_number.

    Strategy: BFS/DFS following `retests` reverse relation.
    `Test.retests` is the related_name for `parent_test`.
    """
    chain = []
    stack = [root]
    while stack:
        node = stack.pop()
        chain.append(node)
        # Expand children (retests)
        children = list(node.retests.all())
        stack.extend(children)

    chain.sort(key=lambda t: t.attempt_number)
    return chain


def improvement(test) -> dict:
    """
    Build the retest-chain improvement dict.

    Resolves the full chain (root + all retests), then for each student
    (matched by `student.roll_number`) builds their attempt history with
    delta_vs_prev.

    Parameters
    ----------
    test : assessments.Test

    Returns
    -------
    dict with keys:
        chain      : [{test_id, attempt_number, title}]
        students   : {roll_number: [{attempt_number, test_id, score, max_score, pct, delta_vs_prev}]}
        class_average : {attempt_number: avg_pct}
        trend      : "improving" | "declining" | "stable" | "insufficient_data"
    """
    from results.models import StudentResult

    root = _walk_to_root(test)
    chain = _collect_chain(root)

    chain_info = [
        {"test_id": t.id, "attempt_number": t.attempt_number, "title": t.title}
        for t in chain
    ]

    # Gather StudentResults for all tests in chain
    test_ids = [t.id for t in chain]
    results = list(
        StudentResult.objects
        .filter(test_id__in=test_ids)
        .select_related("student", "test")
    )

    # Build attempt_number map: test_id → attempt_number
    attempt_num_by_test = {t.id: t.attempt_number for t in chain}

    # Group by (roll_number, attempt_number) — one result per student per attempt
    # Key: roll_number (or str(student_id) if no roll)
    from collections import defaultdict
    by_roll: dict[str, dict[int, dict]] = defaultdict(dict)

    for res in results:
        if res.student and res.student.roll_number:
            roll = res.student.roll_number
        elif res.student_id:
            roll = f"student_{res.student_id}"
        else:
            roll = f"result_{res.id}"

        attempt_num = attempt_num_by_test.get(res.test_id)
        if attempt_num is None:
            continue

        pct = _score_pct(res.score, res.max_score)
        by_roll[roll][attempt_num] = {
            "attempt_number": attempt_num,
            "test_id": res.test_id,
            "score": float(res.score),
            "max_score": float(res.max_score),
            "pct": pct,
        }

    # Build ordered attempt lists with delta_vs_prev
    all_attempt_numbers = sorted({t.attempt_number for t in chain})
    students_out: dict[str, list] = {}
    for roll, attempts_by_num in by_roll.items():
        ordered = []
        prev_pct = None
        for attempt_num in all_attempt_numbers:
            if attempt_num not in attempts_by_num:
                continue  # student absent in this attempt — skip gracefully
            entry = dict(attempts_by_num[attempt_num])
            if prev_pct is None:
                entry["delta_vs_prev"] = None
            else:
                entry["delta_vs_prev"] = entry["pct"] - prev_pct
            prev_pct = entry["pct"]
            ordered.append(entry)
        students_out[roll] = ordered

    # Class average per attempt_number
    class_average: dict[int, float] = {}
    for attempt_num in all_attempt_numbers:
        pcts = []
        for attempts_by_num in by_roll.values():
            if attempt_num in attempts_by_num:
                pcts.append(attempts_by_num[attempt_num]["pct"])
        if pcts:
            class_average[attempt_num] = sum(pcts) / len(pcts)

    # Trend: compare first and last class averages that have data
    avgs_ordered = [class_average[n] for n in all_attempt_numbers if n in class_average]
    if len(avgs_ordered) < 2:
        trend = "insufficient_data"
    else:
        delta = avgs_ordered[-1] - avgs_ordered[0]
        if delta > 1.0:
            trend = "improving"
        elif delta < -1.0:
            trend = "declining"
        else:
            trend = "stable"

    return {
        "chain": chain_info,
        "students": students_out,
        "class_average": class_average,
        "trend": trend,
    }
