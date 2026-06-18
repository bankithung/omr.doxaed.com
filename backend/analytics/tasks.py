"""
analytics.tasks — Celery tasks for analytics computation.

recompute_test_profile(test_id)
    Compute (or recompute) the TestProfile + StudentProfiles for a test.
    Safe to call repeatedly — uses update_or_create.

In development CELERY_TASK_ALWAYS_EAGER=True so .delay() runs synchronously.
"""

from celery import shared_task


@shared_task(bind=False, name="analytics.recompute_test_profile")
def recompute_test_profile(test_id: int) -> None:
    """
    Compute and persist the TestProfile + StudentProfile rows for *test_id*.

    Steps
    -----
    1. Load the Test.
    2. Call build_results_data() to gather per-student item scores.
    3. Call compute_test_profile() for the full psychometric profile.
    4. Call compute_distractor_profiles() to enrich items with distractor data.
    5. Upsert TestProfile (update_or_create keyed on test).
    6. Upsert StudentProfile for each student (update_or_create keyed on test+result).
    """
    from assessments.models import Test
    from analytics.models import TestProfile, StudentProfile
    from analytics.psychometrics import (
        build_results_data,
        compute_test_profile,
        compute_distractor_profiles,
    )

    try:
        test = Test.objects.get(pk=test_id)
    except Test.DoesNotExist:
        return

    results_data = build_results_data(test)
    n = len(results_data)

    if n == 0:
        # No results yet — do not create a profile; leave any stale profile untouched
        # so the endpoint returns a clean 404 rather than a misleading empty profile.
        return

    profile = compute_test_profile(results_data)
    profile = compute_distractor_profiles(test, results_data, profile)

    from analytics.psychometrics import MIN_COHORT_FOR_PSYCHOMETRICS
    if n < MIN_COHORT_FOR_PSYCHOMETRICS:
        status = TestProfile.STATUS_INSUFFICIENT
    else:
        status = TestProfile.STATUS_OK

    TestProfile.objects.update_or_create(
        test=test,
        defaults={
            "profile": profile,
            "cohort_size": n,
            "status": status,
        },
    )

    # Upsert per-student profiles
    for entry in profile.get("percentiles", []):
        student_result_id = entry["student_result_id"]
        student_id = entry["student_id"]

        StudentProfile.objects.update_or_create(
            test=test,
            result_id=student_result_id,
            defaults={
                "student_id": student_id,
                "score": entry["score"],
                "percentile": entry["percentile"],
                "rank": entry["rank"],
                "cohort_size": n,
            },
        )
