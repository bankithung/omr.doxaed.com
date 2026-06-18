---
name: phase5-visibility-decisions
description: Owner-approved decisions for the Phase 5 folders/sharing visibility flip + admin override
metadata:
  type: project
---

Owner decisions (2026-06-18) for **Product v2 Phase 5** (folders + sharing + admin-sees-all), answering the plan's §6 open questions. These gate the 5B scoping + 5C data migration — implement to these, not the plan's defaults where they differ.

1. **Existing-data visibility flip (§6 Q1):** **Keep existing data visible to the whole org.** The 5C data migration must grandfather all pre-existing classes/tests/rosters as org-wide VIEW-visible (e.g. seed one org-wide `FolderShare(share_scope=ORG, permission=VIEW)` per existing folder AND/OR keep existing loose classes org-visible) so NO member loses access on rollout. NEW folders are private-to-creator until shared. Loose-class SECURITY policy for NEW rows stays creator+admin; the migration only preserves the legacy flat-pool view for existing data.

2. **Admin override scope (§6 Q2):** **Admins get FULL edit/delete, not view-only.** `visibility_q`/`IsInScope` admin short-circuit (bounded to the active `X-Organization-Id` org via `request._membership.role == ADMIN`, audit-logged) grants admins read AND write/delete on any member's data in their own org. This is the owner's explicit choice over the research-recommended read-only default — note the higher blast radius if an admin account is compromised.

Other Phase-5 security invariants unchanged from the plan: cross-org `FolderShare` grantee rejected (validate ACTIVE membership in `folder.organization`); folder↔class scope match enforced (CheckConstraint/clean); header-only org resolution (no `?org=`); one shared `visibility_q` used by BOTH get_queryset AND `IsInScope.has_object_permission` (no list/object drift → IDOR); child-chain folder prefixes (`test__class_group__folder__`, `roster__...`, `omr_sheet__test__class_group__folder__`); public `/r/<slug>` must not expose folder/branding fields. See [[productv2-status]].

Resume note: the 5A models agent (`feat/productv2-p5a-models`) STALLED mid-run and likely committed nothing — verify/clean its worktree+branch before re-dispatching 5A.
