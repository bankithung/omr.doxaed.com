"""
omr.views — Generation endpoint + OmrSheet list + scan upload + batch progress.

POST /api/v1/omr/generate/
    Body: {test, roster, shuffle_questions=false, shuffle_options=false}
    Returns 201: {sheets: [...], batch_pdf_url: str, count: int}

GET /api/v1/omr/sheets/?test=<id>
    Returns paginated list of OmrSheets scoped to request.user.

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
from omr.serializers import GenerateSerializer, OmrSheetSerializer, ScanBatchSerializer
from omr.shuffle import build_sheet_plan
from rosters.models import Roster

# Free-tier limits (solo/per-user fallback)
MAX_STUDENTS = 10
MAX_DAILY_GENERATIONS = 5


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
            # Org scope: use billing.limits for per-org quota enforcement
            if not billing_limits.can_generate(org, len(students)):
                plan = billing_limits.org_plan(org)
                # Distinguish student cap vs daily cap for a useful error message
                if (
                    plan.students_per_generation_limit is not None
                    and len(students) > plan.students_per_generation_limit
                ):
                    return Response(
                        {
                            "detail": (
                                f"Your plan allows up to "
                                f"{plan.students_per_generation_limit} students per generation. "
                                "Upgrade your plan to generate larger batches."
                            )
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
                return Response(
                    {
                        "detail": (
                            "Daily generation limit reached for your organisation's plan. "
                            "Upgrade your plan for more daily generations."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            # Solo scope: original per-user free-tier checks
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

        # num_options = max options across all questions, clamped [2, 6]
        max_options = max(
            (q.options.count() for q in questions_list), default=2
        )
        num_options = max(2, min(6, max_options))

        # roll_digits = max(2, digits of largest roll_number)
        roll_numbers = [s.roll_number for s in students if s.roll_number]
        try:
            max_roll_int = max(int(r) for r in roll_numbers if r.isdigit())
        except ValueError:
            max_roll_int = 99
        roll_digits = max(2, len(str(max_roll_int)))

        descriptor = build_template(
            num_questions=num_questions,
            num_options=num_options,
            roll_digits=roll_digits,
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
        per_student_pdfs = []  # list of bytes

        for student in students:
            seed = _derive_seed(test.id, student.id)
            sheet_code, human_code = make_sheet_code(test.id, seed)

            plan = build_sheet_plan(
                questions=question_dicts,
                seed=seed,
                shuffle_questions=shuffle_questions,
                shuffle_options=shuffle_options,
            )

            sheet_dict = {
                "sheet_code": sheet_code,
                "human_readable_code": human_code,
                "institution": "",
                "test_title": test.title,
                "subject": getattr(test, "subject", ""),
                "student_name": student.full_name or "",
                "roll_label": "Roll No.",
                "roll_digits": roll_digits,
            }

            pdf_bytes = render_sheet_pdf(sheet_dict, descriptor)
            per_student_pdfs.append(pdf_bytes)

            omr_sheet = OmrSheet.objects.create(
                test=test,
                student=student,
                sheet_code=sheet_code,
                human_readable_code=human_code,
                shuffle_version=seed,
                question_order=plan["question_order"],
                option_order=plan["option_order"],
                answer_key=plan["answer_key"],
                template_descriptor=descriptor,
                page_count=descriptor["page_count"],
                page_map=descriptor["page_map"],
                assembly_status=OmrSheet.ASSEMBLY_READY,
            )

            # Save per-student PDF file
            pdf_filename = f"omr_sheets/{sheet_code}.pdf"
            omr_sheet.pdf_file.save(pdf_filename, ContentFile(pdf_bytes), save=True)

            created_sheets.append(omr_sheet)

        # ---- merge all student PDFs into one batch PDF -------------------
        out_doc = fitz.open()
        for pdf_bytes in per_student_pdfs:
            src = fitz.open(stream=pdf_bytes, filetype="pdf")
            out_doc.insert_pdf(src)
            src.close()

        batch_bytes = out_doc.tobytes()
        out_doc.close()

        # Save batch PDF to MEDIA
        batch_filename = f"omr_batches/{test.id}-{uuid.uuid4().hex}.pdf"
        batch_content = ContentFile(batch_bytes)

        # Use Django's default storage to save
        from django.core.files.storage import default_storage
        batch_path = default_storage.save(batch_filename, batch_content)
        batch_url = request.build_absolute_uri(
            f"/media/{batch_path.replace(chr(92), '/')}"
        )

        # ---- record GenerationEvent (org=None for solo) -----------------
        GenerationEvent.objects.create(user=request.user, test=test, organization=org)

        # ---- response ---------------------------------------------------
        sheet_data = OmrSheetSerializer(
            created_sheets, many=True, context={"request": request}
        ).data

        return Response(
            {
                "sheets": sheet_data,
                "batch_pdf_url": batch_url,
                "count": len(created_sheets),
            },
            status=status.HTTP_201_CREATED,
        )


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

        # ---- scan gate (org-aware) ----------------------------------------
        scan_org = get_active_org(request)
        if scan_org is not None:
            if not billing_limits.can_scan(scan_org):
                plan = billing_limits.org_plan(scan_org)
                return Response(
                    {
                        "detail": (
                            f"Monthly scan limit reached for your organisation's plan "
                            f"({plan.monthly_scan_limit} scans/month). "
                            "Upgrade to scan more sheets."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        uploaded_files = request.FILES.getlist("files")
        if not uploaded_files:
            return Response(
                {"files": "At least one file is required."},
                status=status.HTTP_400_BAD_REQUEST,
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

        # Import pipeline here (avoid circular at module level)
        from omr.scan.pipeline import process_scan_job

        processed = 0
        for page_no, img_bytes, fname in page_images:
            job = ScanJob(batch=batch, page_no=page_no)
            job.image_file.save(fname, ContentFile(img_bytes), save=True)

            # Eager synchronous processing
            try:
                process_scan_job(job)
            except Exception:
                job.status = ScanJob.STATUS_FAILED
                job.error_reason = "pipeline_exception"
                job.save(update_fields=["status", "error_reason"])

            processed += 1
            batch.processed = processed
            batch.save(update_fields=["processed"])

        batch.status = ScanBatch.STATUS_DONE
        batch.save(update_fields=["status"])

        # ---- record ScanEvent per batch (one event = one upload batch) ----
        # Granularity: per-batch (not per-page).  A batch may contain multiple
        # pages from one upload; recording one ScanEvent per upload call keeps
        # the counter proportional to "scan jobs submitted" rather than
        # "individual sheets processed", which is simpler to reason about and
        # avoids inflating the count for multi-page PDFs.
        ScanEvent.objects.create(
            user=request.user,
            test=test,
            organization=scan_org,  # None for solo
        )

        return Response(
            {"batch_id": batch.id, "total": total, "processed": processed},
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
