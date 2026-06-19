# Exam-First IA Refactor — Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or executing-plans. Steps use checkbox (`- [ ]`) syntax. This changes the scope/visibility layer (class-optional tests) — every backend task ships isolation tests; never weaken `common/scope.py` without one.

**Goal:** Mirror the **Supabase flow**: **organization-first for everyone** (no loose/personal mode — a solo user just gets their own org), the org **home = an Exams grid** (the "projects" equivalent), and the **Exam is the hero** work unit (create directly; class optional). Classes become an optional organizer.

**Architecture:** Every user must have an ACTIVE organization; on login with none → forced "Create organization" (Supabase-style). `Test.class_group` becomes **nullable** (an exam may be class-less). The sidebar is always org-scoped: **Home · Exams · Classes · Members · Settings** (org switcher on top). New **Exams** hub = the org home (grid of all exams + "New exam"). **Folders** removed from the product nav; **standalone Rosters** removed (rosters live inside a class; org-level reuse where needed). Owner decisions (locked 2026-06-19): org-first for everyone; org home = Exams grid; class optional; Folders unnecessary (class is the grouping); rosters inside class.

**Tech stack:** Django 5 + DRF (backend) · React 19 + Vite + Tailwind v4 + shadcn/ui (frontend).

---

## Current state (verified)
- `Test.class_group` = **required** FK → `ClassGroup` (assessments/models.py:52). `Subject.class_group` required.
- `GET /tests/` with NO `?class_group` already returns ALL visible exams (TestViewSet.get_queryset) → an Exams hub can use it.
- Nav is a STATIC list in `frontend/src/components/shell/nav-config.js` (Home / Workspace[Classes,Folders,Rosters] / Tests[Scan] / Organization / Settings) — identical for solo & org.
- `common/scope.visibility_q("class_group__","created_by")` ALREADY has a class-less branch: `Q(class_group__isnull=True) & Q(created_by=user)` → a class-less test is visible to its creator; admins early-return full. So class-less visibility mostly works already.
- `can_edit_class(request, None)` returns False for non-admin members → must be handled so a member can create/edit their OWN class-less exam.

---

### Task 1: Backend — class-optional exams

**Files:** Modify `backend/assessments/models.py`, `serializers.py`, `views.py`; create migration; tests in `backend/assessments/tests_classless_tests.py`.

- [ ] **Step 1 — Failing tests** (`tests_classless_tests.py`): solo user POSTs `/tests/` with NO class_group → 201, class_group null; lists in `GET /tests/`; can add questions + generate. Org member POSTs a class-less test → 201 (their own), visible to them + admin, NOT to another member; another member cannot retrieve it (404). Update/delete of a class-less test allowed only by creator/admin.
- [ ] **Step 2 — Model**: `class_group = models.ForeignKey(ClassGroup, null=True, blank=True, on_delete=models.CASCADE, related_name="tests")`. `makemigrations assessments`.
- [ ] **Step 3 — Serializer** (`TestSerializer`): `class_group` → `required=False, allow_null=True`. `validate_class_group`: if value is None return None; else keep the `parent_in_scope` check.
- [ ] **Step 4 — Viewset** (`TestViewSet`): 
  - `perform_create`: `cg = validated_data.get("class_group"); if cg is not None and not can_edit_class(...): raise PermissionDenied`. (class-less → allowed; creator stamped by scope.)
  - `perform_update`: gate source only when `instance.class_group` is not None; gate destination only when new cg is not None; when both None, allow (creator already proven by queryset scope). When moving class-less→class, the destination gate applies.
  - `perform_destroy`: gate only when `instance.class_group` is not None; else allow (queryset already scoped to creator/admin).
  - `get_queryset`: subject-narrowing block already guarded by `if cg:` (the `?class_group` param) — unaffected.
- [ ] **Step 5 — Run** `./.venv/Scripts/python.exe manage.py test assessments` → green. **Commit** `feat(exam): allow class-optional exams`.

---

### Task 2: Frontend — org-first gate + org-scoped nav

**Files:** new `frontend/src/auth/RequireOrg.jsx` (gate); `App.jsx` (wrap shell routes); `frontend/src/components/shell/nav-config.js`; `AppShell.jsx`; `frontend/src/org/OrgContext.jsx` (auto-select single org).

- [ ] **Step 1 — Org gate**: `RequireOrg` wraps the shell routes. If `orgs.length === 0` → `<Navigate to="/organizations/new">` (a forced create screen). If orgs exist but no `activeOrgId` → auto-select the first (in OrgContext) so there's always an active org. The create-org screen + org switcher already exist (`/organizations`, OrgContext.setActiveOrg) — reuse; add a dedicated `/organizations/new` create page (or reuse the Organizations create flow) that on success sets it active and redirects to `/exams`.
- [ ] **Step 2 — Nav** (always org): `nav-config.js` → sections Home(/dashboard) · Exams(/exams) · Classes(/classes) · Members(→ org panel for active org) · Settings(/profile, footer). NO Folders, NO standalone Rosters, NO separate Tests/Scan rail item (Scan lives in the exam-scoped panel). Keep the org switcher.
- [ ] **Step 3**: `AppShell.jsx` consumes the new nav. Build + lint. **Commit** `feat(nav): org-first gate + org-scoped sidebar (Supabase-style)`.

---

### Task 3: Frontend — Exams hub page

**Files:** Create `frontend/src/routes/Exams.jsx`; add route `/exams`; `frontend/src/api/assessments.js` add `listAllTests(params)` = `GET /tests/`.

- [ ] List all visible exams (title, class name or "—", subject, status, attempt) via `GET /tests/`. Row → `/tests/:id/sheets` (generate) + ActionMenu (Scan/Results/Review/Analytics) — reuse the patterns from `TestList.jsx`. Header action **"New exam"** → `/exams/new`. Empty state → "Create your first exam." Loading skeleton + error state.
- [ ] **Commit** `feat(exam): Exams hub page`.

---

### Task 4: Frontend — class-optional exam creation

**Files:** `frontend/src/routes/TestWizard.jsx` (StepDetails); add route `/exams/new`; `App.jsx`.

- [ ] StepDetails accepts an OPTIONAL `classId` (from route) OR renders a **class picker** (custom Select of the user's classes + a "No class" option) when invoked at `/exams/new`. The class subjects Select only loads when a class is chosen. Create payload omits `class_group` (or sends null) when "No class".
- [ ] Route `/exams/new` → `TestWizard` (no classId). Keep `/classes/:classId/tests/new` (preset class, picker hidden/locked). On finish → navigate to `/tests/:id/sheets` (was `/classes/:classId`); when class-less there's no class page to return to.
- [ ] **Commit** `feat(exam): create an exam directly (class optional)`.

---

### Task 5: Frontend — Students page + remove Folders/Rosters from nav

**Files:** Create `frontend/src/routes/Students.jsx` (or relabel `Rosters.jsx`); routes `/students`; redirect `/rosters`→`/students`; remove Folders nav (route may stay). Wire the 3 create-pages already built (NewClass `/classes/new`, NewRoster→ now "New student list" `/students/new`, AddStudents `/rosters/:id/students/new` → `/students/:id/...`).

- [ ] "Students" = the rosters list, labelled Students; "New student list" → the NewRoster page. RosterDetail reachable at `/students/:id` (keep `/rosters/:id` as alias). Replace the create modals on Classes/Rosters/RosterDetail with navigation to the dedicated pages built earlier (NewClass/NewRoster/AddStudents).
- [ ] Remove `Folders`/`Rosters` from nav (done in Task 2); ensure no dead nav links. **Commit** `feat(nav): Students hub; retire Folders/standalone Rosters from nav`.

---

### Task 6: Wiring, dashboard, E2E + verification

**Files:** `App.jsx` routes; `Dashboard.jsx` quick actions (Create exam / Add students); `e2e/run.mjs`.

- [ ] Update Dashboard quick actions + "recent" to exam-first. Update breadcrumbs/labels.
- [ ] **E2E**: `create-class` step → now optional; rewrite the journey to **create an exam directly** (`/exams` → New exam → no class → questions → ready), keep one org-path test that still uses a class. Update create-roster/add-students steps to the dedicated pages (`/students`). 
- [ ] Run full backend suite + `node e2e/run.mjs` → green. **Final commit + memory update.**

---

## Self-review checklist
- **Owner decisions honored:** Personal=Exams+Students ✓(T2); class optional ✓(T1,T4); Folders removed ✓(T2,T5); rosters in class / Students ✓(T5).
- **Security:** class-less test visibility = creator+admin (visibility_q class-less branch already covers it; T1 adds isolation tests); a member cannot see another member's class-less exam; re-parent gating preserved.
- **No data loss:** existing class-bound exams unaffected (nullable is additive); `/rosters` + `/folders` routes kept as redirects/back-compat.
- **TDD on the backend change; frequent commits; exact files.**
