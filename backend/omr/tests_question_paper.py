"""
Tests for Phase 3a — per-student shuffled question paper PDF + authenticated serving.

Test groups:
  1. S7 golden correctness: for a known seed with shuffle ON, the printed letter
     of the correct option in the rendered paper == answer_key[printed_pos].
     Asserted on the reconstruction function's intermediate output (not PDF text).

  2. Renderer: produces non-empty valid PDF bytes starting with %PDF; shuffle-OFF
     yields a plain ordered paper.

  3. GenerateSerializer: emit_question_paper auto-forced when shuffle is on.

  4. Security:
     - anonymous GET of /omr/sheets/<id>/question-paper/ → 403 (no auth) or 404
     - a different authenticated user → 404
     - the owner → 200 PDF response
     - response Content-Type is application/pdf

  5. Existing OmrSheet model has question_paper_file field.
"""
from __future__ import annotations

import io

from django.contrib.auth import get_user_model
from django.test import TestCase

from assessments.models import ClassGroup, Option, Question, Test
from omr.models import OmrSheet
from omr.shuffle import build_sheet_plan
from rosters.models import Roster, Student

User = get_user_model()

_EMAIL_COUNTER = [0]

GENERATE_URL = "/api/v1/omr/generate/"
SHEETS_URL   = "/api/v1/omr/sheets/"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_user(prefix="u"):
    _EMAIL_COUNTER[0] += 1
    return User.objects.create_user(
        email=f"{prefix}{_EMAIL_COUNTER[0]}@qp.test", password="testpass"
    )


def _auth_header(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {str(refresh.access_token)}"}


def _make_test_with_questions(user, *, shuffle_ready=True, num_q=3):
    """
    Create a Test with `num_q` questions, each having 4 options (A-D).
    Option A is correct for all questions.
    Returns (test, roster, students).
    """
    cg = ClassGroup.objects.create(user=user, created_by=user, name="CG-QP")
    test = Test.objects.create(
        user=user, class_group=cg, created_by=user, title="QP Test"
    )
    for qi in range(num_q):
        q = Question.objects.create(test=test, order_index=qi, text=f"Question {qi + 1}")
        for label in ["A", "B", "C", "D"]:
            Option.objects.create(
                question=q, label=label, text=f"Option {label}", is_correct=(label == "A")
            )
    roster = Roster.objects.create(user=user, created_by=user, name="Roster-QP")
    students = []
    for i in range(1, 3):
        s = Student.objects.create(
            roster=roster, roll_number=str(10 + i), full_name=f"Student {i}"
        )
        students.append(s)
    return test, roster, students


# ---------------------------------------------------------------------------
# 1. S7 Golden correctness — reconstruction invariant
# ---------------------------------------------------------------------------

class S7GoldenCorrectnessTests(TestCase):
    """
    S7 security review requirement:
    The printed letter of the correct option in the rendered paper MUST correspond
    to answer_key[str(printed_pos)].

    We assert this on the shuffle plan's intermediate data (not by parsing PDF text),
    which is the authoritative reconstruction path used by question_paper.py.
    """

    # Known test fixture
    QUESTIONS = [
        {
            "id": 1,
            "options": [
                {"label": "A", "is_correct": True},
                {"label": "B", "is_correct": False},
                {"label": "C", "is_correct": False},
                {"label": "D", "is_correct": False},
            ],
        },
        {
            "id": 2,
            "options": [
                {"label": "A", "is_correct": False},
                {"label": "B", "is_correct": True},
                {"label": "C", "is_correct": False},
                {"label": "D", "is_correct": False},
            ],
        },
        {
            "id": 3,
            "options": [
                {"label": "A", "is_correct": False},
                {"label": "B", "is_correct": False},
                {"label": "C", "is_correct": True},
                {"label": "D", "is_correct": False},
            ],
        },
    ]
    SEED = 42  # fixed known seed

    def _run_plan(self, *, shuffle_questions=True, shuffle_options=True):
        return build_sheet_plan(
            questions=self.QUESTIONS,
            seed=self.SEED,
            shuffle_questions=shuffle_questions,
            shuffle_options=shuffle_options,
        )

    def _verify_golden(self, plan):
        """
        Core invariant: for each printed_pos, reconstruct the printed letter of the
        correct option from option_order, and assert it matches answer_key.
        """
        question_order = plan["question_order"]   # [q_id, ...]
        option_order   = plan["option_order"]     # {str(q_id): [orig_labels in printed order]}
        answer_key     = plan["answer_key"]       # {str(printed_pos): [correct printed letters]}

        # Build correct original label per question
        correct_by_id = {}
        for q in self.QUESTIONS:
            correct_by_id[q["id"]] = {o["label"] for o in q["options"] if o["is_correct"]}

        for printed_pos, q_id in enumerate(question_order):
            printed_orig_labels = option_order[str(q_id)]
            # Reconstruct which printed letter corresponds to the correct original label
            reconstructed_correct_letters = []
            for i, orig_label in enumerate(printed_orig_labels):
                if orig_label in correct_by_id[q_id]:
                    reconstructed_correct_letters.append(chr(ord("A") + i))

            stored_correct_letters = answer_key[str(printed_pos)]

            self.assertEqual(
                sorted(reconstructed_correct_letters),
                sorted(stored_correct_letters),
                msg=(
                    f"S7 GOLDEN FAILURE at printed_pos={printed_pos} q_id={q_id}: "
                    f"reconstructed={reconstructed_correct_letters} "
                    f"stored answer_key={stored_correct_letters}"
                ),
            )

    def test_s7_golden_shuffle_on(self):
        """With shuffle ON, printed letters in answer_key match reconstruction."""
        plan = self._run_plan(shuffle_questions=True, shuffle_options=True)
        self._verify_golden(plan)

    def test_s7_golden_shuffle_off(self):
        """With shuffle OFF (identity permutation), invariant still holds."""
        plan = self._run_plan(shuffle_questions=False, shuffle_options=False)
        self._verify_golden(plan)

    def test_s7_golden_questions_only(self):
        """With only question shuffle ON (options fixed), invariant holds."""
        plan = self._run_plan(shuffle_questions=True, shuffle_options=False)
        self._verify_golden(plan)

    def test_s7_golden_options_only(self):
        """With only option shuffle ON, invariant holds."""
        plan = self._run_plan(shuffle_questions=False, shuffle_options=True)
        self._verify_golden(plan)

    def test_s7_answer_key_letter_is_chr_of_index(self):
        """
        The correct letter in answer_key is exactly chr(ord('A') + i) where i is
        the position of the correct ORIGINAL label in option_order[str(q_id)].
        This is the S7 spec: printed letter = index in printed option_order array.
        """
        plan = self._run_plan(shuffle_questions=True, shuffle_options=True)
        question_order = plan["question_order"]
        option_order   = plan["option_order"]
        answer_key     = plan["answer_key"]

        correct_by_id = {
            q["id"]: {o["label"] for o in q["options"] if o["is_correct"]}
            for q in self.QUESTIONS
        }

        for printed_pos, q_id in enumerate(question_order):
            printed_orig_labels = option_order[str(q_id)]
            ak_letters = answer_key[str(printed_pos)]
            for ak_letter in ak_letters:
                # The letter must correspond to a valid index in the printed order
                idx = ord(ak_letter) - ord("A")
                self.assertGreaterEqual(idx, 0)
                self.assertLess(idx, len(printed_orig_labels))
                orig_label_at_idx = printed_orig_labels[idx]
                self.assertIn(
                    orig_label_at_idx,
                    correct_by_id[q_id],
                    msg=(
                        f"answer_key letter {ak_letter!r} at printed_pos={printed_pos} "
                        f"maps to orig_label={orig_label_at_idx!r} which is NOT correct "
                        f"for q_id={q_id}. S7 violation."
                    ),
                )


# ---------------------------------------------------------------------------
# 2. Renderer tests
# ---------------------------------------------------------------------------

class QuestionPaperRendererTests(TestCase):
    """render_question_paper_pdf returns a valid PDF bytes."""

    def setUp(self):
        self.user = _make_user("renderer")
        self.test_obj, self.roster, self.students = _make_test_with_questions(self.user)

    def _make_omr_sheet(self, *, shuffle=True):
        """
        Build and save an OmrSheet via GenerateView so question_order / option_order /
        answer_key / question_paper_file are all properly set.
        """
        resp = self.client.post(
            GENERATE_URL,
            {
                "test": self.test_obj.id,
                "roster": self.roster.id,
                "shuffle_questions": shuffle,
                "shuffle_options": shuffle,
            },
            content_type="application/json",
            **_auth_header(self.user),
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        return OmrSheet.objects.filter(test=self.test_obj).first()

    def test_render_produces_valid_pdf(self):
        """render_question_paper_pdf returns non-empty bytes starting with %PDF."""
        omr_sheet = self._make_omr_sheet(shuffle=True)
        from omr.question_paper import render_question_paper_pdf
        pdf_bytes = render_question_paper_pdf(omr_sheet)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 100)
        self.assertTrue(
            pdf_bytes.startswith(b"%PDF"),
            f"Rendered PDF does not start with %PDF header (got {pdf_bytes[:8]!r})"
        )

    def test_render_with_answer_key_appendix(self):
        """include_answer_key=True renders a longer PDF (has the appendix section)."""
        omr_sheet = self._make_omr_sheet(shuffle=True)
        from omr.question_paper import render_question_paper_pdf
        without_key = render_question_paper_pdf(omr_sheet, include_answer_key=False)
        with_key    = render_question_paper_pdf(omr_sheet, include_answer_key=True)
        self.assertTrue(with_key.startswith(b"%PDF"))
        # With answer key appended, the PDF is generally at least as large
        self.assertGreaterEqual(len(with_key), len(without_key))

    def test_shuffle_off_produces_valid_pdf(self):
        """When shuffle is OFF, the renderer still produces a valid PDF."""
        omr_sheet = self._make_omr_sheet(shuffle=False)
        from omr.question_paper import render_question_paper_pdf
        pdf_bytes = render_question_paper_pdf(omr_sheet)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_question_paper_file_saved_when_shuffle_on(self):
        """When shuffle is ON, question_paper_file is saved on the OmrSheet."""
        omr_sheet = self._make_omr_sheet(shuffle=True)
        self.assertTrue(
            bool(omr_sheet.question_paper_file),
            "question_paper_file should be set when shuffle is ON"
        )

    def test_question_paper_file_not_saved_when_shuffle_off(self):
        """When shuffle is OFF and emit_question_paper not set, no paper file."""
        omr_sheet = self._make_omr_sheet(shuffle=False)
        # shuffle=False and emit_question_paper not explicitly passed → auto-stays False
        self.assertFalse(
            bool(omr_sheet.question_paper_file),
            "question_paper_file should NOT be set when shuffle is OFF and not requested"
        )


# ---------------------------------------------------------------------------
# 3. GenerateSerializer — emit_question_paper auto-forced
# ---------------------------------------------------------------------------

class GenerateSerializerEmitFlagTests(TestCase):
    """emit_question_paper is auto-forced True when shuffle_questions or shuffle_options is True."""

    def _validate(self, data):
        from omr.serializers import GenerateSerializer
        s = GenerateSerializer(data=data)
        s.is_valid(raise_exception=True)
        return s.validated_data

    def test_emit_forced_when_shuffle_questions_on(self):
        data = self._validate({"test": 1, "roster": 1, "shuffle_questions": True, "shuffle_options": False})
        self.assertTrue(data["emit_question_paper"])

    def test_emit_forced_when_shuffle_options_on(self):
        data = self._validate({"test": 1, "roster": 1, "shuffle_questions": False, "shuffle_options": True})
        self.assertTrue(data["emit_question_paper"])

    def test_emit_forced_when_both_shuffle_on(self):
        data = self._validate({"test": 1, "roster": 1, "shuffle_questions": True, "shuffle_options": True})
        self.assertTrue(data["emit_question_paper"])

    def test_emit_stays_false_when_shuffle_off(self):
        data = self._validate({"test": 1, "roster": 1, "shuffle_questions": False, "shuffle_options": False})
        self.assertFalse(data["emit_question_paper"])

    def test_emit_explicit_true_when_shuffle_off(self):
        """Explicitly requesting emit_question_paper=True without shuffle → still True."""
        data = self._validate(
            {"test": 1, "roster": 1, "shuffle_questions": False, "shuffle_options": False,
             "emit_question_paper": True}
        )
        self.assertTrue(data["emit_question_paper"])


# ---------------------------------------------------------------------------
# 4. API security tests — authenticated serving
# ---------------------------------------------------------------------------

class QuestionPaperServeSecurityTests(TestCase):
    """
    Security: the /omr/sheets/<id>/question-paper/ endpoint must:
      - Reject anonymous requests (401/403/404 — not 200)
      - Reject requests from a different authenticated user (404)
      - Accept requests from the owner (200, content-type: application/pdf)
    """

    def setUp(self):
        self.owner = _make_user("owner")
        self.other  = _make_user("other")

        # Generate a sheet with a question paper for the owner
        self.test_obj, self.roster, self.students = _make_test_with_questions(self.owner)

        resp = self.client.post(
            GENERATE_URL,
            {
                "test": self.test_obj.id,
                "roster": self.roster.id,
                "shuffle_questions": True,
                "shuffle_options": True,
            },
            content_type="application/json",
            **_auth_header(self.owner),
        )
        self.assertEqual(resp.status_code, 201, resp.content)

        # Pick the first sheet that has a question paper
        self.sheet = OmrSheet.objects.filter(
            test=self.test_obj, question_paper_file__isnull=False
        ).exclude(question_paper_file="").first()
        self.assertIsNotNone(self.sheet, "No sheet with question_paper_file found after generate")
        self.paper_url = f"/api/v1/omr/sheets/{self.sheet.pk}/question-paper/"

    def test_anonymous_get_returns_4xx(self):
        """Anonymous request must NOT return 200 — should be 401, 403, or 404."""
        resp = self.client.get(self.paper_url)
        self.assertIn(
            resp.status_code,
            [401, 403, 404],
            f"Expected 401/403/404 for anonymous, got {resp.status_code}"
        )

    def test_different_user_gets_404(self):
        """A different authenticated user cannot access the paper (scope isolation)."""
        resp = self.client.get(self.paper_url, **_auth_header(self.other))
        self.assertEqual(
            resp.status_code, 404,
            f"Expected 404 for wrong user, got {resp.status_code}"
        )

    def test_owner_gets_200_pdf(self):
        """The owner gets a 200 response with a PDF."""
        resp = self.client.get(self.paper_url, **_auth_header(self.owner))
        self.assertEqual(resp.status_code, 200, f"Owner should get 200, got {resp.status_code}")
        content_type = resp.get("Content-Type", "")
        self.assertIn(
            "application/pdf",
            content_type,
            f"Expected application/pdf content-type, got {content_type!r}"
        )

    def test_owner_response_is_valid_pdf(self):
        """The owner's response content starts with %PDF."""
        resp = self.client.get(self.paper_url, **_auth_header(self.owner))
        self.assertEqual(resp.status_code, 200)
        content = b"".join(resp.streaming_content) if resp.streaming else resp.content
        self.assertTrue(
            content.startswith(b"%PDF"),
            f"Response content is not a valid PDF (got {content[:8]!r})"
        )

    def test_sheet_without_paper_returns_404(self):
        """A sheet with no question_paper_file returns 404 (directly cleared)."""
        # Take our existing sheet, clear its paper file, and confirm 404
        omr_sheet = self.sheet

        # Clear the question_paper_file directly (simulates no paper generated)
        omr_sheet.question_paper_file = None
        omr_sheet.save(update_fields=["question_paper_file"])

        url = f"/api/v1/omr/sheets/{omr_sheet.pk}/question-paper/"
        resp = self.client.get(url, **_auth_header(self.owner))
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# 5. OmrSheetSerializer — question_paper_url field
# ---------------------------------------------------------------------------

class OmrSheetSerializerQuestionPaperUrlTests(TestCase):
    """question_paper_url field returns authenticated endpoint URL when file exists."""

    def setUp(self):
        self.user = _make_user("ser")
        self.test_obj, self.roster, _ = _make_test_with_questions(self.user)

    def test_question_paper_url_present_when_paper_exists(self):
        """After generation with shuffle, question_paper_url returns authenticated path."""
        resp = self.client.post(
            GENERATE_URL,
            {
                "test": self.test_obj.id,
                "roster": self.roster.id,
                "shuffle_questions": True,
                "shuffle_options": True,
            },
            content_type="application/json",
            **_auth_header(self.user),
        )
        self.assertEqual(resp.status_code, 201)
        sheets = resp.json()["sheets"]
        for sheet in sheets:
            self.assertIn("question_paper_url", sheet)
            if sheet["question_paper_url"] is not None:
                self.assertIn("/omr/sheets/", sheet["question_paper_url"])
                self.assertIn("/question-paper/", sheet["question_paper_url"])
                # Must NOT be a raw /media/ path
                self.assertNotIn("/media/", sheet["question_paper_url"])

    def test_question_paper_url_none_when_no_paper(self):
        """Without shuffle, question_paper_url is None."""
        resp = self.client.post(
            GENERATE_URL,
            {
                "test": self.test_obj.id,
                "roster": self.roster.id,
                "shuffle_questions": False,
                "shuffle_options": False,
            },
            content_type="application/json",
            **_auth_header(self.user),
        )
        self.assertEqual(resp.status_code, 201)
        sheets = resp.json()["sheets"]
        for sheet in sheets:
            self.assertIsNone(
                sheet.get("question_paper_url"),
                f"Expected question_paper_url=None without shuffle, got {sheet.get('question_paper_url')!r}"
            )

    def test_generate_with_shuffle_includes_batch_paper_url(self):
        """Response includes batch_paper_url when shuffle is on."""
        resp = self.client.post(
            GENERATE_URL,
            {
                "test": self.test_obj.id,
                "roster": self.roster.id,
                "shuffle_questions": True,
                "shuffle_options": True,
            },
            content_type="application/json",
            **_auth_header(self.user),
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertIn("batch_paper_url", body)
        self.assertIsNotNone(body["batch_paper_url"])

    def test_generate_without_shuffle_no_batch_paper_url(self):
        """Response does NOT include batch_paper_url (or it's absent) when shuffle off."""
        resp = self.client.post(
            GENERATE_URL,
            {
                "test": self.test_obj.id,
                "roster": self.roster.id,
                "shuffle_questions": False,
                "shuffle_options": False,
            },
            content_type="application/json",
            **_auth_header(self.user),
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        # batch_paper_url should either be absent or None
        self.assertIsNone(body.get("batch_paper_url"))


# ---------------------------------------------------------------------------
# 6. Model field exists
# ---------------------------------------------------------------------------

class OmrSheetModelFieldTests(TestCase):
    """OmrSheet.question_paper_file field exists and is a FileField."""

    def test_question_paper_file_field_exists(self):
        from django.db.models import FileField
        field = OmrSheet._meta.get_field("question_paper_file")
        self.assertIsInstance(field, FileField)

    def test_question_paper_file_is_nullable(self):
        field = OmrSheet._meta.get_field("question_paper_file")
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_question_paper_file_upload_to(self):
        field = OmrSheet._meta.get_field("question_paper_file")
        self.assertEqual(field.upload_to, "omr_papers/")
