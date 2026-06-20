# Organization Workspace — Supabase-style — Spec

**Goal:** Clicking an organization opens a full workspace at `/org/<slug>/…` with six areas —
**Dashboard** (classes), **Members**, **Roles & Permissions**, **Usage**, **Billing**, **Settings** —
fully functional end-to-end. Built per owner spec + reference Supabase org dashboard.

**Owner decisions (locked):**
- URL scheme: `/org/<readable-slug>/…` (slug derived from name, unique, editable in Settings). Old
  `/organizations/:id/…` + `/classes` redirect to the slug routes.
- Seed roles (all editable; custom roles too): **Owner, Admin, Supervisor, Office, Teacher**.
- One member can be assigned to many classes/sections (∞) + optional subject narrowing.
- Scope: only what's relevant to OMR (no Integrations/SSO/AI-privacy/etc. from Supabase).

---

## 1. URL map

```
/organizations                      → org LIST (no shell)            [existing OrgList]
/org/:slug                          → Dashboard (classes grid)       [was /classes]
/org/:slug/members                  → Members
/org/:slug/roles                    → Roles & Permissions
/org/:slug/usage                    → Usage
/org/:slug/billing                  → Billing
/org/:slug/settings                 → Settings
/classes/:id/…                      → class workspace (UNCHANGED — entered from Dashboard)
/tests/:id/…                        → exam workspace (UNCHANGED)
```
Redirects: `/classes`→`/org/:activeSlug`; `/organizations/:id/*`→`/org/:slug/*`.
Slug resolution: a `slug → org` lookup sets the active org (X-Organization-Id) on entry.

## 2. Backend

### 2a. Organization.slug
- Add `slug = SlugField(unique=True, max_length=63)`. Auto-generate from name on create
  (slugify + de-dupe `-2`,`-3`…). Editable via PATCH (validate unique + slug format).
- New: `GET /api/v1/organizations/by-slug/<slug>/` → org (scope-checked membership) so the SPA
  can resolve slug→id. (Or accept slug in OrgDetailView.)

### 2b. Permission catalog (expand permissions_catalog.py)
Codes (group · code · label):
- **Organization**: `org.view` View organization · `org.edit` Edit organization details ·
  `org.delete` Delete organization · `org.billing` Manage billing & subscription
- **Members**: `member.view` View members · `member.invite` Invite / add members ·
  `member.edit` Edit member roles & assignments · `member.remove` Remove members
- **Roles**: `role.view` View roles · `role.manage` Create / edit / delete roles
- **Classes**: `class.view_all` View ALL classes (else assigned only) · `class.create` Create classes ·
  `class.edit` Edit class details · `class.delete` Delete classes · `group.manage` Manage sections / sub-groups
- **Students**: `student.view` View students · `student.add` Add students · `student.edit` Edit students ·
  `student.delete` Remove students · `student.import` Bulk import students
- **Subjects**: `subject.manage` Manage subjects
- **Exams**: `exam.view` View exams & results · `exam.create` Create exams · `exam.edit` Edit exams & questions ·
  `exam.delete` Delete exams · `exam.grade` Scan & grade · `exam.publish` Publish / share results ·
  `exam.analytics` View analytics
- **Usage**: `usage.view` View usage & limits

`ORG_WIDE` (ignore group scope): org.*, member.*, role.*, usage.view, class.create, class.view_all, billing.
`SCOPED` (respect RoleBinding.scope_group subtree): class.edit/delete, group.manage, student.*, subject.manage, exam.*.
A "view-only" role = the `*.view` codes only.

### 2c. System roles (role_seed.py — seed per org, `is_system=True`, editable)
| Role | Permissions |
|------|-------------|
| **Owner** | ALL codes (incl. org.delete, org.billing). One per org (creator); not deletable. |
| **Admin** | ALL except `org.delete`. (incl. billing, members, roles, class.view_all) |
| **Supervisor** | class.view_all + all class/student/subject/exam codes (org-wide) + usage.view. NO member/role/billing/org.edit/org.delete. |
| **Office** | member.view/invite/edit/remove + student.* + subject.manage + class.view_all + exam.view + usage.view. NO exam.edit/grade, NO billing/role/org.delete. |
| **Teacher** | (scoped via RoleBinding.scope_group) class.view + group.manage + student.view/add/edit + subject.manage + exam.view/create/edit/grade/publish/analytics. NO class.view_all/member/role/billing. |

`accessible_group_ids`/`visibility_q`/`has_perm` already enforce scoped vs org-wide — wire new codes in.

### 2d. Usage endpoint
- `GET /api/v1/billing/usage/` → `{ plan, cycle_start, cycle_end, items: [{ key,label,used,limit,unit }] }`
  for seats(members), students, exams(this cycle), scans(this cycle). Reuse billing/limits.py counters.

### 2e. Member assignments surfaced
- Members list returns, per member: role (system or custom), assigned classes (RoleBinding.scope_group names
  or ClassAccessGrant), narrowed subjects. Add a serializer/endpoint that joins these.

## 3. Frontend

### 3a. Shell — org workspace panel (AppShell.usePanel, matchOrgScope on `/org/:slug/*`)
Secondary nav (role-gated):
`Dashboard /org/:slug` · `Members …/members` · `Roles & permissions …/roles` (role.manage|view) ·
`Usage …/usage` · `Billing …/billing` (org.billing) · `Settings …/settings` (org.edit).
Title = org name. Back = "All organizations" → /organizations. Breadcrumb: Organizations › <Org> › <leaf>.

### 3b. Pages
- **Dashboard** = the existing Classes grid, rendered at `/org/:slug` (reuse Classes.jsx).
- **Members**: table — email · MFA-ish status · role (custom Select to change) · assigned classes (chips) ·
  subjects · actions (edit assignment, remove). "Invite member" (email + role). Assign dialog: pick role,
  pick classes/sections (multi, ∞), optional subjects. Gated by member.* perms.
- **Roles & Permissions**: list roles (system + custom) → click a role → permission matrix (grouped
  checkboxes from the catalog) editable + Save. "Create role" (name + clone-from + permissions). Delete
  custom roles. Gated by role.manage.
- **Usage**: plan banner + cycle dates + usage bars (used/limit) per item from the usage endpoint.
  "Upgrade" → Billing. Read-only.
- **Billing**: existing Billing.jsx, rendered at `/org/:slug/billing` (plan + change + usage summary).
- **Settings**: org details (name, **slug** editable, type) · danger zone (delete org, owner-only).
  Optionally fold Audit log here.

### 3c. Routing & context
- Add slug resolution: on `/org/:slug` entry, resolve slug→org, setActiveOrg(id). A small `useOrgSlug`
  guard (like useClass) maps slug→org via the by-slug endpoint or the loaded orgs list.
- OrgSwitcher + OrgList "open org" → navigate `/org/:slug`. Update all `/organizations/:id/*` links.
- Keep `/organizations/:id/*` + `/classes` as redirects to the slug routes.

## 4. Build order (phases, each tested)
1. **A — backend slug**: model field + migration + auto-gen + by-slug endpoint + serializer.
2. **B — routing**: slug routes + redirects + OrgContext slug resolution + OrgSwitcher/OrgList links +
   panel/breadcrumb. (Dashboard = Classes at /org/:slug.)
3. **C — permissions+roles**: expand catalog + seed Supervisor/Office (+ re-seed) + wire codes into scope.py.
4. **D — Roles & Permissions UI**: matrix + custom-role create/edit/delete.
5. **E — Members UI**: assignments (classes/subjects) + invite + role change + remove.
6. **F — Usage**: endpoint + page.
7. **G — Settings**: slug edit + delete + polish.
Each phase: lint 0 errors, build clean, screenshot-verify, commit. Re-run E2E after routing (B).
