# Session state

Last updated: 2026-07-27. Written so this work survives the loss of any single
dev container. Everything needed to rebuild the environment and continue is
either in this repo or described here.

## Where the work stands

### Done and pushed to `main`
1. **Theme port** (`ba7ee29`). The whole front end now runs the design system
   from `bankithung/fet.doxaed.com` so both products read as one family.
   `frontend/src/index.css` is the single source of truth for every token.
   Change a token there, never a hard coded colour.
2. **Rail icons** (`2502bc6`). The exam lifecycle rail had step numbers and no
   icons, so the collapsed 56px rail rendered bare digits and the active step
   drew indigo on indigo.
3. **Local runner** (`7a2c58e`). `scripts/dev.sh`.
4. **Demo seed + audit snapshot** (this commit). `manage.py seed_demo` and
   `docs/audit/raw-findings.json`.

### In flight
A multi agent usability audit drove the running app as four personas (first time
teacher, coaching institute owner, first run and empty states, phone only) plus
four feature deep dives (sheet generation options, QR and physical sheet design,
scan and review, results and analytics).

**8 audits returned 134 raw findings**, snapshotted to
`docs/audit/raw-findings.json`. Counts by area and severity are in that file.
Those severities are the *reporting* agent's own claim and are NOT yet verified.
Expect a large fraction to be duplicates across auditors, severity inflated, or
artifacts of seeded demo data. Treat the raw file as a lead list, not a backlog.

The verification pass (each finding independently reproduced by a second agent
that defaults to "not real") and the synthesis into one ranked plan had not
finished when this was written. If that work was lost with its container, the
raw findings survive and verification can be re-run against them.

## Rebuilding the environment

```bash
git clone https://github.com/bankithung/omr.doxaed.com
cd omr.doxaed.com
./scripts/dev.sh --seed        # postgres + api + web + demo data
```
Front end http://localhost:5173, API http://localhost:8000.
Sign in `demo@doxaed.com` / `DemoPass123!`, org slug `demo-school`.

`dev.sh` writes `backend/.env` on first run with a freshly generated secret and
field encryption key. That file is gitignored and must never be committed.

`seed_demo` refuses to run unless `DEBUG=True` (override with `--force` only on
a throwaway box) because it sets a known password.

### Manual equivalent
```bash
service postgresql start && createdb -U postgres omrflow
cd backend && python3 -m venv .venv
iconv -f UTF-16 -t UTF-8 requirements.txt -o /tmp/req.txt   # the file is UTF-16
.venv/bin/pip install -r /tmp/req.txt
.venv/bin/python manage.py migrate && .venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver 8000 &
cd ../frontend && npm install && npm run dev
```

## Environment gotchas found the hard way
- **zbar is a required system library and pip will not tell you.** `pyzbar` is a
  ctypes wrapper; it installs fine and only fails when `omr.scan.align` is first
  imported. Without it every scan upload fails to find a QR and the entire
  grading path is dead. Install `libzbar0` (apt, may be `libzbar0t64` on newer
  Ubuntu) or `zbar` (brew). `scripts/dev.sh` now does this, and
  `common.tests.NativeLibImportTests` catches it. Symptom if missed: 60+ test
  errors that look unrelated.
- `backend/requirements.txt` is **UTF-16 encoded**. `pip install -r` fails on it
  directly; convert with `iconv` first.
- The system `cryptography` module is broken in some images (`_cffi_backend`
  missing). Generate the Fernet key with `base64.urlsafe_b64encode(os.urandom(32))`
  instead of importing Fernet.
- The API throttles at 30/min anon and 120/min user. Any scripted sweep trips it
  and gets 429s that look like app bugs. Set `THROTTLE_ANON` / `THROTTLE_USER`
  high in `backend/.env` for local automation.
- The app is **org first**. Every workspace route bounces to `/organizations`
  until an org is selected. Automated drivers must set
  `localStorage.setItem('activeOrg', '<org id>')` after login or every route
  redirects and the run looks broken.
- `Test.title` not `name`; `Section.label` + `order_index` not `title`;
  `Question` has no `key` field. Owner scope is user XOR organization, so seeded
  rows must set exactly one.

## UI verification harness
Playwright is not a repo dependency. Install it in a scratch dir and point it at
the preinstalled browser, do not run `playwright install`:

```js
chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' })
```

The sweep used to verify the theme checks, for every route at 1440px and 390px:
horizontal overflow, console errors, and controls under 40px tall. Last full run
was **52/52 clean at both widths**. Re-run it after any layout change.

## Owner rules in force
See `CLAUDE.md`. The ones most often broken by new code: no dashes in user
facing text, no native `<select>`, no gradients, every page body 90% wide capped
at 1600px (do not add inner `max-w-*` to page content), tap targets 40px.

## Known open items
- `docs/audit/raw-findings.json` is unprocessed. 25 findings self report as
  blockers across scan/review, QR and sheet design, org roles, and generation.
  Verify before acting.
- The QR and scanner assessment is **design and code path only**. No agent
  tested a real camera photo of a physically printed sheet. Optical performance
  in a real classroom is unverified and needs one manual print, fill, photo,
  upload cycle.
- Lint reports 69 warnings, 0 errors. Warnings predate this work.
