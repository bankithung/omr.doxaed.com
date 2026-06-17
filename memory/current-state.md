# Current State

- 2026-06-17: **Phase 1 (Accounts) complete.** Email/password auth on the standalone repo
  (branch `phase-1` → merged to `main`): register, email verification, login (JWT + user),
  logout (refresh blacklist), password reset (request + throttled confirm, no enumeration),
  profile `me/`. Security-reviewed (opus): AllowAny discipline, Argon2, scoped throttles, tokens
  fail-safe. React auth UI (AuthProvider + ProtectedRoute + 6 shadcn screens + context nav).
  **26 backend tests green**; frontend build clean.
- **Next:** Phase 2 (Assessments core, solo scope) per `prompts/BUILD_ROADMAP.md` — ClassGroup →
  Test CRUD, Question + Option authoring, MarkingScheme, retest linkage; global solo owner-scope
  isolation enforced on every endpoint.
- 2026-06-17: Phase 0 (Foundations) done — decoupled Django+DRF / React(Vite,JS)+Tailwind+shadcn
  skeleton on local Postgres `omrflow` (no Docker); owner-scope foundation; CV libs verified.
- Repo: standalone git repo (own `.git`, `backend/`+`frontend/` at root). The Phase-0 granular
  build history is archived on the workspace's `omrflow/phase-0` branch.

## Deferred follow-ups
- **Phase 2 (apply now):** `OwnerScopedModel.clean()` is NOT auto-called by `Model.save()`; DRF
  serializers for the new scoped models must call `full_clean()` (or rely on the DB
  CheckConstraint). Also set the owner scope (user XOR org) on create from `request.user`.
- **Phase 6:** `IsInScope.has_object_permission` should call `super().has_permission()` and add
  the organization-membership path (currently solo-only; org-scoped objects denied).
- **Phase 8 (hardening, from Phase-1 auth review):** (a) registration returns a distinct 400 on
  duplicate email → email-enumeration; consider generic response + notify-existing-user.
  (b) `verify-email/` has no scoped throttle (only global anon 30/min). (c) full account lockout
  (django-axes) deferred from Phase 1 (DRF scoped throttles used instead).
- **Phase 1 leftovers:** `accounts.User` inherits unused `first_name`/`last_name` (we use
  `full_name`) — optionally null in a migration. `frontend/src/components/ui/form.jsx` is
  hand-authored and STILL unexercised (auth screens use plain controlled forms) — validate when
  first used. Bundle exceeds Vite's 500 kB warning (recharts) — add code-splitting later.

## Resolved
- Phase-1 AllowAny watch-item: applied — every public auth view sets `permission_classes=[AllowAny]`.
