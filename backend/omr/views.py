"""
omr.views — Generation endpoint + OmrSheet list + scan upload + batch progress.

POST /api/v1/omr/generate/
    Body: {test, roster, shuffle_questions=false, shuffle_options=false,
           emit_question_paper=false}
    Returns 201: {sheets: [...], batch_pdf_url: str, count: int,
                  batch_paper_url: str|null}
    NOTE: emit_question_paper is auto-forced True when shuffle is on.

GET /api/v1/omr/sheets/?test=<id>
    Returns paginated list of OmrSheets scoped to request.user.

GET /api/v1/omr/sheets/<id>/question-paper/
    Authenticated, scoped endpoint — streams the per-student question paper PDF.
    Only the sheet owner/org can access it.  Anonymous → 403/404.

POST /api/v1/omr/scan/
    Multipart: test (id) + files (one or more images/PDFs)
    Returns 201: {batch_id, total, processed}

GET /api/v1/omr/scan-batches/<id>/
    Returns {id, status, total, processed}
"""
import hashlib
import io
import os
import uuid

import cv2
import fitz  # PyMuPDF
import numpy as np
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

import billing.limits as billing_limits
from assessments.models import Test
from common.scope import (
    can_edit_class,
    get_active_org,
    parent_in_scope,
    scope_filter,
    visibility_q,
)
from omr.codes import make_sheet_code
from omr.geometry import build_template
from omr.generator import render_sheet_pdf
from omr.models import GenerationEvent, OmrSheet, ScanBatch, ScanEvent, ScanJob
from omr.question_paper import render_question_paper_pdf
from omr.serializers import GenerateSerializer, OmrSheetSerializer, ScanBatchSerializer
from omr.shuffle import build_sheet_plan
from organizations.models import Organization
from rosters.models import Roster

# Free-tier limits (solo/per-user fallback)
MAX_STUDENTS = 10
MAX_DAILY_GENERATIONS = 5


class _GateExceeded(Exception):
    """Internal signal that a plan gate was exceeded under the per-org lock.

    Raised inside a ``transaction.atomic()`` block so the lock-holding
    transaction rolls back; the view catches it and returns a 403 with the
    carried detail message outside the atomic block.
    """


_BIGINT_MAX = (2**63) - 1  # max signed 64-bit integer (PostgreSQL bigint)


def _derive_seed(test_id: int, student_id: int) -> int:
    """Stable per-sheet integer seed from (test_id, student_id), fits in a signed bigint."""
    raw = f"{test_id}:{student_id}".encode()
    digest = hashlib.sha256(raw).digest()
    # Take first 8 bytes as big-endian unsigned, then mask to signed 63-bit range
    unsigned = int.from_bytes(digest[:8], "big")
    return unsigned & _BIGINT_MAX  # clears the sign bit → always positive and ≤ BIGINT_MAX


class GenerateView(APIView):
    """
    POST /api/v1/omr/generate/

    Validates ownership, enforces free-tier gates, builds per-student OMR sheets,
    merges them into a batch PDF, persists everything, records a GenerationEvent,
    and returns 201 with the sheet list + batch PDF URL.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        test_id = data["test"]
        roster_id = data["roster"]
        shuffle_questions = data["shuffle_questions"]
        shuffle_options = data["shuffle_options"]
        emit_question_paper = data["emit_question_paper"]  # auto-forced True when shuffle on

        # ---- ownership validation ----------------------------------------
        try:
            test = Test.objects.get(pk=test_id)
        except Test.DoesNotExist:
            return Response({"test": "Test not found."}, status=status.HTTP_400_BAD_REQUEST)

        if not parent_in_scope(test, request):
            return Response(
                {"test": "Test not found in your account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            roster = Roster.objects.get(pk=roster_id)
        except Roster.DoesNotExist:
            return Response({"roster": "Roster not found."}, status=status.HTTP_400_BAD_REQUEST)

        if not parent_in_scope(roster, request):
            return Response(
                {"roster": "Roster not found in your account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---- folder visibility / EDIT gate (Phase 5B) --------------------
        # Generating sheets is a WRITE on the test's class: require EDIT rights
        # (folder creator / EDIT share / active-org admin). VIEW-only → 403.
        if not can_edit_class(request, test.class_group):
            return Response(
                {"detail": "You have view-only access to this folder; editing is not permitted."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ---- generation gates (org-aware) --------------------------------
        students = list(roster.students.order_by("roll_number", "id"))
        org = get_active_org(request)

        if org is not None:
            # Org scope: enforce per-org quota and RESERVE the slot atomically.
            # Serialize concurrent same-org requests with a row lock, re-check
            # under the lock, then record the GenerationEvent now (before the
            # expensive PDF work) so two concurrent calls can't both pass the
            # gate and exceed the cap (closes the TOCTOU window).
            try:
                with transaction.atomic():
                    Organization.objects.select_for_update().get(pk=org.pk)
                    if not billing_limits.can_generate(org, len(students)):
                        plan = billing_limits.org_plan(org)
                        # Distinguish student cap vs daily cap for a useful message.
                        if (
                            plan.students_per_generation_limit is not None
                            and len(students) > plan.students_per_generation_limit
                        ):
                            detail = (
                                f"Your plan allows up to "
                                f"{plan.students_per_generation_limit} students per generation. "
                                "Upgrade your plan to generate larger batches."
                            )
                        else:
                            detail = (
                                "Daily generation limit reached for your organisation's plan. "
                                "Upgrade your plan for more daily generations."
                            )
                        # Raise to roll back the lock-holding transaction, then
                        # return the 403 outside the atomic block.
                        raise _GateExceeded(detail)
                    # Reserve the slot now (org=org).
                    GenerationEvent.objects.create(
                        user=request.user, test=test, organization=org
                    )
            except _GateExceeded as exc:
                return Response(
                    {"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN
                )
        else:
            # Solo scope: original per-user free-tier checks (unchanged).
            if len(students) > MAX_STUDENTS:
                return Response(
                    {
                        "detail": (
                            f"Free tier allows up to {MAX_STUDENTS} students per generation. "
                            "Upgrade your plan to generate larger batches."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            today = timezone.now().date()
            daily_count = GenerationEvent.objects.filter(
                user=request.user, created_at__date=today
            ).count()
            if daily_count >= MAX_DAILY_GENERATIONS:
                return Response(
                    {
                        "detail": (
                            f"Free tier allows up to {MAX_DAILY_GENERATIONS} generations per day. "
                            "Upgrade your plan for unlimited daily generations."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # ---- build descriptor (same layout for all students of this test) -
        questions_qs = test.questions.prefetch_related("options").order_by("order_index", "id")
        questions_list = list(questions_qs)

        num_questions = len(questions_list)
        if num_questions == 0:
            return Response(
                {"detail": "Test has no questions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # num_options = max(test.default_options, max options across questions),
        # clamped to [2, 6].  test.default_options (default 4) lets a 5-option
        # test always lay out 5 columns even if some questions have fewer options.
        max_options = max(
            (q.options.count() for q in questions_list), default=2
        )
        test_default_options = getattr(test, "default_options", 4) or 4
        num_options = max(2, min(6, max(test_default_options, max_options)))

        # roll_digits = max(2, digits of largest roll_number)
        roll_numbers = [s.roll_number for s in students if s.roll_number]
        try:
            max_roll_int = max(int(r) for r in roll_numbers if r.isdigit())
        except ValueError:
            max_roll_int = 99
        roll_digits = max(2, len(str(max_roll_int)))

        # Resolve roll_kind from the test's mode (Phase 1A)
        test_mode = getattr(test, "mode", "standard")
        roll_kind = "prebubbled" if test_mode == "roster_prebubbled" else "writein"

        # Build section metadata for competitive tests (Phase 3B).
        # Sections are authored in canonical Question.order_index space;
        # the printed q_pos order matches the shuffled question_order.
        # For the descriptor we pass canonical-space sections as q_pos_range
        # references so the generator can draw section headers.
        # NOTE: the descriptor sections block is purely cosmetic metadata
        # (C2 invariant: answer bubble cx/cy/r are never moved).
        sections_for_descriptor = None
        if test_mode == "competitive":
            raw_sections = list(
                test.sections.order_by("order_index", "id")
                .values("key", "label", "order_index", "q_start", "q_end",
                        "policy", "choose_k")
            )
            if raw_sections:
                sections_for_descriptor = []
                for s in raw_sections:
                    # q_start/q_end are 1-based; convert to 0-based q_pos
                    lo = s["q_start"] - 1
                    hi = s["q_end"] - 1
                    policy_info = {"type": s["policy"]}
                    if s["policy"] == "choose_k" and s["choose_k"]:
                        policy_info["k"] = s["choose_k"]
                    sections_for_descriptor.append({
                        "key": s["key"],
                        "label": s["label"],
                        "order_index": s["order_index"],
                        "q_pos_range": [lo, hi],
                        "policy": policy_info,
                    })

        descriptor = build_template(
            num_questions=num_questions,
            num_options=num_options,
            roll_digits=roll_digits,
            roll_kind=roll_kind,
            sections=sections_for_descriptor,
        )

        # Build question dicts for shuffle
        question_dicts = [
            {
                "id": q.id,
                "options": [
                    {"label": o.label, "is_correct": o.is_correct}
                    for o in q.options.order_by("label", "id")
                ],
            }
            for q in questions_list
        ]

        # ---- resolve branding once (Test → Org fallback) -----------------
        # Resolution order per S4/Phase-3b spec:
        #   1. Test.sheet_heading / Test.logo (explicit test-level branding)
        #   2. If brand_inherit_org=True → Org.default_sheet_heading / Org.logo
        #   3. If nothing → no branding (sheet unchanged, descriptor identical)
        resolved_heading = ""
        resolved_logo_path = ""
        resolved_logo_position = "left"

        test_heading = getattr(test, "sheet_heading", "") or ""
        test_logo = getattr(test, "logo", None)
        test_logo_field = test_logo if test_logo and test_logo.name else None
        test_logo_position = getattr(test, "logo_position", "left") or "left"
        brand_inherit_org = getattr(test, "brand_inherit_org", True)

        # Fetch org branding once (avoid repeated DB queries per student)
        org_fresh = None
        if brand_inherit_org and org is not None:
            org_fresh = Organization.objects.filter(pk=org.pk).first()

        if test_heading:
            resolved_heading = test_heading
            resolved_logo_position = test_logo_position
        elif org_fresh:
            resolved_heading = getattr(org_fresh, "default_sheet_heading", "") or ""
            resolved_logo_position = "left"  # org doesn't have a position field

        if test_logo_field:
            try:
                resolved_logo_path = test_logo_field.path
                resolved_logo_position = test_logo_position
            except (ValueError, AttributeError):
                resolved_logo_path = ""
        elif org_fresh:
            org_logo = getattr(org_fresh, "logo", None)
            if org_logo and org_logo.name:
                try:
                    resolved_logo_path = org_logo.path
                except (ValueError, AttributeError):
                    resolved_logo_path = ""

        # ---- per-student sheet generation --------------------------------
        created_sheets = []
        per_student_pdfs = []   # list of bytes (OMR sheets)
        per_student_papers = [] # list of bytes (question papers, when emit flag set)

        for student in students:
            seed = _derive_seed(test.id, student.id)
            sheet_code, human_code = make_sheet_code(test.id, seed)

            plan = build_sheet_plan(
                questions=question_dicts,
                seed=seed,
                shuffle_questions=shuffle_questions,
                shuffle_options=shuffle_options,
            )

            # For Mode B (roster_prebubbled), embed the student's roll number in
            # the sheet dict so the generator can draw pre-filled discs. Print the
            # roll ZERO-PADDED to the grid width so a short roll fills every column
            # right-aligned (conventional OMR), not left-aligned with trailing
            # blanks. Digits-only for now (alphanumeric charset deferred). The
            # scanner reconciles via symmetric zfill, so identity is unaffected.
            student_roll = student.roll_number or ""
            if roll_kind == "prebubbled":
                roll_value = student_roll.zfill(roll_digits) if student_roll.isdigit() else student_roll
            else:
                roll_value = ""
            sheet_dict = {
                "sheet_code": sheet_code,
                "human_readable_code": human_code,
                "institution": "",
                "test_title": test.title,
                "subject": getattr(test, "subject", ""),
                "student_name": student.full_name or "",
                "roll_label": "Roll No.",
                "roll_digits": roll_digits,
                "roll_value": roll_value,
                # Phase 3b branding (absent → generator skips branding, output unchanged)
                "heading": resolved_heading,
                "logo_path": resolved_logo_path,
                "logo_position": resolved_logo_position,
            }

            pdf_bytes = render_sheet_pdf(sheet_dict, descriptor)
            per_student_pdfs.append(pdf_bytes)

            # Idempotent per (test, student): regenerating a test's sheets must
            # NOT 500 on the deterministic sheet_code's unique constraint. The
            # seed is derived purely from (test, student), so a regenerated
            # sheet is logically identical (same answer_key / shuffle / code);
            # update the existing row in place — this preserves its pk, so any
            # ScanJobs / StudentResults that reference it stay valid.
            omr_sheet, _created = OmrSheet.objects.update_or_create(
                test=test,
                student=student,
                defaults={
                    "sheet_code": sheet_code,
                    "human_readable_code": human_code,
                    "shuffle_version": seed,
                    "question_order": plan["question_order"],
                    "option_order": plan["option_order"],
                    "answer_key": plan["answer_key"],
                    "template_descriptor": descriptor,
                    "page_count": descriptor["page_count"],
                    "page_map": descriptor["page_map"],
                    "assembly_status": OmrSheet.ASSEMBLY_READY,
                    "roll_kind": roll_kind,
                    "roll_value": roll_value,
                },
            )

            # Save per-student OMR PDF file
            pdf_filename = f"omr_sheets/{sheet_code}.pdf"
            omr_sheet.pdf_file.save(pdf_filename, ContentFile(pdf_bytes), save=True)

            # Generate and save question paper when emit flag is set
            if emit_question_paper:
                paper_bytes = render_question_paper_pdf(omr_sheet)
                paper_filename = f"omr_papers/{sheet_code}-paper.pdf"
                omr_sheet.question_paper_file.save(
                    paper_filename, ContentFile(paper_bytes), save=True
                )
                per_student_papers.append(paper_bytes)

            created_sheets.append(omr_sheet)

        # ---- merge all student PDFs into one batch PDF -------------------
        out_doc = fitz.open()
        for pdf_bytes in per_student_pdfs:
            src = fitz.open(stream=pdf_bytes, filetype="pdf")
            out_doc.insert_pdf(src)
            src.close()

        batch_bytes = out_doc.tobytes()
        out_doc.close()

        # Save batch OMR PDF to MEDIA
        from django.core.files.storage import default_storage
        batch_filename = f"omr_batches/{test.id}-{uuid.uuid4().hex}.pdf"
        batch_content = ContentFile(batch_bytes)
        batch_path = default_storage.save(batch_filename, batch_content)
        batch_url = request.build_absolute_uri(
            f"/media/{batch_path.replace(chr(92), '/')}"
        )

        # Per-student question papers are saved + authenticated above. The BATCH
        # is a multi-student PII document — do NOT write it to /media/ (which is
        # served unauthenticated). Expose it ONLY via the authenticated,
        # scope-checked batch endpoint, which merges the papers on demand.
        batch_paper_url = None
        if per_student_papers:
            batch_paper_url = request.build_absolute_uri(
                f"/api/v1/omr/tests/{test.id}/question-papers/"
            )

        # ---- record GenerationEvent (solo only) -------------------------
        # Org-context events were already reserved under the per-org lock above
        # to close the TOCTOU window; only solo events are recorded here.
        if org is None:
            GenerationEvent.objects.create(
                user=request.user, test=test, organization=None
            )

        # ---- response ---------------------------------------------------
        sheet_data = OmrSheetSerializer(
            created_sheets, many=True, context={"request": request}
        ).data

        resp_data = {
            "sheets": sheet_data,
            "batch_pdf_url": batch_url,
            "count": len(created_sheets),
        }
        if batch_paper_url is not None:
            resp_data["batch_paper_url"] = batch_paper_url

        return Response(resp_data, status=status.HTTP_201_CREATED)


class OmrSheetListView(generics.ListAPIView):
    """
    GET /api/v1/omr/sheets/?test=<id>

    List OmrSheets scoped to request.user via test__user.
    Optional ?test= filter narrows to a specific test.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = OmrSheetSerializer

    def get_queryset(self):
        qs = OmrSheet.objects.filter(
            scope_filter(self.request, "test__")
            & visibility_q(self.request, "test__class_group__", "test__created_by")
        ).distinct()
        test_id = self.request.query_params.get("test")
        if test_id:
            qs = qs.filter(test_id=test_id)
        return qs


# ---------------------------------------------------------------------------
# Scan upload + batch progress
# ---------------------------------------------------------------------------

def _pdf_to_images(file_bytes: bytes) -> list[bytes]:
    """
    Split a PDF into one PNG bytes per page using PyMuPDF.
    Returns a list of PNG bytes (one per page).
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    images = []
    for page in doc:
        # Render at 200 DPI for reliable QR + fiducial detection
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        images.append(png_bytes)
    doc.close()
    return images


class ScanUploadView(APIView):
    """
    POST /api/v1/omr/scan/

    Multipart fields:
        test  : int (Test id)
        files : one or more uploaded files (images or a multi-page PDF)

    Validates that the test belongs to request.user.
    Creates a ScanBatch; for each file:
        - If PDF → split into per-page PNG images via fitz.
        - Else → treat as a single image.
    For each image page → creates a ScanJob, saves the image bytes,
    then EAGERLY calls process_scan_job (synchronous in dev).
    Updates batch total/processed; sets batch status=done.
    Returns 201 {batch_id, total, processed}.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        test_id = request.data.get("test")
        if not test_id:
            return Response(
                {"test": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            test = Test.objects.get(pk=test_id)
        except Test.DoesNotExist:
            return Response(
                {"test": "Test not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not parent_in_scope(test, request):
            return Response(
                {"test": "Test not found in your account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---- folder visibility / EDIT gate (Phase 5B) --------------------
        # Uploading scans is a WRITE on the test's class: require EDIT rights.
        if not can_edit_class(request, test.class_group):
            return Response(
                {"detail": "You have view-only access to this folder; editing is not permitted."},
                status=status.HTTP_403_FORBIDDEN,
            )

        uploaded_files = request.FILES.getlist("files")
        if not uploaded_files:
            return Response(
                {"files": "At least one file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---- scan gate (org-aware) — RESERVE before processing ------------
        # Serialize concurrent same-org uploads with a per-org row lock,
        # re-check the monthly cap under the lock, and record the ScanEvent
        # (reserve the slot) BEFORE the expensive pipeline work, so two
        # concurrent uploads can't both pass the gate and exceed the cap.
        scan_org = get_active_org(request)
        if scan_org is not None:
            try:
                with transaction.atomic():
                    Organization.objects.select_for_update().get(pk=scan_org.pk)
                    if not billing_limits.can_scan(scan_org):
                        plan = billing_limits.org_plan(scan_org)
                        raise _GateExceeded(
                            f"Monthly scan limit reached for your organisation's plan "
                            f"({plan.monthly_scan_limit} scans/month). "
                            "Upgrade to scan more sheets."
                        )
                    # Reserve the slot now (one ScanEvent per upload batch).
                    ScanEvent.objects.create(
                        user=request.user, test=test, organization=scan_org
                    )
            except _GateExceeded as exc:
                return Response(
                    {"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN
                )

        # Create ScanBatch
        batch = ScanBatch.objects.create(
            test=test,
            created_by=request.user,
            status=ScanBatch.STATUS_PROCESSING,
        )

        # Build the list of (page_no, image_bytes) to process
        page_images: list[tuple[int, bytes, str]] = []  # (page_no, bytes, filename)
        page_counter = 0

        for uploaded_file in uploaded_files:
            content_type = uploaded_file.content_type or ""
            file_name = uploaded_file.name or ""
            ext = os.path.splitext(file_name)[1].lower()
            file_bytes = uploaded_file.read()

            is_pdf = (
                content_type == "application/pdf"
                or ext == ".pdf"
            )

            if is_pdf:
                try:
                    per_page = _pdf_to_images(file_bytes)
                except Exception as e:
                    # PDF parse failure — skip this file gracefully
                    continue
                for i, png_bytes in enumerate(per_page):
                    page_counter += 1
                    page_images.append((page_counter, png_bytes, f"page_{page_counter}.png"))
            else:
                page_counter += 1
                page_images.append((page_counter, file_bytes, f"page_{page_counter}{ext or '.png'}"))

        total = len(page_images)
        batch.total = total
        batch.save(update_fields=["total"])

        if total == 0:
            batch.status = ScanBatch.STATUS_DONE
            batch.save(update_fields=["status"])
            return Response(
                {"batch_id": batch.id, "total": 0, "processed": 0},
                status=status.HTTP_201_CREATED,
            )

        # Enqueue one task per page image.
        # Under CELERY_TASK_ALWAYS_EAGER=True (dev / tests) .delay() runs
        # the task synchronously inline, so all processing is complete before
        # the loop returns — identical behaviour to the old direct call.
        # In production (CELERY_TASK_ALWAYS_EAGER=False) the tasks run async
        # on a worker and the batch status is updated by the task itself.
        from omr.tasks import process_scan_job_task

        for page_no, img_bytes, fname in page_images:
            job = ScanJob(batch=batch, page_no=page_no)
            job.image_file.save(fname, ContentFile(img_bytes), save=True)
            process_scan_job_task.delay(job.id)

        # Under eager mode the tasks have already run; refresh to get the
        # final counters set by the tasks.  In async mode this reflects
        # whatever has been processed so far (usually 0 — the client polls
        # /scan-batches/<id>/ for progress).
        batch.refresh_from_db()

        # ---- record ScanEvent per batch (solo only) ----------------------
        # Org-context ScanEvents were already reserved under the per-org lock
        # before processing (closes the TOCTOU window).  Solo uploads have no
        # hard cap, so record their event here once the batch completes.
        # Granularity: per-batch (one event per upload call, not per page).
        if scan_org is None:
            ScanEvent.objects.create(
                user=request.user,
                test=test,
                organization=None,
            )

        return Response(
            {
                "batch_id": batch.id,
                "total": batch.total,
                "processed": batch.processed,
            },
            status=status.HTTP_201_CREATED,
        )


class ScanBatchDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/omr/scan-batches/<id>/

    Returns batch progress {id, status, total, processed}.
    Scoped to request.user via test__user (404 on cross-tenant access).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ScanBatchSerializer

    def get_queryset(self):
        return ScanBatch.objects.filter(
            scope_filter(self.request, "test__")
            & visibility_q(self.request, "test__class_group__", "test__created_by")
        ).distinct()


class OmrSheetQuestionPaperView(APIView):
    """
    GET /api/v1/omr/sheets/<pk>/question-paper/

    Authenticated, scoped endpoint — streams the per-student question paper PDF.

    Security (S1):
    - Requires authentication (IsAuthenticated).
    - Enforces owner/org scope via scope_filter("test__") so a member of a
      different user/org cannot access another user's paper.
    - Returns 404 (not 403) when the sheet exists but is outside scope, to
      avoid leaking whether the sheet id exists.
    - Returns 404 when question_paper_file is not set (no paper generated yet).

    Phase 5B: visibility_q (folder sharing) is ANDed into the scope filter, so a
    member without a visibility grant on the test's class gets 404 (no IDOR).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # Scope-filter through the test owner chain + folder visibility
        qs = OmrSheet.objects.filter(
            scope_filter(request, "test__")
            & visibility_q(request, "test__class_group__", "test__created_by"),
            pk=pk,
        ).distinct()
        try:
            omr_sheet = qs.get()
        except OmrSheet.DoesNotExist:
            raise Http404

        if not omr_sheet.question_paper_file:
            raise Http404

        try:
            f = omr_sheet.question_paper_file.open("rb")
        except (FileNotFoundError, OSError):
            raise Http404

        sheet_code = omr_sheet.sheet_code or str(pk)
        response = FileResponse(
            f,
            content_type="application/pdf",
            as_attachment=False,
        )
        response["Content-Disposition"] = (
            f'inline; filename="{sheet_code}-paper.pdf"'
        )
        return response


class OmrTestQuestionPapersBatchView(APIView):
    """
    GET /api/v1/omr/tests/<pk>/question-papers/

    Authenticated, scoped — merges ALL of the test's per-student question papers
    into one PDF and streams it. This is a multi-student PII document, so it is
    served ONLY here (auth + owner/org scope), never via /media/ or AllowAny.

    Phase 5B: visibility_q (folder sharing) is ANDed into the Test scope filter.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            test = Test.objects.filter(
                scope_filter(request)
                & visibility_q(request, "class_group__", "created_by"),
                pk=pk,
            ).distinct().get()
        except Test.DoesNotExist:
            raise Http404

        sheets = (
            OmrSheet.objects.filter(test=test)
            .exclude(question_paper_file="")
            .order_by("id")
        )
        merged = fitz.open()
        found = False
        for sheet in sheets:
            try:
                data = sheet.question_paper_file.open("rb").read()
            except (FileNotFoundError, OSError, ValueError):
                continue
            src = fitz.open(stream=data, filetype="pdf")
            merged.insert_pdf(src)
            src.close()
            found = True
        if not found:
            merged.close()
            raise Http404

        out = merged.tobytes()
        merged.close()
        response = FileResponse(
            io.BytesIO(out),
            content_type="application/pdf",
            as_attachment=True,
            filename=f"question-papers-test-{test.id}.pdf",
        )
        return response


class ScanBatchSheetsView(APIView):
    """
    GET /api/v1/omr/scan-batches/<id>/sheets/

    Returns the list of ScanJobs for a batch, each with id, page_no, status,
    confidence, error_reason, reads (answers + fill_ratios), omr_sheet id,
    and warped_image_url.

    Scoped to request.user via test__ (404 on cross-tenant access).

    Phase 5B: visibility_q (folder sharing) is ANDed into the scope filter.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # Scope batch to owner + folder visibility
        batch_qs = ScanBatch.objects.filter(
            scope_filter(request, "test__")
            & visibility_q(request, "test__class_group__", "test__created_by")
        ).distinct()
        try:
            batch = batch_qs.get(pk=pk)
        except ScanBatch.DoesNotExist:
            raise Http404

        from results.models import StudentResult

        jobs = list(
            ScanJob.objects.filter(batch=batch)
            .select_related("omr_sheet", "omr_sheet__student")
            .order_by("page_no", "id")
        )
        sheet_ids = [j.omr_sheet_id for j in jobs if j.omr_sheet_id]
        results_by_sheet = {
            r.omr_sheet_id: r
            for r in StudentResult.objects.filter(omr_sheet_id__in=sheet_ids)
        }

        data = []
        for job in jobs:
            sheet = job.omr_sheet
            warped_url = (
                request.build_absolute_uri(f"/api/v1/omr/scan-jobs/{job.id}/warped/")
                if job.warped_file else None
            )

            student = None
            answer_key = None
            bubble_geometry = []
            sheet_code = None
            if sheet is not None:
                sheet_code = sheet.sheet_code
                answer_key = sheet.answer_key
                if sheet.student_id:
                    st = sheet.student  # full_name decrypts on access
                    student = {"id": st.id, "name": st.full_name or "", "roll": st.roll_number}
                # Flatten answer-bubble geometry -> [{q_pos, label, cx, cy, r}]
                for entry in (sheet.template_descriptor or {}).get("answer_bubbles", []):
                    qp = entry.get("q_pos")
                    for opt in entry.get("options", []):
                        bubble_geometry.append({
                            "q_pos": qp, "label": opt.get("label"),
                            "cx": opt.get("cx"), "cy": opt.get("cy"), "r": opt.get("r"),
                        })

            sr = results_by_sheet.get(job.omr_sheet_id)
            student_result = None
            if sr is not None:
                student_result = {
                    "id": sr.id, "score": float(sr.score), "max_score": float(sr.max_score),
                    "correct_count": sr.correct_count, "wrong_count": sr.wrong_count,
                    "blank_count": sr.blank_count, "needs_review": sr.needs_review,
                }

            reads = job.reads or {}
            data.append({
                "id": job.id,
                "scan_job_id": job.id,
                "page_no": job.page_no,
                "status": job.status,
                "confidence": job.confidence,
                "error_reason": job.error_reason,
                "flags": reads.get("flags", []),
                "detected": reads,
                "reads": reads,
                "omr_sheet_id": job.omr_sheet_id,
                "sheet_code": sheet_code,
                "student": student,
                "student_result": student_result,
                "answer_key": answer_key,
                "bubble_geometry": bubble_geometry,
                "warped_image_url": warped_url,
                "warped_url": warped_url,
            })
        return Response(data, status=status.HTTP_200_OK)


class ScanJobWarpedView(APIView):
    """
    GET /api/v1/omr/scan-jobs/<id>/warped/

    Authenticated, scoped endpoint -- streams the warped canonical PNG for a ScanJob.

    Security:
    - Requires authentication (IsAuthenticated).
    - Enforces owner/org scope via test__ chain; 404 (not 403) on cross-tenant.
    - Returns 404 when warped_file is not set (not yet processed or alignment failed).

    Phase 5B: visibility_q (folder sharing) is ANDed into the scope filter.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # Scope: ScanJob -> batch -> test -> user/org + folder visibility
        job_qs = ScanJob.objects.filter(
            scope_filter(request, "batch__test__")
            & visibility_q(
                request, "batch__test__class_group__", "batch__test__created_by"
            ),
            pk=pk,
        ).distinct()
        try:
            job = job_qs.get()
        except ScanJob.DoesNotExist:
            raise Http404

        if not job.warped_file:
            raise Http404

        try:
            f = job.warped_file.open("rb")
        except (FileNotFoundError, OSError):
            raise Http404

        response = FileResponse(
            f,
            content_type="image/png",
            as_attachment=False,
        )
        response["Content-Disposition"] = f'inline; filename="warped_job_{pk}.png"'
        return response


class OmrSheetRegradeView(APIView):
    """
    POST /api/v1/omr/sheets/<id>/regrade/

    Two modes:

    1. CORRECTION MODE — body contains ``answers``:
       Body: {answers: {q_pos: [labels]}, roll?: str, student_id?: int}
       Treats the supplied answers as the authoritative, corrected reads for
       the whole sheet.  Persists them back onto the sheet's primary ScanJob
       (so the correction sticks), re-grades via the shared helper, and
       auto-resolves all open ReviewItems for the sheet.

    2. RE-GRADE MODE — no body (or body without ``answers``):
       Re-grades the sheet using its existing ScanJob reads unchanged.
       Returns 400 when no usable reads exist.

    Both modes:
    - Do NOT create a new ScanEvent (no double-charge).
    - Auto-resolve all open ReviewItems and recompute needs_review.
    - Return 200 with the updated StudentResult.

    Scoped to request.user via test__ (404 on cross-tenant access).

    Phase 5B: visibility_q (folder sharing) is ANDed into the scope filter for the
    read; the regrade WRITE additionally requires EDIT rights on the governing
    class (folder creator / EDIT share / active-org admin) — VIEW-only → 403.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        # Scope-filter through the test owner chain + folder visibility
        qs = OmrSheet.objects.filter(
            scope_filter(request, "test__")
            & visibility_q(request, "test__class_group__", "test__created_by"),
            pk=pk,
        ).distinct()
        try:
            omr_sheet = qs.get()
        except OmrSheet.DoesNotExist:
            raise Http404

        if not can_edit_class(request, omr_sheet.test.class_group):
            return Response(
                {"detail": "You have view-only access to this folder; editing is not permitted."},
                status=status.HTTP_403_FORBIDDEN,
            )

        from omr.models import ScanJob as _ScanJob
        from omr.scan.grade import grade_sheet
        from omr.scan.pipeline import _persist_grading_result
        from results.models import ReviewItem, StudentResult
        from results.serializers import StudentResultSerializer
        from rosters.models import Student as _Student

        body = request.data or {}
        corrected_answers = body.get("answers")  # None when no body / no key

        # ---- Gather usable jobs (same logic as _maybe_grade) ----
        processable_jobs = list(
            _ScanJob.objects.filter(
                omr_sheet=omr_sheet,
                status__in=[_ScanJob.STATUS_DONE, _ScanJob.STATUS_NEEDS_REVIEW],
            )
        )
        done_jobs = [
            j for j in processable_jobs
            if j.reads and "answers" in j.reads
        ]

        if corrected_answers is None:
            # RE-GRADE MODE: require existing usable reads
            if not done_jobs:
                return Response(
                    {"detail": "No usable scan reads found for this sheet."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Aggregate reads from existing ScanJob data
            aggregated_reads: dict[int, list] = {}
            for job in done_jobs:
                answers = job.reads.get("answers", {})
                for q_pos_str, entry in answers.items():
                    q_pos = int(q_pos_str)
                    marked = entry.get("marked", [])
                    if q_pos not in aggregated_reads:
                        aggregated_reads[q_pos] = list(marked)
                    else:
                        aggregated_reads[q_pos].extend(
                            lbl for lbl in marked if lbl not in aggregated_reads[q_pos]
                        )

        else:
            # CORRECTION MODE: use supplied answers as authoritative reads
            # Validate: answers must be a dict
            if not isinstance(corrected_answers, dict):
                return Response(
                    {"detail": "answers must be an object mapping q_pos to label list."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Build aggregated_reads from corrected_answers
            aggregated_reads = {
                int(q_pos_str): list(labels)
                for q_pos_str, labels in corrected_answers.items()
            }

            # Persist corrected answers back onto the primary ScanJob so they stick.
            # If there's an existing usable job, patch its reads.answers with the
            # corrected values (overriding the scanned reads for each supplied q_pos).
            # If there are no existing jobs (edge-case: correction before any scan),
            # synthesize a virtual job record.
            if done_jobs:
                primary_job = done_jobs[0]
                existing_reads = dict(primary_job.reads)
                existing_answers = dict(existing_reads.get("answers", {}))

                # Override with corrected values
                for q_pos_str, labels in corrected_answers.items():
                    existing_answers[str(q_pos_str)] = {
                        "marked": list(labels),
                        "flag": None,  # correction is authoritative — clear any flag
                    }

                existing_reads["answers"] = existing_answers
                # Clear per-question flags that are now resolved by correction
                existing_reads["flags"] = []

                primary_job.reads = existing_reads
                primary_job.status = _ScanJob.STATUS_DONE  # correction resolves review state
                primary_job.error_reason = ""
                primary_job.save(update_fields=["reads", "status", "error_reason"])

                # Refresh done_jobs to reflect the update
                done_jobs = [primary_job] + [j for j in done_jobs if j.pk != primary_job.pk]
            else:
                # No existing scan jobs at all — return 400 in correction mode too,
                # because we have no template/descriptor reference to build from.
                return Response(
                    {"detail": "No usable scan reads found for this sheet."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Optional: reattach / update student when roll or student_id supplied
            new_roll = body.get("roll")
            new_student_id = body.get("student_id")

            if new_student_id is not None:
                # Reattach to a specific student — SCOPED to the requester's own
                # rosters (solo or active org) to prevent cross-tenant IDOR.
                # 404 (not 400) so we don't leak which student ids exist globally.
                try:
                    student = _Student.objects.get(
                        scope_filter(request, "roster__"),
                        pk=new_student_id,
                    )
                    omr_sheet.student = student
                    omr_sheet.save(update_fields=["student"])
                except _Student.DoesNotExist:
                    return Response(
                        {"detail": f"Student {new_student_id} not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            elif new_roll is not None:
                # Resolve by roll number within the requester's scope only
                # (best-effort; no error if ambiguous — the sheet keeps its student).
                try:
                    student = _Student.objects.filter(
                        scope_filter(request, "roster__"),
                        roll_number=new_roll,
                    ).first()
                    if student is not None:
                        omr_sheet.student = student
                        omr_sheet.save(update_fields=["student"])
                except Exception:
                    pass  # roll reattachment is best-effort

        # ---- Auto-resolve all open ReviewItems for this sheet ----
        ReviewItem.objects.filter(
            omr_sheet=omr_sheet,
            resolved=False,
        ).update(resolved=True, resolved_by=request.user)

        # ---- Grade and persist (no new ScanEvent) ----
        grading = grade_sheet(omr_sheet, aggregated_reads)
        _persist_grading_result(omr_sheet, grading, done_jobs)

        # ---- Return updated StudentResult ----
        try:
            result = StudentResult.objects.get(omr_sheet=omr_sheet)
        except StudentResult.DoesNotExist:
            return Response(
                {"detail": "Regrade complete but StudentResult not found."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            StudentResultSerializer(result).data,
            status=status.HTTP_200_OK,
        )