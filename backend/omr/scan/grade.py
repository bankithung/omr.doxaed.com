"""
omr.scan.grade — Sheet grading from aggregated bubble reads.

grade_sheet(omr_sheet, aggregated_reads) applies the test's MarkingScheme (or
per-section SectionMarkingScheme) to each question and returns a structured
grading result.

aggregated_reads format:
    {q_pos (int): set/list of marked printed labels}

The answer_key on OmrSheet is:
    {str(q_pos): [correct printed labels]}

Two coordinate spaces
---------------------
CANONICAL  = Question.order_index (authoring space; examiner's Q1-35).
PRINTED    = q_pos, the shuffled space used by OmrSheet.question_order.
Bridge: omr_sheet.question_order[q_pos] -> Question.id -> Question.section.

Choose-K semantics (C1 - BEST-K of attempted)
----------------------------------------------
In a choose_k section, grade the K attempted questions with the HIGHEST
per-question score (rank by score DESC, tie-break by canonical
Question.order_index ASC).  Surplus attempted questions beyond K get
status="ignored" and do NOT enter any count or max calculation.
Blanks never consume a slot.  This is shuffle-invariant.

Quantization
------------
Full Decimal precision throughout; quantize ONCE at return (2 dp,
ROUND_HALF_UP) for score, max_score, and each section subtotal/max_subtotal.

Backward compatibility
----------------------
A standard test (no sections) follows the no-sections path bit-for-bit:
max_score = len(answer_key) * marks_per_correct (legacy product, not sum).
All new return keys are additive/absent-safe.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP


_TWO_PLACES = Decimal("0.01")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def _scheme_tuple(
    marks_per_correct,
    negative_marks_per_wrong,
    negative_kind: str,
    partial_marking: bool,
    multiple_correct_allowed: bool,
    qualify_pct,
) -> tuple:
    return (
        Decimal(str(marks_per_correct)),
        Decimal(str(negative_marks_per_wrong)),
        negative_kind,
        bool(partial_marking),
        bool(multiple_correct_allowed),
        Decimal(str(qualify_pct)) if qualify_pct is not None else None,
    )


def _resolve_default_scheme(omr_sheet) -> tuple:
    """Fetch the test-level MarkingScheme (existing behavior, bare try/except)."""
    try:
        ms = omr_sheet.test.marking_scheme
        return _scheme_tuple(
            ms.marks_per_correct, ms.negative_marks_per_wrong,
            "flat", ms.partial_marking, ms.multiple_correct_allowed, None,
        )
    except Exception:
        return _scheme_tuple(Decimal("1"), Decimal("0"), "flat", False, False, None)


def _build_section_cache(question_order: list) -> dict:
    """
    Return {question_id: Section_or_None} for all ids in question_order.
    One DB query with select_related.
    """
    if not question_order:
        return {}
    from assessments.models import Question as Q
    qs = Q.objects.filter(id__in=question_order).select_related(
        "section", "section__marking_scheme"
    )
    return {q.id: q.section for q in qs}


def _scheme_for_qpos(
    q_pos: int,
    question_order: list,
    default_scheme: tuple,
    section_cache: dict,
) -> tuple:
    """
    Resolve (section, scheme) for a printed q_pos.
    Returns (None, default_scheme) when no section applies.
    Section resolution is OUTSIDE try/except so resolver bugs are not masked.
    """
    if not question_order or q_pos >= len(question_order):
        return None, default_scheme
    q_id = question_order[q_pos]
    section = section_cache.get(q_id)
    if section is None:
        return None, default_scheme
    sms = getattr(section, "marking_scheme", None)
    if sms is None:
        return section, default_scheme
    return section, _scheme_tuple(
        sms.marks_per_correct, sms.negative_marks_per_wrong,
        sms.negative_kind, sms.partial_marking,
        sms.multiple_correct_allowed, sms.qualify_pct,
    )


def grade_sheet(omr_sheet, aggregated_reads: dict) -> dict:
    """
    Grade a completed OMR sheet against the stored answer key.

    Parameters
    ----------
    omr_sheet : OmrSheet
        Must have .answer_key (dict), .test, .question_order (list[int]|None).
    aggregated_reads : dict
        {q_pos (int): set/list of marked printed labels}
        Questions not present are treated as blank.

    Returns
    -------
    dict with keys:
        score          : Decimal (quantized 2dp, floored at 0)
        max_score      : Decimal (quantized 2dp)
        correct_count  : int
        wrong_count    : int
        blank_count    : int
        per_question   : list[dict] - existing keys {q_pos, marked, is_correct, flagged}
                         plus optional {section (str|None), score (Decimal), status (str)}
        sections       : list[dict] - [] when no sections
        qualified_all  : bool - True when no qualifying sections
    """
    answer_key = omr_sheet.answer_key
    question_order = getattr(omr_sheet, "question_order", None) or []

    # ------------------------------------------------------------------
    # Seam 1: scheme resolver
    # ------------------------------------------------------------------
    default_scheme = _resolve_default_scheme(omr_sheet)

    # Build section cache (one DB query; empty dict when no sections exist)
    section_cache = _build_section_cache(question_order)

    # Check if ANY sections exist (gating flag)
    has_sections = any(s is not None for s in section_cache.values())

    # ------------------------------------------------------------------
    # Seam 2: choose-k pre-pass (best-K of attempted — C1)
    # ------------------------------------------------------------------
    # q_id -> canonical order_index for tie-breaking
    q_id_to_order_index: dict[int, int] = {}
    if has_sections and question_order:
        from assessments.models import Question as Q
        for q in Q.objects.filter(id__in=question_order).only("id", "order_index"):
            q_id_to_order_index[q.id] = q.order_index

    # Build section_id -> list of q_pos for choose_k sections
    section_to_qpos: dict[int, list[int]] = defaultdict(list)
    if has_sections:
        for q_pos_str in answer_key:
            q_pos_i = int(q_pos_str)
            if q_pos_i < len(question_order):
                q_id = question_order[q_pos_i]
                sec = section_cache.get(q_id)
                if sec is not None and sec.policy == "choose_k":
                    section_to_qpos[sec.id].append(q_pos_i)

    def _tentative_score(q_pos: int, scheme: tuple) -> Decimal:
        """Pre-grade a q_pos for choose-k ranking (does NOT affect counts)."""
        marks_pc, neg_marks, neg_kind, partial, multiple, _ = scheme
        correct_labels = set(answer_key.get(str(q_pos), []))
        marked = set(aggregated_reads.get(q_pos, []))
        if not marked:
            return Decimal("0")
        if marked == correct_labels:
            return marks_pc
        if partial and multiple and correct_labels:
            inter = len(marked & correct_labels)
            over = len(marked - correct_labels)
            raw = (Decimal(inter) - Decimal(over)) / Decimal(len(correct_labels)) * marks_pc
            return max(Decimal("0"), raw)
        # Wrong
        if neg_kind == "fractional":
            return -(marks_pc * neg_marks)
        return -neg_marks

    # Determine ignored q_pos (surplus attempted beyond K)
    ignored_qpos: set[int] = set()
    if has_sections:
        for sec_id, qpos_list in section_to_qpos.items():
            sec_obj = None
            for qp in qpos_list:
                if qp < len(question_order):
                    sec_obj = section_cache.get(question_order[qp])
                    if sec_obj is not None:
                        break
            if sec_obj is None or not sec_obj.choose_k:
                continue

            k = sec_obj.choose_k
            sms = getattr(sec_obj, "marking_scheme", None)
            sec_scheme = default_scheme
            if sms is not None:
                sec_scheme = _scheme_tuple(
                    sms.marks_per_correct, sms.negative_marks_per_wrong,
                    sms.negative_kind, sms.partial_marking,
                    sms.multiple_correct_allowed, sms.qualify_pct,
                )

            attempted = [qp for qp in qpos_list if aggregated_reads.get(qp)]
            if len(attempted) <= k:
                continue

            scored = []
            for qp in attempted:
                ts = _tentative_score(qp, sec_scheme)
                q_id = question_order[qp] if qp < len(question_order) else None
                canon_idx = q_id_to_order_index.get(q_id, 9_999_999) if q_id else 9_999_999
                scored.append((ts, canon_idx, qp))

            # Best K: sort score DESC, canonical order ASC
            scored.sort(key=lambda x: (-x[0], x[1]))
            for _, _, qp in scored[k:]:
                ignored_qpos.add(qp)

    # ------------------------------------------------------------------
    # Seam 3: main grade loop
    # ------------------------------------------------------------------
    marks_per_correct_default = default_scheme[0]

    score = Decimal("0")
    correct_count = 0
    wrong_count = 0
    blank_count = 0
    per_question = []

    sec_subtotal: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    sec_correct: dict[int, int] = defaultdict(int)
    sec_wrong: dict[int, int] = defaultdict(int)
    sec_blank: dict[int, int] = defaultdict(int)
    sec_max: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    sec_q_count: dict[int, int] = defaultdict(int)

    # Aggregate max_score accumulator (sections path only)
    max_score_sum = Decimal("0")

    for q_pos_str, correct_labels_list in answer_key.items():
        q_pos = int(q_pos_str)
        correct = set(correct_labels_list)
        marked = set(aggregated_reads.get(q_pos, []))

        is_correct = False
        flagged = False
        section_key = None

        # ---- IGNORED (choose-k surplus) ----
        if q_pos in ignored_qpos:
            entry = {
                "q_pos": q_pos,
                "marked": list(marked),
                "is_correct": False,
                "flagged": flagged,
                "section": None,
                "score": Decimal("0"),
                "status": "ignored",
            }
            if q_pos < len(question_order):
                sec = section_cache.get(question_order[q_pos])
                if sec is not None:
                    entry["section"] = sec.key
            per_question.append(entry)
            continue

        # ---- Resolve scheme ----
        section, scheme = _scheme_for_qpos(q_pos, question_order, default_scheme, section_cache)
        marks_per_correct, neg_marks, neg_kind, partial, multiple, qualify_pct = scheme

        if section is not None:
            section_key = section.key

        # qualifying-only section: score goes into sec_subtotal only, not aggregate
        is_qualifying_only = (qualify_pct is not None)

        # ---- Grade this question ----
        if not marked:
            blank_count += 1
            question_score = Decimal("0")
            status = "blank"
            if section is not None:
                sec_blank[section.id] += 1
        elif marked == correct:
            is_correct = True
            correct_count += 1
            question_score = marks_per_correct
            status = "correct"
            if section is not None:
                sec_correct[section.id] += 1
        elif partial and multiple and correct:
            inter = len(marked & correct)
            over = len(marked - correct)
            raw = (Decimal(inter) - Decimal(over)) / Decimal(len(correct)) * marks_per_correct
            question_score = max(Decimal("0"), raw)
            if question_score > Decimal("0"):
                is_correct = True
                correct_count += 1
                status = "correct"
            else:
                wrong_count += 1
                status = "wrong"
            if section is not None:
                if question_score > Decimal("0"):
                    sec_correct[section.id] += 1
                else:
                    sec_wrong[section.id] += 1
        else:
            wrong_count += 1
            if neg_kind == "fractional":
                penalty = marks_per_correct * neg_marks
            else:
                penalty = neg_marks
            question_score = -penalty
            status = "wrong"
            if section is not None:
                sec_wrong[section.id] += 1

        if section is not None:
            sec_q_count[section.id] += 1
            sec_subtotal[section.id] += question_score
            # choose_k sections: cap max_subtotal at K * marks_per_correct
            is_choose_k = (section.policy == "choose_k" and section.choose_k is not None)
            if not is_choose_k or sec_max[section.id] < section.choose_k * marks_per_correct:
                sec_max[section.id] += marks_per_correct
        else:
            # Unsectioned question: accumulate directly into max_score_sum
            if not is_qualifying_only:
                max_score_sum += marks_per_correct

        if not is_qualifying_only:
            score += question_score

        per_question.append({
            "q_pos": q_pos,
            "marked": list(marked),
            "is_correct": is_correct,
            "flagged": flagged,
            "section": section_key,
            "score": question_score,
            "status": status,
        })

    # ------------------------------------------------------------------
    # max_score: legacy formula when no sections; per-q sum when sections
    # ------------------------------------------------------------------
    if not has_sections:
        max_score = Decimal(len(answer_key)) * marks_per_correct_default
    else:
        # Sum sec_max (already capped for choose_k) for non-qualifying sections
        # plus max_score_sum which holds unsectioned question contributions.
        sectioned_max = Decimal("0")
        for sec in section_cache.values():
            if sec is not None:
                sms = getattr(sec, "marking_scheme", None)
                qualify_pct_val = sms.qualify_pct if sms is not None else None
                if qualify_pct_val is None:  # non-qualifying only
                    sectioned_max += sec_max.get(sec.id, Decimal("0"))
        # Deduplicate sections (section_cache may have duplicates per q_id)
        seen_sec_ids: set[int] = set()
        sectioned_max = Decimal("0")
        for sec in section_cache.values():
            if sec is not None and sec.id not in seen_sec_ids:
                seen_sec_ids.add(sec.id)
                sms = getattr(sec, "marking_scheme", None)
                qualify_pct_val = sms.qualify_pct if sms is not None else None
                if qualify_pct_val is None:
                    sectioned_max += sec_max.get(sec.id, Decimal("0"))
        max_score = max_score_sum + sectioned_max

    # ------------------------------------------------------------------
    # Aggregate floor (unchanged)
    # ------------------------------------------------------------------
    score = max(Decimal("0"), score)

    # ------------------------------------------------------------------
    # Seam 4: subtotal/cutoff post-pass
    # ------------------------------------------------------------------
    sections_out = []
    qualified_all = True

    if has_sections:
        seen_sections: dict[int, object] = {}
        for sec in section_cache.values():
            if sec is not None and sec.id not in seen_sections:
                seen_sections[sec.id] = sec

        for sec in sorted(seen_sections.values(), key=lambda s: (s.order_index, s.id)):
            sms = getattr(sec, "marking_scheme", None)
            qualify_pct_val = sms.qualify_pct if sms is not None else None

            subtotal = sec_subtotal.get(sec.id, Decimal("0"))
            max_subtotal = sec_max.get(sec.id, Decimal("0"))
            q_count = sec_q_count.get(sec.id, 0)

            counts = qualify_pct_val is None
            qualified = True
            qualify_threshold = None

            if qualify_pct_val is not None:
                threshold = Decimal(str(qualify_pct_val)) / Decimal("100") * max_subtotal
                qualify_threshold = threshold
                qualified = subtotal >= threshold
                if not qualified:
                    qualified_all = False

            sections_out.append({
                "section_id": sec.id,
                "key": sec.key,
                "label": sec.label,
                "order_index": sec.order_index,
                "policy": sec.policy,
                "choose_k": sec.choose_k,
                "subtotal": _quantize(subtotal),
                "max_subtotal": _quantize(max_subtotal),
                "q_count": q_count,
                "correct": sec_correct.get(sec.id, 0),
                "wrong": sec_wrong.get(sec.id, 0),
                "blank": sec_blank.get(sec.id, 0),
                "counts": counts,
                "qualify_pct": float(qualify_pct_val) if qualify_pct_val is not None else None,
                "qualify_threshold": float(_quantize(qualify_threshold)) if qualify_threshold is not None else None,
                "qualified": qualified,
            })

    # ------------------------------------------------------------------
    # Quantize final values
    # ------------------------------------------------------------------
    score = _quantize(score)
    max_score = _quantize(max_score)

    return {
        "score": score,
        "max_score": max_score,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "blank_count": blank_count,
        "per_question": per_question,
        "sections": sections_out,
        "qualified_all": qualified_all,
    }
