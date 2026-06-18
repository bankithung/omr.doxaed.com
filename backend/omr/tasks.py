"""
omr.tasks — Celery tasks for async scan processing.

In development / tests CELERY_TASK_ALWAYS_EAGER=True so .delay() runs
synchronously inline — no broker required.  In production set
CELERY_TASK_ALWAYS_EAGER=False with a real CELERY_BROKER_URL.
"""
from celery import shared_task


@shared_task(bind=False, name="omr.process_scan_job_task")
def process_scan_job_task(job_id: int) -> None:
    """
    Process a single ScanJob identified by *job_id*.

    Loads the ScanJob from the database, calls the existing synchronous
    ``process_scan_job`` pipeline, then updates the parent ScanBatch's
    ``processed`` counter and, when all jobs are done, flips the batch
    status to ``done``.
    """
    from omr.models import ScanBatch, ScanJob
    from omr.scan.pipeline import process_scan_job

    job = ScanJob.objects.select_related("batch").get(id=job_id)
    batch = job.batch

    try:
        process_scan_job(job)
    except Exception:
        job.status = ScanJob.STATUS_FAILED
        job.error_reason = "pipeline_exception"
        job.save(update_fields=["status", "error_reason"])

    # Atomically increment the batch processed counter (safe under concurrency).
    from django.db.models import F
    ScanBatch.objects.filter(pk=batch.pk).update(processed=F("processed") + 1)
    batch.refresh_from_db(fields=["processed", "total", "status"])

    # When all jobs have been processed, mark the batch done.
    if batch.processed >= batch.total:
        batch.status = ScanBatch.STATUS_DONE
        batch.save(update_fields=["status"])

        # Phase 2A: enqueue psychometric profile computation for this test.
        # CELERY_TASK_ALWAYS_EAGER=True in dev so this runs inline.
        from analytics.tasks import recompute_test_profile
        recompute_test_profile.delay(batch.test_id)
