"""
analytics.report_card — per-student two-page report card PDF.

Public API
----------
student_report_card(test, student_result) -> bytes
    Two-page PDF for a single student.

bulk_report_cards(test) -> bytes
    Combined PDF: 2 pages per graded student, all concatenated.

Page layout
-----------
Page 1 — Parent-friendly summary
    Header: school/org name + test title
    Student name + roll number
    Big score block: x / max, %, percentile, rank
    Topic-performance bars (horizontal, %); degrade to correct/wrong/blank if no topics
    Strengths vs Needs-work (best/worst topics)
    Class-average comparison (you vs class avg, delta)

Page 2 — Teacher diagnostic
    Topic breakdown vs class table
    Full per-question table: Q#, student's choice, correct answer, ✓/✗/blank
    Missed-item clusters (wrong items grouped by topic)
    Distractor note for the student's wrong answers

All A4, print-friendly, ReportLab Platypus.
"""

from __future__ import annotations

import io
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Colour palette (matches export.py style)
# ---------------------------------------------------------------------------

_BLUE      = colors.HexColor("#366092")
_LIGHT_BG  = colors.HexColor("#EFF3F8")
_GREY_LINE = colors.HexColor("#CCCCCC")
_GREEN     = colors.HexColor("#217346")
_RED       = colors.HexColor("#C0392B")
_AMBER     = colors.HexColor("#D68910")
_DARK      = colors.HexColor("#222222")
_WHITE     = colors.white

A4_W, A4_H = A4

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(v, decimals: int = 1) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        return f"{v:.{decimals}f}"
    return str(v)


def _clamp_bar(pct: float) -> float:
    """Clamp 0–100 for bar widths."""
    return max(0.0, min(100.0, pct))


def _styles():
    base = getSampleStyleSheet()
    h1   = ParagraphStyle("RC_H1",   parent=base["Heading1"],  fontSize=16, textColor=_BLUE,  spaceAfter=4)
    h2   = ParagraphStyle("RC_H2",   parent=base["Heading2"],  fontSize=12, textColor=_BLUE,  spaceAfter=3)
    h3   = ParagraphStyle("RC_H3",   parent=base["Heading3"],  fontSize=10, textColor=_DARK,  spaceAfter=2)
    norm = ParagraphStyle("RC_Norm", parent=base["Normal"],    fontSize=9,  spaceAfter=2)
    sm   = ParagraphStyle("RC_Sm",   parent=base["Normal"],    fontSize=8,  textColor=colors.HexColor("#555555"))
    bold = ParagraphStyle("RC_Bold", parent=base["Normal"],    fontSize=9,  fontName="Helvetica-Bold")
    return h1, h2, h3, norm, sm, bold


def _table_style(header_bg=_BLUE) -> TableStyle:
    return TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR",   (0, 0), (-1, 0), _WHITE),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_WHITE, _LIGHT_BG]),
        ("GRID",        (0, 0), (-1, -1), 0.4, _GREY_LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",(0, 0), (-1, -1), 5),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ])


def _resolve_org_name(test) -> str:
    """Return school/org display name for the header."""
    if test.organization_id:
        try:
            return test.organization.name
        except Exception:
            return ""
    elif test.user_id:
        u = test.user
        full = getattr(u, "get_full_name", lambda: "")()
        return full or getattr(u, "email", "") or ""
    return ""


def _class_avg_by_topic(test) -> dict[str, float]:
    """
    Build a {topic: accuracy_pct} map averaged over all students for the test.
    Returns {} if there are no responses with topic data.
    """
    from results.models import StudentResult

    results = list(
        StudentResult.objects
        .filter(test=test)
        .prefetch_related("responses__question")
    )
    topic_totals: dict[str, list[int]] = {}  # topic → [correct_bools]
    for sr in results:
        for resp in sr.responses.all():
            q = resp.question
            topic = (q.topic.strip() if q and q.topic else "") or "Untagged"
            if topic not in topic_totals:
                topic_totals[topic] = []
            topic_totals[topic].append(1 if resp.is_correct else 0)

    return {
        topic: (sum(vals) / len(vals) * 100.0) if vals else 0.0
        for topic, vals in topic_totals.items()
    }


def _get_class_avg_score(test) -> Optional[float]:
    """Return the class average score as a percentage (0–100), or None."""
    from results.models import StudentResult
    scores = list(
        StudentResult.objects.filter(test=test).values_list("score", "max_score")
    )
    if not scores:
        return None
    pcts = [
        float(s) / float(m) * 100.0
        for s, m in scores
        if m and float(m) > 0
    ]
    return sum(pcts) / len(pcts) if pcts else None


def _get_distractor_note(test, student_result, q_pos: int, marked_options: list) -> Optional[str]:
    """
    Check TestProfile distractor data: was the student's chosen wrong option
    a commonly chosen distractor (rate_overall > 0.30)?
    Returns a short note string or None.
    """
    from analytics.models import TestProfile

    try:
        tp = TestProfile.objects.get(test=test)
    except TestProfile.DoesNotExist:
        return None

    profile = tp.profile or {}
    items = profile.get("items", [])
    if q_pos >= len(items):
        return None

    item = items[q_pos]
    distractor_data = item.get("distractor")
    if not distractor_data or not isinstance(distractor_data, dict):
        return None

    options = distractor_data.get("options", [])
    notes = []
    for marked in marked_options:
        for opt in options:
            if opt.get("label") == marked and not opt.get("is_key"):
                rate = opt.get("rate_overall", 0)
                if rate >= 0.30:
                    notes.append(
                        f"Option {marked} was chosen by {rate*100:.0f}% of students"
                    )
    return "; ".join(notes) if notes else None


# ---------------------------------------------------------------------------
# Page 1 — Parent-friendly summary
# ---------------------------------------------------------------------------

def _build_page1_story(
    test,
    student_result,
    student_profile,        # StudentProfile | None
    topic_acc: dict,        # {topic: {correct, total, accuracy}}
    class_topic_avg: dict,  # {topic: class_avg_pct}
    class_avg_pct: Optional[float],
    org_name: str,
    h1, h2, h3, norm, sm, bold,
) -> list:
    story = []

    # ---- Header ----
    if org_name:
        story.append(Paragraph(org_name, h1))
    story.append(Paragraph(f"<b>Test:</b> {test.title}", norm))
    if getattr(test, "subject", ""):
        story.append(Paragraph(f"<b>Subject:</b> {test.subject}", norm))
    story.append(Spacer(1, 0.3 * cm))

    # ---- Student info ----
    sr = student_result
    student = sr.student
    name   = (student.full_name or "") if student else "—"
    roll   = (student.roll_number or "") if student else "—"
    story.append(Paragraph(f"<b>Student:</b> {name}", h2))
    story.append(Paragraph(f"<b>Roll No.:</b> {roll}", norm))
    story.append(Spacer(1, 0.2 * cm))

    # ---- Big score block ----
    score     = float(sr.score)
    max_score = float(sr.max_score)
    pct       = score / max_score * 100.0 if max_score else 0.0

    small_cohort = False
    if student_profile:
        percentile  = student_profile.percentile
        rank        = student_profile.rank
        cohort_size = student_profile.cohort_size
    else:
        percentile  = None
        rank        = None
        cohort_size = None
        small_cohort = True

    score_str   = f"{score:.0f} / {max_score:.0f}  ({pct:.1f}%)"
    rank_str    = f"Rank {rank} of {cohort_size}" if rank is not None else "Rank unavailable — cohort too small"
    pct_str     = f"Percentile: {percentile:.1f}" if percentile is not None else "Percentile unavailable — cohort too small"

    score_data = [
        ["Score", "Percentile", "Rank"],
        [score_str, pct_str.replace("Percentile: ", ""), rank_str],
    ]
    score_tbl = Table(score_data, colWidths=[6 * cm, 5 * cm, 5.5 * cm])
    score_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), _BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0), _WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 10),
        ("FONTSIZE",     (0, 1), (-1, 1), 13),
        ("FONTNAME",     (0, 1), (-1, 1), "Helvetica-Bold"),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",         (0, 0), (-1, -1), 0.4, _GREY_LINE),
        ("ROWHEIGHTS",   (0, 0), (-1, 0), 18),
        ("ROWHEIGHTS",   (0, 1), (-1, 1), 28),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    story.append(score_tbl)

    if small_cohort:
        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(
            "<i>Note: Percentile and rank require at least 10 graded students.</i>", sm
        ))
    story.append(Spacer(1, 0.4 * cm))

    # ---- Topic performance bars OR overall correct/wrong/blank ----
    story.append(Paragraph("Topic Performance", h2))

    # Filter out only "Untagged" if there are real topics
    real_topics = {t: v for t, v in topic_acc.items() if t != "Untagged"}
    use_topics = bool(real_topics)

    if use_topics:
        display_topics = real_topics
    else:
        display_topics = topic_acc  # includes Untagged / overall

    if display_topics:
        # Draw horizontal bar for each topic
        bar_data = [["Topic", "Accuracy", "Score"]]
        for topic, stats in sorted(display_topics.items()):
            acc = stats["accuracy"] * 100.0
            correct = stats["correct"]
            total   = stats["total"]
            acc_str = f"{acc:.0f}%  ({correct}/{total})"
            # Colour the accuracy cell
            bar_data.append([topic, acc_str, ""])
        bar_tbl = Table(bar_data, colWidths=[6.5 * cm, 4 * cm, 6 * cm])
        bar_style = _table_style()
        # Colour accuracy cells per performance
        for row_idx, (topic, stats) in enumerate(sorted(display_topics.items()), start=1):
            acc = stats["accuracy"] * 100.0
            if acc >= 70:
                bg = colors.HexColor("#D5F5E3")
            elif acc >= 40:
                bg = colors.HexColor("#FFF3CD")
            else:
                bg = colors.HexColor("#FDECEA")
            bar_style.add("BACKGROUND", (1, row_idx), (1, row_idx), bg)
        bar_tbl.setStyle(bar_style)
        story.append(bar_tbl)
    else:
        # Fallback: correct/wrong/blank
        cw_data = [
            ["Correct", "Wrong", "Blank"],
            [str(sr.correct_count), str(sr.wrong_count), str(sr.blank_count)],
        ]
        cw_tbl = Table(cw_data, colWidths=[4 * cm, 4 * cm, 4 * cm])
        cw_tbl.setStyle(_table_style())
        story.append(cw_tbl)

    story.append(Spacer(1, 0.4 * cm))

    # ---- Strengths vs Needs Work ----
    if use_topics and len(real_topics) >= 2:
        story.append(Paragraph("Strengths &amp; Areas to Improve", h2))
        sorted_topics = sorted(real_topics.items(), key=lambda x: x[1]["accuracy"], reverse=True)
        best  = sorted_topics[0]
        worst = sorted_topics[-1]
        sw_data = [
            ["Strength (best topic)", "Needs Work (weakest topic)"],
            [
                f"{best[0]}  ({best[1]['accuracy']*100:.0f}%)",
                f"{worst[0]}  ({worst[1]['accuracy']*100:.0f}%)",
            ],
        ]
        sw_tbl = Table(sw_data, colWidths=[8.25 * cm, 8.25 * cm])
        sw_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), _BLUE),
            ("TEXTCOLOR",    (0, 0), (-1, 0), _WHITE),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 9),
            ("BACKGROUND",   (0, 1), (0, 1), colors.HexColor("#D5F5E3")),
            ("BACKGROUND",   (1, 1), (1, 1), colors.HexColor("#FDECEA")),
            ("GRID",         (0, 0), (-1, -1), 0.4, _GREY_LINE),
            ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ]))
        story.append(sw_tbl)
        story.append(Spacer(1, 0.4 * cm))

    # ---- Class average comparison ----
    story.append(Paragraph("Comparison with Class Average", h2))
    my_pct_fmt    = f"{pct:.1f}%"
    class_pct_fmt = f"{class_avg_pct:.1f}%" if class_avg_pct is not None else "N/A"
    if class_avg_pct is not None:
        delta = pct - class_avg_pct
        delta_str = f"+{delta:.1f}%" if delta >= 0 else f"{delta:.1f}%"
        delta_color = "#217346" if delta >= 0 else "#C0392B"
    else:
        delta_str  = "N/A"
        delta_color = "#555555"

    comp_data = [
        ["Your Score", "Class Average", "Delta"],
        [my_pct_fmt, class_pct_fmt, delta_str],
    ]
    comp_tbl = Table(comp_data, colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm])
    comp_style = _table_style()
    comp_style.add("TEXTCOLOR", (2, 1), (2, 1), colors.HexColor(delta_color))
    comp_style.add("FONTNAME",  (2, 1), (2, 1), "Helvetica-Bold")
    comp_tbl.setStyle(comp_style)
    story.append(comp_tbl)

    return story


# ---------------------------------------------------------------------------
# Page 2 — Teacher diagnostic
# ---------------------------------------------------------------------------

def _build_page2_story(
    test,
    student_result,
    topic_acc: dict,
    class_topic_avg: dict,
    h1, h2, h3, norm, sm, bold,
) -> list:
    story = []
    sr = student_result
    student = sr.student
    name = (student.full_name or "") if student else "—"
    roll = (student.roll_number or "") if student else "—"

    story.append(Paragraph(f"Diagnostic Report — {name} ({roll})", h1))
    story.append(Paragraph(f"<b>Test:</b> {test.title}", norm))
    story.append(Spacer(1, 0.3 * cm))

    # ---- Topic breakdown vs class table ----
    story.append(Paragraph("Topic Breakdown vs Class Average", h2))

    real_topics = {t: v for t, v in topic_acc.items() if t != "Untagged"}
    all_disp_topics = real_topics if real_topics else topic_acc

    if all_disp_topics:
        td_data = [["Topic", "Student Correct", "Student Acc", "Class Avg"]]
        for topic, stats in sorted(all_disp_topics.items()):
            acc     = stats["accuracy"] * 100.0
            c_avg   = class_topic_avg.get(topic)
            c_str   = f"{c_avg:.1f}%" if c_avg is not None else "N/A"
            td_data.append([
                topic,
                f"{stats['correct']}/{stats['total']}",
                f"{acc:.1f}%",
                c_str,
            ])
        td_tbl = Table(td_data, colWidths=[6 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm])
        td_tbl.setStyle(_table_style())
        story.append(td_tbl)
    else:
        story.append(Paragraph("No topic data available.", norm))

    story.append(Spacer(1, 0.4 * cm))

    # ---- Per-question table ----
    story.append(Paragraph("Per-Question Detail", h2))

    responses = list(sr.responses.select_related("question").order_by("q_pos"))

    # Build correct answers map from omr_sheet
    omr_sheet = sr.omr_sheet
    q_order = omr_sheet.question_order if omr_sheet else []
    answer_key = omr_sheet.answer_key if omr_sheet else {}

    pq_data = [["Q#", "Student's Answer", "Correct Answer", "Result"]]
    for resp in responses:
        q_pos = resp.q_pos
        q_num = q_pos + 1
        marked = ", ".join(resp.marked_options) if resp.marked_options else "—"
        # Correct answer from answer_key (printed labels)
        correct_printed = answer_key.get(str(q_pos), [])
        correct_str = ", ".join(correct_printed) if correct_printed else "?"

        if not resp.marked_options:
            result_sym = "blank"
        elif resp.is_correct:
            result_sym = "Correct"
        else:
            result_sym = "Wrong"

        pq_data.append([str(q_num), marked, correct_str, result_sym])

    pq_tbl = Table(pq_data, colWidths=[1.5 * cm, 4.5 * cm, 4.5 * cm, 2.5 * cm])
    pq_style = _table_style()
    for row_idx, resp in enumerate(responses, start=1):
        if not resp.marked_options:
            pq_style.add("TEXTCOLOR", (3, row_idx), (3, row_idx), _AMBER)
        elif resp.is_correct:
            pq_style.add("TEXTCOLOR", (3, row_idx), (3, row_idx), _GREEN)
        else:
            pq_style.add("TEXTCOLOR", (3, row_idx), (3, row_idx), _RED)
        pq_style.add("FONTNAME", (3, row_idx), (3, row_idx), "Helvetica-Bold")
    pq_tbl.setStyle(pq_style)
    story.append(pq_tbl)
    story.append(Spacer(1, 0.4 * cm))

    # ---- Missed-item clusters (wrong items by topic) ----
    wrong_responses = [r for r in responses if not r.is_correct and r.marked_options]
    if wrong_responses:
        story.append(Paragraph("Missed Items by Topic", h2))
        from collections import defaultdict
        by_topic: dict[str, list] = defaultdict(list)
        for resp in wrong_responses:
            q = resp.question
            topic = (q.topic.strip() if q and q.topic else "") or "Untagged"
            by_topic[topic].append(resp)

        missed_data = [["Topic", "Missed Questions (Q#)", "Distractor Note"]]
        for topic, resps in sorted(by_topic.items()):
            q_nums = ", ".join(str(r.q_pos + 1) for r in resps)
            # Distractor note for first wrong response in this topic
            notes = []
            for resp in resps:
                note = _get_distractor_note(test, sr, resp.q_pos, resp.marked_options)
                if note:
                    notes.append(f"Q{resp.q_pos+1}: {note}")
            note_str = "; ".join(notes) if notes else "—"
            # Truncate long notes
            if len(note_str) > 80:
                note_str = note_str[:77] + "..."
            missed_data.append([topic, q_nums, note_str])

        missed_tbl = Table(
            missed_data,
            colWidths=[4 * cm, 4 * cm, 8.5 * cm],
        )
        missed_tbl.setStyle(_table_style())
        story.append(missed_tbl)
    else:
        story.append(Paragraph("No wrong answers — nothing to cluster.", norm))

    return story


# ---------------------------------------------------------------------------
# Main entry: build one student's 2-page PDF
# ---------------------------------------------------------------------------

def _build_student_story(test, student_result) -> list:
    """Return a Platypus story (list of flowables) for one student, 2 pages."""
    from analytics.models import StudentProfile
    from analytics.services import student_detail

    h1, h2, h3, norm, sm, bold = _styles()

    # Student psychometric profile (for percentile/rank)
    try:
        sp = StudentProfile.objects.get(test=test, result=student_result)
    except StudentProfile.DoesNotExist:
        sp = None

    # Topic accuracy (per student)
    detail = student_detail(student_result)
    topic_acc = detail.get("topic_accuracy", {})

    # Class-level data
    class_topic_avg = _class_avg_by_topic(test)
    class_avg_pct   = _get_class_avg_score(test)
    org_name        = _resolve_org_name(test)

    # Load test with org relation if needed
    if test.organization_id and not hasattr(test, "_organization_loaded"):
        from assessments.models import Test as TestModel
        test = TestModel.objects.select_related("organization", "user").get(pk=test.pk)

    # Page 1
    page1 = _build_page1_story(
        test, student_result, sp,
        topic_acc, class_topic_avg, class_avg_pct,
        org_name,
        h1, h2, h3, norm, sm, bold,
    )

    # Page 2 (force page break between them)
    page2 = _build_page2_story(
        test, student_result,
        topic_acc, class_topic_avg,
        h1, h2, h3, norm, sm, bold,
    )

    return page1 + [PageBreak()] + page2


def _build_pdf_from_story(story: list, title: str) -> bytes:
    """Render a Platypus story to PDF bytes (A4)."""
    buf = io.BytesIO()

    margin = 2 * cm
    frame = Frame(
        margin, margin,
        A4_W - 2 * margin,
        A4_H - 2 * margin,
        id="body",
    )
    page_tpl = PageTemplate(id="A4", frames=[frame])
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title=title,
        pageTemplates=[page_tpl],
    )
    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def student_report_card(test, student_result) -> bytes:
    """
    Generate a two-page A4 PDF report card for one student.

    Parameters
    ----------
    test           : assessments.Test  (should be select_related("organization","user"))
    student_result : results.StudentResult

    Returns
    -------
    bytes — valid PDF content (starts with %PDF).
    """
    student = student_result.student
    name = (student.full_name or "student") if student else "student"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)

    story = _build_student_story(test, student_result)
    return _build_pdf_from_story(story, title=f"Report Card — {safe}")


def bulk_report_cards(test) -> bytes:
    """
    Generate a combined PDF of all graded students for the test.
    Each student occupies 2 pages.

    Parameters
    ----------
    test : assessments.Test

    Returns
    -------
    bytes — valid PDF content (starts with %PDF).
    Empty-cohort: returns a single-page "No results" PDF.
    """
    from results.models import StudentResult

    results = list(
        StudentResult.objects
        .filter(test=test)
        .select_related("student", "omr_sheet")
        .prefetch_related("responses__question")
        .order_by("student__roll_number", "id")
    )

    if not results:
        h1, h2, h3, norm, sm, bold = _styles()
        story = [
            Paragraph("Report Cards", h1),
            Paragraph(f"Test: {test.title}", norm),
            Spacer(1, 0.5 * cm),
            Paragraph("No graded students found for this test.", norm),
        ]
        return _build_pdf_from_story(story, title=f"Report Cards — {test.title}")

    story = []
    for idx, sr in enumerate(results):
        if idx > 0:
            story.append(PageBreak())
        story.extend(_build_student_story(test, sr))

    return _build_pdf_from_story(story, title=f"Report Cards — {test.title}")
