# OMRFlow — Phase 0 (Foundations) Design Spec

- **Date:** 2026-06-17
- **Project:** OMRFlow (`projects/omr.doxaed.com/`)
- **Phase:** 0 — Foundations (pre-MVP bootstrap)
- **Branch:** `omrflow/phase-0` (off `main`)
- **Status:** Approved design → next: implementation plan (writing-plans)

> This spec covers **only Phase 0**. OMRFlow is a 10-phase product (0–9) per
> `prompts/BUILD_ROADMAP.md`; each phase ships independently and gets its own
> spec → plan → build cycle. MVP = Phases 1–5.

---

## 1. Context & goal

OMRFlow is a decoupled **React SPA + Django/DRF JSON API + PostgreSQL** platform for
creating MCQ tests, generating personalized printable OMR bubble sheets, scanning &
auto-grading them server-side, and tracking student improvement across retests. The
authoritative product/design is fixed by the 8 spec docs in `prompts/` (PRD,
TECHNICAL_ARCHITECTURE, DATA_MODEL, OMR_ENGINE_SPEC, DESIGN_SYSTEM, AGENT_PROMPT,
BUILD_ROADMAP, README).

**Phase 0 goal:** stand up the decoupled skeleton — a Django+DRF JSON API and a separate
React+Tailwind SPA — wired to a **local PostgreSQL** install (no Docker), with env-driven
config, the load-bearing **owner-scope isolation foundation**, the full custom **shadcn/ui**
component library in a style guide, and CI. Nothing in Phase 0 is a product feature; it is
the platform every later phase builds on.

## 2. Locked decisions (this session)

| Decision | Choice | Note |
|---|---|---|
| Git isolation | New branch `omrflow/phase-0` off `main`; code under `projects/omr.doxaed.com/` | Excludes the unrelated `habitquest/phase-1a` code commits |
| UI primitives | **shadcn/ui** (Radix + Tailwind), JS mode | Components are copied in and owned/restyled by us |
| UI breadth in Phase 0 | **Full** component library + `/style-guide` | Per spec's literal Phase 0 done-criteria |
| Python | Installed **3.13.3** | Flagged deviation from spec's locked 3.12 |
| Frontend language | **JavaScript/JSX** (not TypeScript) | Per user request ("react js") |
| Containerization | **None** (no Docker) | Local Postgres; Celery/Redis deferred to Phase 4 |
| Build sequence | **Approach B** — walking skeleton → de-risk CV libs → full foundation | Front-loads the two highest-risk unknowns |

### Flagged deviations from the specs (accepted)
- **No Docker** (specs mandate Docker Compose for dev). We use a locally-installed Postgres
  and will run Celery/Redis natively when Phase 4 needs them. All config is env-driven, so
  this is a configuration difference, not a code difference.
- **Python 3.13.3** vs spec-locked 3.12. Django 5/DRF/OpenCV/pyzbar/ReportLab ship 3.13
  wheels; if any native wheel misbehaves, fall back to installing 3.12 alongside.

## 3. Verified environment

- Python 3.13.3, Node v22.21.0, npm 10.9.4 — present.
- PostgreSQL **18.1** running (service `postgresql-x64-18`), listening on `localhost:5432`;
  password `postgress` confirmed working for user `postgres`. (`psql.exe` lives at
  `C:\Program Files\PostgreSQL\18\bin\` and is **not** on PATH.)
- A dedicated database `omrflow` will be created for this project; the machine's other 14
  databases belong to unrelated projects and are out of scope (workspace isolation rule).

## 4. Repository & directory layout

The 8 specs remain in `prompts/` (pristine source of truth). New generated docs live under
`docs/`. Backend and frontend are independent apps.

```
projects/omr.doxaed.com/
├── CLAUDE.md, README.md              # workspace project scaffold (new)
├── memory/ {MEMORY.md, current-state.md, progress-log.md}
├── prompts/                          # the 8 specs — untouched
├── docs/superpowers/specs/2026-06-17-omrflow-phase0-design.md   # this file
├── backend/
│   ├── .venv/ (gitignored)  .env (gitignored)  .env.example
│   ├── manage.py  requirements.txt
│   ├── config/                       # project pkg: settings, urls, wsgi, asgi
│   ├── common/                       # owner-scope base, mixins, permissions, health
│   ├── accounts/ organizations/ billing/ assessments/
│   ├── rosters/ omr/ results/ analytics/
│   └── media/ (gitignored)           # MEDIA_ROOT for generated PDFs / uploaded scans
├── frontend/
│   ├── .env (gitignored)  .env.example  vite.config.js  tailwind.config.js
│   └── src/{api/client.js, components/ui/, routes/, lib/, App.jsx, main.jsx}
└── .gitignore
```

## 5. Build sequence (Approach B)

1. Branch + folders + workspace scaffold (`PROJECTS.md` row, project `CLAUDE.md`/`README.md`,
   seed `memory/`).
2. **Walking skeleton:** create `omrflow` DB → Django `/api/v1/health` (checks DB
   connectivity) → Vite React page fetches it through the axios+JWT client across CORS.
   Proves the decoupled seam (CORS + ports + client) end-to-end.
3. **De-risk CV libs:** `python -c "import cv2, pyzbar.pyzbar, fitz, reportlab"` — confirm the
   native wheels import on Windows + Python 3.13; record the result. Converts a Phase-4
   surprise into a Phase-0 known.
4. **Backend foundation:** 9 apps, custom `User`, minimal `Organization`, owner-scope base +
   global DRF permission, JWT endpoints, env settings, migrations, admin.
5. **Frontend foundation:** Tailwind theme tokens + full shadcn/ui component library +
   `/style-guide` route.
6. CI workflow + tests + commit.

## 6. Backend skeleton & owner-scope foundation

The owner-scope foundation is the load-bearing part of Phase 0; every later model depends on
it, and two pieces here are one-way doors in Django.

- **Custom `User`** (`accounts`): email-unique, `USERNAME_FIELD='email'`, `AUTH_USER_MODEL`
  set **before the first migration** (effectively immutable afterward). Phase 0 = model +
  admin only; signup/verify/login/reset are Phase 1.
- **Minimal `Organization`** (`organizations`): `name`, `owner→User`, `created_at`,
  `updated_at`. A skeleton — invitations, membership, roles, audit log are Phase 6 — but the
  table must exist because the scope foundation references it.
- **`OwnerScopedModel`** (abstract, `common`): nullable `user` FK **XOR** nullable
  `organization` FK, plus `created_at`/`updated_at`. A Postgres `CheckConstraint` enforces
  that **exactly one** of `user`/`organization` is set. A `clean()` hook validates a row's
  scope matches its parent's scope. (Abstract → emits no table of its own; concrete scoped
  models arrive in Phase 2.)
- **`ScopedQuerySet`/manager** + **`IsInScope` DRF permission**, registered as project-wide
  defaults (`DEFAULT_PERMISSION_CLASSES`) so isolation is **global, not per-view**.
- **DRF defaults:** simplejwt authentication, default pagination (`PAGE_SIZE`), throttle
  classes/rates.
- **Endpoints (Phase 0):** `GET /api/v1/health`, `POST /api/v1/auth/token`,
  `POST /api/v1/auth/token/refresh`, `/admin/`. Everything under `/api/v1/`.

### Dependencies (`backend/requirements.txt`)
Core: `django>=5,<6`, `djangorestframework`, `djangorestframework-simplejwt`,
`django-cors-headers`, `psycopg[binary]`, `argon2-cffi`, `django-environ`.
OMR (installed now to surface native issues early, used Phase 3–4): `reportlab`,
`qrcode[pil]`, `opencv-python`, `numpy`, `pyzbar`, `Pillow`, `PyMuPDF`.
Deferred installs (noted, added at their phase): `celery`, `redis` (Phase 4); `openpyxl`
(Phase 5); `razorpay` (Phase 7).

### Settings highlights
`PASSWORD_HASHERS` with `Argon2PasswordHasher` first; `AUTH_USER_MODEL='accounts.User'`;
`REST_FRAMEWORK` (JWT auth, global scope permission, pagination, throttling); `SIMPLE_JWT`
short access + refresh TTLs; `CORS_ALLOWED_ORIGINS` from env; `MEDIA_ROOT=backend/media`,
`MEDIA_URL=/media/`; all secrets via `django-environ` (never hardcoded).

## 7. Environment & config (local Postgres, no Docker)

- `backend/.env` (gitignored): `DJANGO_SECRET_KEY`, `DEBUG=True`,
  `DATABASE_URL=postgres://postgres:postgress@localhost:5432/omrflow`,
  `CORS_ALLOWED_ORIGINS=http://localhost:5173`, `ALLOWED_HOSTS=localhost,127.0.0.1`.
- `backend/.env.example` (committed): every key with placeholder values.
- `frontend/.env` (gitignored): `VITE_API_BASE_URL=http://localhost:8000/api/v1`;
  `frontend/.env.example` committed.
- Driver: `psycopg` (v3). DB `omrflow` created via the full path to PG18's `psql.exe`.

## 8. Frontend skeleton & shadcn/ui library

- **Vite + React (JavaScript/JSX)**; shadcn/ui configured in JS mode.
- **Tailwind theme** seeded from `DESIGN_SYSTEM.md`: type scale 12/14/16/20/24/32, spacing
  4/8/12/16/24/32, radius 8 (inputs/cards) / 12–16 (modals), a small semantic color palette
  (primary + success/warning/error/info) as CSS variables for theming.
- **Full custom component library** (`src/components/ui/`): shadcn primitives — Button,
  Input, Label, Textarea, **Select**, **Dialog** (Modal), **AlertDialog** (Confirm),
  **Toast** (sonner), DropdownMenu (Menu), Tabs, Table (DataTable base), Checkbox,
  RadioGroup, Switch (toggle), Form, Progress, Accordion — plus hand-built **Stepper**,
  **EmptyState**, and a **Recharts Chart wrapper**. **No native `<select>`/`alert()`/
  `confirm()`/`prompt()` anywhere.**
- `src/api/client.js`: axios `baseURL` from `VITE_API_BASE_URL`, JWT request interceptor +
  refresh-on-401.
- Routing via `react-router-dom`; a `/style-guide` route renders every primitive; a health
  page demonstrates a live API call across CORS.

## 9. CI & testing

- **Backend tests (Phase 0 scope):** owner-scope `CheckConstraint` rejects rows with zero or
  both scopes; `ScopedQuerySet` filters by request scope; `/api/v1/health` returns ok with
  `db: ok`; custom-`User` creation via email.
- **CI:** a GitHub Actions workflow running backend `python manage.py test` + frontend
  `npm run build`/lint. Activates when a remote exists; locally, equivalent run scripts are
  provided. (If no remote push is planned, the workflow file is harmless and can stay.)

## 10. Workspace integration

Register OMRFlow as a first-class workspace project: add a row to `PROJECTS.md`; create the
project `CLAUDE.md` and `README.md` from `_template/`; seed `memory/MEMORY.md`,
`current-state.md`, and `progress-log.md` with Phase 0 status.

## 11. Definition of Done

- [ ] `omrflow` DB created; backend migrates; `/admin/` and `GET /api/v1/health` load.
- [ ] SPA fetches `/api/v1/health` across CORS through the axios+JWT client.
- [ ] `import cv2, pyzbar.pyzbar, fitz, reportlab` succeeds on Win+Py3.13 (result recorded).
- [ ] `OwnerScopedModel` + `CheckConstraint` + `ScopedQuerySet` + global `IsInScope`
      permission in place, with passing unit tests.
- [ ] Custom `User` + minimal `Organization` + JWT token/refresh endpoints work.
- [ ] Full shadcn-based UI library renders at `/style-guide`; no native dropdown/alert used.
- [ ] CI workflow present; backend tests pass; frontend builds.
- [ ] Workspace scaffold complete + `PROJECTS.md` row added.
- [ ] Committed on `omrflow/phase-0`; `.env`/`.venv`/`media`/`node_modules` gitignored;
      `.env.example` files committed.

## 12. Risks & mitigations (Phase 0-relevant)

- **Native CV libs on Windows** (pyzbar's zbar DLL, OpenCV, PyMuPDF, ReportLab): smoke-test
  imports in step 3; pin known-good wheels. A failure here would block Phases 3–4.
- **Python 3.13 vs 3.12 deviation:** generally fine; if a wheel misbehaves, install 3.12
  alongside and recreate the venv.
- **DB password is literally `postgress`** (double-s) — confirmed working; a wrong value
  silently breaks every migration/run. Target the running PG18 cluster on port 5432.
- **Repo hygiene:** build only on `omrflow/phase-0`, files under `projects/omr.doxaed.com/`;
  never touch sibling projects (`habittracker/`, etc.) per the workspace isolation rule.

## 13. Out of scope for Phase 0 (deferred to later phases)
Account flows (Phase 1) · assessments/tests/questions (Phase 2) · rosters & OMR generation
(Phase 3) · scanning/grading/Celery/Redis (Phase 4) · analytics/export (Phase 5) · org
features/billing/Razorpay (Phases 6–7) · hardening & mobile (Phases 8–9). Phase 0 creates the
empty `billing`/`assessments`/`rosters`/`omr`/`results`/`analytics` apps but no models in
them beyond the scope foundation's `User`/`Organization`.
