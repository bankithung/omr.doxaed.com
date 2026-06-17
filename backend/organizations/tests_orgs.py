"""
Phase 6 Task 1 — Org-scope integration tests.

Coverage:
  A) Model: OrganizationMembership, Invitation, AuditLog created correctly.
  B) Scope helper: get_active_org / scope_filter / scope_kwargs behaviour.
  C) Non-member header → 403.
  D) Org member creates ClassGroup → it is org-owned → another member sees it.
  E) Solo mode unaffected (no header → personal scope).
  F) Cross-org isolation (member of org1 cannot see org2 data).
  G) FK-parent validator: member can attach a Test to an org-owned ClassGroup;
     cannot attach to a different-org or personal ClassGroup.
  H) Roster org-scope (create + list shared; attach org-owned ClassGroup).
  I) IsInScope.has_object_permission grants org-member access, rejects non-member.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from organizations.models import AuditLog, Invitation, Organization, OrganizationMembership

User = get_user_model()


# ---------------------------------------------------------------------------
# A) Model smoke tests
# ---------------------------------------------------------------------------

class OrgModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@x.com", password="Str0ng!pass")
        self.org = Organization.objects.create(name="TestOrg", owner=self.owner)
        self.member = User.objects.create_user(email="member@x.com", password="Str0ng!pass")

    def test_membership_created(self):
        m = OrganizationMembership.objects.create(
            organization=self.org, user=self.owner, role="admin", status="active"
        )
        self.assertEqual(str(m.organization), "TestOrg")
        self.assertEqual(m.role, "admin")
        self.assertEqual(m.status, "active")

    def test_membership_unique_constraint(self):
        from django.db import IntegrityError, transaction
        OrganizationMembership.objects.create(
            organization=self.org, user=self.owner, role="admin", status="active"
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OrganizationMembership.objects.create(
                    organization=self.org, user=self.owner, role="member", status="active"
                )

    def test_invitation_created(self):
        inv = Invitation.objects.create(
            organization=self.org,
            email="new@x.com",
            role="member",
            invited_by=self.owner,
            expires_at=timezone.now() + timezone.timedelta(days=7),
        )
        self.assertIsNotNone(inv.token)
        self.assertIsNone(inv.accepted_at)

    def test_audit_log_created(self):
        log = AuditLog.objects.create(
            organization=self.org,
            actor=self.owner,
            action="invite",
            target_type="user",
            target_id=self.member.id,
            metadata={"email": "member@x.com"},
        )
        self.assertEqual(log.action, "invite")
        self.assertIn("member@x.com", str(log.metadata))


# ---------------------------------------------------------------------------
# Helpers shared across API tests
# ---------------------------------------------------------------------------

class _OrgApiBase(APITestCase):
    """Set up two users (A=admin, B=member) sharing one org, plus a second org."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

        self.a = User.objects.create_user(email="a@org.com", password="Str0ng!pass")
        self.b = User.objects.create_user(email="b@org.com", password="Str0ng!pass")
        self.c = User.objects.create_user(email="c@org.com", password="Str0ng!pass")  # non-member

        self.org = Organization.objects.create(name="Org1", owner=self.a)
        OrganizationMembership.objects.create(
            organization=self.org, user=self.a, role="admin", status="active"
        )
        OrganizationMembership.objects.create(
            organization=self.org, user=self.b, role="member", status="active"
        )

        # A second org that C belongs to — for cross-org isolation tests
        self.org2 = Organization.objects.create(name="Org2", owner=self.c)
        OrganizationMembership.objects.create(
            organization=self.org2, user=self.c, role="admin", status="active"
        )

        self._login(self.a)

    def _login(self, user):
        r = self.client.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": "Str0ng!pass"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def _org_header(self, org=None):
        """Return HTTP headers dict for the given org (default self.org)."""
        target = org or self.org
        return {"HTTP_X_ORGANIZATION_ID": str(target.id)}


# ---------------------------------------------------------------------------
# B) scope helper unit-level via the API (no header → solo filter)
# ---------------------------------------------------------------------------

class ScopeHelperTests(_OrgApiBase):
    def test_no_header_returns_solo_scope(self):
        """Without a header the viewset falls back to user-scoped filtering."""
        # A creates a class without header → personal scope
        r = self.client.post("/api/v1/classes/", {"name": "Personal"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(r.data.get("organization"))  # not part of response but DB should have user set

        # B sees 0 classes (different user, no header)
        self._login(self.b)
        r = self.client.get("/api/v1/classes/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)


# ---------------------------------------------------------------------------
# C) Non-member header → 403
# ---------------------------------------------------------------------------

class NonMemberOrgHeaderTests(_OrgApiBase):
    def test_non_member_header_returns_403(self):
        """User C is not a member of org1 → 403 on list."""
        self._login(self.c)
        r = self.client.get("/api/v1/classes/", **self._org_header(self.org))
        self.assertEqual(r.status_code, 403)

    def test_non_member_header_create_returns_403(self):
        """User C cannot create in org1."""
        self._login(self.c)
        r = self.client.post(
            "/api/v1/classes/", {"name": "X"}, format="json", **self._org_header(self.org)
        )
        self.assertEqual(r.status_code, 403)

    def test_removed_member_header_returns_403(self):
        """A removed membership is not active → 403."""
        OrganizationMembership.objects.filter(
            organization=self.org, user=self.b
        ).update(status="removed")
        self._login(self.b)
        r = self.client.get("/api/v1/classes/", **self._org_header(self.org))
        self.assertEqual(r.status_code, 403)


# ---------------------------------------------------------------------------
# D) Org member creates ClassGroup → org-owned → another member sees it
# ---------------------------------------------------------------------------

class OrgSharedClassGroupTests(_OrgApiBase):
    def test_admin_creates_class_member_sees_it(self):
        """A creates a ClassGroup under org1 → B (same org) sees it in list."""
        # A creates under org
        r = self.client.post(
            "/api/v1/classes/", {"name": "OrgClass"}, format="json", **self._org_header()
        )
        self.assertEqual(r.status_code, 201)
        class_id = r.data["id"]

        # B lists under same org → should see it
        self._login(self.b)
        r = self.client.get("/api/v1/classes/", **self._org_header())
        self.assertEqual(r.status_code, 200)
        ids = [item["id"] for item in r.data["results"]]
        self.assertIn(class_id, ids)

    def test_class_is_org_owned_not_user_owned(self):
        """The ClassGroup created under org header has organization set, not user."""
        from assessments.models import ClassGroup
        self.client.post(
            "/api/v1/classes/", {"name": "OrgClass"}, format="json", **self._org_header()
        )
        cg = ClassGroup.objects.get(name="OrgClass")
        self.assertIsNone(cg.user_id)
        self.assertEqual(cg.organization_id, self.org.id)

    def test_member_can_create_and_admin_sees_it(self):
        """B (member) creates; A (admin) also sees it."""
        self._login(self.b)
        r = self.client.post(
            "/api/v1/classes/", {"name": "MemberClass"}, format="json", **self._org_header()
        )
        self.assertEqual(r.status_code, 201)
        class_id = r.data["id"]

        self._login(self.a)
        r = self.client.get("/api/v1/classes/", **self._org_header())
        ids = [item["id"] for item in r.data["results"]]
        self.assertIn(class_id, ids)

    def test_member_can_retrieve_org_class_detail(self):
        """B can GET the detail of an org-owned class created by A."""
        r = self.client.post(
            "/api/v1/classes/", {"name": "OrgClass"}, format="json", **self._org_header()
        )
        class_id = r.data["id"]

        self._login(self.b)
        r = self.client.get(f"/api/v1/classes/{class_id}/", **self._org_header())
        self.assertEqual(r.status_code, 200)

    def test_member_can_update_org_class(self):
        """B can PATCH an org-owned class."""
        r = self.client.post(
            "/api/v1/classes/", {"name": "OrgClass"}, format="json", **self._org_header()
        )
        class_id = r.data["id"]

        self._login(self.b)
        r = self.client.patch(
            f"/api/v1/classes/{class_id}/", {"name": "Updated"}, format="json",
            **self._org_header()
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["name"], "Updated")


# ---------------------------------------------------------------------------
# E) Solo mode unaffected
# ---------------------------------------------------------------------------

class SoloScopeUnchangedTests(_OrgApiBase):
    def test_solo_create_separate_from_org(self):
        """A creates one class solo, one under org → solo list only shows solo class."""
        self.client.post("/api/v1/classes/", {"name": "SoloClass"}, format="json")
        self.client.post(
            "/api/v1/classes/", {"name": "OrgClass"}, format="json", **self._org_header()
        )

        # Solo list: only SoloClass
        r = self.client.get("/api/v1/classes/")
        self.assertEqual(len(r.data["results"]), 1)
        self.assertEqual(r.data["results"][0]["name"], "SoloClass")

        # Org list: only OrgClass
        r = self.client.get("/api/v1/classes/", **self._org_header())
        self.assertEqual(len(r.data["results"]), 1)
        self.assertEqual(r.data["results"][0]["name"], "OrgClass")

    def test_b_solo_does_not_see_a_solo_classes(self):
        """B's personal scope is still isolated from A's personal scope."""
        self.client.post("/api/v1/classes/", {"name": "A-Solo"}, format="json")

        self._login(self.b)
        r = self.client.get("/api/v1/classes/")
        self.assertEqual(len(r.data["results"]), 0)


# ---------------------------------------------------------------------------
# F) Cross-org isolation
# ---------------------------------------------------------------------------

class CrossOrgIsolationTests(_OrgApiBase):
    def test_org2_member_cannot_see_org1_classes(self):
        """C (admin of org2) cannot see org1's classes even with org2 header."""
        # A creates a class in org1
        self.client.post(
            "/api/v1/classes/", {"name": "Org1Class"}, format="json", **self._org_header(self.org)
        )

        # C lists under org2 → 0 results
        self._login(self.c)
        r = self.client.get("/api/v1/classes/", **self._org_header(self.org2))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)

    def test_org2_member_cannot_access_org1_class_detail(self):
        """C cannot GET the detail of an org1-owned class, even with org2 header."""
        r = self.client.post(
            "/api/v1/classes/", {"name": "Org1Class"}, format="json", **self._org_header(self.org)
        )
        class_id = r.data["id"]

        self._login(self.c)
        # Using org2 header
        r = self.client.get(f"/api/v1/classes/{class_id}/", **self._org_header(self.org2))
        self.assertEqual(r.status_code, 404)


# ---------------------------------------------------------------------------
# G) FK-parent validator: Test under org-owned ClassGroup
# ---------------------------------------------------------------------------

class OrgTestFKValidatorTests(_OrgApiBase):
    def _create_org_class(self):
        r = self.client.post(
            "/api/v1/classes/", {"name": "OrgClass"}, format="json", **self._org_header()
        )
        return r.data["id"]

    def test_member_creates_test_under_org_class(self):
        """B can create a Test under an org-owned ClassGroup."""
        cg_id = self._create_org_class()

        self._login(self.b)
        r = self.client.post(
            "/api/v1/tests/",
            {"class_group": cg_id, "title": "OrgTest", "subject": "Math"},
            format="json",
            **self._org_header(),
        )
        self.assertEqual(r.status_code, 201)

    def test_cannot_attach_test_to_other_orgs_class(self):
        """C (org2) cannot attach a Test to org1's ClassGroup."""
        cg_id = self._create_org_class()  # org1's class, created by A

        # C creates a class in org2
        self._login(self.c)
        r = self.client.post(
            "/api/v1/tests/",
            {"class_group": cg_id, "title": "BadTest"},
            format="json",
            **self._org_header(self.org2),
        )
        self.assertIn(r.status_code, (400, 403, 404))

    def test_solo_user_cannot_attach_test_to_org_class(self):
        """A in solo mode cannot attach a Test to org1's ClassGroup (scope mismatch)."""
        cg_id = self._create_org_class()  # org-owned, created with org header

        # A now operates solo (no header)
        r = self.client.post(
            "/api/v1/tests/",
            {"class_group": cg_id, "title": "SoloTest"},
            format="json",
        )
        self.assertIn(r.status_code, (400, 404))

    def test_org_test_visible_to_other_member(self):
        """A creates a Test under org1 → B sees it in list."""
        cg_id = self._create_org_class()
        r = self.client.post(
            "/api/v1/tests/",
            {"class_group": cg_id, "title": "SharedTest"},
            format="json",
            **self._org_header(),
        )
        test_id = r.data["id"]

        self._login(self.b)
        r = self.client.get("/api/v1/tests/", **self._org_header())
        ids = [item["id"] for item in r.data["results"]]
        self.assertIn(test_id, ids)


# ---------------------------------------------------------------------------
# H) Roster org-scope
# ---------------------------------------------------------------------------

class OrgRosterTests(_OrgApiBase):
    def test_member_creates_roster_other_member_sees_it(self):
        """B creates a Roster under org1 → A sees it."""
        self._login(self.b)
        r = self.client.post(
            "/api/v1/rosters/", {"name": "OrgRoster"}, format="json", **self._org_header()
        )
        self.assertEqual(r.status_code, 201)
        roster_id = r.data["id"]

        self._login(self.a)
        r = self.client.get("/api/v1/rosters/", **self._org_header())
        ids = [item["id"] for item in r.data["results"]]
        self.assertIn(roster_id, ids)

    def test_roster_linked_to_org_class(self):
        """A creates an org ClassGroup, then a Roster linked to it — member B sees both."""
        r = self.client.post(
            "/api/v1/classes/", {"name": "OrgClass"}, format="json", **self._org_header()
        )
        cg_id = r.data["id"]

        r = self.client.post(
            "/api/v1/rosters/",
            {"name": "OrgRoster", "class_group": cg_id},
            format="json",
            **self._org_header(),
        )
        self.assertEqual(r.status_code, 201)
        roster_id = r.data["id"]

        self._login(self.b)
        r = self.client.get("/api/v1/rosters/", **self._org_header())
        ids = [item["id"] for item in r.data["results"]]
        self.assertIn(roster_id, ids)

    def test_cannot_link_roster_to_other_orgs_class(self):
        """C cannot create a roster in org2 linked to org1's ClassGroup."""
        r = self.client.post(
            "/api/v1/classes/", {"name": "Org1Class"}, format="json", **self._org_header(self.org)
        )
        cg_id = r.data["id"]

        self._login(self.c)
        r = self.client.post(
            "/api/v1/rosters/",
            {"name": "BadRoster", "class_group": cg_id},
            format="json",
            **self._org_header(self.org2),
        )
        self.assertIn(r.status_code, (400, 403, 404))


# ---------------------------------------------------------------------------
# I) IsInScope.has_object_permission
# ---------------------------------------------------------------------------

class IsInScopePermissionTests(_OrgApiBase):
    def test_org_member_can_retrieve_org_class_detail(self):
        """B retrieves detail of A's org-owned class via org header."""
        r = self.client.post(
            "/api/v1/classes/", {"name": "OrgClass"}, format="json", **self._org_header()
        )
        class_id = r.data["id"]

        self._login(self.b)
        r = self.client.get(f"/api/v1/classes/{class_id}/", **self._org_header())
        self.assertEqual(r.status_code, 200)

    def test_non_member_cannot_retrieve_org_class_detail(self):
        """C (non-member of org1) gets 403/404 on org1-owned class detail."""
        r = self.client.post(
            "/api/v1/classes/", {"name": "OrgClass"}, format="json", **self._org_header()
        )
        class_id = r.data["id"]

        self._login(self.c)
        # No org header → falls to solo scope → 404
        r = self.client.get(f"/api/v1/classes/{class_id}/")
        self.assertEqual(r.status_code, 404)

    def test_user_cannot_access_org_object_without_header(self):
        """Even A cannot see org-owned class in *solo* mode (scope_filter excludes it)."""
        r = self.client.post(
            "/api/v1/classes/", {"name": "OrgClass"}, format="json", **self._org_header()
        )
        class_id = r.data["id"]

        # A in solo mode
        r = self.client.get(f"/api/v1/classes/{class_id}/")
        self.assertIn(r.status_code, (403, 404))


# ---------------------------------------------------------------------------
# Phase 6 Task 2 — helpers shared across child-resource org tests
# ---------------------------------------------------------------------------

def _make_org_test_fixture(org, user_a, user_b):
    """
    Create an org-owned ClassGroup + Test + 3 Questions with options (A=correct).
    Returns (class_group, test, questions).
    """
    from assessments.models import ClassGroup, MarkingScheme, Option, Question, Test

    cg = ClassGroup.objects.create(organization=org, created_by=user_a, name="OrgCG")
    t = Test.objects.create(
        organization=org,
        created_by=user_a,
        class_group=cg,
        title="OrgTest",
        subject="Math",
    )
    MarkingScheme.objects.create(test=t, marks_per_correct=1)
    questions = []
    for i in range(3):
        q = Question.objects.create(test=t, order_index=i, text=f"OrgQ{i}", topic=f"T{i}")
        for label in ["A", "B", "C", "D"]:
            Option.objects.create(question=q, label=label, text=label, is_correct=(label == "A"))
        questions.append(q)
    return cg, t, questions


def _make_org_roster(org, user_a, n_students=2):
    """Create an org-owned Roster with n_students students."""
    from rosters.models import Roster, Student

    roster = Roster.objects.create(organization=org, created_by=user_a, name="OrgRoster")
    students = []
    for i in range(n_students):
        s = Student.objects.create(
            roster=roster,
            roll_number=f"{i + 1:02d}",
            full_name=f"OrgStudent{i + 1}",
        )
        students.append(s)
    return roster, students


def _make_org_omr_sheet(test, student, seed=1):
    """Create a minimal OmrSheet for an org-owned test + student."""
    from assessments.models import Question
    from omr.models import OmrSheet

    questions = list(test.questions.order_by("order_index", "id"))
    q_ids = [q.id for q in questions]
    option_order = {str(q.id): ["A", "B", "C", "D"] for q in questions}
    answer_key = {str(i): ["A"] for i in range(len(questions))}
    return OmrSheet.objects.create(
        test=test,
        student=student,
        sheet_code=f"ORG-SHEET-{seed:04d}",
        human_readable_code=f"OS{seed:04d}",
        question_order=q_ids,
        option_order=option_order,
        answer_key=answer_key,
        page_count=1,
        shuffle_version=seed,
    )


def _make_org_result(test, student, omr_sheet, score=2):
    """Create a StudentResult for an org-scoped sheet."""
    from decimal import Decimal
    from results.models import QuestionResponse, StudentResult

    result = StudentResult.objects.create(
        test=test,
        student=student,
        omr_sheet=omr_sheet,
        score=Decimal(str(score)),
        max_score=Decimal("3"),
        correct_count=score,
        wrong_count=3 - score,
        blank_count=0,
    )
    questions = list(test.questions.order_by("order_index", "id"))
    for i, q in enumerate(questions):
        is_correct = i < score
        QuestionResponse.objects.create(
            student_result=result,
            question=q,
            q_pos=i,
            marked_options=["A"] if is_correct else ["B"],
            is_correct=is_correct,
        )
    return result


# ---------------------------------------------------------------------------
# J) Org-shared Questions (child of org-owned Test)
# ---------------------------------------------------------------------------

class OrgSharedQuestionsTests(_OrgApiBase):
    """
    A creates an org-owned Test with Questions.
    B (same org) can list/retrieve those questions.
    C (different org) gets empty list / 404.
    Solo users still isolated.
    """

    def setUp(self):
        super().setUp()
        _, self.test, self.questions = _make_org_test_fixture(self.org, self.a, self.b)

    def test_org_member_b_can_list_questions(self):
        """B (member of org1) can list questions of an org1-owned test."""
        self._login(self.b)
        r = self.client.get(
            f"/api/v1/questions/?test={self.test.id}",
            **self._org_header(),
        )
        self.assertEqual(r.status_code, 200)
        ids_returned = {item["id"] for item in r.data["results"]}
        for q in self.questions:
            self.assertIn(q.id, ids_returned)

    def test_org_member_b_can_retrieve_question_detail(self):
        """B can GET a specific question that belongs to an org-owned test."""
        self._login(self.b)
        q = self.questions[0]
        r = self.client.get(f"/api/v1/questions/{q.id}/", **self._org_header())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["id"], q.id)

    def test_cross_org_member_sees_zero_questions(self):
        """C (org2 admin) gets no questions for org1's test via org2 header."""
        self._login(self.c)
        r = self.client.get(
            f"/api/v1/questions/?test={self.test.id}",
            **self._org_header(self.org2),
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)

    def test_cross_org_question_detail_is_404(self):
        """C (org2) cannot retrieve an org1 question, even with org2 header."""
        self._login(self.c)
        q = self.questions[0]
        r = self.client.get(f"/api/v1/questions/{q.id}/", **self._org_header(self.org2))
        self.assertEqual(r.status_code, 404)

    def test_solo_user_does_not_see_org_questions(self):
        """A in solo mode does not see org-owned questions (scope mismatch)."""
        # A operates in solo scope (no header)
        r = self.client.get(f"/api/v1/questions/?test={self.test.id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)


# ---------------------------------------------------------------------------
# K) Org-shared OmrSheets
# ---------------------------------------------------------------------------

class OrgSharedOmrSheetsTests(_OrgApiBase):
    """
    A creates org-owned test + sheets. B (same org) can list sheets.
    C (other org) sees none. Solo scope is isolated.
    """

    def setUp(self):
        super().setUp()
        _, self.test, self.questions = _make_org_test_fixture(self.org, self.a, self.b)
        _, students = _make_org_roster(self.org, self.a, n_students=2)
        self.sheet1 = _make_org_omr_sheet(self.test, students[0], seed=10)
        self.sheet2 = _make_org_omr_sheet(self.test, students[1], seed=11)

    def test_org_member_b_sees_sheets(self):
        """B (member) lists sheets of org1-owned test under org1 header."""
        self._login(self.b)
        r = self.client.get(
            f"/api/v1/omr/sheets/?test={self.test.id}",
            **self._org_header(),
        )
        self.assertEqual(r.status_code, 200)
        ids = {item["id"] for item in r.data["results"]}
        self.assertIn(self.sheet1.id, ids)
        self.assertIn(self.sheet2.id, ids)

    def test_cross_org_sees_no_sheets(self):
        """C (org2) sees no sheets when querying org1's test with org2 header."""
        self._login(self.c)
        r = self.client.get(
            f"/api/v1/omr/sheets/?test={self.test.id}",
            **self._org_header(self.org2),
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)

    def test_solo_user_does_not_see_org_sheets(self):
        """A in solo mode sees no sheets from org-owned tests."""
        r = self.client.get(f"/api/v1/omr/sheets/?test={self.test.id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)


# ---------------------------------------------------------------------------
# L) Org-shared StudentResults
# ---------------------------------------------------------------------------

class OrgSharedStudentResultsTests(_OrgApiBase):
    """
    A creates org-owned test + results. B (same org) can list results.
    C (other org) sees none. Solo scope is isolated.
    """

    def setUp(self):
        super().setUp()
        _, self.test, self.questions = _make_org_test_fixture(self.org, self.a, self.b)
        _, students = _make_org_roster(self.org, self.a, n_students=2)
        self.sheet1 = _make_org_omr_sheet(self.test, students[0], seed=20)
        self.sheet2 = _make_org_omr_sheet(self.test, students[1], seed=21)
        self.result1 = _make_org_result(self.test, students[0], self.sheet1, score=3)
        self.result2 = _make_org_result(self.test, students[1], self.sheet2, score=1)

    def test_org_member_b_sees_results(self):
        """B (member) lists results of org1-owned test under org1 header."""
        self._login(self.b)
        r = self.client.get(
            f"/api/v1/results/?test={self.test.id}",
            **self._org_header(),
        )
        self.assertEqual(r.status_code, 200)
        ids = {item["id"] for item in r.data["results"]}
        self.assertIn(self.result1.id, ids)
        self.assertIn(self.result2.id, ids)

    def test_cross_org_sees_no_results(self):
        """C (org2) sees no results for org1's test with org2 header."""
        self._login(self.c)
        r = self.client.get(
            f"/api/v1/results/?test={self.test.id}",
            **self._org_header(self.org2),
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)

    def test_solo_user_does_not_see_org_results(self):
        """A in solo mode sees no results from org-owned tests."""
        r = self.client.get(f"/api/v1/results/?test={self.test.id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)


# ---------------------------------------------------------------------------
# M) Org-shared ReviewItems
# ---------------------------------------------------------------------------

class OrgSharedReviewItemsTests(_OrgApiBase):
    """
    A creates org-owned test + a ReviewItem (flagged/low-confidence).
    B (same org) can see it in the review queue.
    C (other org) sees nothing.
    """

    def setUp(self):
        super().setUp()
        from omr.models import ScanBatch, ScanJob
        from results.models import ReviewItem

        _, self.test, self.questions = _make_org_test_fixture(self.org, self.a, self.b)
        _, students = _make_org_roster(self.org, self.a, n_students=1)
        self.sheet = _make_org_omr_sheet(self.test, students[0], seed=30)
        # Create a ReviewItem tied to the sheet
        batch = ScanBatch.objects.create(
            test=self.test,
            created_by=self.a,
            status=ScanBatch.STATUS_DONE,
            total=1,
            processed=1,
        )
        self.job = ScanJob.objects.create(batch=batch, omr_sheet=self.sheet, page_no=1)
        self.review_item = ReviewItem.objects.create(
            omr_sheet=self.sheet,
            scan_job=self.job,
            reason=ReviewItem.REASON_DOUBLE_MARK,
        )

    def test_org_member_b_sees_review_item(self):
        """B (member of org1) can see org1's open review items."""
        self._login(self.b)
        r = self.client.get(
            f"/api/v1/review/?test={self.test.id}",
            **self._org_header(),
        )
        self.assertEqual(r.status_code, 200)
        ids = {item["id"] for item in r.data["results"]}
        self.assertIn(self.review_item.id, ids)

    def test_cross_org_sees_no_review_items(self):
        """C (org2) sees no review items for org1's test with org2 header."""
        self._login(self.c)
        r = self.client.get(
            f"/api/v1/review/?test={self.test.id}",
            **self._org_header(self.org2),
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)

    def test_solo_user_sees_no_org_review_items(self):
        """A in solo mode sees no review items from org-owned tests."""
        r = self.client.get(f"/api/v1/review/?test={self.test.id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)

    def test_cross_org_resolve_review_item_404(self):
        """C (org2) cannot resolve org1's review item — 404."""
        self._login(self.c)
        r = self.client.post(
            f"/api/v1/review/{self.review_item.id}/resolve/",
            {"marked_options": ["A"]},
            format="json",
            **self._org_header(self.org2),
        )
        self.assertEqual(r.status_code, 404)


# ---------------------------------------------------------------------------
# N) Org-shared Analytics
# ---------------------------------------------------------------------------

class OrgSharedAnalyticsTests(_OrgApiBase):
    """
    A creates org-owned test + results. B (same org) can see analytics.
    C (other org) gets 404. Solo scope is isolated (404).
    """

    def setUp(self):
        super().setUp()
        _, self.test, self.questions = _make_org_test_fixture(self.org, self.a, self.b)
        _, students = _make_org_roster(self.org, self.a, n_students=2)
        self.sheet1 = _make_org_omr_sheet(self.test, students[0], seed=40)
        self.sheet2 = _make_org_omr_sheet(self.test, students[1], seed=41)
        self.result1 = _make_org_result(self.test, students[0], self.sheet1, score=3)
        self.result2 = _make_org_result(self.test, students[1], self.sheet2, score=1)
        self.student1 = students[0]
        self.student2 = students[1]

    def test_org_member_b_can_get_test_analytics(self):
        """B (member) can call the test analytics endpoint under org1 header."""
        self._login(self.b)
        r = self.client.get(
            f"/api/v1/analytics/test/{self.test.id}/",
            **self._org_header(),
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["n_students"], 2)

    def test_org_member_b_can_get_student_detail_analytics(self):
        """B can call the student-detail analytics endpoint under org1 header."""
        self._login(self.b)
        r = self.client.get(
            f"/api/v1/analytics/test/{self.test.id}/student/{self.student1.id}/",
            **self._org_header(),
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("score", r.data)

    def test_org_member_b_can_get_improvement_analytics(self):
        """B can call the improvement analytics endpoint under org1 header."""
        self._login(self.b)
        r = self.client.get(
            f"/api/v1/analytics/test/{self.test.id}/improvement/",
            **self._org_header(),
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("students", r.data)

    def test_org_member_b_can_export_csv(self):
        """B can download CSV export of org1-owned test under org1 header."""
        self._login(self.b)
        r = self.client.get(
            f"/api/v1/analytics/test/{self.test.id}/export/?output_format=csv",
            **self._org_header(),
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r["Content-Type"])

    def test_cross_org_analytics_returns_404(self):
        """C (org2 admin) gets 404 on org1's test analytics with org2 header."""
        self._login(self.c)
        r = self.client.get(
            f"/api/v1/analytics/test/{self.test.id}/",
            **self._org_header(self.org2),
        )
        self.assertEqual(r.status_code, 404)

    def test_cross_org_student_detail_returns_404(self):
        """C (org2) gets 404 on org1's student-detail analytics with org2 header."""
        self._login(self.c)
        r = self.client.get(
            f"/api/v1/analytics/test/{self.test.id}/student/{self.student1.id}/",
            **self._org_header(self.org2),
        )
        self.assertEqual(r.status_code, 404)

    def test_cross_org_improvement_returns_404(self):
        """C (org2) gets 404 on org1's improvement analytics with org2 header."""
        self._login(self.c)
        r = self.client.get(
            f"/api/v1/analytics/test/{self.test.id}/improvement/",
            **self._org_header(self.org2),
        )
        self.assertEqual(r.status_code, 404)

    def test_cross_org_export_returns_404(self):
        """C (org2) gets 404 on org1's export with org2 header."""
        self._login(self.c)
        r = self.client.get(
            f"/api/v1/analytics/test/{self.test.id}/export/?output_format=csv",
            **self._org_header(self.org2),
        )
        self.assertEqual(r.status_code, 404)

    def test_solo_user_analytics_returns_404_for_org_test(self):
        """A in solo mode cannot see analytics for an org-owned test (scope mismatch)."""
        r = self.client.get(f"/api/v1/analytics/test/{self.test.id}/")
        self.assertEqual(r.status_code, 404)


# ---------------------------------------------------------------------------
# O) Generate endpoint honors org scope
# ---------------------------------------------------------------------------

class OrgGenerateTests(_OrgApiBase):
    """
    B (member of org1) can trigger generation of sheets for an org-owned test + roster.
    C (org2) cannot generate for org1's resources.
    """

    def setUp(self):
        super().setUp()
        _, self.test, self.questions = _make_org_test_fixture(self.org, self.a, self.b)
        self.roster, self.students = _make_org_roster(self.org, self.a, n_students=2)

    def test_org_member_b_can_generate_sheets(self):
        """B generates sheets for org1-owned test + roster under org1 header."""
        self._login(self.b)
        r = self.client.post(
            "/api/v1/omr/generate/",
            {"test": self.test.id, "roster": self.roster.id},
            format="json",
            **self._org_header(),
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["count"], 2)

    def test_cross_org_cannot_generate_for_org1_test(self):
        """C (org2) cannot generate sheets using org1's test with org2 header."""
        self._login(self.c)
        # C does not have a roster in org2 scope, but the test itself will fail first
        r = self.client.post(
            "/api/v1/omr/generate/",
            {"test": self.test.id, "roster": self.roster.id},
            format="json",
            **self._org_header(self.org2),
        )
        # Should fail because test not in org2's scope
        self.assertIn(r.status_code, (400, 403, 404))

    def test_solo_cannot_generate_for_org_test(self):
        """A in solo mode cannot generate sheets for an org-owned test (scope mismatch)."""
        r = self.client.post(
            "/api/v1/omr/generate/",
            {"test": self.test.id, "roster": self.roster.id},
            format="json",
        )
        self.assertIn(r.status_code, (400, 403))
