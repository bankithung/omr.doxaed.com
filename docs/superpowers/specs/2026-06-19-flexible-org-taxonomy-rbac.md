# DoxaEd OMR — Flexible Organizations, Nested Groups, RBAC, Plans & IA (design spec)

> **Status:** DESIGN ONLY (owner: "deeply analyse… don't implement yet"). No code until decisions below are confirmed.
> Supersedes parts of `2026-06-19-exam-first-ia-refactor` (org-first auto-select → explicit **org list** entry).

## 0. What the owner asked for (captured)
1. **Org list page is the entry** — *only* a list of organizations + a "Create organization" button. **No sidebar / no chrome.**
2. **Create org** asks: **name · type · plan.** Types: **Personal, School, College, University, Coaching, Other**.
3. **Type drives terminology + structure.** Schools use *Classes → Sections → Students*; universities use *Departments → Programs → …*; users must be able to **name anything** and **nest groups infinitely** (a class → Section A / Section B → under Section A: students *and* further sub-groups).
4. **Plans change:** **Free → ₹1000 → ₹2000 → Enterprise** (was Free/₹500/₹1000/Enterprise).
5. **After entering an org → a sidebar** with: **Dashboard (all classes), Members (roles + permissions), Roles & Permissions (create roles, add permissions, apply to roles *or* individuals), Usage, Billing, Organization Settings** (+ anything missing for production grade).
6. **Under a class (sidebar):** Sub-groups (Sections/…, type-aware) · **Students** · **Subjects** · **Exams**.
7. **Inside an exam:** **Questions · Students list · Marks · Analytics · OMR/Scan · …** — every existing feature placed in a proper page/location.

---

## Decisions (LOCKED 2026-06-19 with owner)
- **D1 ✓** Use the proposed **type-preset table** (§1). Labels are defaults only; every node renamable; **nesting unlimited** (UI lazy-loads deep trees; no hard cap).
- **D2 ✓** **Full RBAC in v1** — custom + system roles, `RoleBinding` **scoped to a group subtree** (or org-wide), plus individual `PermissionGrant`. `common/scope.py` rebuilt on `has_perm`; ships with the full adversarial isolation suite.
- **D3 ✓** Plans **Free / Pro ₹1000 / Business ₹2000 / Enterprise** with the default limits in §3 (tunable later in billing).
- **D4** (pending, non-blocking) routing scheme — lean toward keeping `/classes`,`/tests` paths internally to shrink the diff, with the new IA layered on; revisit per phase.
- **D5 ✓** Tenant data already wiped → **clean rebuild**, no data migration needed.
- **D6 ✓** §8 v1 set: bulk CSV import · audit log · exam lifecycle · question-bank basics · class/org analytics rollups · guided onboarding · invoices. v2: integrations/API keys · calibration · multi-language · per-class branding override.

## 1. The flexible taxonomy — the core of the design

The hard requirement is "**name anything, nest infinitely, defaults by type.**" We model this as a **self-nesting Group tree**, *generalizing the existing `ClassGroup`* (least disruption; ClassGroup already owns Subjects/Rosters/Tests).

**`ClassGroup` evolves into a Group node:**
- add `parent` → self-FK (nullable; null = top-level).
- add `kind_label` (CharField, e.g. "Class", "Section", "Department", "Batch") — the *display type* of this node.
- add `order` (PositiveInt) for sibling ordering.
- keep `organization`, `created_by`, `name`, `description`.
- (the `folder` FK is retired — the tree replaces folders.)

A node can hold **child nodes** (sub-structure) **and** **Students** (its roster), **Subjects**, **Exams** — at whatever depth fits. Drilling into a child = the *same* workspace recursively (a Section is a Group too).

**Type → default level-label presets** (defaults only; every node is renamable; depth is **not** capped):

| Org type   | depth 0   | depth 1   | depth 2  | deeper |
|------------|-----------|-----------|----------|--------|
| School     | Class     | Section   | Group    | Group  |
| College    | Course    | Year      | Section  | Group  |
| University | Department| Program   | Batch    | Group  |
| Coaching   | Batch     | Section   | Group    | Group  |
| Personal   | Group     | Group     | Group    | Group  |
| Other      | Group     | Group     | Group    | Group  |

"Add sub-group" under depth *d* → `kind_label` defaults to `preset[d]` (else "Group"); user can rename. So: *Class 10 → Section A → students*; *Computer Science (Dept) → B.Tech (Program) → 2026 (Batch) → students*.

**Attachment rules:**
- **Students** → a node's roster (any node; usually leaf, e.g. Section A).
- **Subjects** → a node (usually the class/course node); visible to its subtree for exam tagging.
- **Exams** (`Test`) → a node; the exam's **cohort** = that node's subtree students (or a chosen roster). `Test.class_group` already nullable → now points to any node.

**Effective-students / rollups:** a node's "Students" stat = sum over its subtree rosters; lets a class-level exam target all sections.

**Decision D1 — presets above OK?** (and nesting: unlimited vs soft cap ~5 for sane UX).

---

## 2. RBAC — roles + granular permissions (on roles *or* individuals)

Replaces the binary `OrganizationMembership.role ∈ {admin,member}` + the one-off `ClassAccessGrant`.

**Permission catalog** (static codes, grouped):
- **Org:** `org.settings.manage`, `org.billing.manage`, `org.usage.view`, `member.invite`, `member.manage`, `role.manage`, `audit.view`
- **Structure:** `group.create`, `group.edit`, `group.delete`, `subject.manage`, `student.manage`
- **Exams:** `exam.create`, `exam.edit`, `exam.delete`, `exam.generate`, `exam.scan`, `exam.grade`, `exam.results.view`, `exam.analytics.view`, `exam.share`

**`Role`** (org-scoped): `name`, `is_system`, `permissions` (list of codes). Seeded system roles:
- **Owner** — all perms, undeletable, billing + ownership.
- **Admin** — all except ownership transfer.
- **Teacher** — `exam.*` + `student.manage` + `subject.manage` + results/analytics, normally **scoped** to assigned groups.
- **Viewer** — `*.results.view` + `*.analytics.view`.
- **Custom** — admin creates, picks permissions.

**Assignment + scope:**
- **`RoleBinding`** (org, user, role, `scope_group` nullable). `scope_group=null` → org-wide; else the role applies only within that group's **subtree**. (This *is* the generalized ClassAccessGrant: "Teacher @ Class 10/Section A".)
- **`PermissionGrant`** (org, user, `permission_code`, `scope_group` nullable) — grant a single permission to an **individual** (the "permissions on individuals" ask), optionally scoped.

**Enforcement:** `has_perm(user, org, code, group=None)` = (any RoleBinding whose role has `code` and whose scope covers `group`) **OR** (any matching PermissionGrant). Subject-narrowing (current feature) becomes a property on the Teacher binding. `common/scope.py` visibility/edit predicates are rebuilt on `has_perm` (every existing isolation test must still pass).

**Decision D2 — catalog granularity + system roles OK? Is per-group scoping in v1, or v1 = org-wide roles + keep ClassAccessGrant, scoping in v2?**

---

## 3. Plans

| Tier | Price | Intent |
|---|---|---|
| **Free** | ₹0 | try it — 1 admin seat, small caps |
| **Pro** | ₹1000/mo | small school/coaching |
| **Business** | ₹2000/mo | larger, more seats/scans |
| **Enterprise** | custom | unlimited + SSO/support/SLA |

Per-tier **default limits** (reuse the `billing.limits` engine; re-seed `Plan`; tunable later):

| Tier | Seats | Groups | Students | Exams/mo | Scans/mo |
|---|---|---|---|---|---|
| Free | 1 | 2 | 50 | 5 | 100 |
| Pro ₹1000 | 5 | unlimited | 500 | 50 | 2,000 |
| Business ₹2000 | 20 | unlimited | 2,000 | 200 | 10,000 |
| Enterprise | custom | unlimited | unlimited | unlimited | custom + SSO/SLA |

---

## 4. Information architecture — four levels

**L0 · Organizations** (`/organizations`) — **no sidebar.** Grid/list of the user's orgs (name · **type badge** · **plan badge** · role) + **New organization** (name → type → plan). Landing after login. (Org switcher stays *inside* the workspace for quick switching.)

**L1 · Org workspace** (left sidebar):
- **Dashboard** — overview + top-level groups (classes) grid
- **Members** — people + their roles; invite
- **Roles & permissions** — roles, the permission matrix, individual grants
- **Usage** · **Billing** · **Settings** (name, type, branding)
- *(production extras to add: Audit log, API/Integrations later)*

**L2 · Group workspace** (sidebar, **type-aware labels**, recursive):
- **Overview** (stats + sub-groups + recent exams) · **Sub-groups** (e.g. "Sections") · **Students** · **Subjects** · **Exams** · **Settings** (rename node + its `kind_label`, delete)

**L3 · Exam workspace** (sidebar) — places every existing feature:
- **Overview** · **Questions** (build/answer-key) · **Students** (cohort) · **Sheets/OMR** (generate & print — *done*) · **Scan** (auto-grade) · **Results/Marks** (+ review queue) · **Analytics** (item analysis, report cards) · **Share** (public results) · **Settings** (marking scheme, delete)

**Routing (proposed):** `/organizations` · `/o/:org/(dashboard|members|roles|usage|billing|settings)` · `/o/:org/g/:group/(…|sub-groups|students|subjects|exams|settings)` · `/o/:org/e/:exam/(…)`. **Decision D4 — adopt `/o/:org/g/:group` scheme, or keep `/classes` / `/tests` paths for back-compat + smaller diff?**

---

## 5. Data-model & migration summary
- `ClassGroup`: + `parent` (self-FK, null), + `kind_label`, + `order`; drop `folder` usage. Existing rows → top-level nodes (`kind_label="Class"`).
- `Test.class_group`: already nullable → points to any node.
- `Organization`: + `type` (choices).
- New: `Role`, `RoleBinding`, `PermissionGrant`. `OrganizationMembership.role` retained as a coarse flag during transition (admin → Owner binding).
- `ClassAccessGrant` → migrate to `RoleBinding(Teacher, scope_group)` (subject-narrowing kept).
- `Plan` re-seed (Free/Pro/Business/Enterprise).
- Every change ships with isolation tests; `common/scope.py` rebuilt on `has_perm` with all current tests green.

## 6. Build order (once approved — each a shippable phase)
1. **Org type + plan picker** on a real **org-list entry** page (L0). (small) 
2. **Nested group tree** (ClassGroup parent/kind_label + migration) + recursive group workspace (L2 sub-groups). (big — the core)
3. **RBAC** (Role/RoleBinding/PermissionGrant + `has_perm` + Roles & Permissions UI + scope.py rebuild). (big — security-sensitive, adversarially tested)
4. **Org workspace shell** (L1 sidebar: Dashboard/Members/Roles/Usage/Billing/Settings).
5. **Exam workspace** (L3: Questions/Students/Marks/Analytics/Scan/Share as sections).
6. **Plans re-seed** + billing wiring.
7. Production pass (responsive, a11y, empty/loading/error, Supabase-token alignment).

---

## 8. Production-grade additions (gaps filled — things not in the original list)

A best-in-market product needs these; each is placed where it lives in the IA. (✓ = already built, just needs placing; ＋ = new.)

**A. Org level (L1)**
- ＋ **Audit log** — every sensitive action (member/role/permission/billing/delete) with actor·target·time (`AuditLog` model exists, surface it).
- ＋ **Notifications** — in-app bell + email: invite received/accepted, **results ready**, **scans need review**, nearing plan limit, payment events.
- ＋ **Activity feed** on the dashboard (recent exams scanned, members added…).
- ＋ **Pending invitations** management (resend/revoke) under Members.
- ＋ **Seat & usage meters** — seats used / plan cap; usage page (exams·scans this cycle) — Supabase right-rail "plan usage" pattern.
- ✓ **Org branding** (logo + default sheet heading; used on every sheet unless overridden) → in **Settings**.
- ＋ **Danger zone** — transfer ownership · delete org (confirm + audit).
- ✓ **Search (⌘K)** — jump to any class/exam/student/setting (exists; extend scope).
- ＋ **Integrations / API keys** (v2) — LMS/export.

**B. Group/Class level (L2)**
- ＋ **Bulk student import (CSV / paste)** — names + roll numbers; the fast path for schools (alongside manual add + blank-count ✓).
- ＋ **Move / re-parent** a group + its subtree within the org tree.
- ＋ **Archive** (hide, keep data) vs delete.
- ＋ **Subject inheritance** — subjects on a class flow to its sub-groups for exam tagging.
- ✓ **Roster reuse** — a section's roster is its default exam cohort; reusable across exams.
- ＋ **Per-class branding override** (optional).

**C. Exam level (L3)**
- ＋ **Question bank** — reusable question pool (org/class scoped); build an exam from the bank + new questions; **import questions** (CSV). (Today questions are per-test only.)
- ＋ **Exam lifecycle** — Draft → Ready → Live → Closed (+ optional schedule window); status gates generate/scan.
- ✓ **Duplicate / template** + **retest / versions** (exists) → exam actions.
- ✓ **Marking scheme** — per-exam + per-section (competitive), negative/partial/multi-mark policy (exists) → exam **Settings**.
- ✓ **Review queue** — low-confidence/ambiguous scans, manual resolve (exists) → exam section.
- ✓ **Per-student detail** — drill-down: their sheet + marks + corrections (exists).
- ✓ **Re-grade / corrections** — inline scan correction → whole-sheet re-grade (exists).
- ✓ **Exports** — CSV/Excel/PDF + **bulk report-card PDFs** (exists) → in **Results**.
- ✓ **Share / public portal** — publish `/r/:slug`, roll lookup, leaderboard, name-masking (exists) → **Share**.

**D. Student dimension**
- ＋ **Student profile** — a roster student's cross-exam history + performance trend (aggregates existing per-student analytics).
- Parent/student access = the public share portal (no student logins in v1).

**E. Analytics & reporting**
- ✓ **Exam analytics** — difficulty, discrimination, point-biserial, KR-20, distractors, distributions, toppers (exists).
- ＋ **Class/group analytics** — aggregate across the group's exams (trends, **section comparison**).
- ＋ **Org analytics** — KPIs (exams run, students assessed, avg performance) on the org dashboard.
- ✓ **Report cards** — per-student 2-page PDF (exists).

**F. Scanning / OMR**
- ✓ **Sheet modes** — standard · roster pre-bubbled roll · competitive sections (exists; chosen at generate).
- ✓ **Generate & print** — branding + roster + shuffle + question papers (**done**).
- ✓ **Scan** — drag-drop + mobile camera, batch, progress, identity cross-checks (test/roll-mismatch flags) (exists).
- ＋ (v2) **calibration** for real-photo robustness.

**G. Cross-cutting production**
- ＋ **Guided onboarding** — after creating an org (by type): a "create first class · import students · make first exam" checklist.
- ✓ **Email** — verify / reset / invite / results-ready (`doxaed@gmail.com`; provider via env).
- ✓ **Billing** — Razorpay checkout + signature-verified webhooks (exists); ＋ **invoices/receipts**, upgrade/downgrade/proration.
- ✓ **Security/compliance** — PII (names/rolls) encrypted at rest, scoped authed endpoints; Terms/Privacy gating; rate-limits; axes lockout (exists).
- ＋ **Localization** — INR currency; (v2) multi-language.
- ✓ **Mobile-responsive 320→desktop + a11y** (mandatory UI rules).
- ✓ **Ops** — Celery/Redis async scanning, monitoring, backups (deploy checklist exists).
- ✓ **Help & support** — docs / FAQ / help / contact (pages exist).

---

## 7. Decisions to confirm (blocking implementation)
- **D1** Type presets (the label table) + nesting depth (unlimited vs soft cap).
- **D2** RBAC granularity + whether per-group scoping is v1 or v2.
- **D3** Plan tier names + limits (or "use sensible defaults").
- **D4** Routing scheme (`/o/:org/g/:group` vs keep `/classes`).
- **D5** Migration of existing data is moot (tenant data was wiped) — confirm a clean rebuild is fine.
- **D6** Of §8, which are **v1** vs **v2**? (Recommend v1: bulk CSV student import · audit log · exam lifecycle · question-bank basics · class/org analytics rollups · guided onboarding · invoices. v2: integrations/API keys · real-photo calibration · multi-language · per-class branding override.)
