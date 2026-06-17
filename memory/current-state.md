# Current State

- 2026-06-17: **Phase 2 (Assessments core) complete** (branch `phase-2` → merged to `main`).
  ClassGroup → Test CRUD, Question/Option authoring, MarkingScheme, retest deep-copy — all
  solo-scope isolated. **45 backend tests green** (incl. a sonnet scope/IDOR audit with a live
  cross-tenant probe). React: Classes list, per-class Test list (+ retest), and a 3-step
  test-creation Wizard (details+marking → adaptive single/multiple-correct question authoring →
  review/finish). The Phase-0 owner-scope DB `CheckConstraint` is now validated on real tables.
- **Next:** Phase 3 (Roster & OMR generation) per `prompts/BUILD_ROADMAP.md` + `OMR_ENGINE_SPEC.md`
  + `DATA_MODEL.md`: Roster + Student (named+roll OR count-only), OMR PDF generation via ReportLab
  (header, per-page QR `sheet_code`+page, fiducials, roll-number dot grid, answer grid), per-student
  shuffle (`question_order`/`answer_key`), `template_descriptor` JSON, multi-page + `page_map`,
  batch PDF, free-tier gates (10 students/gen, 5 gens/day). Generation must be deterministic.
- Done: Phase 0 (foundations) · Phase 1 (auth) · Phase 2 (assessments). Repo: standalone git repo,
  `main` holds Phases 0–2.

## Architecture patterns (FOLLOW in later phases)
- **Owner-scope (direct):** models inheriting `OwnerScopedModel` (user XOR org) use
  `common.viewsets.ScopedModelViewSet` (permission `IsInScope`; `get_queryset` filters
  `user=request.user`; `perform_create` stamps `user` + `owner_extra_fields`). The inherited
  `CheckConstraint` lands automatically; if you add a child `Meta` (e.g. ordering), run
  `makemigrations` to capture the `AlterModelOptions`.
- **Child-scope (CRITICAL):** resources that are NOT `OwnerScopedModel` but belong to a scoped
  parent (e.g. `Question`→Test; in Phase 3+: `Student`→Roster, OMR sheets→Test, results, scan jobs)
  MUST use `permission_classes=[IsAuthenticated]` + a `get_queryset` filtered through the parent's
  scope (e.g. `test__user=request.user`). Do NOT use `IsInScope` on them — it checks `obj.user_id`
  which child models lack, causing 403 on every detail op. (This was a Critical bug in Phase 2.)
- **Cross-scope attach:** serializers validate FK parents belong to `request.user`
  (`validate_<fk>` → 400). Owner fields (`user`/`organization`) are never writable serializer fields.

## Deferred follow-ups
- **Phase 3+:** Question/Option `image` upload API absent (models have ImageField; serializers omit
  it — text-only MVP). `?class_group` filter on /tests/ doesn't 400 on a foreign id (safe: returns
  empty). `OwnerScopedModel.clean()` not auto-called by save() — rely on the DB constraint or call
  `full_clean()`.
- **Phase 6:** `IsInScope.has_object_permission` → add org-membership path + `super().has_permission()`.
- **Phase 8 (hardening):** register duplicate-email enumeration; `verify-email/` unthrottled; full
  account lockout (django-axes); frontend bundle code-splitting (recharts).
- **Phase 1 leftover:** unused `first_name`/`last_name` on User; hand-authored `form.jsx` still unused.

## Resolved
- Phase-1 AllowAny applied on all public auth views. Phase-2 child-scope 403 bug fixed (Question).
