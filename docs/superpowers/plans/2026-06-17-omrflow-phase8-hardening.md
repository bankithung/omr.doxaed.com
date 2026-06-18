# OMRFlow Phase 8 (Hardening & polish — production-grade) Implementation Plan

> Standalone repo `projects/omr.doxaed.com/` (own `.git`), branch `phase-8`. Paths relative to repo
> root. Commit to THIS repo. TDD where testable; `- [ ]` steps. venv `backend/.venv`.

**Goal:** Take the working app to production-grade: env-driven production security settings, the
deferred auth hardening, async scanning (Celery, eager-in-dev), DB indexes, frontend code-splitting +
accessibility, and deployment docs + an OWASP checklist. Stays runnable locally (no Docker, no broker).

## Locked decisions
- **D1 Security via env, dev unchanged:** all production toggles default to dev-safe values; setting
  `DEBUG=False` + the prod env vars flips on HSTS/secure-cookies/SSL-redirect. Static via WhiteNoise.
- **D2 Async eager-in-dev:** real Celery app; `CELERY_TASK_ALWAYS_EAGER` defaults True (inline, no
  broker) — prod sets it False with `CELERY_BROKER_URL`. Scan processing becomes a `@shared_task`.
- **D3 Auth hardening:** registration no-enumeration (generic response; email existing users instead of
  400-leaking); verify-email scoped throttle; login lockout via django-axes.

---

## Task 1: Production security settings + auth hardening (TDD)
**Files:** `backend/config/settings.py`, `accounts/{views,serializers,emails}.py`, `.env(.example)`, tests.
- [ ] Install `whitenoise` + `django-axes`; `pip freeze > requirements.txt`.
- [ ] `settings.py` — add env-driven security (all default dev-safe):
  - `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE="Lax"`,
    `SESSION_COOKIE_SECURE=env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)`,
    `CSRF_COOKIE_SECURE` likewise, `CSRF_COOKIE_SAMESITE="Lax"`.
  - `SECURE_SSL_REDIRECT=env.bool(default=False)`, `SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")`,
    `SECURE_HSTS_SECONDS=env.int(default=0)` (+ INCLUDE_SUBDOMAINS/PRELOAD when set),
    `SECURE_CONTENT_TYPE_NOSNIFF=True`, `SECURE_REFERRER_POLICY="same-origin"`, `X_FRAME_OPTIONS="DENY"`.
  - WhiteNoise: add `whitenoise.middleware.WhiteNoiseMiddleware` (after SecurityMiddleware); `STATIC_ROOT=BASE_DIR/"staticfiles"`; `STORAGES["staticfiles"]` = WhiteNoise compressed manifest.
  - A guard: if `not DEBUG` and `SECRET_KEY` is the dev default or `ALLOWED_HOSTS` is empty → raise `ImproperlyConfigured` (fail-closed in prod).
  - django-axes: add to INSTALLED_APPS, `AxesStandaloneBackend` first in `AUTHENTICATION_BACKENDS`, `axes.middleware.AxesMiddleware` last; `AXES_FAILURE_LIMIT=env.int(default=5)`, `AXES_COOLOFF_TIME=1` (hour), `AXES_LOCKOUT_PARAMETERS=[["username","ip_address"]]`, `AXES_ENABLED=env.bool(default=True)`. migrate (axes tables).
- [ ] **Auth hardening:**
  - Registration no-enumeration (`accounts`): on duplicate email, do NOT 400-leak — return the SAME success response as a new signup (e.g. 201 `{detail:"Check your email to verify your account."}`) and instead email the existing user a "you already have an account" notice (console). New email → create + verify email as before. Update the existing `test_register_duplicate_email_rejected` to assert the no-enumeration behavior (same status + no new user created + the existing-account email sent).
  - `VerifyEmailView`: add `throttle_classes=[ScopedRateThrottle]`, `throttle_scope="verify_email"` (+ rate in settings).
  - Login lockout: django-axes wraps `authenticate()`; simplejwt's login goes through it. Add a test: AXES_FAILURE_LIMIT failed logins for an email → subsequent login is locked (403/429). (Use `AccessAttempt`/the axes lockout response; reset between tests via `axes` utils or `cache.clear()`.)
- [ ] `manage.py collectstatic --noinput` works. Tests for: secure-cookie/HSTS settings respond to env; the prod SECRET_KEY/ALLOWED_HOSTS guard; no-enumeration register; verify-email throttle; axes lockout. Commit `feat(hardening): production security settings + auth hardening (no-enumeration, axes lockout, throttles)`.

## Task 2: Async scanning (Celery, eager-in-dev) + DB indexes (TDD)
**Files:** `backend/config/celery.py`, `config/__init__.py`, `omr/tasks.py`, `omr/views.py`, model `Meta.indexes`, settings, tests.
- [ ] Install `celery` + `redis`; freeze. `config/celery.py`: `app = Celery("omrflow")`, config from Django settings (`namespace="CELERY"`), autodiscover. Import it in `config/__init__.py`. Settings: `CELERY_BROKER_URL=env(default="redis://localhost:6379/0")`, `CELERY_TASK_ALWAYS_EAGER=env.bool(default=True)`, `CELERY_TASK_EAGER_PROPAGATES=True`.
- [ ] `omr/tasks.py`: `@shared_task process_scan_job_task(job_id)` → loads the ScanJob, calls the existing `process_scan_job`. The scan upload endpoint enqueues `process_scan_job_task.delay(job.id)` per job (in eager mode it runs inline → identical behavior; in prod async). Batch status flips to done when all jobs processed (the task updates batch.processed; a final check sets done). Keep the existing synchronous path working under eager.
- [ ] **DB indexes** (`Meta.indexes` / `db_index`): add indexes on hot paths — `StudentResult(test, student, graded_at)`, `QuestionResponse(student_result, question)`, `ScanJob(batch, omr_sheet, status)`, `OmrSheet(test)`, `GenerationEvent(organization, user, created_at)`, `ScanEvent(organization, user, created_at)`, `OrganizationMembership(organization, status)`, `AuditLog(organization, created_at)`. makemigrations + migrate.
- [ ] Tests: scanning still works end-to-end under eager (the Phase-4 round-trip still passes via the task path); `makemigrations --check` clean after indexes. Commit `feat(hardening): async scanning via Celery (eager in dev) + DB indexes`.

## Task 3: Frontend code-splitting + accessibility (build-verified)
**Files:** `frontend/src/App.jsx` (lazy routes), components, `eslint.config.js`.
- [ ] Route-level code-splitting: convert route imports to `React.lazy(() => import(...))` wrapped in a `<Suspense fallback={...}>`; verify `npm run build` now emits multiple smaller chunks (the ~900 kB single bundle splits; analytics/recharts loads only on its route).
- [ ] Accessibility pass: add `eslint-plugin-jsx-a11y` (recommended) to the eslint config and fix violations; ensure all interactive custom elements have accessible names/roles, inputs have associated labels, the nav/skip-link, focus-visible styles, and dialogs trap focus (shadcn handles most). Run `npm run lint` clean.
- [ ] `npm run build` succeeds with split chunks; commit `feat(hardening): route code-splitting + accessibility pass`.

## Task 4: Image upload API + deployment config & docs
**Files:** `assessments/serializers.py` (image fields), `omr` (sheet image render — optional), `Procfile`,
`gunicorn.conf.py`, `.env.prod.example`, `docs/DEPLOYMENT.md`, `docs/SECURITY-CHECKLIST.md`.
- [ ] **Question/Option image upload** (deferred feature): add `image` to `QuestionSerializer`/`OptionSerializer`
  (ImageField, optional) + ensure the question endpoints accept multipart; a test uploading an image to a question. (Rendering images on the OMR sheet is optional/deferred — note it.)
- [ ] **Deployment:** a `gunicorn.conf.py` (workers, bind, timeout), a `Procfile`/start script (web: gunicorn config.wsgi; worker: celery -A config worker), a `backend/.env.prod.example` with ALL prod env vars (DEBUG=False, real SECRET_KEY, ALLOWED_HOSTS, DATABASE_URL, CORS, Razorpay keys, EMAIL_*, SECURE_* toggles, CELERY_BROKER_URL, CELERY_TASK_ALWAYS_EAGER=False). `docs/DEPLOYMENT.md`: step-by-step (Postgres, Redis, env, migrate, collectstatic, gunicorn behind nginx, the React build served as static / on a CDN, the Razorpay webhook URL, seed_plans). `docs/SECURITY-CHECKLIST.md`: OWASP Top 10 mapped to what's done + what to verify before launch.
- [ ] Commit `feat(hardening): image upload API + deployment config + security/deploy docs`.

## Task 5: Phase 8 wrap-up + comprehensive production-readiness review + merge
- [ ] Full backend suite + check + `makemigrations --check`; `collectstatic` works; frontend `npm run build` (split) + `npm run lint`. A COMPREHENSIVE final review across the whole app: security (settings prod-safe, axes, throttles, no secrets, scope), the test suite, deployment readiness, and a spot-check that the core loop still works. Memory; merge `phase-8` → `main`.

## Self-review
- Production-grade items: security settings, auth hardening, async scanning, indexes, code-splitting,
  a11y, deployment docs, OWASP checklist. All default-dev-safe so local stays runnable.
- Deferred to Phase 9 / ops: real Redis + Celery worker in prod (config provided); load/perf testing;
  monitoring/Sentry; CDN; the mobile app.
