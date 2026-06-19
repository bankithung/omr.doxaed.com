# Per-Teacher Class + Subject Access Control — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development or superpowers:executing-plans to implement task-by-task. Steps use checkbox (`- [ ]`) syntax. **This touches the scope/isolation layer — every task ships its isolation tests; never weaken `common/scope.py` without a test proving the boundary holds.**

**Goal:** An org **admin** grants each **teacher (member)** access to specific **classes**; a class grant includes **all its subjects by default**, but the admin can **narrow** it to chosen subjects. Teachers only ever see/act on their granted classes (and, when narrowed, only the granted subjects). Admins keep full access.

**Architecture:** A new `ClassAccessGrant` row links `(organization, user, class_group)` with `all_subjects` (default `True`) + a `subjects` M2M (used only when narrowed). Enforcement is woven into the existing `common/scope.py` visibility layer — members' class visibility becomes "created-by-them **OR** has a grant **OR** folder-shared (kept)", and subject/test reads are additionally filtered by the grant's subjects. Admins short-circuit to full access (unchanged). Grants are managed from an **Access** section on the class-detail page.

**Tech stack:** Django 5 + DRF (backend), React 19 + Vite + Tailwind v4 + shadcn/ui (frontend). Owner-scope is `user XOR organization`; grants are an org-only concept (personal/solo scope has no members, so grants don't apply).

---

## Current state (verified)

- `ClassGroup` (assessments) — owner-scoped (`user XOR organization`).
- `Subject` (assessments) — `class_group` FK + `name`; unique per `(class_group, name)`.
- `Roster` (rosters) — nullable `class_group` FK.
- `Test` (assessments) — `class_group` FK; **`subject` is a free-text `CharField`** (matches a Subject name by convention, not a FK).
- `OrganizationMembership` — `(organization, user, role∈{admin,member}, status∈{active,…})`.
- `common/scope.py` — `get_active_org`, `scope_filter`, `visibility_q(request, class_prefix, row_creator_prefix)`, `can_edit_class`, `is_active_admin`. Today member visibility is **folder-based**; admins get `Q()` (full).

**Design decisions locked with the owner:**
- Default: **class grant → all subjects**; admin may narrow to specific subjects.
- A grant gives the teacher **read+write** access to that class's resources (they teach it); subject-narrowing limits which subjects' content they see/edit. Admins manage grants.
- Keep existing folder-sharing working (do not remove); grants are an **additional** visibility path.

---

## File structure

- Create `backend/access/` app (or add to `organizations/`) — **decision: add to `organizations/`** (grants are an org/membership concept; avoids a new app + INSTALLED_APPS churn). Files:
  - Modify `backend/organizations/models.py` — `ClassAccessGrant`.
  - Create migration `backend/organizations/migrations/00XX_classaccessgrant.py`.
  - Modify `backend/organizations/serializers.py` — `ClassAccessGrantSerializer`.
  - Modify `backend/organizations/views.py` — `ClassAccessGrantViewSet` (admin-gated).
  - Modify `backend/organizations/urls.py` (or the router) — register the viewset.
  - Modify `backend/common/scope.py` — fold grants into `visibility_q` + add `accessible_subject_names(request, class_group)` helper + `can_edit_class`.
  - Create `backend/organizations/tests_access_grants.py` — isolation tests.
- Frontend:
  - Modify `frontend/src/api/orgs.js` — grant CRUD + `listOrgMembers`.
  - Modify `frontend/src/routes/TestList.jsx` — an `AccessSection` (admin-only) on the class page.
  - (member experience needs no new files — the filtered API responses flow through existing pages).

---

### Task 1: `ClassAccessGrant` model + migration

**Files:**
- Modify: `backend/organizations/models.py`
- Create: `backend/organizations/migrations/00XX_classaccessgrant.py` (via `makemigrations`)
- Test: `backend/organizations/tests_access_grants.py`

- [ ] **Step 1: Write the failing model test**

```python
# backend/organizations/tests_access_grants.py
from django.test import TestCase
from django.db import IntegrityError
from accounts.models import User
from organizations.models import Organization, OrganizationMembership, ClassAccessGrant
from assessments.models import ClassGroup, Subject


class ClassAccessGrantModelTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="a@o.com", password="Str0ng!pass")
        self.teacher = User.objects.create_user(email="t@o.com", password="Str0ng!pass")
        self.org = Organization.objects.create(name="O", owner=self.admin)
        self.cls = ClassGroup.objects.create(organization=self.org, created_by=self.admin, name="10A")

    def test_grant_defaults_to_all_subjects(self):
        g = ClassAccessGrant.objects.create(organization=self.org, user=self.teacher, class_group=self.cls)
        self.assertTrue(g.all_subjects)
        self.assertEqual(g.subjects.count(), 0)

    def test_grant_is_unique_per_org_user_class(self):
        ClassAccessGrant.objects.create(organization=self.org, user=self.teacher, class_group=self.cls)
        with self.assertRaises(IntegrityError):
            ClassAccessGrant.objects.create(organization=self.org, user=self.teacher, class_group=self.cls)
```

- [ ] **Step 2: Run → fails** (`ImportError: ClassAccessGrant`).
  Run: `./.venv/Scripts/python.exe manage.py test organizations.tests_access_grants.ClassAccessGrantModelTests -v2`

- [ ] **Step 3: Implement the model**

```python
# backend/organizations/models.py  (append)
class ClassAccessGrant(models.Model):
    """An org admin's grant of a class (and, optionally, only specific subjects of
    it) to a member/teacher. all_subjects=True (default) → the whole class; else
    only `subjects`. Org-only concept; personal scope has no members."""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="class_grants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="class_grants")
    class_group = models.ForeignKey(
        "assessments.ClassGroup", on_delete=models.CASCADE, related_name="access_grants"
    )
    all_subjects = models.BooleanField(default=True)
    subjects = models.ManyToManyField("assessments.Subject", blank=True, related_name="access_grants")
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "user", "class_group"], name="uniq_grant_org_user_class")
        ]
```
(Ensure `from django.conf import settings` is imported — it is.)

- [ ] **Step 4: makemigrations + run tests** → PASS.
  `./.venv/Scripts/python.exe manage.py makemigrations organizations` then re-run the test.

- [ ] **Step 5: Commit** `feat(access): ClassAccessGrant model + migration`.

---

### Task 2: Grant management API (admin-only)

**Files:** Modify `backend/organizations/serializers.py`, `views.py`, the router/`urls.py`. Test: `tests_access_grants.py`.

Endpoints (all require the requester be an **active admin of the active org**, via `is_active_admin(request)`):
- `GET /api/v1/class-grants/?class_group=<id>` — grants for a class (admin manages "who can access this class").
- `GET /api/v1/class-grants/?user=<id>` — grants for a member.
- `POST /api/v1/class-grants/` `{user, class_group, all_subjects, subjects:[ids]}`.
- `PATCH /api/v1/class-grants/<id>/` — change `all_subjects`/`subjects`.
- `DELETE /api/v1/class-grants/<id>/`.

- [ ] **Step 1: Failing API tests** — assert: a member POSTing a grant → 403; an admin POSTing → 201; admin can only grant `class_group`/`subjects`/`user` that belong to the **active org** (cross-org `class_group` or non-member `user` → 400/403); list filters by `?class_group`/`?user`.

- [ ] **Step 2: Serializer** — validate `class_group.organization_id == active_org.id`, `user` is an active member of the active org, and every `subjects` item's `class_group_id == class_group_id`. Stamp `organization=active_org`, `granted_by=request.user`.

- [ ] **Step 3: ViewSet** — `permission` gate: `if not is_active_admin(request): raise PermissionDenied`. `get_queryset` = `ClassAccessGrant.objects.filter(organization=get_active_org(request))` + optional `?class_group`/`?user` (guard `.isdigit()`). Register on the router as `class-grants`.

- [ ] **Step 4: Run tests** → PASS. **Step 5: Commit** `feat(access): admin-gated grant CRUD API`.

---

### Task 3: Class-level visibility via grants (the core enforcement)

**Files:** Modify `backend/common/scope.py`. Test: `tests_access_grants.py` (+ ensure existing `organizations/tests_orgs.py` still green).

- [ ] **Step 1: Failing isolation tests** (the security crux), in `tests_access_grants.py`:
  - A member with **no grant** for an org class → `GET /api/v1/classes/` with the org header does **not** include it; `GET /classes/<id>/` → 404; `POST /tests/` under it → 403.
  - A member **with a grant** → the class appears; can read/create tests + rosters under it.
  - An **admin** → sees all classes (grants irrelevant). 
  - A grant in **org A** does not leak the class into **org B**'s scope.

- [ ] **Step 2: Implement** — extend `visibility_q`. Today, for a non-admin org member it returns the folder predicate `q`. Add a grant predicate and OR it in. Using the existing `class_prefix` (FK path to the governing ClassGroup; `""` when the row IS the ClassGroup):

```python
# in visibility_q(...), for the non-admin member branch, BEFORE `return q`:
cp = class_prefix
grant_path = f"{cp}access_grants__user" if cp else "access_grants__user"
q |= Q(**{grant_path: user})
# (loose-class / class-less rows keep their existing created_by predicates)
```
Admins still early-return `Q()`. Solo scope still early-returns `Q()`. Because `visibility_q` already AND-distinct-guards every `get_queryset`, granted classes now surface for members across ClassGroup / Subject / Test / Roster (all of which pass a `class_prefix` to the governing class). Keep `.distinct()`.

- [ ] **Step 3: `can_edit_class`** — a granted member may edit their class. Add, after the admin check:
```python
# a direct class grant in the active org = edit rights on that class
if ClassAccessGrant.objects.filter(organization=org.id, user=user, class_group=class_group).exists():
    return True
```
(Import `ClassAccessGrant` lazily inside the function to avoid app-load cycles, mirroring the existing `from folders.models import FolderShare`.)

- [ ] **Step 4: Run the new tests + the full `organizations.tests_orgs` + `folders.tests_visibility`** → all PASS (no regression). **Step 5: Commit** `feat(access): members see/edit only granted classes`.

---

### Task 4: Subject narrowing (Subjects + Tests filtered)

**Files:** Modify `backend/common/scope.py` (+ the Subject + Test viewsets if they don't already route through `visibility_q`). Test: `tests_access_grants.py`.

- [ ] **Step 1: Failing tests** — a member granted class `C` but narrowed to subject "Math":
  - `GET /subjects/?class_group=C` returns only "Math" (not "Physics").
  - `GET /tests/?class_group=C` returns only tests whose `subject` is "Math" **or blank** (blank = unclassified, visible to any class-grantee). A "Physics" test is hidden.
  - With `all_subjects=True`, all subjects + all tests of `C` are visible.
  - Admin → everything.

- [ ] **Step 2: Helper** in `scope.py`:
```python
def narrowed_subject_names(request, class_group):
    """For an org MEMBER with a narrowed grant on `class_group`, return the SET of
    allowed subject names; return None when unrestricted (admin / all_subjects /
    solo / no narrowing) so callers skip subject filtering."""
    org = get_active_org(request)
    if org is None or is_active_admin(request):
        return None
    g = ClassAccessGrant.objects.filter(
        organization=org.id, user=request.user, class_group=class_group, all_subjects=False
    ).prefetch_related("subjects").first()
    if g is None:
        return None  # no narrowing grant → class-level visibility already governs
    return set(g.subjects.values_list("name", flat=True))
```

- [ ] **Step 3: Apply** — in the Subject viewset `get_queryset`, after the scope+visibility filter, if `narrowed_subject_names(...)` is not None for the requested class, `qs = qs.filter(name__in=names)`. In the Test viewset `get_queryset`, similarly `qs = qs.filter(Q(subject__in=names) | Q(subject=""))`. (Both already filter by `class_group`/scope; this AND-restricts subjects.) Keep it per-`?class_group=` request to keep the name set well-defined.

- [ ] **Step 4: Run tests** → PASS. **Step 5: Commit** `feat(access): subject-narrowed grants filter subjects + tests`.

---

### Task 5: Admin UI — Access section on the class page

**Files:** Modify `frontend/src/api/orgs.js` (grant CRUD + `listOrgMembers`), `frontend/src/routes/TestList.jsx` (`AccessSection`, admin-only).

- [ ] **Step 1: API helpers** — `listClassGrants(classId)`, `createClassGrant({user,class_group,all_subjects,subjects})`, `updateClassGrant(id, body)`, `deleteClassGrant(id)`, and `listOrgMembers(orgId)` (already exists? reuse). 

- [ ] **Step 2: `AccessSection({ classId })`** — render ONLY when the active org's role is `admin` (read `useOrg().activeOrg?.role === "admin"`). A `Card` titled "Teacher access" with:
  - The list of current grants: teacher email + "All subjects" or the narrowed chips, with a remove (custom-confirm) + an "Edit subjects" control.
  - An "Add teacher" row: a custom `Select` of org members (excluding admins/existing grantees) → on pick, `createClassGrant({user, class_group: Number(classId), all_subjects: true})`.
  - "Narrow to subjects": a multi-select of the class's `Subject`s → sets `all_subjects=false` + `subjects:[ids]`; clearing → `all_subjects=true`.
  - Honest empty/loading/403 states via toast (never `alert`); custom Select (no native `<select>`); tap targets ≥40px.

- [ ] **Step 3: Render** `<AccessSection classId={id} />` on the class page (after `RostersSection`), gated to admins. Build + lint clean.

- [ ] **Step 4: Commit** `feat(access): admin 'Teacher access' UI on the class page`.

---

### Task 6: Member experience polish

**Files:** none new — verify the filtered API flows through existing pages.

- [ ] **Step 1:** As a granted member, confirm `/classes` shows only granted classes, the class page shows only granted subjects (and tests), the dashboard "Recent classes" respects it. Add a small empty-state line on `/classes` ("No classes yet — ask an admin to grant you access.") when an org member has zero visible classes. **Step 2: Commit.**

---

### Task 7: Final isolation sweep + cross-cutting tests

- [ ] **Step 1:** Add adversarial tests: re-parenting a Subject/Test into a class the member lacks a grant for → blocked (mirror the existing parent-FK gating). A removed membership → grants stop applying (the org-header path already 403s a removed member; assert grant rows don't resurrect access). Generating sheets / scanning under a non-granted class → 403.
- [ ] **Step 2:** Run the **entire** backend suite (`./.venv/Scripts/python.exe manage.py test`) → green. Run the cross-browser E2E (`node e2e/run.mjs`) → green. **Step 3: Final commit + merge** via superpowers:finishing-a-development-branch.

---

## Self-review checklist
- **Spec coverage:** class-level grant (default all subjects) ✓ Task 3; per-subject narrowing ✓ Task 4; admin-only management ✓ Task 2/5; teacher sees only granted ✓ Task 3/6.
- **Security:** every visibility change has an isolation test; admins early-return; cross-org leakage tested; `.distinct()` preserved; folder-sharing untouched (additive OR).
- **`Test.subject` is text** — narrowing matches by name (+ blank = visible); a future FK migration is optional, out of scope here.
- **No placeholders, TDD, frequent commits, exact files.**
