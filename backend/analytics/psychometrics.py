"""
analytics.psychometrics — pure psychometric computation functions.

All functions are pure over plain Python data structures (lists, dicts)
so they are easy to unit-test without a database.

TERMINOLOGY
-----------
items       : list of question positions (0-based q_pos integers)
scores      : list of total raw scores (one per student)
item_matrix : list of lists — item_matrix[student_idx][item_idx] = 1 (correct)
              or 0 (wrong/blank)

THRESHOLDS
----------
MIN_COHORT_FOR_PSYCHOMETRICS = 10

Below this cohort size:
  - difficulty (p-value) and basic stats ARE returned.
  - discrimination, point-biserial, KR-20, distractor-tertile analysis are
    returned as {"status": "insufficient_sample", "n": <count>}.

FORMULA REFERENCES
------------------
Difficulty (p):     p = (number correct) / n
Discrimination (D): D = p_upper - p_lower
                    Groups: top 27% and bottom 27% by total score.
                    Rows are sorted by total score; upper group = top floor(0.27*n)
                    rows, lower group = bottom floor(0.27*n) rows.
Point-biserial:     r_pb = (M_1 - M_0) / s_T * sqrt(p * q)
                    M_1 = mean total-minus-item score of students who got item correct
                    M_0 = mean total-minus-item score of students who got item wrong
                    s_T = std dev of total-minus-item scores (population std, ddof=0)
                    p   = proportion correct (difficulty)
                    q   = 1 - p
                    Uses total-MINUS-item to avoid item-test inflation.
                    Returns None if zero variance or insufficient cohort.
KR-20:              r_KR20 = (k/(k-1)) * (1 - sum(p_i*q_i) / var_T)
                    k     = number of items
                    var_T = population variance of total scores (ddof=0)
                    Returns None when k<2 or zero variance.
Percentile:         Percentile of student s = (# students scoring <= s) / n * 100
                    Rank (1-based): rank 1 = highest score (ties share the best rank).
"""

from __future__ import annotations

import math
from typing import Optional

MIN_COHORT_FOR_PSYCHOMETRICS = 10

# Sentinel dict for results that need more students.
_INSUFFICIENT = None  # internal; converted to {"status":"insufficient_sample","n":n} at surface


# ---------------------------------------------------------------------------
# Low-level math helpers
# ---------------------------------------------------------------------------

def _mean(values: list[float]) -> Optional[float]:
    """Population mean; None for empty list."""
    if not values:
        return None
    return sum(values) / len(values)


def _variance(values: list[float]) -> Optional[float]:
    """Population variance (ddof=0); None for empty list."""
    if not values:
        return None
    mu = _mean(values)
    return sum((v - mu) ** 2 for v in values) / len(values)


def _stddev(values: list[float]) -> Optional[float]:
    """Population std dev (ddof=0); None for empty list or zero variance."""
    var = _variance(values)
    if var is None or var <= 0:
        return None
    return math.sqrt(var)


# ---------------------------------------------------------------------------
# Item difficulty (p-value)
# ---------------------------------------------------------------------------

def item_difficulty(item_col: list[int]) -> Optional[float]:
    """
    Compute the difficulty index (p-value) for one item.

    Parameters
    ----------
    item_col : list[int]
        1 for each student who answered correctly, 0 otherwise.
        Length = cohort size.

    Returns
    -------
    float in [0.0, 1.0] — fraction correct.
    None if the list is empty.
    """
    n = len(item_col)
    if n == 0:
        return None
    return sum(item_col) / n


# ---------------------------------------------------------------------------
# Item discrimination (upper 27% - lower 27%)
# ---------------------------------------------------------------------------

def item_discrimination(
    item_col: list[int],
    total_scores: list[float],
    *,
    n: int,
) -> Optional[float]:
    """
    Discrimination index: correct-rate in upper 27% minus lower 27% by total score.

    Parameters
    ----------
    item_col      : list[int]  — 1/0 per student (length == n)
    total_scores  : list[float] — total score per student (length == n)
    n             : int         — cohort size

    Returns
    -------
    float in [-1.0, 1.0] or None if groups cannot be formed.
    """
    if n < MIN_COHORT_FOR_PSYCHOMETRICS:
        return None

    group_size = math.floor(0.27 * n)
    if group_size == 0:
        return None

    # Sort (total_score, item) pairs by score
    pairs = sorted(zip(total_scores, item_col), key=lambda x: x[0])
    lower_items = [it for _, it in pairs[:group_size]]
    upper_items = [it for _, it in pairs[n - group_size:]]

    p_lower = sum(lower_items) / group_size
    p_upper = sum(upper_items) / group_size
    return p_upper - p_lower


# ---------------------------------------------------------------------------
# Point-biserial correlation (item vs total-minus-item)
# ---------------------------------------------------------------------------

def point_biserial(
    item_col: list[int],
    total_scores: list[float],
    *,
    n: int,
) -> Optional[float]:
    """
    Point-biserial correlation using total-MINUS-item to avoid inflation.

    Parameters
    ----------
    item_col     : list[int]   — 1/0 per student
    total_scores : list[float] — total score per student
    n            : int         — cohort size

    Returns
    -------
    float in [-1.0, 1.0] or None on zero variance / insufficient cohort.
    """
    if n < MIN_COHORT_FOR_PSYCHOMETRICS:
        return None

    # total-minus-item scores
    rest_scores = [t - i for t, i in zip(total_scores, item_col)]

    p = sum(item_col) / n
    q = 1.0 - p

    if p == 0.0 or q == 0.0:
        return None  # zero variance on item side

    sd = _stddev(rest_scores)
    if sd is None or sd == 0.0:
        return None  # zero variance on score side

    correct_rest = [rest_scores[i] for i in range(n) if item_col[i] == 1]
    wrong_rest   = [rest_scores[i] for i in range(n) if item_col[i] == 0]

    m1 = _mean(correct_rest)
    m0 = _mean(wrong_rest)

    if m1 is None:
        return None

    if m0 is None:
        # All students correct — p==1, already caught above
        return None

    r_pb = (m1 - m0) / sd * math.sqrt(p * q)
    return r_pb


# ---------------------------------------------------------------------------
# KR-20 reliability
# ---------------------------------------------------------------------------

def kr20(item_matrix: list[list[int]], total_scores: list[float]) -> Optional[float]:
    """
    Kuder-Richardson Formula 20 reliability estimate.

    Parameters
    ----------
    item_matrix  : list[list[int]]  — shape (n_students, k_items), each cell 0/1
    total_scores : list[float]      — total score per student (length == n_students)

    Returns
    -------
    float — KR-20 reliability coefficient, or None if k<2 or zero total variance.
    """
    n = len(item_matrix)
    if n < 2:
        return None
    k = len(item_matrix[0]) if n > 0 else 0
    if k < 2:
        return None

    var_t = _variance(total_scores)
    if var_t is None or var_t == 0.0:
        return None

    # Sum of p_i * q_i across items
    sum_pq = 0.0
    for j in range(k):
        col = [item_matrix[i][j] for i in range(n)]
        p = sum(col) / n
        sum_pq += p * (1.0 - p)

    kr = (k / (k - 1)) * (1.0 - sum_pq / var_t)
    return kr


# ---------------------------------------------------------------------------
# Distractor analysis
# ---------------------------------------------------------------------------

def distractor_analysis(
    option_choices: dict[str, list[int]],
    total_scores: list[float],
    correct_label: str,
    *,
    n: int,
) -> dict:
    """
    Distractor analysis — per option, selection rate by performance tertile.

    Parameters
    ----------
    option_choices : dict[str, list[int]]
        {label: [1/0 per student]} — whether that option was chosen by each student.
        Covers ALL options (including the correct one).
    total_scores   : list[float] — total score per student (length == n)
    correct_label  : str         — the original correct option label
    n              : int         — cohort size

    Returns
    -------
    dict with keys:
        options : list[{label, total_count, rate_overall, by_tertile, is_key,
                        is_nfd (non-functioning distractor), miskey_suspect}]
        flags   : list[str]  — "non_functioning_distractor:<label>", "miskey_suspect:<label>"

    Non-functioning distractor (NFD): a distractor selected by < 5% of students.
    Miskey suspect: a distractor is selected MORE by the high tertile than the key.

    When n < MIN_COHORT_FOR_PSYCHOMETRICS: tertile breakdown is omitted and
    miskey_suspect is False; NFD flags are still computed from overall rate.
    """
    tertiles_available = n >= MIN_COHORT_FOR_PSYCHOMETRICS

    # Tertile boundaries (1/3 split)
    if tertiles_available:
        pairs = sorted(enumerate(total_scores), key=lambda x: x[1])
        t1 = math.floor(n / 3)
        t2 = math.floor(2 * n / 3)
        low_idx  = {p[0] for p in pairs[:t1]}
        mid_idx  = {p[0] for p in pairs[t1:t2]}
        high_idx = {p[0] for p in pairs[t2:]}
    else:
        low_idx = mid_idx = high_idx = set()

    flags = []
    options_out = []

    # Build per-option stats
    key_high_rate = None

    for label, chosen in option_choices.items():
        total_count = sum(chosen)
        rate_overall = total_count / n if n > 0 else 0.0
        is_key = label == correct_label

        if tertiles_available:
            def _rate(idx_set):
                if not idx_set:
                    return 0.0
                cnt = sum(chosen[i] for i in idx_set)
                return cnt / len(idx_set)
            by_tertile = {
                "high": _rate(high_idx),
                "mid":  _rate(mid_idx),
                "low":  _rate(low_idx),
            }
        else:
            by_tertile = {"status": "insufficient_sample", "n": n}

        is_nfd = (not is_key) and (rate_overall < 0.05)
        if is_nfd:
            flags.append(f"non_functioning_distractor:{label}")

        if is_key and tertiles_available:
            key_high_rate = by_tertile["high"]

        options_out.append({
            "label": label,
            "total_count": total_count,
            "rate_overall": rate_overall,
            "by_tertile": by_tertile,
            "is_key": is_key,
            "is_nfd": is_nfd,
            "miskey_suspect": False,  # computed below after key_high_rate is known
        })

    # Miskey detection: a distractor in the HIGH tertile has a higher rate than the KEY
    if tertiles_available and key_high_rate is not None:
        for opt in options_out:
            if not opt["is_key"] and isinstance(opt["by_tertile"], dict) and "high" in opt["by_tertile"]:
                if opt["by_tertile"]["high"] > key_high_rate:
                    opt["miskey_suspect"] = True
                    flags.append(f"miskey_suspect:{opt['label']}")

    return {"options": options_out, "flags": flags}


# ---------------------------------------------------------------------------
# Percentile + rank
# ---------------------------------------------------------------------------

def percentile_rank(scores: list[float]) -> list[dict]:
    """
    Compute percentile and rank for each student.

    Percentile of student s = (# students scoring <= s) / n * 100  (inclusive definition).
    Rank (1-based, dense): rank 1 = highest score; ties get the same (best) rank.

    Parameters
    ----------
    scores : list[float]  — raw scores, one per student (order matches)

    Returns
    -------
    list of dicts in the SAME order as ``scores``:
        [{"score": s, "percentile": p, "rank": r}, ...]
    """
    n = len(scores)
    if n == 0:
        return []

    # Percentile
    sorted_scores = sorted(scores)
    percentiles = []
    for s in scores:
        count_le = sum(1 for x in sorted_scores if x <= s)
        percentiles.append(count_le / n * 100.0)

    # Dense rank (rank 1 = highest)
    unique_scores_desc = sorted(set(scores), reverse=True)
    rank_map = {score: rank + 1 for rank, score in enumerate(unique_scores_desc)}

    return [
        {"score": scores[i], "percentile": percentiles[i], "rank": rank_map[scores[i]]}
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Full test profile computation
# ---------------------------------------------------------------------------

def compute_test_profile(results_data: list[dict]) -> dict:
    """
    Compute the full psychometric analytical profile for one test.

    Parameters
    ----------
    results_data : list of dicts, one per student result:
        {
          "student_id": int,
          "student_result_id": int,
          "score": float,
          "max_score": float,
          "item_scores": list[int],    # 1/0 per item position (q_pos order)
          "option_choices": dict[int, dict[str, int]],
                             # {q_pos: {option_label: 1/0}} per student
        }

    Returns
    -------
    dict with keys:
        n, mean, median, stddev, min, max, max_score,
        percentiles,    # list of {student_id, score, percentile, rank}
        items,          # list of per-item analysis dicts
        kr20,           # float | {"status":"insufficient_sample","n":n}
        flags,          # list of notable global flags
    """
    n = len(results_data)
    insufficient = n < MIN_COHORT_FOR_PSYCHOMETRICS

    if n == 0:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "stddev": None,
            "min": None,
            "max": None,
            "max_score": None,
            "percentiles": [],
            "items": [],
            "kr20": None,
            "flags": [],
        }

    scores = [r["score"] for r in results_data]
    max_scores = [r["max_score"] for r in results_data]

    # Basic stats
    mean_val = _mean(scores)
    sorted_s = sorted(scores)
    if n % 2 == 1:
        median_val = sorted_s[n // 2]
    else:
        median_val = (sorted_s[n // 2 - 1] + sorted_s[n // 2]) / 2.0
    sd_val = _stddev(scores)
    min_val = min(scores)
    max_val = max(scores)
    max_score_val = max(max_scores)

    # Percentiles + ranks
    pr_list = percentile_rank(scores)
    percentiles = [
        {
            "student_id": results_data[i]["student_id"],
            "student_result_id": results_data[i]["student_result_id"],
            "score": pr_list[i]["score"],
            "percentile": pr_list[i]["percentile"],
            "rank": pr_list[i]["rank"],
        }
        for i in range(n)
    ]

    # Build item matrix
    # Infer item count from the first student
    if results_data[0]["item_scores"]:
        k = len(results_data[0]["item_scores"])
    else:
        k = 0

    item_matrix = [r["item_scores"] for r in results_data]

    # Per-item analysis
    items_out = []
    for j in range(k):
        item_col = [item_matrix[i][j] for i in range(n)]

        p_val = item_difficulty(item_col)

        # Discrimination
        disc = item_discrimination(item_col, scores, n=n)

        # Point-biserial
        pb = point_biserial(item_col, scores, n=n)

        # Distractor analysis — collect per-option choice vectors
        opt_choices: dict[str, list[int]] = {}
        correct_label = None
        for student_idx, r in enumerate(results_data):
            q_opts = r.get("option_choices", {}).get(j, {})
            for label, chosen in q_opts.items():
                if label not in opt_choices:
                    opt_choices[label] = [0] * n
                opt_choices[label][student_idx] = int(chosen)
            # Track correct label via the one with is_key
            if "correct_option" in r:
                # Not expected in the per-student dict; set externally via item param
                pass

        # Flags
        item_flags = []
        if p_val is not None:
            if p_val > 0.90:
                item_flags.append("too_easy")
            elif p_val < 0.20:
                item_flags.append("too_hard")
        if disc is not None and disc < 0:
            item_flags.append("negative_discrimination")

        if insufficient:
            disc_out = {"status": "insufficient_sample", "n": n}
            pb_out   = {"status": "insufficient_sample", "n": n}
        else:
            disc_out = disc
            pb_out   = pb

        items_out.append({
            "q_pos": j,
            "difficulty": p_val,
            "discrimination": disc_out,
            "point_biserial": pb_out,
            "distractor": None,  # populated separately via compute_distractor_profiles
            "flags": item_flags,
        })

    # KR-20
    if insufficient:
        kr20_out = {"status": "insufficient_sample", "n": n}
    else:
        kr20_val = kr20(item_matrix, scores)
        kr20_out = kr20_val  # float or None

    global_flags = []
    if insufficient:
        global_flags.append("insufficient_sample")

    return {
        "n": n,
        "mean": mean_val,
        "median": median_val,
        "stddev": sd_val,
        "min": min_val,
        "max": max_val,
        "max_score": max_score_val,
        "percentiles": percentiles,
        "items": items_out,
        "kr20": kr20_out,
        "flags": global_flags,
    }


# ---------------------------------------------------------------------------
# Helper: build results_data from Django ORM (for use in tasks)
# ---------------------------------------------------------------------------

def build_results_data(test) -> list[dict]:
    """
    Build the results_data list from the database for a given Test.

    This function reads StudentResult + QuestionResponse + OmrSheet to produce
    the canonical results_data format expected by compute_test_profile().

    Respects per-student option shuffle (via OmrSheet.option_order) when
    mapping printed choices back to original option labels for distractor analysis.

    Parameters
    ----------
    test : assessments.Test

    Returns
    -------
    list of dicts (see compute_test_profile docstring for shape).
    """
    from results.models import StudentResult, QuestionResponse
    from assessments.models import Question, Option

    results = list(
        StudentResult.objects
        .filter(test=test)
        .select_related("student", "omr_sheet")
        .prefetch_related("responses")
    )

    if not results:
        return []

    # Build a mapping q_pos → correct ORIGINAL option labels for this test.
    # We derive from the first sheet's question_order + DB Options.
    # (All sheets for a test share the same underlying Questions.)
    first_sheet = results[0].omr_sheet if results[0].omr_sheet else None
    q_order = first_sheet.question_order if first_sheet else []
    k = len(q_order)

    # Per-question correct labels (original) {q_pos: set of correct labels}
    correct_labels_by_pos: dict[int, set] = {}
    if q_order:
        q_objs = {
            q.id: q
            for q in Question.objects.filter(id__in=q_order).prefetch_related("options")
        }
        for pos, q_id in enumerate(q_order):
            q_obj = q_objs.get(q_id)
            if q_obj:
                correct_labels_by_pos[pos] = {
                    o.label for o in q_obj.options.all() if o.is_correct
                }
            else:
                correct_labels_by_pos[pos] = set()

    data = []
    for sr in results:
        omr_sheet = sr.omr_sheet
        option_order = omr_sheet.option_order if omr_sheet else {}
        q_order_sheet = omr_sheet.question_order if omr_sheet else []

        responses = {resp.q_pos: resp for resp in sr.responses.all()}

        item_scores = []
        option_choices: dict[int, dict[str, int]] = {}

        for pos in range(k):
            resp = responses.get(pos)
            if resp is None:
                item_scores.append(0)
                continue

            item_scores.append(1 if resp.is_correct else 0)

            # Build option choice vector for distractor analysis.
            # Map printed choices back to original labels via option_order.
            q_id = q_order_sheet[pos] if pos < len(q_order_sheet) else None
            opt_order_for_q = option_order.get(str(q_id), []) if q_id else []

            choices_this_q: dict[str, int] = {}
            for printed_label in resp.marked_options:
                # Convert printed label → original label
                printed_idx = ord(printed_label) - ord('A')
                if 0 <= printed_idx < len(opt_order_for_q):
                    orig_label = opt_order_for_q[printed_idx]
                else:
                    orig_label = printed_label
                choices_this_q[orig_label] = 1

            option_choices[pos] = choices_this_q

        data.append({
            "student_id": sr.student_id,
            "student_result_id": sr.id,
            "score": float(sr.score),
            "max_score": float(sr.max_score),
            "item_scores": item_scores,
            "option_choices": option_choices,
        })

    return data


def compute_distractor_profiles(
    test,
    results_data: list[dict],
    profile: dict,
) -> dict:
    """
    Enrich the profile's items list with distractor analysis.

    Parameters
    ----------
    test         : assessments.Test
    results_data : output of build_results_data()
    profile      : output of compute_test_profile() — modified in-place

    Returns
    -------
    The modified profile dict.
    """
    from assessments.models import Question, Option

    if not results_data:
        return profile

    first_sheet = None
    from results.models import StudentResult
    sr = StudentResult.objects.filter(test=test).select_related("omr_sheet").first()
    if sr:
        first_sheet = sr.omr_sheet

    q_order = first_sheet.question_order if first_sheet else []
    k = len(q_order)
    n = len(results_data)
    scores = [r["score"] for r in results_data]

    q_objs = {}
    if q_order:
        for q in Question.objects.filter(id__in=q_order).prefetch_related("options"):
            q_objs[q.id] = q

    for j in range(k):
        q_id = q_order[j] if j < len(q_order) else None
        q_obj = q_objs.get(q_id) if q_id else None
        if q_obj is None:
            continue

        all_option_labels = [o.label for o in q_obj.options.all()]
        correct_labels = {o.label for o in q_obj.options.all() if o.is_correct}
        correct_label = next(iter(correct_labels), None)  # primary correct label

        # Build per-option choice vectors across all students
        opt_choices: dict[str, list[int]] = {label: [0] * n for label in all_option_labels}
        for stu_idx, r in enumerate(results_data):
            chosen = r["option_choices"].get(j, {})
            for label in chosen:
                if label in opt_choices:
                    opt_choices[label][stu_idx] = 1
                else:
                    # Unknown label (possibly from a different shuffle mapping)
                    opt_choices[label] = [0] * n
                    opt_choices[label][stu_idx] = 1

        da = distractor_analysis(
            opt_choices,
            scores,
            correct_label or "",
            n=n,
        )

        # Inject into profile item
        if j < len(profile["items"]):
            profile["items"][j]["distractor"] = da

    return profile
