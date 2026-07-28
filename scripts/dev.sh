#!/usr/bin/env bash
# One command local dev. Brings up Postgres, the Django API and the Vite front
# end, then leaves both running with live reload.
#
#   ./scripts/dev.sh            start everything
#   ./scripts/dev.sh --seed     start everything and seed a demo account
#
# Front end: http://localhost:5173      API: http://localhost:8000
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

info() { printf '\033[1;34m▸\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!\033[0m %s\n' "$*"; }

# ── 0. Native libraries ──────────────────────────────────────────────────────
# pyzbar is a thin ctypes wrapper: pip installs it happily and it only fails at
# import time, when the scan pipeline first tries to decode a QR. Without zbar
# every upload fails to find a QR code and the whole grading path is dead, so
# check it up front rather than letting a teacher discover it mid exam.
if ! python3 -c "import ctypes.util,sys; sys.exit(0 if ctypes.util.find_library('zbar') else 1)" 2>/dev/null; then
  info "installing the zbar library (needed to decode the QR on each sheet)"
  if command -v brew >/dev/null 2>&1; then
    brew install zbar >/dev/null 2>&1 || true
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -q >/dev/null 2>&1 || true
    sudo apt-get install -y -q --no-install-recommends libzbar0 >/dev/null 2>&1 \
      || sudo apt-get install -y -q --no-install-recommends libzbar0t64 >/dev/null 2>&1 || true
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y zbar >/dev/null 2>&1 || true
  fi
  python3 -c "import ctypes.util,sys; sys.exit(0 if ctypes.util.find_library('zbar') else 1)" 2>/dev/null \
    || warn "zbar is still missing. Scanning will fail until it is installed (apt: libzbar0, brew: zbar)."
fi

# ── 1. Postgres ──────────────────────────────────────────────────────────────
if ! pg_isready -q 2>/dev/null; then
  info "starting postgres"
  if command -v brew >/dev/null 2>&1; then
    brew services start postgresql >/dev/null 2>&1 || true
  elif command -v service >/dev/null 2>&1; then
    sudo service postgresql start >/dev/null 2>&1 || true
  fi
  for _ in $(seq 1 20); do pg_isready -q 2>/dev/null && break; sleep 0.5; done
fi
pg_isready -q 2>/dev/null || { warn "postgres is not reachable on :5432"; exit 1; }

# Connect over TCP with the password the app itself uses, not a local socket as
# the current OS user. A bare `psql -U postgres` hits peer authentication and
# fails even when the database is present and healthy.
PGUSER_=${PGUSER:-postgres}
PGPASS_=${PGPASSWORD:-postgress}
DBNAME_=${PGDATABASE:-omrflow}

db_exists() {
  PGPASSWORD="$PGPASS_" psql -h localhost -U "$PGUSER_" -tAc \
    "SELECT 1 FROM pg_database WHERE datname='${DBNAME_}'" postgres 2>/dev/null | grep -q 1
}

if ! db_exists; then
  info "creating database ${DBNAME_}"
  if ! PGPASSWORD="$PGPASS_" createdb -h localhost -U "$PGUSER_" "$DBNAME_" 2>/dev/null; then
    # First run on a fresh cluster: the postgres role may have no password yet.
    info "setting a local password for the ${PGUSER_} role"
    sudo -u postgres psql -qc "ALTER USER ${PGUSER_} PASSWORD '${PGPASS_}';" >/dev/null 2>&1 || true
    sudo -u postgres createdb "$DBNAME_" >/dev/null 2>&1 || true
  fi
  db_exists || { warn "could not create or reach database ${DBNAME_}"; exit 1; }
fi

# ── 2. Backend ───────────────────────────────────────────────────────────────
cd backend
[ -d .venv ] || { info "creating virtualenv"; python3 -m venv .venv; }
if [ ! -f .env ]; then
  info "writing backend/.env"
  python3 - <<'PY'
import base64, os, secrets, pathlib
pathlib.Path('.env').write_text(f"""DJANGO_SECRET_KEY=django-insecure-{secrets.token_urlsafe(50)}
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://postgres:postgress@localhost:5432/omrflow
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
FRONTEND_URL=http://localhost:5173
FIELD_ENCRYPTION_KEY={base64.urlsafe_b64encode(os.urandom(32)).decode()}
RAZORPAY_KEY_ID=rzp_test_PLACEHOLDER
RAZORPAY_KEY_SECRET=PLACEHOLDER_SECRET
RAZORPAY_WEBHOOK_SECRET=whsec_test
GOOGLE_CLIENT_ID=
CELERY_TASK_ALWAYS_EAGER=True
""")
PY
fi

info "installing backend dependencies"
REQ=$(mktemp)
iconv -f UTF-16 -t UTF-8 requirements.txt -o "$REQ" 2>/dev/null || cp requirements.txt "$REQ"
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r "$REQ"
rm -f "$REQ"

info "running migrations"
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py seed_plans >/dev/null 2>&1 || true

if [ "${1:-}" = "--seed" ]; then
  info "seeding demo data"
  .venv/bin/python manage.py seed_demo
fi

info "starting API on http://localhost:8000"
.venv/bin/python manage.py runserver 8000 &
API_PID=$!
cd "$ROOT"

# ── 3. Frontend ──────────────────────────────────────────────────────────────
cd frontend
[ -d node_modules ] || { info "installing frontend dependencies"; npm install; }
info "starting front end on http://localhost:5173"
npm run dev &
WEB_PID=$!
cd "$ROOT"

cleanup() { info "stopping"; kill "$API_PID" "$WEB_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

printf '\n\033[1;32m  ready\033[0m  →  http://localhost:5173   (api on :8000)\n'
printf '  press ctrl+c to stop\n\n'
wait
