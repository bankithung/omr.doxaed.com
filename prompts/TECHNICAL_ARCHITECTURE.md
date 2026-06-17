# Technical Architecture — OMRFlow

## 1. Stack (recommended)

| Layer | Choice | Why |
|---|---|---|
| Backend | **Python 3.12 + Django 5 + Django REST Framework** | Your chosen stack. DRF makes it API-first so the future mobile app reuses the same backend. |
| Database | **PostgreSQL** | Relational integrity for the class→test→retest→result hierarchy; strong indexing for analytics. |
| Async tasks | **Celery + Redis** | Scanning and batch PDF generation run off the request thread with progress tracking. |
| Image processing | **OpenCV + NumPy**, `pyzbar` (QR), `Pillow` | The OMR scanning engine. Server-side for reliability. |
| PDF generation | **ReportLab** (precise vector layout) or **WeasyPrint** (HTML→PDF) | OMR sheets need pixel-precise bubble positions → ReportLab recommended. |
| Web frontend | **React (SPA) + Tailwind CSS** | Chosen. App-like UI, fully custom components, consumes the DRF API. Charts via **Recharts** (or Chart.js). |
| Auth | Django auth (server) + **JWT** for the API | React app and mobile app both authenticate via JWT (short expiry + refresh). |
| Payments | **Razorpay** | ₹ payments, India-first, subscriptions + webhooks. |
| File/object storage | Local in dev; **S3-compatible** (e.g., S3 / Cloudflare R2) in prod | Stores uploaded scans and generated PDFs. |
| Deployment | Docker; Gunicorn + Nginx (API) + static React build behind CDN; managed Postgres + Redis | Reproducible, scalable. |

**Architecture style:** decoupled. Django + DRF is a pure JSON API (no server-rendered app pages); the React SPA is a separate build that consumes it. This is the same API the mobile app will use, so there's no rework later. Keep all business logic in the backend — the React app is presentation + API calls only.

## 2. High-level architecture

```
   React SPA (web) ─▶│                                              │
   Mobile app      ─▶│  Nginx  ─▶  Gunicorn  ─▶  Django + DRF        │
                     │              (JSON REST API only)             │
                     └───────┬───────────────┬───────────────┬──────┘
                             │               │               │
                       PostgreSQL        Redis broker     Object storage
                             │               │           (scans, PDFs)
                             │         ┌──────┴───────┐
                             └────────▶│ Celery worker │ OMR engine:
                                       │  (OpenCV)     │ generate + scan
                                       └───────────────┘
                                             │
                                       Razorpay (webhooks)
```
The React SPA is served as static files (CDN); it talks to the API over HTTPS. The mobile app hits the same API.

## 3. App/module breakdown (Django apps)

- `accounts` — users, signup/verify/reset, profile.
- `organizations` — orgs, membership, roles, invitations, audit log.
- `billing` — plans, subscriptions, Razorpay integration, plan-limit enforcement.
- `assessments` — classes, tests, retests, questions, options, marking schemes.
- `rosters` — students (test-taker records), roll numbers, saved rosters.
- `omr` — sheet templates, PDF generation, shuffle/versioning, scan pipeline, review queue.
- `results` — graded responses, scores, review items.
- `analytics` — aggregation queries, improvement comparisons, exports.
- `common` — shared utils, custom permissions, pagination, throttling.

## 4. API-first principle

Every feature is exposed through DRF endpoints. The React web app and the mobile app both call the same endpoints — no business logic lives in the frontend. See `DATA_MODEL.md` for entities; endpoints follow REST conventions (`/api/v1/...`).

## 5. Multi-tenancy & data isolation

- Every tenant-owned row carries an **owner scope**: either `user_id` (solo) or `organization_id` (org).
- A custom DRF permission + queryset mixin enforces that **users only ever read/write rows in their own scope**. This is applied globally, not per-view, to prevent leaks.
- Org members see org-scoped data; org admins additionally see all members' activity within that org.

## 6. Async processing (scanning)

1. Client uploads one or many sheet images → stored → a `ScanBatch` + `ScanJob`s created (status `queued`).
2. Celery workers pick up jobs, run the OMR pipeline (see `OMR_ENGINE_SPEC.md`), write results, set status `done` / `needs_review` / `failed`.
3. Client polls (or websocket, phase 2) a progress endpoint; UI shows live progress and the review queue.
4. Idempotent jobs (safe to retry); failures captured with reason.

## 7. Security

- **Transport**: TLS everywhere; HSTS.
- **Auth**: strong password hashing (Argon2), email verification, lockout/throttle on repeated failures, secure session cookies (`HttpOnly`, `Secure`, `SameSite`), JWT for API with short expiry + refresh.
- **AuthZ**: global org-scope enforcement (see §5); role checks for admin-only actions.
- **PII**: student names are PII — encrypt sensitive fields at rest (e.g., `django-cryptography` / pgcrypto), restrict exports to authorized roles.
- **CSRF/XSS**: Django CSRF on web; auto-escaping templates; sanitize any rich input.
- **Rate limiting / throttling**: DRF throttles + `django-ratelimit`; strictly enforce free-tier limits (5 generations/day, 10 students/gen) server-side.
- **File uploads**: validate type/size of scan images; never trust client; process in isolated workers; strip EXIF.
- **Payments**: Razorpay handles card data; verify webhook signatures; never store raw card details.
- **Audit log**: record member actions for admin visibility.
- **Secrets**: env vars / secret manager; never in repo.
- Target **OWASP Top 10** coverage as a checklist before launch.

## 8. Performance

- DB indexes on hot paths (org_id, test_id, student_id, created_at).
- Aggregate analytics via efficient queries / materialized summaries where needed.
- OMR scan: QR-assisted alignment keeps per-sheet processing fast (target sub-second); batches parallelized across workers.
- Cache heavy read-only analytics; paginate all list endpoints.

## 9. Environments & deployment

- **Dev**: Docker Compose (web, worker, postgres, redis, minio).
- **Prod**: containerized; Gunicorn behind Nginx; managed Postgres + Redis; object storage; HTTPS via reverse proxy/Let's Encrypt; healthchecks; backups for DB and stored PDFs/scans.
- CI: lint + tests on every push; migrations checked.

## 10. Testing

- Unit tests for grading logic, plan-limit enforcement, shuffle/versioning correctness, org-scope isolation.
- OMR engine: a fixture set of sample filled sheets (clean, skewed, faint, double-marked) with known answers to validate accuracy and the review-queue triggers.
- Integration tests for billing webhooks and end-to-end test→generate→scan→grade flow.
