# Current State

- 2026-06-17: **Phase 0 (Foundations) complete.** Backend and frontend skeletons run against
  local Postgres `omrflow` (no Docker). Owner-scope foundation, custom User, minimal
  Organization, JWT endpoints, health endpoint, full shadcn UI library + style guide, and CI
  are in place; full test suite green (11 tests). Native CV libs import-verified on Win+Py3.13.
- **Next:** Phase 1 (Accounts) per `prompts/BUILD_ROADMAP.md` — signup, email verification,
  login/logout, password reset, profile; Argon2 + throttle/lockout already configured.
- 2026-06-17: Extracted to its OWN standalone git repository (in place, fresh history; `backend/`
  & `frontend/` at repo root). The granular 19-commit Phase-0 build history is archived on the
  workspace's `omrflow/phase-0` branch. CI now lives at `.github/workflows/ci.yml` in this repo.

## Deferred follow-ups (surfaced during Phase 0 reviews)
- **Phase 6:** `common/permissions.py` `IsInScope.has_object_permission` should call
  `super().has_permission()` and add the organization-membership path (currently solo-only;
  org-scoped objects are denied for now).
- **Phase 2:** `OwnerScopedModel.clean()` is NOT auto-called by `Model.save()`; DRF serializers
  must call `full_clean()` (or rely on the DB CheckConstraint). Document this in serializers.
- **Phase 1 (IMPORTANT):** `IsInScope` is the GLOBAL default DRF permission, so every public
  view (signup, login, password-reset request/confirm, email-verify) MUST explicitly set
  `permission_classes = [AllowAny]` or it silently 401s. Pattern is proven by the health +
  simplejwt token views.
- **Phase 1:** `accounts.User` inherits unused `first_name`/`last_name` columns from
  AbstractUser (we use `full_name`); optionally null them in a migration while convenient.
  Also `frontend/src/components/ui/form.jsx` is hand-authored (shadcn v4 radix-nova registry
  lacked `form`) and unexercised until the first form screen — validate it then.
- **Later:** the frontend JS bundle exceeds Vite's 500 kB warning (recharts) — add code-splitting.
