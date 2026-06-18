# OMRFlow — End-to-End Browser Suite

Drives the **complete product loop** in real browsers, across every available
engine (bundled Chromium, system Chrome, system Edge):

```
register → verify email → login → create class → create test (MCQs)
→ create roster + students → generate OMR sheets → upload synthetic scans
→ auto-grade → results → student drill-down → analytics → export (CSV/Excel/PDF)
```

Each run registers a fresh account (unique email per browser + run) and captures
a screenshot at every step under `screenshots/<browser>/`.

## Why a Django helper?

Two steps a pure-UI test can't perform are bridged by `django_helper.py`, exactly
as a real user would experience them:

- **Email verification** — regenerates the same `uid`/`token` the verification
  email contains (`accounts.tokens.make_uid_token`), so the browser can visit the
  real `/verify-email` link.
- **Scanned sheets** — renders synthetic *filled* scans of the REAL generated
  sheets (`omr.simulate.simulate_scan` + `omr.scan.pipeline.simulate_correct_marks`,
  scale 2.0 so the QR decodes), then the browser uploads them through the actual
  scan UI. Every 3rd sheet drops one answer so scores/analytics aren't degenerate.

The synthetic scans drive the genuine CV/QR/grade pipeline end-to-end; nothing
about grading is mocked.

## Prerequisites

- Backend running: `cd ../backend && .venv/Scripts/python.exe manage.py runserver 8000 --noreload`
- Frontend running: `cd ../frontend && npm run dev`  (Vite on :5173)
- Local Postgres `omrflow` migrated; `python manage.py seed_plans` once.
- Browsers: `npm install` here, then `npx playwright install chromium chromium-headless-shell`
  (Chrome/Edge use the system install via channels).

## Run

```bash
node run.mjs            # all browsers (chromium, chrome, edge)
node run.mjs chromium   # a single browser
```

Exit code 0 = every browser passed all steps. Results summary written to
`last-run.json`; downloaded exports saved under `downloads/`.

## Helper sub-commands (used internally by run.mjs)

```bash
python django_helper.py token <email>            # {uid, token, verify_path}
python django_helper.py latest-ids <email>       # {class_id, test_id, roster_id}
python django_helper.py make-scans <test_id> <out_dir>   # synthetic scan manifest
```

Artifacts (`node_modules/`, `screenshots/`, `scans/`, `downloads/`, `last-run.json`)
are git-ignored.
