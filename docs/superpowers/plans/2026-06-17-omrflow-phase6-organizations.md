# OMRFlow Phase 6 (Organizations & roles) Implementation Plan

> Standalone repo `projects/omr.doxaed.com/` (own `.git`), branch `phase-6`. Paths relative to repo
> root (`backend/...`). Commit to THIS repo. TDD; `- [ ]` steps. venv `backend/.venv`.

**Goal:** A user can create an organization (becoming its admin), invite staff by email, and the org's
members share an org workspace (classes/tests/rosters/sheets/results owned by the org, visible to all
members). Admins manage membership/roles; all actions are audit-logged. Solo behavior is unchanged.

**Architecture:** Introduce a request "active scope" — solo (the user) by default, or an org context
when the request carries an `X-Organization-Id` header and the user is an active member. A single
`common/scope.py` helper produces the scope and a `scope_filter(request, prefix)` Q object; EVERY
tenant viewset routes through it so the change is centralized and the 308 existing solo tests keep
passing (no header → user filter, identical to today). Org-owned rows are shared across members.

## Locked decisions
- **D1 Active scope:** header `X-Organization-Id`. If present and the user is an `active` member of that
  org → scope = (organization=org). If present but not a member → 403. Absent → scope = (user=request.user).
- **D2 `common/scope.py`:** `get_request_scope(request) -> (user|None, org|None)` (raises PermissionDenied
  on non-member org header); `scope_filter(request, prefix="") -> Q` (`Q(**{prefix+'organization': org})`
  if org else `Q(**{prefix+'user': user})`); `scope_kwargs(request) -> dict` for create (`{'organization':org}`
  or `{'user':user}`).
- **D3 Viewsets route through scope:** `ScopedModelViewSet.get_queryset` → `filter(scope_filter(request))`;
  `perform_create` → `serializer.save(**scope_kwargs(request), **owner_extra)`. Child-scoped viewsets use
  `scope_filter(request, prefix="test__")` (or the right FK chain). FK-parent validators accept a parent in
  the SAME scope (user's own OR the active org's).
- **D4 Org data is org-owned (shared):** all active members see all org-scoped rows; `created_by` records the
  author. "Admin sees all members' work" is inherent (shared) + the audit log. Roles gate management actions.
- **D5 Org creation gate:** spec says creating an org requires a paid subscription — DEFERRED to Phase 7
  (billing). Phase 6 allows org creation; Phase 7 adds the subscription gate. Documented.
- **D6 Roles:** `admin` (manage members/roles/org, + billing later) and `member`. The creator is auto-admin.

## Models (`organizations/models.py`)
- `Organization` (exists): name, owner→User, timestamps. Add `__str__` (have).
- `OrganizationMembership`: organization FK (related_name memberships), user FK (related_name memberships),
  role (admin|member), status (active|invited|removed), joined_at; unique_together (organization, user).
- `Invitation`: organization FK, email, token (unique), role, invited_by FK, expires_at, accepted_at null,
  created_at.
- `AuditLog`: organization FK, actor FK→User null, action (char), target_type (char), target_id (int null),
  metadata JSON, created_at.

---

## Task 1: Org models + scope helper + DIRECT-scoped viewsets (TDD — careful refactor)
**Files:** `organizations/models.py`, `common/scope.py`, `common/viewsets.py`, `common/permissions.py`,
`assessments/views.py` + `serializers.py`, `rosters/views.py` + `serializers.py`, tests.
- [ ] Add `OrganizationMembership`, `Invitation`, `AuditLog` models. makemigrations + migrate.
- [ ] `common/scope.py`:
```python
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from organizations.models import OrganizationMembership


def get_active_org(request):
    org_id = request.headers.get("X-Organization-Id") or request.query_params.get("org")
    if not org_id:
        return None
    m = OrganizationMembership.objects.filter(
        organization_id=org_id, user=request.user, status="active"
    ).select_related("organization").first()
    if not m:
        raise PermissionDenied("Not a member of this organization.")
    request._membership = m
    return m.organization


def scope_filter(request, prefix=""):
    org = get_active_org(request)
    if org is not None:
        return Q(**{f"{prefix}organization": org})
    return Q(**{f"{prefix}user": request.user})


def scope_kwargs(request):
    org = get_active_org(request)
    return {"organization": org} if org is not None else {"user": request.user}
```
- [ ] `common/viewsets.py` `ScopedModelViewSet`: `get_queryset` → `super().get_queryset().filter(scope_filter(self.request))`; `perform_create` → `serializer.save(**scope_kwargs(self.request), **{f: self.request.user for f in self.owner_extra_fields})`.
- [ ] `common/permissions.py` `IsInScope.has_object_permission`: allow if `obj.user_id == request.user.id` OR (`obj.organization_id` and the user is an active member of `obj.organization_id`). (Add the org path the Phase-0 review flagged.)
- [ ] Update FK-parent validators in assessments/rosters serializers (`validate_class_group`, `validate_test`, `validate_roster`): accept a parent whose scope matches the request scope — i.e. parent is `user`-owned by the requester OR `organization`-owned by the active org. Implement a `validate_in_scope(value, request)` helper.
- [ ] Tests (`organizations/tests_orgs.py` + adjust existing if needed): (a) SOLO unchanged — no header → existing behavior (run the full suite, 308 still pass); (b) with `X-Organization-Id` of an org the user is an active member of, ClassGroup/Test/Roster create→list are org-scoped and visible to ANOTHER member; (c) a non-member's header → 403; (d) cross-org isolation (member of org1 can't see org2 data).
- [ ] Commit `feat(organizations): membership/invitation/audit models + org-aware scope (direct viewsets)`.

## Task 2: Child-scoped viewsets + generation/scan honor org scope (TDD)
**Files:** `assessments/views.py` (QuestionViewSet), `omr/views.py` (generate, scan, sheets, batches),
`results/views.py`, `analytics/views.py`, tests.
- [ ] Replace hardcoded `test__user=request.user` (and `*_user=request.user`) filters with `scope_filter(request, prefix="test__")` (or the correct FK chain, e.g. `omr_sheet__test__`, `scan_job__batch__test__`) across QuestionViewSet, omr generate/scan/sheets/batches, results, review, analytics. The generate/scan endpoints' `get_object_or_404(Test, ...)` ownership checks must accept org-owned tests for active members → use `scope_filter`.
- [ ] Tests: an org member generates sheets + uploads a scan for an ORG-owned test and sees the results; another member of the same org sees them; a member of a DIFFERENT org gets 404. Solo still isolated.
- [ ] Run the FULL suite — all green (solo + org). Commit `feat(organizations): child-scoped endpoints + generation/scan/analytics honor org scope`.

## Task 3: Org management endpoints + roles + audit log (TDD)
**Files:** `organizations/serializers.py`, `views.py`, `urls.py`, `emails.py`, tests.
- [ ] `POST /api/v1/organizations/` → create org + an `admin` active OrganizationMembership for the creator + AuditLog. `GET /api/v1/organizations/` → orgs the user is an active member of (with role).
- [ ] `POST /api/v1/organizations/{id}/invite/` `{email, role}` (admin only) → create Invitation + email a link (console) to `FRONTEND_URL/accept-invite?token=...`; audit. `POST /api/v1/invitations/accept/` `{token}` (auth'd user whose email matches) → create/activate membership; audit.
- [ ] `GET /api/v1/organizations/{id}/members/` (member) → list memberships (role/status/user email). `PATCH /api/v1/organizations/{id}/members/{user_id}/` (admin) → change role. `DELETE` (admin) → set status removed. (Admin cannot remove/demote the last admin.) Audit each.
- [ ] `GET /api/v1/organizations/{id}/audit/` (admin) → recent AuditLog entries.
- [ ] A small `require_org_role(request, org, role)` helper / permission. Tests: admin invites → member accepts → member sees org workspace; member CANNOT invite/remove (403); last-admin protection; audit entries created; cross-org 404.
- [ ] Commit `feat(organizations): org creation, invitations, member management, roles, audit log`.

## Task 4: Frontend — org context + management
**Files:** `src/api/orgs.js`, an `OrgContext`, an org switcher in the nav, `routes/Organizations.jsx`,
`routes/OrgMembers.jsx`, `routes/AcceptInvite.jsx`, set the `X-Organization-Id` header on the api client.
- [ ] `OrgContext` (active org id in localStorage); the axios client adds `X-Organization-Id` when set. A nav switcher (Personal vs each org) updates the context and refetches. Create-org dialog; members page (invite by email + role, list, change role, remove — admin only); accept-invite screen reading `?token=`. Build clean.
- [ ] Commit `feat(organizations): org switcher + management UI`.

## Task 5: Phase 6 wrap-up + review + merge
- [ ] Full backend suite + check + frontend build; `makemigrations --check`. Review (scope refactor preserves solo isolation AND enforces org sharing + cross-org isolation; role gating; audit). Memory; merge `phase-6` → `main`.

## Self-review
- The scope refactor is centralized in `common/scope.py`; every tenant viewset routes through it, so solo
  behavior is preserved (no header) and org sharing/isolation is added uniformly. Roles gate management.
- Deferred: org-level analytics dashboards (could add); the org-creation→billing gate (Phase 7).
