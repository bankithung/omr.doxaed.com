---
name: brand-name
description: The product's official user-facing name is "DoxaEd OMR" (not OMRFlow)
metadata:
  type: project
---

The product's official **user-facing name is "DoxaEd OMR"** (parent brand DoxaEd; domain omr.doxaed.com). It was previously called "OMRFlow" throughout — the owner renamed it on 2026-06-18.

**How to apply:** replace user-facing "OMRFlow" strings with "DoxaEd OMR" (nav wordmark, footer, landing copy, auth pages, page `<title>`, report-card PDFs, email templates, public result portal). The cinematic landing rebrand uses it already.

**Do NOT change internal identifiers** — these stay as-is: the Postgres DB name `omrflow`, package.json names, Python/JS module names, and the demo/test fixture email domain `@omrflow.test` (e.g. teacher@omrflow.test / Teacher@12345). Only human-visible product-name strings change. See [[productv2-status]].
