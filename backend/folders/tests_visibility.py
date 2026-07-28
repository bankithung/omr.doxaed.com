"""
folders.tests_visibility — Product v2 Phase 5B + 5C folder-visibility scoping.

Covers (per the implementation brief):
  1. A member sees only creator + member-shared + org-shared + loose-own folders/
     classes/tests/rosters; a non-shared folder's class/test/roster/students are
     invisible in LIST and via direct ?test=/?roster=/detail (404, no IDOR).
  2. An admin sees the full org pool (override) AND can edit/delete a member's
     class; an admin can NOT see another org's data (bounded to active org).
  3. Cross-org FolderShare grantee → 400; folder↔class scope mismatch → rejected.
  4. Solo scope unchanged (no folders/sharing applied).
  5. Loose class = creator + admin only.
  6. VIEW-share member gets 403 creating/updating a test/class in that folder;
     EDIT-share member succeeds.
  7. List-filter and object-permission use the SAME predicate (a member who can't
     list object X also gets 404 on retrieve/update/delete X).
  8. The 5C migration leaves existing org classes visible to all members.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase

from assessments.models import ClassGroup, Test
from folders.models import Folder, FolderShare
from organizations.models import Organization, OrganizationMembership
from rosters.models import Roster, Student

User = get_user_model()


class _VisBase(APITestCase):
    """Two members (m1, m2) + one admin in org1, plus org2 (foreign) with user f."""

    def setUp(self):
        cache.clear()
        self.m1 = User.objects.create_user(email="m1@org.com", password="Str0ng!pass")
        self.m2 = User.objects.create_user(email="m2@org.com", password="Str0ng!pass")
        self.admin = User.objects.create_user(email="adm@org.com", password="Str0ng!pass")
        self.f = User.objects.create_user(email="f@org2.com", password="Str0ng!pass")

        self.org = Organization.objects.create(name="Org1", owner=self.admin)
        OrganizationMembership.objects.create(
            organization=self.org, user=self.admin, role="admin", status="active"
        )
        OrganizationMembership.objects.create(
            organization=self.org, user=self.m1, role="member", status="active"
        )
        OrganizationMembership.objects.create(
            organization=self.org, user=self.m2, role="member", status="active"
        )

        self.org2 = Organization.objects.create(name="Org2", owner=self.f)
        OrganizationMembership.objects.create(
            organization=self.org2, user=self.f, role="admin", status="active"
        )

        self._login(self.m1)

    def _login(self, user):
        r = self.client.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": "Str0ng!pass"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def _h(self, org=None):
        return {"HTTP_X_ORGANIZATION_ID": str((org or self.org).id)}

    # ---- DB factory helpers (bypass the API to set up fixtures) -------------
    def _folder(self, creator, org=None, name="F"):
        return Folder.objects.create(
            created_by=creator, name=name, organization=org or self.org
        )

    def _class(self, creator, folder=None, org=None, name="C"):
        return ClassGroup.objects.create(
            created_by=creator, name=name, folder=folder, organization=org or self.org
        )

    def _test(self, creator, cg, title="T"):
        return Test.objects.create(
            created_by=creator, class_group=cg, title=title, organization=cg.organization
        )

    def _roster(self, creator, cg=None, org=None, name="R"):
        return Roster.objects.create(
            created_by=creator, class_group=cg, name=name, organization=org or self.org
        )

    def _share(self, folder, user, perm="view", scope="member", creator=None):
        return FolderShare.objects.create(
            folder=folder,
            shared_with=(None if scope == "org" else user),
            share_scope=scope,
            permission=perm,
            created_by=creator or folder.created_by,
        )


# ---------------------------------------------------------------------------
# (1) Member visibility — creator / member-shared / org-shared / loose-own
# ---------------------------------------------------------------------------
class MemberVisibilityTests(_VisBase):
    def test_member_sees_only_visible_classes(self):
        # m1-owned folder + class (creator-visible)
        f_mine = self._folder(self.m1, name="mine")
        c_mine = self._class(self.m1, folder=f_mine, name="mine")
        # m2-owned folder shared to m1 (member share)
        f_shared = self._folder(self.m2, name="shared")
        c_shared = self._class(self.m2, folder=f_shared, name="shared")
        self._share(f_shared, self.m1, perm="view", scope="member")
        # m2-owned folder shared org-wide
        f_org = self._folder(self.m2, name="org")
        c_org = self._class(self.m2, folder=f_org, name="org")
        self._share(f_org, None, scope="org")
        # m2-owned folder NOT shared (invisible to m1)
        f_hidden = self._folder(self.m2, name="hidden")
        c_hidden = self._class(self.m2, folder=f_hidden, name="hidden")
        # m1 loose class (folder NULL, own creator)
        c_loose_mine = self._class(self.m1, folder=None, name="loose-mine")
        # m2 loose class (folder NULL, NOT m1's) → invisible
        c_loose_m2 = self._class(self.m2, folder=None, name="loose-m2")

        r = self.client.get("/api/v1/classes/", **self._h())
        self.assertEqual(r.status_code, 200)
        ids = {c["id"] for c in r.data["results"]}
        self.assertIn(str(c_mine.id), ids)
        self.assertIn(str(c_shared.id), ids)
        self.assertIn(str(c_org.id), ids)
        self.assertIn(str(c_loose_mine.id), ids)
        self.assertNotIn(str(c_hidden.id), ids)
        self.assertNotIn(str(c_loose_m2.id), ids)

    def test_hidden_class_test_roster_students_invisible_no_idor(self):
        f_hidden = self._folder(self.m2, name="hidden")
        c_hidden = self._class(self.m2, folder=f_hidden, name="hidden")
        t_hidden = self._test(self.m2, c_hidden, title="hidden-test")
        r_hidden = self._roster(self.m2, cg=c_hidden, name="hidden-roster")
        s_hidden = Student.objects.create(roster=r_hidden, roll_number="1")

        # Direct detail → 404
        self.assertEqual(
            self.client.get(f"/api/v1/classes/{c_hidden.id}/", **self._h()).status_code, 404
        )
        self.assertEqual(
            self.client.get(f"/api/v1/tests/{t_hidden.id}/", **self._h()).status_code, 404
        )
        self.assertEqual(
            self.client.get(f"/api/v1/rosters/{r_hidden.id}/", **self._h()).status_code, 404
        )
        self.assertEqual(
            self.client.get(f"/api/v1/students/{s_hidden.id}/", **self._h()).status_code, 404
        )

        # Direct ?filter= → empty list (no leak)
        r = self.client.get(f"/api/v1/tests/?class_group={c_hidden.id}", **self._h())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)
        r = self.client.get(f"/api/v1/students/?roster={r_hidden.id}", **self._h())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)
        r = self.client.get(f"/api/v1/tests/?test={t_hidden.id}", **self._h())
        # ?test isn't a Test filter, but the test itself must not appear in list
        r = self.client.get("/api/v1/tests/", **self._h())
        self.assertNotIn(str(t_hidden.id), {t["id"] for t in r.data["results"]})

    def test_member_share_makes_test_and_students_visible(self):
        f = self._folder(self.m2, name="shared")
        c = self._class(self.m2, folder=f, name="shared")
        t = self._test(self.m2, c)
        rost = self._roster(self.m2, cg=c)
        Student.objects.create(roster=rost, roll_number="1")
        self._share(f, self.m1, perm="view", scope="member")

        self.assertEqual(
            self.client.get(f"/api/v1/tests/{t.id}/", **self._h()).status_code, 200
        )
        r = self.client.get(f"/api/v1/students/?roster={rost.id}", **self._h())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 1)


# ---------------------------------------------------------------------------
# (2) Admin override + org boundary
# ---------------------------------------------------------------------------
class AdminOverrideTests(_VisBase):
    def test_admin_sees_full_org_pool(self):
        f_hidden = self._folder(self.m2, name="hidden")
        c_hidden = self._class(self.m2, folder=f_hidden, name="hidden")
        t_hidden = self._test(self.m2, c_hidden)

        self._login(self.admin)
        r = self.client.get("/api/v1/classes/", **self._h())
        self.assertIn(str(c_hidden.id), {c["id"] for c in r.data["results"]})
        self.assertEqual(
            self.client.get(f"/api/v1/tests/{t_hidden.id}/", **self._h()).status_code, 200
        )

    def test_admin_can_edit_and_delete_member_class(self):
        f = self._folder(self.m2, name="hidden")
        c = self._class(self.m2, folder=f, name="hidden")
        self._login(self.admin)
        r = self.client.patch(
            f"/api/v1/classes/{c.id}/", {"name": "renamed"}, format="json", **self._h()
        )
        self.assertEqual(r.status_code, 200)
        r = self.client.delete(f"/api/v1/classes/{c.id}/", **self._h())
        self.assertEqual(r.status_code, 204)

    def test_admin_cannot_see_other_org_data(self):
        c_other = self._class(self.f, folder=None, org=self.org2, name="other")
        # admin of org1, sending org1 header, must not see org2 class
        self._login(self.admin)
        r = self.client.get("/api/v1/classes/", **self._h())
        self.assertNotIn(str(c_other.id), {c["id"] for c in r.data["results"]})
        self.assertEqual(
            self.client.get(f"/api/v1/classes/{c_other.id}/", **self._h()).status_code, 404
        )


# ---------------------------------------------------------------------------
# (3) Cross-org share rejection + scope mismatch
# ---------------------------------------------------------------------------
class ShareValidationTests(_VisBase):
    def test_cross_org_member_share_rejected_400(self):
        f = self._folder(self.m1, name="mine")
        # m1 (creator) tries to share with f, who is NOT a member of org1.
        r = self.client.post(
            f"/api/v1/folders/{f.id}/shares/",
            {"shared_with": self.f.id, "share_scope": "member", "permission": "view"},
            format="json",
            **self._h(),
        )
        self.assertEqual(r.status_code, 400)

    def test_member_share_to_active_member_succeeds(self):
        f = self._folder(self.m1, name="mine")
        r = self.client.post(
            f"/api/v1/folders/{f.id}/shares/",
            {"shared_with": self.m2.id, "share_scope": "member", "permission": "edit"},
            format="json",
            **self._h(),
        )
        self.assertEqual(r.status_code, 201, r.data)

    def test_only_creator_or_admin_may_share(self):
        f = self._folder(self.m1, name="mine")
        # m2 (not creator, not admin) cannot share m1's folder even if visible.
        self._share(f, self.m2, perm="view", scope="member")
        self._login(self.m2)
        r = self.client.post(
            f"/api/v1/folders/{f.id}/shares/",
            {"shared_with": self.m2.id, "share_scope": "member", "permission": "view"},
            format="json",
            **self._h(),
        )
        self.assertIn(r.status_code, (403, 400))

    def test_admin_can_share_member_folder(self):
        f = self._folder(self.m1, name="mine")
        self._login(self.admin)
        r = self.client.post(
            f"/api/v1/folders/{f.id}/shares/",
            {"shared_with": self.m2.id, "share_scope": "member", "permission": "view"},
            format="json",
            **self._h(),
        )
        self.assertEqual(r.status_code, 201, r.data)

    def test_class_folder_scope_mismatch_rejected(self):
        # A folder in org2 cannot be assigned to an org1 class via the API.
        f_org2 = self._folder(self.f, org=self.org2, name="o2")
        r = self.client.post(
            "/api/v1/classes/",
            {"name": "X", "folder": f_org2.id},
            format="json",
            **self._h(),
        )
        self.assertEqual(r.status_code, 400)


# ---------------------------------------------------------------------------
# (4) Solo scope unchanged
# ---------------------------------------------------------------------------
class SoloScopeTests(_VisBase):
    def test_solo_scope_no_folder_logic(self):
        # No org header → solo scope. m1 creates a class; folders never apply.
        r = self.client.post("/api/v1/classes/", {"name": "Solo"}, format="json")
        self.assertEqual(r.status_code, 201)
        cid = r.data["id"]
        # m1 sees it (solo). m2 (different solo user) sees nothing.
        r = self.client.get("/api/v1/classes/")
        self.assertIn(cid, {c["id"] for c in r.data["results"]})
        self._login(self.m2)
        r = self.client.get("/api/v1/classes/")
        self.assertEqual(len(r.data["results"]), 0)


# ---------------------------------------------------------------------------
# (5) Loose class = creator + admin only
# ---------------------------------------------------------------------------
class LooseClassTests(_VisBase):
    def test_loose_class_visible_to_creator_and_admin_only(self):
        c_loose = self._class(self.m1, folder=None, name="loose")
        # creator m1 sees it
        r = self.client.get("/api/v1/classes/", **self._h())
        self.assertIn(str(c_loose.id), {c["id"] for c in r.data["results"]})
        # m2 does NOT
        self._login(self.m2)
        r = self.client.get("/api/v1/classes/", **self._h())
        self.assertNotIn(str(c_loose.id), {c["id"] for c in r.data["results"]})
        self.assertEqual(
            self.client.get(f"/api/v1/classes/{c_loose.id}/", **self._h()).status_code, 404
        )
        # admin DOES
        self._login(self.admin)
        r = self.client.get("/api/v1/classes/", **self._h())
        self.assertIn(str(c_loose.id), {c["id"] for c in r.data["results"]})


# ---------------------------------------------------------------------------
# (6) VIEW vs EDIT enforcement
# ---------------------------------------------------------------------------
class EditEnforcementTests(_VisBase):
    def test_view_share_member_cannot_write_edit_share_member_can(self):
        f = self._folder(self.m2, name="shared")
        c = self._class(self.m2, folder=f, name="shared")
        # VIEW share to m1
        share = self._share(f, self.m1, perm="view", scope="member")

        # m1 can READ the class but NOT create a test under it.
        self.assertEqual(
            self.client.get(f"/api/v1/classes/{c.id}/", **self._h()).status_code, 200
        )
        r = self.client.post(
            "/api/v1/tests/",
            {"class_group": c.id, "title": "X"},
            format="json",
            **self._h(),
        )
        self.assertEqual(r.status_code, 403, r.data)
        # m1 cannot rename the class either
        r = self.client.patch(
            f"/api/v1/classes/{c.id}/", {"name": "nope"}, format="json", **self._h()
        )
        self.assertEqual(r.status_code, 403)

        # Upgrade to EDIT share → m1 can now create a test.
        share.permission = FolderShare.PERM_EDIT
        share.save(update_fields=["permission"])
        r = self.client.post(
            "/api/v1/tests/",
            {"class_group": c.id, "title": "Y"},
            format="json",
            **self._h(),
        )
        self.assertEqual(r.status_code, 201, r.data)

    def test_org_view_share_blocks_writes(self):
        f = self._folder(self.m2, name="orgshared")
        c = self._class(self.m2, folder=f, name="orgshared")
        self._share(f, None, perm="view", scope="org")
        # m1 sees it via org-share but is VIEW-only.
        r = self.client.post(
            "/api/v1/tests/",
            {"class_group": c.id, "title": "X"},
            format="json",
            **self._h(),
        )
        self.assertEqual(r.status_code, 403)


# ---------------------------------------------------------------------------
# (7) list-filter == object-permission (same predicate)
# ---------------------------------------------------------------------------
class SamePredicateTests(_VisBase):
    def test_unlistable_object_also_unreachable_by_id(self):
        f_hidden = self._folder(self.m2, name="hidden")
        c = self._class(self.m2, folder=f_hidden, name="hidden")
        t = self._test(self.m2, c)

        # Not in list
        r = self.client.get("/api/v1/tests/", **self._h())
        self.assertNotIn(str(t.id), {x["id"] for x in r.data["results"]})
        # 404 on retrieve / update / delete
        self.assertEqual(
            self.client.get(f"/api/v1/tests/{t.id}/", **self._h()).status_code, 404
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/tests/{t.id}/", {"title": "z"}, format="json", **self._h()
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/tests/{t.id}/", **self._h()).status_code, 404
        )


# ---------------------------------------------------------------------------
# (8) 5C migration grandfathering (simulate by replicating its effect, then
#     assert visibility holds for a second member)
# ---------------------------------------------------------------------------
class GrandfatherMigrationTests(_VisBase):
    def test_org_general_folder_keeps_pre_migration_class_visible(self):
        """After grandfathering, an existing org-scoped loose class created by m1
        is org-shared (via the General folder) and therefore visible to m2."""
        # Replicate the 5C migration's effect for a class created by m1.
        c = self._class(self.m1, folder=None, name="pre-migration")
        general = Folder.objects.create(
            created_by=self.admin, name="General", organization=self.org
        )
        FolderShare.objects.create(
            folder=general, shared_with=None, share_scope="org",
            permission="view", created_by=self.admin,
        )
        c.folder = general
        c.save(update_fields=["folder"])

        # m2 (a different member) must still see m1's pre-migration class.
        self._login(self.m2)
        r = self.client.get("/api/v1/classes/", **self._h())
        self.assertIn(str(c.id), {x["id"] for x in r.data["results"]})


# ---------------------------------------------------------------------------
# Folder endpoint sanity (visibility + permission field)
# ---------------------------------------------------------------------------
class FolderEndpointTests(_VisBase):
    def test_folder_list_visibility_and_permission_field(self):
        f_mine = self._folder(self.m1, name="mine")
        f_shared = self._folder(self.m2, name="shared")
        self._share(f_shared, self.m1, perm="view", scope="member")
        f_hidden = self._folder(self.m2, name="hidden")

        r = self.client.get("/api/v1/folders/", **self._h())
        self.assertEqual(r.status_code, 200)
        by_id = {x["id"]: x for x in r.data["results"]}
        self.assertIn(str(f_mine.id), by_id)
        self.assertIn(str(f_shared.id), by_id)
        self.assertNotIn(str(f_hidden.id), by_id)
        self.assertEqual(by_id[f_mine.id]["permission"], "edit")
        self.assertEqual(by_id[f_shared.id]["permission"], "view")

    def test_create_folder_stamps_org_and_creator(self):
        r = self.client.post(
            "/api/v1/folders/", {"name": "New"}, format="json", **self._h()
        )
        self.assertEqual(r.status_code, 201, r.data)
        folder = Folder.objects.get(pk=r.data["id"])
        self.assertEqual(folder.organization_id, self.org.id)
        self.assertEqual(folder.created_by_id, self.m1.id)


# ---------------------------------------------------------------------------
# Subject endpoint
# ---------------------------------------------------------------------------
class SubjectEndpointTests(_VisBase):
    def test_subject_create_requires_edit_and_scopes_visibility(self):
        f = self._folder(self.m2, name="shared")
        c = self._class(self.m2, folder=f, name="shared")
        # VIEW share → m1 cannot create a subject
        share = self._share(f, self.m1, perm="view", scope="member")
        r = self.client.post(
            "/api/v1/subjects/",
            {"class_group": c.id, "name": "Math"},
            format="json",
            **self._h(),
        )
        self.assertEqual(r.status_code, 403, r.data)
        # EDIT share → succeeds
        share.permission = FolderShare.PERM_EDIT
        share.save(update_fields=["permission"])
        r = self.client.post(
            "/api/v1/subjects/",
            {"class_group": c.id, "name": "Math"},
            format="json",
            **self._h(),
        )
        self.assertEqual(r.status_code, 201, r.data)

    def test_subject_list_hidden_class_invisible(self):
        f_hidden = self._folder(self.m2, name="hidden")
        c = self._class(self.m2, folder=f_hidden, name="hidden")
        from assessments.models import Subject

        Subject.objects.create(class_group=c, name="Sci")
        r = self.client.get(f"/api/v1/subjects/?class_group={c.id}", **self._h())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)


# ---------------------------------------------------------------------------
# (Audit fix) Parent-FK reassignment must gate the DESTINATION's EDIT rights
# ---------------------------------------------------------------------------

class ParentReassignmentEditGateTests(_VisBase):
    """A member with EDIT on a source test/roster must NOT be able to re-parent a
    child (question/student) into a test/roster they can only VIEW. The destination
    parent's EDIT rights are gated, not just the source's."""

    def test_question_cannot_be_reparented_into_view_only_test(self):
        from assessments.models import Question
        # m1 owns TA (m1 created the folder → m1 has EDIT on TA's class)
        fa = self._folder(self.m1, name="m1-edit")
        ca = self._class(self.m1, folder=fa, name="m1class")
        ta = self._test(self.m1, ca, title="TA")
        # m2 owns TB in an ORG-WIDE VIEW-shared folder → m1 can SEE TB but only VIEW
        fb = self._folder(self.m2, name="m2-orgview")
        cb = self._class(self.m2, folder=fb, name="m2class")
        tb = self._test(self.m2, cb, title="TB")
        self._share(fb, None, perm="view", scope="org")

        self._login(self.m1)
        r = self.client.post(
            "/api/v1/questions/",
            {"test": ta.id, "order_index": 0, "text": "q",
             "options": [{"label": "A", "text": "x", "is_correct": True}]},
            format="json", **self._h(),
        )
        self.assertEqual(r.status_code, 201, r.data)
        qid = r.data["id"]

        # Attempt to re-parent the question into the VIEW-only test TB → 403
        r2 = self.client.patch(
            f"/api/v1/questions/{qid}/",
            {"test": tb.id, "order_index": 0, "text": "injected",
             "options": [{"label": "A", "text": "x", "is_correct": True}]},
            format="json", **self._h(),
        )
        self.assertEqual(r2.status_code, 403, getattr(r2, "data", r2))
        self.assertFalse(Question.objects.filter(id=qid, test=tb).exists())
        # Source unchanged
        self.assertTrue(Question.objects.filter(id=qid, test=ta).exists())

    def test_student_cannot_be_reparented_into_view_only_roster(self):
        from rosters.models import Student
        fa = self._folder(self.m1, name="m1-edit-r")
        ca = self._class(self.m1, folder=fa, name="m1class-r")
        ra = self._roster(self.m1, cg=ca, name="RA")
        fb = self._folder(self.m2, name="m2-orgview-r")
        cb = self._class(self.m2, folder=fb, name="m2class-r")
        rb = self._roster(self.m2, cg=cb, name="RB")
        self._share(fb, None, perm="view", scope="org")

        student = Student.objects.create(roster=ra, roll_number="1", full_name="S")

        self._login(self.m1)
        r2 = self.client.patch(
            f"/api/v1/students/{student.id}/",
            {"roster": rb.id}, format="json", **self._h(),
        )
        self.assertEqual(r2.status_code, 403, getattr(r2, "data", r2))
        self.assertFalse(Student.objects.filter(id=student.id, roster=rb).exists())
        self.assertTrue(Student.objects.filter(id=student.id, roster=ra).exists())
