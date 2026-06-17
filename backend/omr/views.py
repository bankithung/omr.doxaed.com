"""
omr.views — Generation endpoint + OmrSheet list.

POST /api/v1/omr/generate/
    Body: {test, roster, shuffle_questions=false, shuffle_options=false}
    Returns 201: {sheets: [...], batch_pdf_url: str, count: int}

GET /api/v1/omr/sheets/?test=<id>
    Returns paginated list of OmrSheets scoped to request.user.
"""
import hashlib
import uuid

import fitz  # PyMuPDF
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics

from assessments.models import Test
from rosters.models import Roster
from omr.codes import make_sheet_code
from omr.geometry import build_template
from omr.generator import render_sheet_pdf
from omr.models import GenerationEvent, OmrSheet
from omr.serializers import GenerateSerializer, OmrSheetSerializer
from omr.shuffle import build_sheet_plan

# Free-tier limits
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

        if test.user_id != request.user.id:
            return Response(
                {"test": "Test not found in your account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            roster = Roster.objects.get(pk=roster_id)
        except Roster.DoesNotExist:
            return Response({"roster": "Roster not found."}, status=status.HTTP_400_BAD_REQUEST)

        if roster.user_id != request.user.id:
            return Response(
                {"roster": "Roster not found in your account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---- free-tier gates ---------------------------------------------
        students = list(roster.students.order_by("roll_number", "id"))
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

        # ---- record GenerationEvent -------------------------------------
        GenerationEvent.objects.create(user=request.user, test=test)

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
        qs = OmrSheet.objects.filter(test__user=self.request.user)
        test_id = self.request.query_params.get("test")
        if test_id:
            qs = qs.filter(test_id=test_id)
        return qs
