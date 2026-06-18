# OMRFlow — Security Checklist (OWASP Top 10 mapping)

> Review this before every production launch. Update the "Done" column as items
> are completed. All "TODO" items must be resolved before handling real student PII.

---

## OWASP Top 10 (2021) — Implementation Status

### A01 — Broken Access Control

| Control | Status | Detail |
|---------|--------|--------|
| Owner-scope isolation | Done | Every row has a `user XOR organization` scope constraint enforced at the DB level (CHECK constraint) and filtered in every queryset via `scope_filter()` in `common/scope.py`. |
| Cross-tenant isolation tests | Done | Every app has tests asserting a second user/org cannot read or modify another tenant's data (returns 403/404). |
| `IsInScope` DRF permission | Done | Global `DEFAULT_PERMISSION_CLASSES = [IsInScope]` — unauthenticated or out-of-scope requests are rejected at the view layer. |
| Admin restricted | Done | Django admin requires staff status; not exposed via the public API. |

### A02 — Cryptographic Failures

| Control | Status | Detail |
|---------|--------|--------|
| Passwords hashed with Argon2 | Done | `PASSWORD_HASHERS` has `Argon2PasswordHasher` first. |
| JWT short-lived (15 min) | Done | `ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)`; refresh tokens rotate and are blacklisted after use. |
| PII encryption at rest | Done | Student names stored via `django-encrypted-model-fields` using a Fernet key (`FIELD_ENCRYPTION_KEY`). The key must stay constant — see deployment guide. |
| TLS in production | Done (config) | Nginx config enforces HTTPS (TLSv1.2+); `SECURE_SSL_REDIRECT=True` in prod env. |
| Secrets in env vars only | Done | No secrets in source code; `.env` is git-ignored; `.env.prod.example` has only placeholders. |
| TODO: rotate FIELD_ENCRYPTION_KEY process | Pre-launch | Document a safe key-rotation runbook before handling live PII. |
| TODO: TLS certificate expiry monitoring | Pre-launch | Set up cert-expiry alerts (e.g. Certbot auto-renew cron + monitoring). |

### A03 — Injection

| Control | Status | Detail |
|---------|--------|--------|
| ORM parameterised queries | Done | All DB access via Django ORM; no raw SQL with user input. |
| DRF input validation | Done | All API inputs go through DRF serializers with field-level validation before hitting the DB. |
| TODO: dependency audit | Pre-launch | Run `pip-audit` and `npm audit`; fix or accept all HIGH/CRITICAL findings. |

### A04 — Insecure Design

| Control | Status | Detail |
|---------|--------|--------|
| No-enumeration registration | Done | Duplicate-email registration returns the same 201 response as a new signup; existing user receives an "account already exists" email instead of a 400 leak. |
| Webhook signature verification | Done | Razorpay webhook validates `X-Razorpay-Signature` with HMAC-SHA256 before processing any payment event. |
| Low-confidence OMR reads → review queue | Done | Sheets with low-confidence scans land in a review queue; they are never silently guessed. |
| TODO: payments security review | Pre-launch | Have a second developer review the Razorpay integration (order creation, webhook processing, idempotency). |

### A05 — Security Misconfiguration

| Control | Status | Detail |
|---------|--------|--------|
| Prod guard on SECRET_KEY/ALLOWED_HOSTS | Done | `settings.py` raises `ImproperlyConfigured` if `DEBUG=False` and the dev-default secret key or empty ALLOWED_HOSTS is detected. |
| `DEBUG=False` in production | Done (env) | `DEBUG` defaults to `False`; set via `DEBUG=True` in dev `.env` only. |
| `X_FRAME_OPTIONS = DENY` | Done | Clickjacking header set globally. |
| `SECURE_CONTENT_TYPE_NOSNIFF` | Done | MIME sniffing protection enabled. |
| `SECURE_REFERRER_POLICY = same-origin` | Done | Referrer limited to same origin. |
| HSTS (1 year) | Done (env) | `SECURE_HSTS_SECONDS=31536000` in prod env; 0 in dev so localhost works. |
| TODO: real domain in ALLOWED_HOSTS | Pre-launch | Set `ALLOWED_HOSTS=yourdomain.com` before going live. |
| TODO: `pip-audit` clean | Pre-launch | No HIGH or CRITICAL CVEs in Python dependencies. |
| TODO: `npm audit` clean | Pre-launch | No HIGH or CRITICAL CVEs in Node dependencies. |

### A06 — Vulnerable and Outdated Components

| Control | Status | Detail |
|---------|--------|--------|
| `requirements.txt` pinned | Done | All Python deps are pinned. |
| `package.json` + lockfile | Done | Node deps pinned via `package-lock.json`. |
| TODO: automated dependency scanning | Pre-launch | Add `pip-audit` + `npm audit` to CI pipeline; review monthly. |

### A07 — Identification and Authentication Failures

| Control | Status | Detail |
|---------|--------|--------|
| JWT authentication | Done | DRF uses `JWTAuthentication` via `rest_framework_simplejwt`. |
| Refresh token rotation + blacklist | Done | `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True`. |
| Login rate limiting | Done | DRF `UserRateThrottle` at `5/min` on the login endpoint. |
| Login lockout (axes) | Done | `django-axes` locks out after `AXES_FAILURE_LIMIT=5` consecutive failures (combined username + IP); 1-hour cooldown. |
| Email verification before login | Done | Users must verify their email before the account is active. |
| Scoped throttle on verify-email | Done | `ScopedRateThrottle` at `10/min` on the verify-email endpoint. |
| Argon2 password hashing | Done | See A02 above. |

### A08 — Software and Data Integrity Failures

| Control | Status | Detail |
|---------|--------|--------|
| Razorpay webhook HMAC verification | Done | See A04 above. |
| DB migrations in version control | Done | All schema changes are committed migration files. |
| TODO: integrity checks on OMR sheet images | Pre-launch | Consider adding a checksum check on uploaded scan images before processing. |

### A09 — Security Logging and Monitoring Failures

| Control | Status | Detail |
|---------|--------|--------|
| Django request logging | Done | Gunicorn access log to stdout; process supervisor captures to journal. |
| Axes lockout logging | Done | `django-axes` logs failed login attempts to the `axes_accessattempt` table. |
| TODO: Sentry / error monitoring | Pre-launch | Integrate Sentry (or equivalent) and set `SENTRY_DSN` env var before launch. |
| TODO: DB backup schedule | Pre-launch | Set up automated PostgreSQL backups (daily snapshots + WAL archiving). |
| TODO: uptime monitoring | Pre-launch | Add an external uptime monitor (e.g. BetterUptime, UptimeRobot) for the `/api/v1/health/` endpoint. |

### A10 — Server-Side Request Forgery (SSRF)

| Control | Status | Detail |
|---------|--------|--------|
| No outbound URL fetching from user input | Done | OMRFlow does not fetch user-supplied URLs server-side. |
| Email sending isolated to SMTP | Done | Outbound network calls go only to the configured SMTP server and Razorpay API. |

---

## Pre-Launch TODO Summary

Priority order for completion before first real-student data:

1. [ ] Replace all placeholder env vars (`RAZORPAY_*`, `DJANGO_SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, `EMAIL_*`, `DATABASE_URL`) with real production values.
2. [ ] Run `pip-audit` — fix or document acceptance for any HIGH/CRITICAL CVEs.
3. [ ] Run `npm audit` — same.
4. [ ] Have a second developer review the Razorpay payment integration end-to-end.
5. [ ] Set up DB backups (daily + point-in-time recovery).
6. [ ] Integrate Sentry or equivalent error monitoring.
7. [ ] Set up uptime monitoring on `/api/v1/health/`.
8. [ ] Add `pip-audit` + `npm audit` to CI so dependency regressions are caught automatically.
9. [ ] Document FIELD_ENCRYPTION_KEY rotation runbook.
10. [ ] Review scan-metering granularity — confirm billing event counts match the plan spec.

---

## Implemented Controls Summary

| Layer | What's in place |
|-------|-----------------|
| Authentication | JWT (15 min) + rotating refresh tokens + email verification |
| Password security | Argon2 hashing |
| Brute-force protection | django-axes lockout (5 failures, 1h cooldown) + DRF throttles |
| Authorisation | Owner-scope XOR constraint + IsInScope global permission |
| PII protection | Fernet encryption on student names at rest |
| Transport | TLS via Nginx (prod) + HSTS + secure cookies + CSRF protection |
| Input validation | DRF serializers + Django ORM (no raw SQL) |
| Payments | HMAC-SHA256 webhook signature verification |
| Secrets | Env vars only; no secrets in code or git history |
| Clickjacking | `X-Frame-Options: DENY` |
| MIME sniffing | `X-Content-Type-Options: nosniff` |
| OMR integrity | Low-confidence reads queued for human review |
