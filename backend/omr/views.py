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
from common.scope import get_active_org, parent_in_scope, scope_filter
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
        qs = OmrSheet.objects.filter(scope_filter(self.request, "test__"))
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
        return ScanBatch.objects.filter(scope_filter(self.request, "test__"))


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

    TODO Phase 5: add visibility_q(request, folder_prefix="test__class_group__folder__")
    to the queryset filter when folder-level sharing is introduced.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # Scope-filter through the test owner chain
        qs = OmrSheet.objects.filter(
            scope_filter(request, "test__"),
            pk=pk,
        )
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

    TODO Phase 5: add visibility_q(folder_prefix="class_group__folder__") to the
    Test queryset when folder-level sharing is introduced.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            test = Test.objects.filter(scope_filter(request), pk=pk).get()
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
