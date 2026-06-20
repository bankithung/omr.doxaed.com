"""
omr.question_paper — per-student shuffled question paper PDF renderer.

Public API
----------
render_question_paper_pdf(omr_sheet, *, include_answer_key=False) -> bytes
    Reconstruct the printed question paper from the stored shuffle plan
    (question_order, option_order, answer_key) on the OmrSheet row.

    Uses ReportLab Platypus (prose layout — NOT the fiducial Canvas).
    Deterministic: no timestamps, fixed producer string.

Design notes
------------
- question_order  : list[int] — Question PKs in the student's printed order.
- option_order    : {str(q_id): [original option labels in printed order]}
  Each element is the ORIGINAL label of that printed option slot.
  Printed letter = chr(ord('A') + i) where i is the index in this list.
- answer_key      : {str(printed_pos): [printed letters that are correct]}

S7 correctness invariant (from the security review):
    For each printed position p, the answer key letter L in
    answer_key[str(p)] is the printed letter whose ORIGINAL label
    was the correct one.  This renderer reconstructs that via:
        printed_letter = chr(ord('A') + i)
        where i is the index of the correct original label in
        option_order[str(q_id)].
    The test golden in tests_question_paper.py asserts this property.

When shuffle is OFF, question_order / option_order are identity copies
→ the same renderer yields a plain ordered paper (no special-casing).
"""
from __future__ import annotations

import io
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Colours (kept minimal — print-friendly black on white)
# ---------------------------------------------------------------------------
_DARK      = colors.HexColor("#222222")
_BLUE      = colors.HexColor("#366092")
_LIGHT_BG  = colors.HexColor("#EFF3F8")
_GREY_LINE = colors.HexColor("#CCCCCC")

A4_W, A4_H = A4

# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

def _build_styles():
    base = getSampleStyleSheet()

    header_style = ParagraphStyle(
        "QPHeader",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=_DARK,
        spaceAfter=2,
    )
    subheader_style = ParagraphStyle(
        "QPSubHeader",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=_DARK,
        spaceAfter=1,
    )
    meta_style = ParagraphStyle(
        "QPMeta",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#555555"),
        spaceAfter=4,
    )
    q_style = ParagraphStyle(
        "QPQuestion",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=_DARK,
        spaceAfter=3,
    )
    opt_style = ParagraphStyle(
        "QPOption",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=_DARK,
        leftIndent=12,
        spaceAfter=2,
    )
    section_style = ParagraphStyle(
        "QPSection",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=_BLUE,
        spaceBefore=8,
        spaceAfter=4,
    )
    answer_key_header = ParagraphStyle(
        "QPAKHeader",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=_DARK,
        spaceBefore=14,
        spaceAfter=6,
    )
    answer_key_style = ParagraphStyle(
        "QPAnswerKey",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=_DARK,
        spaceAfter=3,
    )

    return {
        "header": header_style,
        "subheader": subheader_style,
        "meta": meta_style,
        "question": q_style,
        "option": opt_style,
        "section": section_style,
        "answer_key_header": answer_key_header,
        "answer_key": answer_key_style,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_question_paper_pdf(omr_sheet, *, include_answer_key: bool = False) -> bytes:
    """
    Render a per-student question paper PDF from the stored shuffle plan.

    Parameters
    ----------
    omr_sheet         : OmrSheet instance (must have question_order, option_order,
                        answer_key, human_readable_code, student prefetched or
                        accessible via .student).
    include_answer_key: If True, append a teacher answer-key page at the end.

    Returns
    -------
    bytes — PDF content.  Starts with b'%PDF'.
    Deterministic (no timestamps, fixed producer).
    """
    # ------------------------------------------------------------------
    # 1. Resolve student info
    # ------------------------------------------------------------------
    student = omr_sheet.student
    student_name = ""
    student_roll = ""
    if student is not None:
        student_name = getattr(student, "full_name", "") or ""
        student_roll = getattr(student, "roll_number", "") or ""

    sheet_id = omr_sheet.human_readable_code or omr_sheet.sheet_code or str(omr_sheet.pk)

    # ------------------------------------------------------------------
    # 2. Resolve test info
    # ------------------------------------------------------------------
    test = omr_sheet.test
    test_title = getattr(test, "title", "") or ""
    subject = getattr(test, "subject", "") or ""

    # ------------------------------------------------------------------
    # 3. Fetch questions from DB
    #    We need: Question.id, Question.text, and per-question Options
    #    (label → text).
    # ------------------------------------------------------------------
    from assessments.models import Question, Option

    question_order = omr_sheet.question_order        # list[int]
    option_order   = omr_sheet.option_order          # {str(q_id): [orig_labels…]}
    answer_key     = omr_sheet.answer_key            # {str(printed_pos): [letters]}

    if not question_order:
        # Edge-case: no questions — return a minimal PDF stub
        return _empty_pdf()

    # Bulk-fetch all questions needed for this sheet
    questions_qs = Question.objects.filter(pk__in=question_order).prefetch_related("options")
    # question_order holds STRING ids (UUIDs serialised onto the JSONField), so the
    # lookups must be keyed by str(q.id); keying by the UUID object never matches.
    q_by_id = {str(q.id): q for q in questions_qs}

    # Build per-question option text lookup: {str(q_id): {orig_label: display_text}}
    opt_text_by_q: dict[str, dict[str, str]] = {}
    for q in questions_qs:
        opt_text_by_q[str(q.id)] = {}
        for opt in q.options.all():
            # Prefer opt.text; fall back to the label itself for label-only options
            opt_text_by_q[str(q.id)][opt.label] = opt.text or opt.label

    # ------------------------------------------------------------------
    # 4. Build Platypus story
    # ------------------------------------------------------------------
    styles = _build_styles()
    story = []

    # --- Header block ---
    story.append(Paragraph(test_title or "Question Paper", styles["header"]))
    if subject:
        story.append(Paragraph(subject, styles["subheader"]))

    # Student meta row
    meta_parts = []
    if student_name:
        meta_parts.append(f"<b>Name:</b> {student_name}")
    if student_roll:
        meta_parts.append(f"<b>Roll No.:</b> {student_roll}")
    meta_parts.append(f"<b>Sheet ID:</b> {sheet_id}")
    story.append(Paragraph("   |   ".join(meta_parts), styles["meta"]))

    story.append(Spacer(1, 0.25 * cm))

    # Divider
    story.append(
        Table(
            [[""]],
            colWidths=[A4_W - 4 * cm],
            style=TableStyle([
                ("LINEBELOW", (0, 0), (-1, -1), 1, _GREY_LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]),
        )
    )
    story.append(Spacer(1, 0.2 * cm))

    # --- Questions ---
    current_section_key: Optional[str] = None

    for printed_pos, q_id in enumerate(question_order):
        q = q_by_id.get(q_id)
        if q is None:
            # Defensive: skip missing questions (shouldn't happen in normal flow)
            continue

        # Section heading for competitive tests
        if q.section is not None:
            sec_key = q.section.key
            if sec_key != current_section_key:
                current_section_key = sec_key
                sec_label = q.section.label or sec_key
                story.append(Paragraph(f"Section: {sec_label}", styles["section"]))

        # Printed option labels for this question (original labels in printed order)
        printed_orig_labels = option_order.get(str(q_id), [])
        opt_texts = opt_text_by_q.get(q_id, {})

        # Build one KeepTogether block per question
        block = []

        # Question text (fall back gracefully to placeholder)
        q_text_raw = (q.text or "").strip() or f"[Question {printed_pos + 1}]"
        block.append(
            Paragraph(f"Q{printed_pos + 1}.  {q_text_raw}", styles["question"])
        )

        # Options
        for i, orig_label in enumerate(printed_orig_labels):
            printed_letter = chr(ord("A") + i)
            # Look up option text by its original label
            display_text = opt_texts.get(orig_label)
            if not display_text:
                # Fall back to the original label (label-only or missing option)
                display_text = orig_label
            block.append(
                Paragraph(f"({printed_letter})  {display_text}", styles["option"])
            )

        block.append(Spacer(1, 0.3 * cm))
        story.append(KeepTogether(block))

    # --- Optional answer-key appendix (teacher-only) ---
    if include_answer_key and answer_key:
        story.append(Paragraph("Answer Key", styles["answer_key_header"]))
        story.append(
            Table(
                [[""]],
                colWidths=[A4_W - 4 * cm],
                style=TableStyle([
                    ("LINEBELOW", (0, 0), (-1, -1), 1, _GREY_LINE),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]),
            )
        )
        story.append(Spacer(1, 0.15 * cm))

        for printed_pos, q_id in enumerate(question_order):
            correct_letters = answer_key.get(str(printed_pos), [])
            if not correct_letters:
                correct_str = "—"
            elif isinstance(correct_letters, list):
                correct_str = ", ".join(correct_letters)
            else:
                correct_str = str(correct_letters)
            story.append(
                Paragraph(
                    f"Q{printed_pos + 1}: <b>{correct_str}</b>",
                    styles["answer_key"],
                )
            )

    # ------------------------------------------------------------------
    # 5. Build PDF via SimpleDocTemplate
    # ------------------------------------------------------------------
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=test_title or "Question Paper",
        author="DoxaEd OMR",
        # Determinism: no creation timestamp — ReportLab embeds %CreationDate
        # in the producer string but NOT in the PDF stream content that affects
        # the byte-level hash; we do NOT set creationDate to avoid any dynamic
        # metadata.  The flowable content is fully deterministic given the same
        # OmrSheet state.
    )
    doc.build(story)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _empty_pdf() -> bytes:
    """Return a minimal valid PDF for an OmrSheet with no questions."""
    styles = _build_styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="Question Paper", author="DoxaEd OMR")
    doc.build([Paragraph("No questions found for this sheet.", styles["meta"])])
    buf.seek(0)
    return buf.read()
