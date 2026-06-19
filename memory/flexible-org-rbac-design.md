---
name: flexible-org-rbac-design
description: The locked Supabase-grade redesign — flexible org types, nested-group tree, full RBAC, new plans, 4-level IA
metadata:
  type: project
---

Locked 2026-06-19 with the owner. Full design: `docs/superpowers/specs/2026-06-19-flexible-org-taxonomy-rbac.md`.
Supabase UI reference HTML lives in `prompts/uiuxreference/` (organisation/ = Projects page, project page/ =
Project Overview). **Design only — not yet implemented** (build order = spec §6).

**The pivot:** the product becomes Supabase-shaped and production-grade. Four nav levels:
**Organizations list (no sidebar)** → **Org workspace** (Dashboard·Members·Roles&Permissions·Usage·Billing·
Settings) → **Group workspace** (recursive, type-aware) → **Exam workspace** (Questions·Students·Marks·
Analytics·Scan·Share). Entry is now an explicit ORG LIST (supersedes the org-first auto-select-into-an-org).

**Locked decisions:**
- **Types + nesting:** `Organization.type` (personal/school/college/university/coaching/other) seeds default
  level labels. `ClassGroup` evolves into a self-nesting tree (`parent` self-FK + `kind_label` + `order`):
  infinite, renamable nesting. Presets — School: Class→Section · College: Course→Year→Section · University:
  Department→Program→Batch · Coaching: Batch→Section · Personal/Other: Group. Students/Subjects/Exams attach
  to any node; subtree rollups for cohorts/stats; `folder` retired.
- **RBAC (full, v1):** `Role` (custom + seeded Owner/Admin/Teacher/Viewer) · `RoleBinding(user, role,
  scope_group?)` (org-wide or scoped to a group subtree) · `PermissionGrant(user, code, scope_group?)` for
  individuals → `has_perm()`. `common/scope.py` rebuilt on it with the FULL adversarial isolation suite.
  Today's `ClassAccessGrant` (see [[rbac-class-subject-access]]) generalizes into a scoped Teacher binding.
- **Plans:** Free / Pro ₹1000 / Business ₹2000 / Enterprise (default limits in spec §3; tunable in billing).
- **Clean rebuild** — tenant data already wiped; no migration.

**Already shipped that this builds on:** org-first gate + create-org onboarding + Classes-as-Projects grid;
the **class workspace** (Overview + section sidebar via `matchClassScope`/`useClass`); class-optional exams
([[rbac-class-subject-access]] + `can_edit_test`); dedicated Generate & Print page. The class workspace's
recursive section sidebar is the foundation the nested-group tree extends.

**§8 production additions to build:** bulk CSV student import, audit log, exam lifecycle, question bank,
notifications (results-ready/needs-review/billing), student profiles, class/org analytics rollups, guided
onboarding, invoices.
