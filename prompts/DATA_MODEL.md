# Data Model — OMRFlow

Conventions: every tenant-owned table has an **owner scope** — exactly one of `user` (solo) or `organization` set — plus `created_at`, `updated_at`. All queries are filtered by scope (see `TECHNICAL_ARCHITECTURE.md §5`).

## Entities & relationships (overview)

```
User ──< OrganizationMembership >── Organization
Organization ──< Invitation
Organization / User (scope) ──< Class ──< Test ──< Question ──< Option
                                   │         │
                                   │         └──< Retest (a Test linked to a parent Test)
                                   │
Roster ──< Student                 Test ──< MarkingScheme (1:1)
Test + Roster ──< OmrSheet (one per student, with shuffle version)
OmrSheet ──< ScanJob ──< StudentResult ──< QuestionResponse
ScanBatch ──< ScanJob
StudentResult ──< ReviewItem (for flagged marks)
Organization ──< Subscription ──< Plan
Organization ──< AuditLog
```

## Tables

### accounts
**User**
- `id`, `email` (unique), `password_hash`, `full_name`, `is_email_verified`, `last_login`
- A user may own solo data and/or belong to orgs.

### organizations
**Organization**
- `id`, `name`, `owner` (User, the creator/admin), `created_at`

**OrganizationMembership**
- `id`, `organization`, `user`, `role` (`admin` | `member`), `status` (`active`|`invited`|`removed`), `joined_at`

**Invitation**
- `id`, `organization`, `email`, `token`, `role`, `expires_at`, `accepted_at`

**AuditLog**
- `id`, `organization`, `actor` (User), `action`, `target_type`, `target_id`, `metadata` (JSON), `created_at`

### billing
**Plan**
- `id`, `code` (`free`|`team`|`business`|`enterprise`), `name`, `price_inr`, `seat_limit`, `students_per_generation_limit` (null = unlimited), `generations_per_day_limit` (null = unlimited), `monthly_scan_limit`

**Subscription**
- `id`, `organization`, `plan`, `status` (`active`|`past_due`|`canceled`), `razorpay_subscription_id`, `current_period_end`, `seats_purchased`

> Free solo users have no Subscription row; their limits come from the `free` Plan constants enforced in code.

### assessments
**Class** (avoid the Python keyword in code → model name e.g. `ClassGroup`)
- `id`, scope (`user`/`organization`), `created_by` (User), `name`, `description`

**Test**
- `id`, scope, `class_group` (FK), `created_by`, `title`, `subject`, `parent_test` (nullable FK → Test, set when this is a **retest**), `attempt_number` (1 for original, 2+ for retests), `status` (`draft`|`ready`|`closed`)

**MarkingScheme** (1:1 with Test)
- `marks_per_correct`, `negative_marks_per_wrong` (default 0), `partial_marking` (bool), `multiple_correct_allowed` (bool)

**Question**
- `id`, `test` (FK), `order_index`, `text`, `image` (nullable), `topic`/`tag` (nullable), `difficulty` (nullable)

**Option**
- `id`, `question` (FK), `label` (A/B/C/D…), `text`, `image` (nullable), `is_correct` (bool)

### rosters
**Roster**
- `id`, scope, `created_by`, `class_group` (FK, nullable), `name`

**Student**
- `id`, `roster` (FK), `full_name` (PII, encrypted), `roll_number` (unique within roster), `external_ref` (nullable)

> A "count only" generation creates lightweight Students numbered 1..N with names attachable later.

### omr
**OmrSheet** — one logical answer sheet, per student per test (may print across several pages)
- `id`, `test` (FK), `student` (FK, nullable until assigned), `sheet_code` (unique, encoded in QR), `shuffle_version` (int/seed), `question_order` (JSON: ordered Question IDs for this sheet), `option_order` (JSON, optional), `answer_key` (JSON: for this sheet's order, the correct option per position), `page_count` (int), `page_map` (JSON: which question positions are on which page), `pdf_file` (path), `printed_at`
- Aggregate scan status: `assembly_status` (`partial`|`complete`) — flips to complete once all pages are scanned; grading runs then.

**ScanBatch**
- `id`, scope, `created_by`, `test` (FK), `status`, `total`, `processed`, `created_at`

**ScanJob** — one scanned **page** image
- `id`, `batch` (FK), `omr_sheet` (FK, resolved from QR), `page_no` (int, from QR), `image_file` (path), `status` (`queued`|`done`|`needs_review`|`failed`), `confidence` (float), `error_reason` (nullable)
- A sheet's pages may span multiple ScanJobs arriving in any order; they're grouped by `omr_sheet`.

### results
**StudentResult**
- `id`, `test` (FK), `student` (FK), `omr_sheet` (FK), `score`, `max_score`, `correct_count`, `wrong_count`, `blank_count`, `needs_review` (bool), `graded_at`
- Created once the OmrSheet's pages are all scanned (assembly complete).

**QuestionResponse**
- `id`, `student_result` (FK), `question` (FK), `marked_option` (nullable), `is_correct` (bool), `flagged` (bool — double/faint mark)

**ReviewItem** — items routed to manual review
- `id`, `scan_job` (FK, nullable), `omr_sheet` (FK), `question` (FK, nullable for roll-number/page issues), `reason` (`double_mark`|`faint`|`no_qr`|`roll_unreadable`|`alignment`|`missing_page`), `resolved` (bool), `resolved_by`, `resolution` (JSON)

## Key rules

- **Retest series**: walk `parent_test` to get the chain; `attempt_number` orders it. Improvement analytics compare the same Student's StudentResults across the chain (matched by roll number/student identity).
- **Answer-key versioning**: grading uses the **OmrSheet's** `answer_key` + `question_order`, never the test's default order — because each sheet may be shuffled differently.
- **Scope integrity**: a row's scope must match its parents' scope (a Test's scope == its Class's scope). Enforce in validation.
- **Uniqueness**: `roll_number` unique per roster; `sheet_code` globally unique; one StudentResult per (test, student) per scan unless re-scanned (then supersede/version).
