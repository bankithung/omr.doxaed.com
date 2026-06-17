# OMRFlow — Project Documentation

> Working name: **OMRFlow** (rename freely). A web + mobile platform for creating MCQ tests, generating personalized OMR sheets, scanning them fast, and tracking student improvement over retests.

This folder is the single source of truth for building the product. Feed these files to your AI coding agent in this order. Each doc is self-contained but cross-references the others.

## Document index

| File | Purpose | Read when |
|------|---------|-----------|
| `PRD.md` | What we're building and why — features, users, roles, monetization, scope | First. Defines the product. |
| `TECHNICAL_ARCHITECTURE.md` | Stack, system design, security model, deployment | Before writing any code. |
| `DATA_MODEL.md` | Entities, relationships, key fields, multi-tenancy | When building models/DB. |
| `OMR_ENGINE_SPEC.md` | Sheet generation + scanning pipeline (the hard part) | When building OMR features. |
| `DESIGN_SYSTEM.md` | UI rules — custom components, responsiveness, no native dropdowns/alerts | When building any UI. |
| `AGENT_PROMPT.md` | The system prompt for the AI coding agent | Paste into your agent at project start. |
| `BUILD_ROADMAP.md` | Phased build plan, MVP first | To sequence the work. |

## How to use these with an AI agent

1. Start a project/repo. Paste `AGENT_PROMPT.md` as the system prompt.
2. Give the agent `PRD.md` + `TECHNICAL_ARCHITECTURE.md` + `DATA_MODEL.md` as context.
3. Build phase by phase per `BUILD_ROADMAP.md`. Pull in `OMR_ENGINE_SPEC.md` and `DESIGN_SYSTEM.md` when those phases arrive.
4. Keep these docs in the repo at `/docs`. Update them as decisions change — they are living documents.

## Decisions to confirm before locking the prompts

All five decisions are now locked:

1. ✅ **Billing model.** Anyone signs up free (solo, free tier). Creating an organization requires a **paid subscription** (no free org). The org creator is automatically its **admin**. A "seat" = a staff member who logs in (admin included); test-takers are never accounts.
2. ✅ **Pricing tiers & caps.** Free / Team ₹500 (≤50 seats) / Business ₹1,000 (51–200 seats) / Enterprise. Metered by monthly scans; past cap → upgrade prompt, no silent overage; annual = 2 months free. Numbers are starting points to validate. See `PRD.md → Monetization`.
3. ✅ **Identity on the sheet.** No handwriting/OCR. Student bubbles a **roll-number dot grid**; scanner detects the filled dots → gets the number → **looks up the name in the DB**. See `OMR_ENGINE_SPEC.md`.
4. ✅ **QR code on every sheet/page.** Encodes test + student + shuffle-version + **page number**, so scanning is unambiguous and multi-page sheets auto-stitch. See `OMR_ENGINE_SPEC.md`.
5. ✅ **Frontend = React** (SPA) on a Django + DRF API backend; charts via a React chart lib. Mobile app reuses the same API. See `TECHNICAL_ARCHITECTURE.md`.
