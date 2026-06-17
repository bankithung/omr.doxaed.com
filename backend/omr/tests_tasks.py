"""
omr/tests_tasks.py — TDD tests for async scanning via Celery (Task 2, Phase 8).

All tests run under CELERY_TASK_ALWAYS_EAGER=True (the default for dev/tests),
so .delay() executes synchronously inline — no broker required.
"""
import cv2
import numpy as np
from decimal import Decimal
from django.test import TestCase

from omr.codes import make_sheet_code
from omr.geometry import build_template


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _build_user_and_test(email="task_test_user@test.com", n_questions=10, n_options=4):
    """Create User → ClassGroup → Test → Questions + MarkingScheme."""
    from django.contrib.auth import get_user_model
    from assessments.models import ClassGroup, MarkingScheme, Option, Question, Test

    User = get_user_model()
    user = User.objects.create_user(email=email, password="taskpass")
    cg = ClassGroup.objects.create(user=user, created_by=user, name="Task CG")
    test = Test.objects.create(
        user=user, class_group=cg, created_by=user,
        title="Task Test", subject="OMR",
    )
    MarkingScheme.objects.create(test=test, marks_per_correct=1, negative_marks_per_wrong=0)
    for i in range(n_questions):
        q = Question.objects.create(test=test, order_index=i, text=f"Q{i}?")
        for j in range(n_options):
            label = chr(ord("A") + j)
            Option.objects.create(question=q, label=label, text=label, is_correct=(j == 0))
    return user, test


def _build_omr_sheet(test, user, n_questions=10, n_options=4, roll_digits=3):
    """Build OmrSheet + Roster + Student; return (omr_sheet, sheet_meta, descriptor)."""
    from assessments.models import Question
    from omr.models import OmrSheet
    from omr.shuffle import build_sheet_plan
    from rosters.models import Roster, Student

    roster = Roster.objects.create(user=user, created_by=user, name="Task Roster")
    student = Student.objects.create(roster=roster, roll_number="001")

    questions_data = [
        {
            "id": q.id,
            "options": [{"label": o.label, "is_correct": o.is_correct}
                        for o in q.options.all()],
        }
        for q in Question.objects.filter(test=test).order_by("order_index")
    ]
    seed = 99999
    plan = build_sheet_plan(questions_data, seed=seed,
                            shuffle_questions=False, shuffle_options=False)
    descriptor = build_template(
        num_questions=n_questions, num_options=n_options, roll_digits=roll_digits
    )
    sheet_code, human_code = make_sheet_code(test.id, seed)
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
    )
    sheet_meta = {
        "sheet_code": sheet_code,
        "human_readable_code": human_code,
        "institution": "Task School",
        "test_title": "Task Test",
        "subject": "OMR",
        "student_name": "Task Student",
        "roll_label": "Roll No.",
        "roll_digits": roll_digits,
    }
    return omr_sheet, sheet_meta, descriptor, student


def _make_scan_job(test, user, omr_sheet, sheet_meta, descriptor,
                   marked, roll="001", scale=2.0):
    """Simulate a scan image, create ScanBatch + ScanJob, return (batch, job)."""
    from django.core.files.base import ContentFile
    from omr.models import ScanBatch, ScanJob
    from omr.simulate import simulate_scan

    img = simulate_scan(descriptor, sheet_meta, marked=marked,
                        roll=roll, page=0, scale=scale)
    ok, buf = cv2.imencode(".png", img)
    assert ok, "cv2.imencode failed"
    img_bytes = buf.tobytes()

    batch = ScanBatch.objects.create(test=test, created_by=user, total=1)
    job = ScanJob(batch=batch, page_no=1)
    job.image_file.save("task_scan.png", ContentFile(img_bytes), save=True)
    return batch, job


# ===========================================================================
# Tests
# ===========================================================================

class CeleryTaskImportTest(TestCase):
    """process_scan_job_task is importable and is a Celery task."""

    def test_task_is_importable(self):
        from omr.tasks import process_scan_job_task
        self.assertIsNotNone(process_scan_job_task)

    def test_task_has_delay_method(self):
        from omr.tasks import process_scan_job_task
        self.assertTrue(callable(process_scan_job_task.delay),
                        "process_scan_job_task must have a .delay() method")

    def test_task_name(self):
        from omr.tasks import process_scan_job_task
        self.assertEqual(process_scan_job_task.name, "omr.process_scan_job_task")


class ProcessScanJobTaskDirectTest(TestCase):
    """
    Call process_scan_job_task(job_id) directly (not via .delay()) to grade
    a perfect-score scan; assert batch status=done and processed==total.
    """

    N_QUESTIONS = 10
    SCALE = 2.0

    def setUp(self):
        self.user, self.test = _build_user_and_test(
            email="task_direct@test.com",
            n_questions=self.N_QUESTIONS,
        )
        self.omr_sheet, self.sheet_meta, self.descriptor, self.student = \
            _build_omr_sheet(self.test, self.user, self.N_QUESTIONS)

    def test_task_grades_job_and_creates_student_result(self):
        """Direct call: task grades the job and creates StudentResult."""
        from omr.scan.pipeline import simulate_correct_marks
        from omr.models import ScanJob
        from omr.tasks import process_scan_job_task
        from results.models import StudentResult

        correct_marks = simulate_correct_marks(self.omr_sheet)
        batch, job = _make_scan_job(
            self.test, self.user, self.omr_sheet,
            self.sheet_meta, self.descriptor, correct_marks,
        )
        # Update batch total to 1 (already set) and let the task handle it
        batch.total = 1
        batch.save(update_fields=["total"])

        # Call the task directly (not via .delay()) — behaves like calling
        # the function, updates processed counter, sets batch done.
        process_scan_job_task(job.id)

        job.refresh_from_db()
        self.assertEqual(
            job.status, ScanJob.STATUS_DONE,
            f"Job status should be 'done', got {job.status!r} (err: {job.error_reason})",
        )

        batch.refresh_from_db()
        self.assertEqual(batch.status, "done",
                         f"Batch status should be 'done', got {batch.status!r}")
        self.assertEqual(batch.processed, 1,
                         f"batch.processed should be 1, got {batch.processed}")
        self.assertEqual(batch.total, 1)

        sr = StudentResult.objects.get(omr_sheet=self.omr_sheet)
        self.assertEqual(
            sr.score, Decimal(str(self.N_QUESTIONS)),
            f"Expected perfect score={self.N_QUESTIONS}, got {sr.score}",
        )
        self.assertEqual(sr.max_score, Decimal(str(self.N_QUESTIONS)))

    def test_task_via_delay_grades_job(self):
        """
        process_scan_job_task.delay(job_id) under CELERY_TASK_ALWAYS_EAGER=True
        runs synchronously and grades the job.
        """
        from omr.scan.pipeline import simulate_correct_marks
        from omr.models import ScanJob
        from omr.tasks import process_scan_job_task
        from results.models import StudentResult

        # Need a different sheet_code — use a new user/test for isolation.
        user2, test2 = _build_user_and_test(email="task_delay@test.com")
        omr_sheet2, sheet_meta2, descriptor2, _ = _build_omr_sheet(test2, user2)

        correct_marks = simulate_correct_marks(omr_sheet2)
        batch, job = _make_scan_job(
            test2, user2, omr_sheet2, sheet_meta2, descriptor2, correct_marks,
        )

        # .delay() is synchronous under CELERY_TASK_ALWAYS_EAGER=True
        process_scan_job_task.delay(job.id)

        job.refresh_from_db()
        self.assertEqual(job.status, ScanJob.STATUS_DONE,
                         f".delay() task: job status should be 'done', got {job.status!r}")

        batch.refresh_from_db()
        self.assertEqual(batch.status, "done")
        self.assertEqual(batch.processed, 1)

        sr = StudentResult.objects.filter(omr_sheet=omr_sheet2).first()
        self.assertIsNotNone(sr, "StudentResult should exist after task.delay()")


class TaskBatchCompletionTest(TestCase):
    """
    Batch processed counter and status=done are correct after tasks run
    (via .delay() in eager mode).
    """

    N_QUESTIONS = 10
    SCALE = 2.0

    def setUp(self):
        self.user, self.test = _build_user_and_test(email="task_batch@test.com")
        self.omr_sheet, self.sheet_meta, self.descriptor, self.student = \
            _build_omr_sheet(self.test, self.user, self.N_QUESTIONS)

    def test_batch_status_done_after_task(self):
        """After a single-job batch is processed, batch.status == 'done'."""
        from omr.scan.pipeline import simulate_correct_marks
        from omr.tasks import process_scan_job_task

        correct_marks = simulate_correct_marks(self.omr_sheet)
        batch, job = _make_scan_job(
            self.test, self.user, self.omr_sheet,
            self.sheet_meta, self.descriptor, correct_marks,
        )
        process_scan_job_task.delay(job.id)

        batch.refresh_from_db()
        self.assertEqual(batch.status, "done")

    def test_batch_processed_equals_total(self):
        """After processing, batch.processed == batch.total."""
        from omr.scan.pipeline import simulate_correct_marks
        from omr.tasks import process_scan_job_task

        correct_marks = simulate_correct_marks(self.omr_sheet)
        batch, job = _make_scan_job(
            self.test, self.user, self.omr_sheet,
            self.sheet_meta, self.descriptor, correct_marks,
        )
        process_scan_job_task.delay(job.id)

        batch.refresh_from_db()
        self.assertEqual(batch.processed, batch.total,
                         f"processed={batch.processed} != total={batch.total}")


class ScanUploadViaTaskEndpointTest(TestCase):
    """
    End-to-end: POST /api/v1/omr/scan/ goes through the Celery task path
    (eager mode) and still produces the correct StudentResult.

    This is the Phase-4 generate→scan→grade round-trip, now via the task.
    """

    N_QUESTIONS = 10
    SCALE = 2.0

    def setUp(self):
        self.user, self.test = _build_user_and_test(email="task_e2e@test.com")
        self.omr_sheet, self.sheet_meta, self.descriptor, self.student = \
            _build_omr_sheet(self.test, self.user, self.N_QUESTIONS)

    def _get_client(self):
        from rest_framework.test import APIClient
        client = APIClient()
        response = client.post("/api/v1/auth/token/", {
            "email": self.user.email,
            "password": "taskpass",
        }, format="json")
        token = response.data["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def test_scan_upload_via_task_returns_correct_result(self):
        """
        Uploading via /omr/scan/ dispatches via process_scan_job_task.delay();
        under eager mode the task runs inline and StudentResult is created.
        """
        from django.core.files.uploadedfile import SimpleUploadedFile
        from omr.scan.pipeline import simulate_correct_marks
        from omr.simulate import simulate_scan
        from results.models import StudentResult

        client = self._get_client()
        correct_marks = simulate_correct_marks(self.omr_sheet)
        img = simulate_scan(
            self.descriptor, self.sheet_meta,
            marked=correct_marks, roll="001",
            page=0, scale=self.SCALE,
        )
        ok, buf = cv2.imencode(".png", img)
        self.assertTrue(ok)

        uploaded = SimpleUploadedFile("task_scan.png", buf.tobytes(),
                                      content_type="image/png")
        response = client.post(
            "/api/v1/omr/scan/",
            {"test": self.test.id, "files": uploaded},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201,
                         f"Expected 201, got {response.status_code}: {response.data}")

        # Batch must be done with processed == total
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(response.data["processed"], 1)

        # Check the batch status via the progress endpoint
        batch_id = response.data["batch_id"]
        progress = client.get(f"/api/v1/omr/scan-batches/{batch_id}/")
        self.assertEqual(progress.status_code, 200)
        self.assertEqual(progress.data["status"], "done")
        self.assertEqual(progress.data["processed"], 1)

        # StudentResult with perfect score
        sr = StudentResult.objects.filter(omr_sheet=self.omr_sheet).first()
        self.assertIsNotNone(sr, "StudentResult should exist after task-based upload")
        self.assertEqual(
            sr.score, Decimal(str(self.N_QUESTIONS)),
            f"Expected perfect score, got score={sr.score} / max={sr.max_score}",
        )
        self.assertEqual(sr.score, sr.max_score)
