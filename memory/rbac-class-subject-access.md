---
name: rbac-class-subject-access
description: Per-teacher class+subject access control — model, enforcement points in scope.py, and the re-parent hole that was fixed
metadata:
  type: project
---

Per-teacher class + subject access control (shipped 2026-06-19, `main` `76afe5d`; plan
`docs/superpowers/plans/2026-06-19-class-subject-access-control.md`). The first slice of the owner's
"org → classes → subjects → members → assign access" setup vision.

**Model:** `organizations.ClassAccessGrant` = `(organization, user, class_group)` + `all_subjects`
(default True) + `subjects` M2M (used only when narrowed) + `granted_by`. Unique per (org, user, class).
Org-only concept — solo scope has no members so grants never apply.

**API:** admin-only `/api/v1/class-grants/` (DefaultRouter in `organizations/urls.py`). `ClassAccessGrantViewSet.initial()`
raises `PermissionDenied` unless `is_active_admin`. Serializer validates class/user/subjects all belong to the
active org. List filters `?class_group=` / `?user=`.

**Enforcement — ALL in `common/scope.py` (never weaken without an isolation test):**
- `visibility_q` ORs in `Q(**{f"{cp}access_grants__user": user})` for org members → a member sees a class only
  with a grant (the existing folder-sharing predicate is KEPT — grants are additive). Admins early-return `Q()`.
- `can_edit_class` returns True if a `ClassAccessGrant` exists for (org, user, class) → a grant = read+write.
- `narrowed_subject_names(request, class_group_id)` returns the SET of allowed subject names, or `None` when
  unrestricted (admin / solo / no grant / `all_subjects=True`). Callers check `is not None` (an empty set is a
  valid "narrowed to nothing"). The Subject viewset filters `name__in=names`; the Test viewset filters
  `Q(subject__in=names) | Q(subject="")` — `Test.subject` is free-text, and blank/untagged tests stay visible.

**UI:** admin-only "Teacher access" tab on the class page (`frontend/src/routes/TestList.jsx`, gated on
`useOrg().activeOrg?.role === "admin"`). Grant helpers in `frontend/src/api/orgs.js`. The frontend gate is pure
UX — the server refuses regardless.

**The hole the adversarial sweep found+fixed (Task 7):** `class_group` is a WRITABLE FK and `perform_update`
on Test/Subject only gated the SOURCE class, so a member with a grant on class A could PATCH their Test/Subject
into class B (no grant) — injecting rows into a class they can't see (200, should be 403). Fix: both viewsets
now also gate the DESTINATION class (`can_edit_class(new_cg)`), mirroring the Question/Section viewsets that
already did this. Tests in `organizations/tests_access_grants.py::ClassGrantAdversarialTests`.

Related: [[phase5-visibility-decisions]] (admins keep FULL edit/delete; existing data org-visible).
