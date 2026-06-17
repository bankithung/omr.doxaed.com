# OMRFlow Phase 0 (Foundations) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the decoupled OMRFlow skeleton — a Django+DRF JSON API and a separate React (Vite, JavaScript) + Tailwind v4 + shadcn/ui SPA — wired to a local PostgreSQL database (no Docker), with the global owner-scope isolation foundation, JWT auth endpoints, the full custom UI component library in a style guide, and CI.

**Architecture:** Two independent apps under `projects/omr.doxaed.com/` (`backend/`, `frontend/`). The backend is a pure JSON API under `/api/v1`; the frontend consumes it over CORS using an axios client with JWT interceptors. Build order is "walking skeleton first" (prove the DB→API→SPA seam and the native CV-lib imports before investing in the foundation), then the owner-scope base, then the UI library.

**Tech Stack:** Python 3.13.3, Django 5 + DRF + djangorestframework-simplejwt + django-cors-headers + psycopg v3 + argon2-cffi + django-environ; PostgreSQL 18 (local, password `postgress`); React 19 (Vite, JSX) + Tailwind CSS v4 (`@tailwindcss/vite`) + shadcn/ui + axios + react-router-dom + Recharts. OMR/CV deps (reportlab, qrcode, opencv-python, numpy, pyzbar, Pillow, PyMuPDF) installed now but used in later phases.

**Conventions for every task:** Windows PowerShell is the primary shell. The backend venv must be activated (`.\.venv\Scripts\Activate.ps1`) before any `python`/`manage.py` command. `psql.exe` is at `C:\Program Files\PostgreSQL\18\bin\psql.exe` (not on PATH). All work happens on the `omrflow/phase-0` branch (already created off `main`). Never read or modify sibling projects under `projects/` (workspace isolation rule).

---

## File Structure

**Backend (`projects/omr.doxaed.com/backend/`)**
- `config/settings.py` — env-driven Django settings (apps, DB, DRF, JWT, CORS, media). One responsibility: configuration.
- `config/urls.py` — root URL map; mounts `/api/v1/health`, JWT token endpoints, admin.
- `common/models.py` — `OwnerScopedModel` abstract base (user XOR organization + CheckConstraint).
- `common/managers.py` — `ScopedQuerySet`/`ScopedManager` (scope filtering).
- `common/permissions.py` — `IsInScope` global DRF permission.
- `common/views.py` — `health` endpoint.
- `common/tests.py` — owner-scope + permission + health + CV-lib-import tests.
- `accounts/models.py` — custom email `User` + `UserManager`.
- `accounts/admin.py`, `accounts/tests.py`.
- `organizations/models.py` — minimal `Organization` skeleton.
- `billing/`, `assessments/`, `rosters/`, `omr/`, `results/`, `analytics/` — empty apps (models added in later phases).
- `requirements.txt`, `.env` (gitignored), `.env.example`.

**Frontend (`projects/omr.doxaed.com/frontend/`)**
- `vite.config.js` — React + `@tailwindcss/vite` plugins + `@/*` alias.
- `jsconfig.json` — `@/*` path alias for editor/shadcn.
- `src/index.css` — `@import "tailwindcss"` + DESIGN_SYSTEM `@theme` tokens + shadcn variables.
- `src/api/client.js` — axios instance + JWT request/refresh interceptors.
- `src/components/ui/*` — shadcn primitives (generated) + hand-built `stepper.jsx`, `empty-state.jsx`, `chart.jsx`.
- `src/routes/StyleGuide.jsx` — renders every primitive.
- `src/routes/Health.jsx` — live API call across CORS.
- `src/App.jsx`, `src/main.jsx` — router setup.
- `.env` (gitignored), `.env.example`.

**Workspace / repo root**
- `projects/omr.doxaed.com/{CLAUDE.md, README.md, .gitignore}`, `memory/{MEMORY.md, current-state.md, progress-log.md}`.
- `PROJECTS.md` (repo root) — add OMRFlow row.
- `.github/workflows/omrflow-ci.yml` (repo root) — CI.

---

## Task 0: Prerequisites — gitignore, database, workspace registration

**Files:**
- Create: `projects/omr.doxaed.com/.gitignore`
- Create: `projects/omr.doxaed.com/README.md`, `projects/omr.doxaed.com/CLAUDE.md`
- Create: `projects/omr.doxaed.com/memory/MEMORY.md`, `memory/current-state.md`, `memory/progress-log.md`
- Modify: `PROJECTS.md` (repo root)

- [ ] **Step 1: Create the project `.gitignore`**

Create `projects/omr.doxaed.com/.gitignore`:

```gitignore
# Python / Django
backend/.venv/
__pycache__/
*.pyc
backend/.env
backend/media/
*.sqlite3
.pytest_cache/

# Node / Vite
frontend/node_modules/
frontend/dist/
frontend/.env

# Misc
.DS_Store
.playwright-mcp/
```

- [ ] **Step 2: Create the `omrflow` PostgreSQL database**

Run (PowerShell):

```powershell
$env:PGPASSWORD = "postgress"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -p 5432 -c "CREATE DATABASE omrflow;"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -p 5432 -c "\l omrflow"
$env:PGPASSWORD = $null
```

Expected: `CREATE DATABASE`, then a row listing `omrflow`. If it already exists (`database "omrflow" already exists`), that is fine — continue.

- [ ] **Step 3: Write the workspace project files**

Create `projects/omr.doxaed.com/README.md`:

```markdown
# OMRFlow

Web (then mobile) platform to create MCQ tests, generate personalized printable OMR
bubble sheets, scan & auto-grade them server-side, and track student improvement across
retests. Stack: Django 5 + DRF (JSON API) · React (Vite, JS) + Tailwind v4 + shadcn/ui ·
PostgreSQL (local). Product specs live in `prompts/`; phase specs/plans in `docs/superpowers/`.
```

Create `projects/omr.doxaed.com/CLAUDE.md`:

```markdown
# OMRFlow — Project Router

Code project. Build strictly phase-by-phase per `prompts/BUILD_ROADMAP.md` (Phases 0–9;
MVP = 1–5). One phase at a time; do not start a phase before the prior is "done".

## Source of truth
- `prompts/` — 8 product specs (PRD, TECHNICAL_ARCHITECTURE, DATA_MODEL, OMR_ENGINE_SPEC,
  DESIGN_SYSTEM, AGENT_PROMPT, BUILD_ROADMAP, README). Treat as authoritative; flag conflicts.
- `docs/superpowers/specs/` and `docs/superpowers/plans/` — per-phase design + implementation.

## Stack & rules
- Backend: Django 5 + DRF, pure JSON API under `/api/v1`, all business logic server-side.
- Frontend: React (Vite, JavaScript) + Tailwind v4 + shadcn/ui; custom components only —
  NO native `<select>`/`alert()`/`confirm()`/`prompt()`. Responsive 320→desktop.
- DB: local PostgreSQL `omrflow` (user `postgres`, password `postgress`, localhost:5432). No Docker.
- Owner-scope isolation is global: every tenant row is owned by user XOR organization.
- OMR grading uses each sheet's stored answer_key; low-confidence reads → review queue, never guessed.
- Secrets via env vars only. Tests required for grading, scope isolation, plan limits.

## Onboarding
Read this file → `memory/MEMORY.md` → `memory/current-state.md` → the active phase plan.
```

Create `projects/omr.doxaed.com/memory/MEMORY.md`:

```markdown
# OMRFlow — Memory Index

**Status:** Phase 0 (Foundations) — in progress (started 2026-06-17).
**Stack:** Django 5 + DRF · React (Vite, JS) + Tailwind v4 + shadcn/ui · local PostgreSQL `omrflow`.
**Branch:** `omrflow/phase-0` off `main`. Code under `projects/omr.doxaed.com/{backend,frontend}`.

## Next steps
- Execute Phase 0 plan: `docs/superpowers/plans/2026-06-17-omrflow-phase0-foundations.md`.
- Then Phase 1 (Accounts) per `prompts/BUILD_ROADMAP.md`.

## Key facts
- DB: `omrflow`, user `postgres`, password `postgress`, localhost:5432 (no Docker). PG18.
- Python 3.13.3 (deviation from spec's 3.12). Node 22.
- UI primitives: shadcn/ui (Radix+Tailwind), JavaScript mode. Charts: Recharts.
- Roadmap: Phases 0–9, MVP = 1–5. Build one phase at a time.

## Memory index
- (none yet)
```

Create `projects/omr.doxaed.com/memory/current-state.md`:

```markdown
# Current State

- 2026-06-17: Phase 0 started. Branch `omrflow/phase-0` created off `main`. Specs + Phase 0
  design + plan committed. Environment verified (Python 3.13.3, Node 22, PG18 with password
  `postgress`). `omrflow` database created. Executing the Phase 0 implementation plan next.
```

Create `projects/omr.doxaed.com/memory/progress-log.md`:

```markdown
# Progress Log

- 2026-06-17 — Analyzed all 8 product specs; verified local toolchain; created
  `omrflow/phase-0` branch; wrote + committed Phase 0 design spec and implementation plan.
```

- [ ] **Step 4: Register OMRFlow in `PROJECTS.md`**

Add this row to the table in `PROJECTS.md` (repo root), after the `habittracker` row:

```markdown
| omrflow | `projects/omr.doxaed.com/` | "OMRFlow" — MCQ test + personalized OMR sheet generation, server-side OpenCV scanning/grading, retest improvement analytics. Django+DRF API + React SPA, local Postgres. | Phase 0 (Foundations) in progress (2026-06-17) | no (code project) | 2026-06-17 |
```

- [ ] **Step 5: Commit**

```powershell
cd C:\Users\Asus\Music\WorkSpace
git add projects/omr.doxaed.com/.gitignore projects/omr.doxaed.com/README.md projects/omr.doxaed.com/CLAUDE.md projects/omr.doxaed.com/memory PROJECTS.md
git commit -m "chore(omrflow): register project + workspace scaffold + create db"
```

---

## Task 1: Backend scaffold (venv, dependencies, Django project, 9 apps)

**Files:**
- Create: `backend/.venv/` (gitignored), `backend/manage.py`, `backend/config/*`, 9 app dirs, `backend/requirements.txt`

- [ ] **Step 1: Create backend dir + virtualenv + upgrade pip**

```powershell
cd C:\Users\Asus\Music\WorkSpace\projects\omr.doxaed.com
mkdir backend
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Expected: prompt now shows `(.venv)`. `python --version` → `Python 3.13.3`.

- [ ] **Step 2: Install core + OMR dependencies**

```powershell
pip install "django>=5,<6" djangorestframework djangorestframework-simplejwt django-cors-headers "psycopg[binary]" argon2-cffi django-environ
pip install reportlab "qrcode[pil]" opencv-python numpy pyzbar Pillow PyMuPDF
```

Expected: all install without error. (If `pyzbar` or `opencv-python` fail to build/install, stop and report — this is the native-lib risk; do not proceed.)

- [ ] **Step 3: Create the Django project and 9 apps**

```powershell
django-admin startproject config .
python manage.py startapp common
python manage.py startapp accounts
python manage.py startapp organizations
python manage.py startapp billing
python manage.py startapp assessments
python manage.py startapp rosters
python manage.py startapp omr
python manage.py startapp results
python manage.py startapp analytics
```

Expected: `backend/manage.py`, `backend/config/`, and 9 app folders now exist.

- [ ] **Step 4: Freeze dependencies**

```powershell
pip freeze > requirements.txt
```

Expected: `requirements.txt` lists Django, djangorestframework, etc.

- [ ] **Step 5: Commit**

```powershell
cd C:\Users\Asus\Music\WorkSpace
git add projects/omr.doxaed.com/backend/manage.py projects/omr.doxaed.com/backend/config projects/omr.doxaed.com/backend/common projects/omr.doxaed.com/backend/accounts projects/omr.doxaed.com/backend/organizations projects/omr.doxaed.com/backend/billing projects/omr.doxaed.com/backend/assessments projects/omr.doxaed.com/backend/rosters projects/omr.doxaed.com/backend/omr projects/omr.doxaed.com/backend/results projects/omr.doxaed.com/backend/analytics projects/omr.doxaed.com/backend/requirements.txt
git commit -m "feat(omrflow): scaffold Django backend with 9 apps"
```

---

## Task 2: Env-driven settings (DB, DRF, JWT, CORS, media)

**Files:**
- Modify: `backend/config/settings.py` (replace generated content)
- Create: `backend/.env`, `backend/.env.example`

- [ ] **Step 1: Create `backend/.env` (gitignored) and `backend/.env.example`**

`backend/.env`:

```dotenv
DJANGO_SECRET_KEY=dev-insecure-change-me-please-0123456789abcdef
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://postgres:postgress@localhost:5432/omrflow
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

`backend/.env.example` (committed — placeholders only):

```dotenv
DJANGO_SECRET_KEY=replace-with-a-50-char-random-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://postgres:YOUR_DB_PASSWORD@localhost:5432/omrflow
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

- [ ] **Step 2: Replace `backend/config/settings.py`**

Replace the file's entire contents with:

```python
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "corsheaders",
    # local
    "common",
    "accounts",
    "organizations",
    "billing",
    "assessments",
    "rosters",
    "omr",
    "results",
    "analytics",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}

AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("common.permissions.IsInScope",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {"anon": "30/min", "user": "120/min"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"])

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

> NOTE: This references `common.permissions.IsInScope`, created in Task 6. Until then the
> server will error on API calls — that is expected; Task 4's health view uses `AllowAny` and
> Task 6 creates the permission. To run the server before Task 6, the health endpoint and JWT
> endpoints (added in Task 4) do not depend on the default permission. If `manage.py check`
> fails importing `IsInScope` before Task 6, temporarily set
> `"DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",)` and switch it
> to `IsInScope` in Task 6. (Plan executes Task 6 before any protected endpoint exists, so the
> default is exercised correctly by the end.)

- [ ] **Step 3: Sanity check settings load**

```powershell
cd C:\Users\Asus\Music\WorkSpace\projects\omr.doxaed.com\backend
.\.venv\Scripts\Activate.ps1
python -c "import environ; print('environ ok')"
```

Expected: `environ ok`. (Full `manage.py check` is run after the User model exists in Task 3.)

- [ ] **Step 4: Commit**

```powershell
cd C:\Users\Asus\Music\WorkSpace
git add projects/omr.doxaed.com/backend/config/settings.py projects/omr.doxaed.com/backend/.env.example
git commit -m "feat(omrflow): env-driven settings (local Postgres, DRF, JWT, CORS)"
```

---

## Task 3: Custom email User model (TDD) + first migration

**Files:**
- Modify: `backend/accounts/models.py`, `backend/accounts/admin.py`
- Create/Modify: `backend/accounts/tests.py`

- [ ] **Step 1: Write the failing tests**

Replace `backend/accounts/tests.py`:

```python
from django.contrib.auth import get_user_model
from django.test import TestCase


class UserModelTests(TestCase):
    def test_create_user_with_email(self):
        User = get_user_model()
        user = User.objects.create_user(email="teacher@example.com", password="Str0ng!pass")
        self.assertEqual(user.email, "teacher@example.com")
        self.assertTrue(user.check_password("Str0ng!pass"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_email_verified)

    def test_email_is_required(self):
        User = get_user_model()
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="x")

    def test_create_superuser(self):
        User = get_user_model()
        admin = User.objects.create_superuser(email="admin@example.com", password="Str0ng!pass")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
```

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
python manage.py test accounts -v 2
```

Expected: FAIL/ERROR (the default `User` has no `is_email_verified`, and `create_user` requires a username) — confirms the custom model isn't there yet.

- [ ] **Step 3: Implement the custom User + manager**

Replace `backend/accounts/models.py`:

```python
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField("email address", unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    is_email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
```

Replace `backend/accounts/admin.py`:

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "full_name", "is_email_verified", "is_staff")
    search_fields = ("email", "full_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("full_name", "is_email_verified")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
```

- [ ] **Step 4: Make migrations and migrate (proves local Postgres connection)**

```powershell
python manage.py makemigrations accounts organizations billing assessments rosters omr results analytics common
python manage.py migrate
```

Expected: migrations created for `accounts` (and empty ones for the rest), then `Applying ... OK` lines. A successful `migrate` proves the connection to the local `omrflow` database with password `postgress`. (If you see an auth/connection error, fix `DATABASE_URL` in `.env` before continuing.)

- [ ] **Step 5: Run the tests to verify they pass**

```powershell
python manage.py test accounts -v 2
```

Expected: `OK` (3 tests pass).

- [ ] **Step 6: Create a superuser (for /admin smoke later)**

```powershell
$env:DJANGO_SUPERUSER_PASSWORD = "Admin!2345"
python manage.py createsuperuser --email admin@omrflow.local --noinput
$env:DJANGO_SUPERUSER_PASSWORD = $null
```

Expected: `Superuser created successfully.`

- [ ] **Step 7: Commit**

```powershell
cd C:\Users\Asus\Music\WorkSpace
git add projects/omr.doxaed.com/backend/accounts projects/omr.doxaed.com/backend/*/migrations
git commit -m "feat(omrflow): custom email User model + initial migrations"
```

---

## Task 4: Health endpoint (TDD) + JWT endpoints + server smoke

**Files:**
- Create: `backend/common/views.py`
- Modify: `backend/config/urls.py`
- Modify: `backend/common/tests.py`

- [ ] **Step 1: Write the failing health test**

Create `backend/common/tests.py`:

```python
from django.test import TestCase


class HealthEndpointTests(TestCase):
    def test_health_returns_ok(self):
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["db"], "ok")
```

- [ ] **Step 2: Run it to verify it fails**

```powershell
python manage.py test common.tests.HealthEndpointTests -v 2
```

Expected: FAIL (404 — the URL doesn't exist yet).

- [ ] **Step 3: Implement the health view**

Create `backend/common/views.py`:

```python
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    db_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        db_ok = False
    return Response({"status": "ok", "db": "ok" if db_ok else "error"})
```

- [ ] **Step 4: Wire URLs (health + JWT + admin)**

Replace `backend/config/urls.py`:

```python
from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from common.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health", health),
    path("api/v1/auth/token", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
]
```

- [ ] **Step 5: Run the health test to verify it passes**

```powershell
python manage.py test common.tests.HealthEndpointTests -v 2
```

Expected: `OK`.

- [ ] **Step 6: Smoke-test the running server**

```powershell
python manage.py runserver
```

In a second terminal:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
```

Expected: `status ok`, `db ok`. Also open `http://localhost:8000/admin/` in a browser and log in with `admin@omrflow.local` / `Admin!2345`. Stop the server with Ctrl+C.

- [ ] **Step 7: Commit**

```powershell
cd C:\Users\Asus\Music\WorkSpace
git add projects/omr.doxaed.com/backend/common/views.py projects/omr.doxaed.com/backend/common/tests.py projects/omr.doxaed.com/backend/config/urls.py
git commit -m "feat(omrflow): /api/v1/health endpoint + JWT token routes"
```

---

## Task 5: De-risk native CV libraries (import smoke test)

**Files:**
- Modify: `backend/common/tests.py` (append)

- [ ] **Step 1: Add the import smoke test**

Append to `backend/common/tests.py`:

```python
class NativeLibImportTests(TestCase):
    """Phase 0 de-risk: confirm the OMR/CV native wheels import on Win + Py3.13.

    These libs are not USED until Phases 3-4, but a failed import then would block the
    riskiest phase. Importing here surfaces any native-DLL problem now.
    """

    def test_cv_and_pdf_libs_import(self):
        import cv2  # noqa: F401  (OpenCV)
        import numpy  # noqa: F401
        import pyzbar.pyzbar  # noqa: F401  (QR decode; bundles zbar DLL on Windows)
        import fitz  # noqa: F401  (PyMuPDF; multi-page PDF split)
        import reportlab  # noqa: F401  (OMR PDF generation)
        from PIL import Image  # noqa: F401
        import qrcode  # noqa: F401  (QR encode)
```

- [ ] **Step 2: Run it and record the result**

```powershell
python manage.py test common.tests.NativeLibImportTests -v 2
```

Expected: `OK`. If any import errors (most likely `pyzbar` → "Unable to find zbar shared library"), STOP and report: this is the documented native-lib risk. Mitigation to note for the user: install the zbar DLL, or fall back to a Python 3.12 venv. Do not proceed to Phase 4 work until this passes — but Phase 0 can continue (it does not use these libs).

- [ ] **Step 3: Commit**

```powershell
cd C:\Users\Asus\Music\WorkSpace
git add projects/omr.doxaed.com/backend/common/tests.py
git commit -m "test(omrflow): de-risk OMR/CV native lib imports (Win + Py3.13)"
```

---

## Task 6: Owner-scope foundation — Organization, base model, manager, permission (TDD)

**Files:**
- Modify: `backend/organizations/models.py`
- Create: `backend/common/managers.py`, `backend/common/permissions.py`
- Modify: `backend/common/models.py`, `backend/common/tests.py`

- [ ] **Step 1: Write the failing foundation tests**

Append to `backend/common/tests.py`:

```python
from django.core.exceptions import ValidationError
from django.test.utils import isolate_apps

from common.models import OwnerScopedModel
from common.permissions import IsInScope


@isolate_apps("common")
class OwnerScopeCleanTests(TestCase):
    def _probe_cls(self):
        class Probe(OwnerScopedModel):
            class Meta:
                app_label = "common"

        return Probe

    def test_clean_rejects_no_scope(self):
        Probe = self._probe_cls()
        with self.assertRaises(ValidationError):
            Probe().clean()

    def test_clean_rejects_both_scopes(self):
        Probe = self._probe_cls()
        with self.assertRaises(ValidationError):
            Probe(user_id=1, organization_id=1).clean()

    def test_clean_accepts_user_only(self):
        Probe = self._probe_cls()
        Probe(user_id=1).clean()  # must not raise

    def test_clean_accepts_org_only(self):
        Probe = self._probe_cls()
        Probe(organization_id=1).clean()  # must not raise


class IsInScopePermissionTests(TestCase):
    def _request(self, user_id):
        return type("Req", (), {"user": type("U", (), {"id": user_id})()})()

    def _obj(self, user_id=None, org_id=None):
        return type("Obj", (), {"user_id": user_id, "organization_id": org_id})()

    def test_solo_owner_allowed(self):
        perm = IsInScope()
        self.assertTrue(perm.has_object_permission(self._request(5), None, self._obj(user_id=5)))

    def test_other_user_denied(self):
        perm = IsInScope()
        self.assertFalse(perm.has_object_permission(self._request(5), None, self._obj(user_id=9)))
```

- [ ] **Step 2: Run them to verify they fail**

```powershell
python manage.py test common.tests.OwnerScopeCleanTests common.tests.IsInScopePermissionTests -v 2
```

Expected: ImportError/FAIL (`common.models.OwnerScopedModel` and `common.permissions.IsInScope` don't exist yet).

- [ ] **Step 3: Implement the minimal Organization skeleton**

Replace `backend/organizations/models.py`:

```python
from django.conf import settings
from django.db import models


class Organization(models.Model):
    """Phase 0 skeleton. Membership, invitations, roles, audit log arrive in Phase 6.
    Exists now because the owner-scope foundation references this table."""

    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_organizations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
```

- [ ] **Step 4: Implement the scoped manager**

Create `backend/common/managers.py`:

```python
from django.db import models


class ScopedQuerySet(models.QuerySet):
    """Filters tenant-owned rows to a single owner scope (solo user XOR organization)."""

    def in_scope(self, *, user=None, organization=None):
        if organization is not None:
            return self.filter(organization=organization)
        if user is not None:
            return self.filter(user=user)
        return self.none()


class ScopedManager(models.Manager.from_queryset(ScopedQuerySet)):
    pass
```

- [ ] **Step 5: Implement the abstract owner-scope base model**

Replace `backend/common/models.py`:

```python
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from common.managers import ScopedManager


class OwnerScopedModel(models.Model):
    """Abstract base: every tenant-owned row is owned by exactly one of `user` (solo) or
    `organization`. Enforced in the DB via a CheckConstraint and in Python via clean()."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ScopedManager()

    class Meta:
        abstract = True
        constraints = [
            # Django 5.1+: use `condition=`. On Django 5.0 rename to `check=`.
            models.CheckConstraint(
                condition=(
                    (Q(user__isnull=False) & Q(organization__isnull=True))
                    | (Q(user__isnull=True) & Q(organization__isnull=False))
                ),
                name="%(app_label)s_%(class)s_exactly_one_scope",
            )
        ]

    def clean(self):
        if bool(self.user_id) == bool(self.organization_id):
            raise ValidationError("Exactly one of user or organization must be set.")
```

- [ ] **Step 6: Implement the global scope permission**

Create `backend/common/permissions.py`:

```python
from rest_framework.permissions import IsAuthenticated


class IsInScope(IsAuthenticated):
    """Global default permission. Requires authentication everywhere, and at the object level
    confirms the row belongs to the requester's solo scope.

    Phase 0 implements the solo (user) path. Organization-scoped object access depends on
    membership, which is modeled in Phase 6; until then org-scoped objects are denied here and
    list endpoints must scope their querysets via ScopedQuerySet.in_scope().
    """

    def has_object_permission(self, request, view, obj):
        user_id = getattr(obj, "user_id", None)
        if user_id is not None:
            return request.user.is_authenticated and user_id == request.user.id
        return False
```

- [ ] **Step 7: Set the default permission to IsInScope (if not already)**

Ensure `backend/config/settings.py` `REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]` is exactly:

```python
    "DEFAULT_PERMISSION_CLASSES": ("common.permissions.IsInScope",),
```

(If Task 2's note had you temporarily set it to `IsAuthenticated`, switch it to `IsInScope` now.)

- [ ] **Step 8: Migrate the Organization table**

```powershell
python manage.py makemigrations organizations
python manage.py migrate
```

Expected: a migration for `organizations.Organization`, applied OK.

- [ ] **Step 9: Run the foundation tests to verify they pass**

```powershell
python manage.py test common -v 2
```

Expected: `OK` (health + native-lib + scope-clean + permission tests all pass).

- [ ] **Step 10: Run the full backend suite + system check**

```powershell
python manage.py check
python manage.py test
```

Expected: `System check identified no issues`, then `OK`.

- [ ] **Step 11: Commit**

```powershell
cd C:\Users\Asus\Music\WorkSpace
git add projects/omr.doxaed.com/backend/organizations projects/omr.doxaed.com/backend/common projects/omr.doxaed.com/backend/config/settings.py
git commit -m "feat(omrflow): global owner-scope foundation (base model, manager, permission)"
```

---

## Task 7: Frontend scaffold (Vite React JS + Tailwind v4)

**Files:**
- Create: `frontend/` (Vite output), `frontend/vite.config.js`, `frontend/jsconfig.json`, `frontend/src/index.css`, `frontend/.env`, `frontend/.env.example`

- [ ] **Step 1: Scaffold Vite React (JavaScript) and install**

```powershell
cd C:\Users\Asus\Music\WorkSpace\projects\omr.doxaed.com
npm create vite@latest frontend -- --template react
cd frontend
npm install
```

Expected: `frontend/` with `package.json`, `src/main.jsx`, `src/App.jsx`. (Template `react` is JavaScript/JSX, not TS.)

- [ ] **Step 2: Install Tailwind v4 + the Vite plugin + app deps**

```powershell
npm install tailwindcss @tailwindcss/vite
npm install react-router-dom axios recharts
```

Expected: installs succeed; `package.json` lists `tailwindcss`, `@tailwindcss/vite`, `react-router-dom`, `axios`, `recharts`.

- [ ] **Step 3: Configure `vite.config.js` (Tailwind plugin + `@` alias + port)**

Replace `frontend/vite.config.js`:

```javascript
import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: { port: 5173 },
})
```

- [ ] **Step 4: Create `frontend/jsconfig.json` (path alias for shadcn/editor)**

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

- [ ] **Step 5: Set up Tailwind CSS entry + DESIGN_SYSTEM theme tokens**

Replace `frontend/src/index.css`:

```css
@import "tailwindcss";

/* OMRFlow design tokens (DESIGN_SYSTEM.md). shadcn init (Task 8) appends its own
   :root / @theme color variables below this block — keep both. */
@theme {
  --text-xs: 12px;
  --text-sm: 14px;
  --text-base: 16px;
  --text-lg: 20px;
  --text-xl: 24px;
  --text-2xl: 32px;

  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;

  --color-success: #16a34a;
  --color-warning: #d97706;
  --color-error: #dc2626;
  --color-info: #2563eb;
}
```

Remove the default `App.css` import if present in `App.jsx` (we use Tailwind). Ensure `src/main.jsx` imports `./index.css`.

- [ ] **Step 6: Create `frontend/.env` and `.env.example`**

`frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

`frontend/.env.example`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

- [ ] **Step 7: Smoke-test the dev server + build**

```powershell
npm run dev
```

Open `http://localhost:5173` — the Vite page renders. Stop (Ctrl+C). Then:

```powershell
npm run build
```

Expected: `dist/` produced with no errors.

- [ ] **Step 8: Commit**

```powershell
cd C:\Users\Asus\Music\WorkSpace
git add projects/omr.doxaed.com/frontend
git reset -- projects/omr.doxaed.com/frontend/node_modules
git commit -m "feat(omrflow): scaffold React (Vite, JS) + Tailwind v4 frontend"
```

(`node_modules` is gitignored; the `reset` is a safety no-op if the ignore already excludes it.)

---

## Task 8: shadcn/ui init + full component library

**Files:**
- Create: `frontend/components.json`, `frontend/src/lib/utils.js`, `frontend/src/components/ui/*` (generated)

- [ ] **Step 1: Initialize shadcn/ui (JavaScript mode)**

```powershell
cd C:\Users\Asus\Music\WorkSpace\projects\omr.doxaed.com\frontend
npx shadcn@latest init
```

When prompted, choose: base color **Neutral** (accept other defaults). Because the project has no `tsconfig.json` but has `jsconfig.json`, shadcn configures **JavaScript** mode and writes `.jsx` components. Expected: `components.json` and `src/lib/utils.js` (the `cn` helper) are created, and `src/index.css` gains shadcn's color variables.

- [ ] **Step 2: Add the full component set**

```powershell
npx shadcn@latest add button input label textarea select dialog alert-dialog dropdown-menu tabs table checkbox radio-group switch sonner progress accordion form
```

Expected: files appear under `src/components/ui/` (e.g. `button.jsx`, `select.jsx`, `dialog.jsx`, `alert-dialog.jsx`, `dropdown-menu.jsx`, `sonner.jsx`, etc.). `form` pulls in `react-hook-form` + `zod`; let it install.

Mapping to the design system's required custom components:
- Select/Dropdown → `select`; Multi-select → compose `select` + chips later.
- Modal/Dialog → `dialog`; Confirm dialog → `alert-dialog`.
- Toast/Snackbar → `sonner`. Menu/Context menu → `dropdown-menu`.
- Tabs → `tabs`; Accordion → `accordion`; Data table → `table` (sortable/paginated wrapper added when a screen needs it).
- Form fields → `input`, `label`, `textarea`, `checkbox`, `radio-group`, `switch`, `form`.
- Progress → `progress`. (Stepper, EmptyState, Chart wrapper are hand-built in Task 10.)

- [ ] **Step 3: Verify the build still compiles**

```powershell
npm run build
```

Expected: build succeeds with the new components present.

- [ ] **Step 4: Commit**

```powershell
cd C:\Users\Asus\Music\WorkSpace
git add projects/omr.doxaed.com/frontend/components.json projects/omr.doxaed.com/frontend/src projects/omr.doxaed.com/frontend/package.json projects/omr.doxaed.com/frontend/package-lock.json
git commit -m "feat(omrflow): shadcn/ui library (full primitive set, JS mode)"
```

---

## Task 9: API client + router + Health page (proves the CORS+JWT seam)

**Files:**
- Create: `frontend/src/api/client.js`, `frontend/src/routes/Health.jsx`
- Modify: `frontend/src/App.jsx`, `frontend/src/main.jsx`

- [ ] **Step 1: Create the axios API client (JWT interceptors)**

Create `frontend/src/api/client.js`:

```javascript
import axios from "axios"

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"

export const api = axios.create({ baseURL })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access")
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshPromise = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem("refresh")
      if (!refresh) return Promise.reject(error)
      try {
        refreshPromise =
          refreshPromise || axios.post(`${baseURL}/auth/token/refresh`, { refresh })
        const { data } = await refreshPromise
        refreshPromise = null
        localStorage.setItem("access", data.access)
        original.headers.Authorization = `Bearer ${data.access}`
        return api(original)
      } catch (e) {
        refreshPromise = null
        return Promise.reject(e)
      }
    }
    return Promise.reject(error)
  },
)
```

- [ ] **Step 2: Create the Health page (calls the API across CORS)**

Create `frontend/src/routes/Health.jsx`:

```jsx
import { useEffect, useState } from "react"
import { api } from "@/api/client"

export default function Health() {
  const [status, setStatus] = useState("loading…")
  const [error, setError] = useState(null)

  useEffect(() => {
    api
      .get("/health")
      .then((res) => setStatus(JSON.stringify(res.data)))
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div className="p-8 space-y-2">
      <h1 className="text-2xl font-semibold">API Health</h1>
      {error ? (
        <p className="text-[color:var(--color-error)]">Error: {error}</p>
      ) : (
        <p className="text-base">Backend says: {status}</p>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Set up routing in `App.jsx` and `main.jsx`**

Replace `frontend/src/App.jsx`:

```jsx
import { Link, Route, Routes } from "react-router-dom"
import Health from "@/routes/Health"
import StyleGuide from "@/routes/StyleGuide"

export default function App() {
  return (
    <div>
      <nav className="flex gap-4 p-4 border-b">
        <Link to="/health">Health</Link>
        <Link to="/style-guide">Style Guide</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Health />} />
        <Route path="/health" element={<Health />} />
        <Route path="/style-guide" element={<StyleGuide />} />
      </Routes>
    </div>
  )
}
```

Replace `frontend/src/main.jsx`:

```jsx
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"
import App from "./App.jsx"
import "./index.css"

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
```

> NOTE: `App.jsx` imports `StyleGuide`, created in Task 10. To smoke-test Task 9 alone first,
> temporarily comment out the StyleGuide import and its `<Route>`; restore them in Task 10.

- [ ] **Step 4: Smoke-test the full seam (backend + frontend running)**

Terminal A (backend): `cd backend; .\.venv\Scripts\Activate.ps1; python manage.py runserver`
Terminal B (frontend): `cd frontend; npm run dev`
Open `http://localhost:5173/health`.

Expected: the page shows `Backend says: {"status":"ok","db":"ok"}` — proving CORS + the axios client + the running API all work end-to-end. Stop both servers.

- [ ] **Step 5: Commit**

```powershell
cd C:\Users\Asus\Music\WorkSpace
git add projects/omr.doxaed.com/frontend/src
git commit -m "feat(omrflow): axios JWT client + router + Health page (CORS seam proven)"
```

---

## Task 10: Hand-built primitives + Style Guide route

**Files:**
- Create: `frontend/src/components/ui/stepper.jsx`, `empty-state.jsx`, `chart.jsx`
- Create: `frontend/src/routes/StyleGuide.jsx`

- [ ] **Step 1: Create the Stepper component**

Create `frontend/src/components/ui/stepper.jsx`:

```jsx
import { cn } from "@/lib/utils"

export function Stepper({ steps, current = 0, className }) {
  return (
    <ol className={cn("flex items-center gap-4", className)}>
      {steps.map((label, i) => {
        const state = i < current ? "done" : i === current ? "active" : "todo"
        return (
          <li key={label} className="flex items-center gap-2">
            <span
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium",
                state === "done" && "bg-primary text-primary-foreground",
                state === "active" && "border-2 border-primary text-primary",
                state === "todo" && "border border-muted-foreground/40 text-muted-foreground",
              )}
            >
              {i + 1}
            </span>
            <span className={cn("text-sm", state === "todo" && "text-muted-foreground")}>
              {label}
            </span>
          </li>
        )
      })}
    </ol>
  )
}
```

- [ ] **Step 2: Create the EmptyState component**

Create `frontend/src/components/ui/empty-state.jsx`:

```jsx
import { cn } from "@/lib/utils"

export function EmptyState({ title, description, action, className }) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-2 p-10 text-center", className)}>
      <h3 className="text-lg font-semibold">{title}</h3>
      {description && <p className="text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
```

- [ ] **Step 3: Create the Recharts Chart wrapper**

Create `frontend/src/components/ui/chart.jsx`:

```jsx
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

export function SimpleBarChart({ data, xKey = "name", barKey = "value", height = 240 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey={xKey} />
        <YAxis />
        <Tooltip />
        <Bar dataKey={barKey} fill="var(--color-info)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
```

- [ ] **Step 4: Create the Style Guide route rendering every primitive**

Create `frontend/src/routes/StyleGuide.jsx`:

```jsx
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { Switch } from "@/components/ui/switch"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Progress } from "@/components/ui/progress"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { Stepper } from "@/components/ui/stepper"
import { EmptyState } from "@/components/ui/empty-state"
import { SimpleBarChart } from "@/components/ui/chart"

function Section({ title, children }) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">{title}</h2>
      <div className="flex flex-wrap items-center gap-4">{children}</div>
    </section>
  )
}

export default function StyleGuide() {
  const [progress] = useState(60)
  const chartData = [
    { name: "0-20", value: 2 },
    { name: "21-40", value: 5 },
    { name: "41-60", value: 9 },
    { name: "61-80", value: 7 },
    { name: "81-100", value: 4 },
  ]

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-8">
      <h1 className="text-2xl font-bold">OMRFlow Style Guide</h1>
      <Toaster />

      <Section title="Buttons">
        <Button>Create test</Button>
        <Button variant="secondary">Generate sheets</Button>
        <Button variant="destructive">Delete</Button>
        <Button variant="outline">Scan</Button>
      </Section>

      <Section title="Form fields">
        <div className="grid w-full max-w-sm gap-2">
          <Label htmlFor="t">Title</Label>
          <Input id="t" placeholder="Test 1" />
          <Textarea placeholder="Description" />
        </div>
        <Checkbox /> <Switch />
        <RadioGroup defaultValue="a" className="flex gap-3">
          <RadioGroupItem value="a" id="a" />
          <RadioGroupItem value="b" id="b" />
        </RadioGroup>
      </Section>

      <Section title="Select (custom, not native)">
        <Select>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Subject" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="math">Math</SelectItem>
            <SelectItem value="sci">Science</SelectItem>
          </SelectContent>
        </Select>
      </Section>

      <Section title="Modal / Confirm / Menu / Toast">
        <Dialog>
          <DialogTrigger asChild>
            <Button>Open modal</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Custom modal</DialogTitle>
            </DialogHeader>
            <p className="text-sm">No native dialogs anywhere.</p>
          </DialogContent>
        </Dialog>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="destructive">Confirm delete</Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete this test?</AlertDialogTitle>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction>Delete</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline">Actions</Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>Edit</DropdownMenuItem>
            <DropdownMenuItem>Duplicate</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Button onClick={() => toast.success("Saved")}>Show toast</Button>
      </Section>

      <Section title="Tabs / Accordion">
        <Tabs defaultValue="one" className="w-full">
          <TabsList>
            <TabsTrigger value="one">Overview</TabsTrigger>
            <TabsTrigger value="two">Settings</TabsTrigger>
          </TabsList>
          <TabsContent value="one">Overview content</TabsContent>
          <TabsContent value="two">Settings content</TabsContent>
        </Tabs>
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="a1">
            <AccordionTrigger>Analytics</AccordionTrigger>
            <AccordionContent>Improvement across retests.</AccordionContent>
          </AccordionItem>
        </Accordion>
      </Section>

      <Section title="Table / Progress / Stepper">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Student</TableHead>
              <TableHead>Score</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Asha</TableCell>
              <TableCell>18/20</TableCell>
            </TableRow>
          </TableBody>
        </Table>
        <div className="w-64">
          <Progress value={progress} />
        </div>
        <Stepper steps={["Details", "Questions", "Generate"]} current={1} />
      </Section>

      <Section title="Empty state / Chart">
        <EmptyState
          title="No tests yet"
          description="Create your first MCQ test to get started."
          action={<Button>Create test</Button>}
        />
        <div className="w-full max-w-md">
          <SimpleBarChart data={chartData} />
        </div>
      </Section>
    </div>
  )
}
```

- [ ] **Step 5: Restore the StyleGuide route (if commented in Task 9) and build**

Ensure the `StyleGuide` import and `<Route path="/style-guide" ...>` in `App.jsx` are active. Then:

```powershell
cd C:\Users\Asus\Music\WorkSpace\projects\omr.doxaed.com\frontend
npm run build
```

Expected: build succeeds. Then `npm run dev` and open `http://localhost:5173/style-guide` — every component renders; the modal/confirm/menu/toast/select are all custom (no native popups). Stop the server.

- [ ] **Step 6: Commit**

```powershell
cd C:\Users\Asus\Music\WorkSpace
git add projects/omr.doxaed.com/frontend/src
git commit -m "feat(omrflow): hand-built Stepper/EmptyState/Chart + /style-guide"
```

---

## Task 11: CI workflow + final verification

**Files:**
- Create: `.github/workflows/omrflow-ci.yml` (repo root)

- [ ] **Step 1: Create the CI workflow**

Create `.github/workflows/omrflow-ci.yml` (at repo root `C:\Users\Asus\Music\WorkSpace\.github\workflows\`):

```yaml
name: omrflow-ci

on:
  push:
    paths: ["projects/omr.doxaed.com/**"]
  pull_request:
    paths: ["projects/omr.doxaed.com/**"]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgress
          POSTGRES_DB: omrflow
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 10s
          --health-timeout 5s --health-retries 5
    defaults:
      run:
        working-directory: projects/omr.doxaed.com/backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install -r requirements.txt
      - env:
          DJANGO_SECRET_KEY: ci-secret
          DEBUG: "True"
          ALLOWED_HOSTS: localhost,127.0.0.1
          DATABASE_URL: postgres://postgres:postgress@localhost:5432/omrflow
          CORS_ALLOWED_ORIGINS: http://localhost:5173
        run: python manage.py test

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: projects/omr.doxaed.com/frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
      - run: npm ci
      - run: npm run build
```

> NOTE: CI uses a Postgres service container — that is GitHub-side infrastructure, not local
> Docker, so it does not violate the no-Docker constraint for local dev. This workflow only runs
> if the repo is pushed to GitHub; locally it is inert.

- [ ] **Step 2: Run the full backend suite locally one more time**

```powershell
cd C:\Users\Asus\Music\WorkSpace\projects\omr.doxaed.com\backend
.\.venv\Scripts\Activate.ps1
python manage.py test
```

Expected: `OK`.

- [ ] **Step 3: Run the frontend build locally one more time**

```powershell
cd C:\Users\Asus\Music\WorkSpace\projects\omr.doxaed.com\frontend
npm run build
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```powershell
cd C:\Users\Asus\Music\WorkSpace
git add .github/workflows/omrflow-ci.yml
git commit -m "ci(omrflow): backend tests + frontend build workflow"
```

---

## Task 12: Phase 0 Definition-of-Done verification + memory update

**Files:**
- Modify: `projects/omr.doxaed.com/memory/current-state.md`, `memory/progress-log.md`, `memory/MEMORY.md`

- [ ] **Step 1: Walk the Definition of Done and confirm each item**

Verify and check off (from the design spec §11):
- `omrflow` DB created; `python manage.py migrate` succeeds; `/admin/` + `GET /api/v1/health` load.
- SPA `http://localhost:5173/health` shows `{"status":"ok","db":"ok"}` (CORS+client seam).
- `python manage.py test common.tests.NativeLibImportTests` passes (CV libs import) — or the failure is recorded for the user.
- `python manage.py test` is green (User, health, owner-scope, permission tests).
- Custom `User` + minimal `Organization` + JWT token/refresh endpoints exist.
- `/style-guide` renders the full shadcn library; no native dropdown/alert used.
- CI workflow present; backend tests pass; frontend builds.
- Workspace scaffold + `PROJECTS.md` row present.

- [ ] **Step 2: Update memory files**

Append to `projects/omr.doxaed.com/memory/progress-log.md`:

```markdown
- 2026-06-17 — Phase 0 complete: Django+DRF backend (9 apps, custom User, owner-scope
  foundation, JWT, /api/v1/health) on local Postgres `omrflow`; React (Vite, JS) + Tailwind v4
  + full shadcn/ui library + /style-guide; CORS+JWT seam proven; CV libs import-verified; CI added.
```

Replace `projects/omr.doxaed.com/memory/current-state.md`:

```markdown
# Current State

- 2026-06-17: **Phase 0 (Foundations) complete.** Backend and frontend skeletons run against
  local Postgres `omrflow` (no Docker). Owner-scope foundation, custom User, minimal
  Organization, JWT endpoints, health endpoint, full shadcn UI library + style guide, and CI
  are in place; full test suite green. Native CV libs import-verified on Win+Py3.13.
- **Next:** Phase 1 (Accounts) per `prompts/BUILD_ROADMAP.md` — signup, email verification,
  login/logout, password reset, profile; Argon2 + throttle/lockout already configured.
```

Update the **Status** line in `projects/omr.doxaed.com/memory/MEMORY.md` to:

```markdown
**Status:** Phase 0 (Foundations) — DONE (2026-06-17). Next: Phase 1 (Accounts).
```

- [ ] **Step 3: Update the `PROJECTS.md` status cell**

In `PROJECTS.md`, change the omrflow row's Status from `Phase 0 (Foundations) in progress (2026-06-17)` to `Phase 0 DONE (2026-06-17); → Phase 1 (Accounts)`.

- [ ] **Step 4: Final commit**

```powershell
cd C:\Users\Asus\Music\WorkSpace
git add projects/omr.doxaed.com/memory PROJECTS.md
git commit -m "docs(omrflow): mark Phase 0 complete; update memory + registry"
```

---

## Self-Review

**1. Spec coverage** (against `2026-06-17-omrflow-phase0-design.md`):
- Repo/branch isolation → Task 0 (branch pre-created) + commits throughout. ✓
- Local Postgres, no Docker → Task 0 (DB create), Task 2 (`DATABASE_URL`). ✓
- 9 Django apps → Task 1. ✓
- Env-driven secrets → Task 2 (`.env`/`.env.example`, django-environ). ✓
- Custom User (one-way door) before first migration → Task 3. ✓
- Health endpoint + walking skeleton → Tasks 4 & 9. ✓
- De-risk CV libs → Task 5. ✓
- Owner-scope base + CheckConstraint + ScopedManager + global IsInScope → Task 6. ✓
- minimal Organization → Task 6. ✓
- JWT endpoints → Task 4. ✓
- Frontend Vite JS + Tailwind v4 → Task 7. ✓
- shadcn full library → Task 8; hand-built Stepper/EmptyState/Chart + style guide → Task 10. ✓
- API client (JWT interceptor) → Task 9. ✓
- CI → Task 11. ✓
- Workspace integration (PROJECTS.md, CLAUDE.md, memory) → Tasks 0 & 12. ✓
- Definition of Done → Task 12. ✓

**2. Placeholder scan:** No "TBD"/"add error handling"-style placeholders; every code/test/command step shows actual content. ✓

**3. Type/name consistency:** `OwnerScopedModel`, `ScopedManager`/`ScopedQuerySet.in_scope`, `IsInScope.has_object_permission`, `common.permissions.IsInScope`, `api` axios export, `@/api/client`, component import paths, and the `health` view name are used consistently across tasks and settings. The `CheckConstraint(condition=...)` kwarg is noted for Django 5.1+ with the 5.0 fallback. ✓

**Known sequencing caveat (documented inline):** Task 2 wires `DEFAULT_PERMISSION_CLASSES = IsInScope` which doesn't exist until Task 6; Task 2's note gives the temporary `IsAuthenticated` fallback and Task 6 Step 7 switches it back. No protected endpoint exists before Task 6, so behavior is correct end-to-end.
