"""
omr.scan.grade — Sheet grading from aggregated bubble reads.

grade_sheet(omr_sheet, aggregated_reads) applies the test's MarkingScheme to
each question and returns a structured grading result.

aggregated_reads format:
    {q_pos (int): set/list of marked printed labels}

The answer_key on OmrSheet is:
    {str(q_pos): [correct printed labels]}
"""

from __future__ import annotations

from decimal import Decimal


def grade_sheet(omr_sheet, aggregated_reads: dict) -> dict:
    """
    Grade a completed OMR sheet against the stored answer key.

    Parameters
    ----------
    omr_sheet : OmrSheet
        The OmrSheet model instance.  Must have .answer_key (dict) and
        .test.marking_scheme available.
    aggregated_reads : dict
        {q_pos (int): set/list of marked printed labels}
        Questions not present are treated as blank.

    Returns
    -------
    dict with keys:
        score          : Decimal — total score (floored at 0)
        max_score      : Decimal — n_questions * marks_per_correct
        correct_count  : int
        wrong_count    : int
        blank_count    : int
        per_question   : list[dict] — one entry per q_pos, each with:
                           {q_pos, marked (list), is_correct (bool), flagged (bool)}
    """
    answer_key = omr_sheet.answer_key  # {str(q_pos): [correct printed labels]}

    # Fetch the marking scheme
    try:
        ms = omr_sheet.test.marking_scheme
        marks_per_correct = Decimal(str(ms.marks_per_correct))
        negative_marks = Decimal(str(ms.negative_marks_per_wrong))
        partial_marking = bool(ms.partial_marking)
        multiple_correct_allowed = bool(ms.multiple_correct_allowed)
    except Exception:
        # No marking scheme — fall back to 1 mark per correct, no negatives
        marks_per_correct = Decimal("1")
        negative_marks = Decimal("0")
        partial_marking = False
        multiple_correct_allowed = False

    n_questions = len(answer_key)
    max_score = Decimal(n_questions) * marks_per_correct

    score = Decimal("0")
    correct_count = 0
    wrong_count = 0
    blank_count = 0
    per_question = []

    for q_pos_str, correct_labels in answer_key.items():
        q_pos = int(q_pos_str)
        correct = set(correct_labels)
        marked_raw = aggregated_reads.get(q_pos, [])
        marked = set(marked_raw)

        is_correct = False
        flagged = False

        if not marked:
            # Blank — no mark, no penalty
            blank_count += 1
            question_score = Decimal("0")
        elif marked == correct:
            # Exact match → full marks
            is_correct = True
            correct_count += 1
            question_score = marks_per_correct
        elif partial_marking and multiple_correct_allowed and correct:
            # Proportional credit: (|marked∩correct| - |marked-correct|) / |correct| * marks_per_correct
            intersection = len(marked & correct)
            overmarks = len(marked - correct)
            raw = (Decimal(intersection) - Decimal(overmarks)) / Decimal(len(correct)) * marks_per_correct
            question_score = max(Decimal("0"), raw)
            if question_score > Decimal("0"):
                is_correct = True  # partial credit counts as "correct-ish"
                correct_count += 1
            else:
                wrong_count += 1
        else:
            # Wrong (non-empty, non-matching)
            wrong_count += 1
            question_score = -negative_marks

        score += question_score

        per_question.append({
            "q_pos": q_pos,
            "marked": list(marked),
            "is_correct": is_correct,
            "flagged": flagged,
        })

    # Floor total score at 0
    score = max(Decimal("0"), score)

    return {
        "score": score,
        "max_score": max_score,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "blank_count": blank_count,
        "per_question": per_question,
    }
