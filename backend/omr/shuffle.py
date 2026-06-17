"""
omr.shuffle — deterministic per-sheet question/option shuffle + answer key.

Uses random.Random(seed) for full reproducibility from a stored integer seed.
"""
import random


def build_sheet_plan(
    questions: list,
    seed: int,
    shuffle_questions: bool = True,
    shuffle_options: bool = True,
) -> dict:
    """
    Build the per-sheet print plan.

    Parameters
    ----------
    questions         : list of {"id": int, "options": [{"label": str, "is_correct": bool}]}
    seed              : int — deterministic RNG seed (stored as OmrSheet.shuffle_version)
    shuffle_questions : bool — if False, keep original question order
    shuffle_options   : bool — if False, keep original option order per question

    Returns
    -------
    dict with:
        question_order  list[int]       — question ids in printed order
        option_order    dict[str, list] — {str(question_id): [printed option labels]}
        answer_key      dict[str, list] — {str(printed_position): [correct printed labels]}
    """
    rng = random.Random(seed)

    # ------------------------------------------------------------------ #
    # 1. Determine printed question order
    # ------------------------------------------------------------------ #
    question_ids = [q["id"] for q in questions]
    if shuffle_questions:
        question_ids = list(question_ids)      # copy
        rng.shuffle(question_ids)

    # Build a quick lookup: id → question dict
    q_by_id = {q["id"]: q for q in questions}

    # ------------------------------------------------------------------ #
    # 2. Determine printed option order per question
    # ------------------------------------------------------------------ #
    option_order = {}    # str(question_id) → [printed labels]
    for q_id in question_ids:
        q = q_by_id[q_id]
        orig_labels = [opt["label"] for opt in q["options"]]
        if shuffle_options:
            printed = list(orig_labels)
            rng.shuffle(printed)
        else:
            printed = list(orig_labels)
        option_order[str(q_id)] = printed

    # ------------------------------------------------------------------ #
    # 3. Build answer key
    #    answer_key[str(printed_position)] = [printed option labels that are correct]
    # ------------------------------------------------------------------ #
    # Correct original labels per question id
    correct_by_id = {
        q["id"]: {opt["label"] for opt in q["options"] if opt["is_correct"]}
        for q in questions
    }

    answer_key = {}
    for printed_pos, q_id in enumerate(question_ids):
        printed_labels = option_order[str(q_id)]
        correct_originals = correct_by_id[q_id]

        # For each printed label, check if its original label was correct.
        # The i-th element in printed_labels is an original label; the
        # printed option letter is chr(ord('A') + i).
        correct_printed = []
        for i, orig_label in enumerate(printed_labels):
            if orig_label in correct_originals:
                printed_letter = chr(ord("A") + i)
                correct_printed.append(printed_letter)

        answer_key[str(printed_pos)] = correct_printed

    return {
        "question_order": question_ids,
        "option_order": option_order,
        "answer_key": answer_key,
    }
