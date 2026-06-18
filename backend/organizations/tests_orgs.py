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


# ---------------------------------------------------------------------------
# P) Org-shared Students (child of org-owned Roster) — StudentViewSet org scope
# ---------------------------------------------------------------------------

class OrgSharedStudentsTests(_OrgApiBase):
    """
    A creates an org-owned Roster + Student (via the org header).
    B (same org) can GET/list that student under the org header.
    C (different org) gets 404 / empty. A solo user (no header) gets 404 / empty.

    Covers the gap that hid the StudentViewSet org-scope bug.
    """

    def setUp(self):
        super().setUp()
        self.roster, self.students = _make_org_roster(self.org, self.a, n_students=2)
        self.student = self.students[0]

    def test_org_member_b_can_retrieve_org_student(self):
        """B (member of org1) can GET an org1-owned student detail under org1 header."""
        self._login(self.b)
        r = self.client.get(
            f"/api/v1/students/{self.student.id}/",
            **self._org_header(),
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["id"], self.student.id)

    def test_org_member_b_sees_student_in_roster_list(self):
        """B can list org1-owned students filtered by ?roster= under org1 header."""
        self._login(self.b)
        r = self.client.get(
            f"/api/v1/students/?roster={self.roster.id}",
            **self._org_header(),
        )
        self.assertEqual(r.status_code, 200)
        ids = {item["id"] for item in r.data["results"]}
        for s in self.students:
            self.assertIn(s.id, ids)

    def test_org_member_b_can_update_org_student(self):
        """B can PATCH an org1-owned student under org1 header."""
        self._login(self.b)
        r = self.client.patch(
            f"/api/v1/students/{self.student.id}/",
            {"full_name": "Renamed Student"},
            format="json",
            **self._org_header(),
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["full_name"], "Renamed Student")

    def test_cross_org_member_cannot_retrieve_org_student(self):
        """C (org2 admin) gets 404 on an org1-owned student, even with org2 header."""
        self._login(self.c)
        r = self.client.get(
            f"/api/v1/students/{self.student.id}/",
            **self._org_header(self.org2),
        )
        self.assertEqual(r.status_code, 404)

    def test_cross_org_member_sees_no_students_in_list(self):
        """C (org2) sees no org1 students in the ?roster= list with org2 header."""
        self._login(self.c)
        r = self.client.get(
            f"/api/v1/students/?roster={self.roster.id}",
            **self._org_header(self.org2),
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)

    def test_solo_user_cannot_retrieve_org_student(self):
        """A in solo mode (no header) gets 404 on an org-owned student."""
        r = self.client.get(f"/api/v1/students/{self.student.id}/")
        self.assertEqual(r.status_code, 404)

    def test_solo_user_sees_no_org_students_in_list(self):
        """A in solo mode (no header) sees no org-owned students in the list."""
        r = self.client.get(f"/api/v1/students/?roster={self.roster.id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)


# ===========================================================================
# Phase 6 Task 3 — Org management endpoints: create, invite, accept, members,
# roles, audit log.
# ===========================================================================

class _OrgMgmtBase(APITestCase):
    """Base for Task-3 management tests.

    Users:
      admin_user  — org admin
      member_user — org member
      outside_user — registered but NOT in org
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

        self.admin_user = User.objects.create_user(
            email="admin@mgmt.com", password="Str0ng!pass"
        )
        self.member_user = User.objects.create_user(
            email="member@mgmt.com", password="Str0ng!pass"
        )
        self.outside_user = User.objects.create_user(
            email="outside@mgmt.com", password="Str0ng!pass"
        )

        # Create org via the API so the setUp mirrors real usage.
        self._login(self.admin_user)
        r = self.client.post(
            "/api/v1/organizations/", {"name": "MgmtOrg"}, format="json"
        )
        self.assertEqual(r.status_code, 201, r.data)
        self.org_id = r.data["id"]

        # Manually add member_user as an active member.
        from organizations.models import Organization
        org = Organization.objects.get(pk=self.org_id)
        OrganizationMembership.objects.create(
            organization=org,
            user=self.member_user,
            role=OrganizationMembership.MEMBER,
            status=OrganizationMembership.ACTIVE,
        )

        # Grant the org an active Team subscription so the seat gate (free=1)
        # does not block invite/management tests (this org already has 2 members).
        from billing.models import Plan, Subscription
        team_plan, _ = Plan.objects.get_or_create(
            code=Plan.TEAM,
            defaults={
                "name": "Team",
                "price_inr": "500.00",
                "seat_limit": 50,
                "students_per_generation_limit": None,
                "generations_per_day_limit": None,
                "monthly_scan_limit": 5000,
            },
        )
        Subscription.objects.update_or_create(
            organization=org,
            defaults={"plan": team_plan, "status": Subscription.ACTIVE},
        )

    def _login(self, user):
        r = self.client.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": "Str0ng!pass"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


# ---------------------------------------------------------------------------
# P) Create org
# ---------------------------------------------------------------------------

class OrgCreateTests(_OrgMgmtBase):
    def test_create_org_returns_201_with_role(self):
        """Creating an org returns 201 and the creator's role is 'admin'."""
        self._login(self.admin_user)
        r = self.client.post(
            "/api/v1/organizations/", {"name": "NewOrg"}, format="json"
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["name"], "NewOrg")
        self.assertEqual(r.data["role"], "admin")

    def test_creator_is_active_admin_member(self):
        """After creation the creator is an active admin OrganizationMembership."""
        self._login(self.admin_user)
        r = self.client.post(
            "/api/v1/organizations/", {"name": "AnotherOrg"}, format="json"
        )
        org_id = r.data["id"]
        m = OrganizationMembership.objects.get(
            organization_id=org_id, user=self.admin_user
        )
        self.assertEqual(m.role, "admin")
        self.assertEqual(m.status, "active")

    def test_org_appears_in_list(self):
        """After creation the org shows up in GET /organizations/."""
        r = self.client.get("/api/v1/organizations/")
        self.assertEqual(r.status_code, 200)
        org_ids = [o["id"] for o in r.data]
        self.assertIn(self.org_id, org_ids)

    def test_create_org_missing_name_returns_400(self):
        self._login(self.admin_user)
        r = self.client.post("/api/v1/organizations/", {}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_audit_log_created_on_org_create(self):
        """org.created AuditLog entry is created when the org is created."""
        log = AuditLog.objects.filter(
            organization_id=self.org_id, action="org.created"
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.admin_user)


# ---------------------------------------------------------------------------
# Q) List orgs
# ---------------------------------------------------------------------------

class OrgListTests(_OrgMgmtBase):
    def test_member_sees_org_in_list(self):
        """member_user is an active member → org appears in their GET /organizations/."""
        self._login(self.member_user)
        r = self.client.get("/api/v1/organizations/")
        self.assertEqual(r.status_code, 200)
        org_ids = [o["id"] for o in r.data]
        self.assertIn(self.org_id, org_ids)

    def test_outside_user_does_not_see_org(self):
        """outside_user has no membership → empty list."""
        self._login(self.outside_user)
        r = self.client.get("/api/v1/organizations/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 0)

    def test_removed_member_does_not_see_org(self):
        """Removed members are not active → org disappears from list."""
        OrganizationMembership.objects.filter(
            organization_id=self.org_id, user=self.member_user
        ).update(status="removed")
        self._login(self.member_user)
        r = self.client.get("/api/v1/organizations/")
        self.assertEqual(r.status_code, 200)
        org_ids = [o["id"] for o in r.data]
        self.assertNotIn(self.org_id, org_ids)


# ---------------------------------------------------------------------------
# R) Invite + accept flow
# ---------------------------------------------------------------------------

class InviteAcceptTests(_OrgMgmtBase):
    def setUp(self):
        super().setUp()
        self.invite_email = "newbie@mgmt.com"
        self.newbie = User.objects.create_user(
            email=self.invite_email, password="Str0ng!pass"
        )

    def _invite(self, email=None, role="member"):
        self._login(self.admin_user)
        return self.client.post(
            f"/api/v1/organizations/{self.org_id}/invite/",
            {"email": email or self.invite_email, "role": role},
            format="json",
        )

    def test_admin_can_invite(self):
        """Admin can send an invitation → 201 + token in response."""
        r = self._invite()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertIn("token", r.data)

    def test_invite_creates_invitation_object(self):
        """An Invitation row is created after a successful invite."""
        self._invite()
        inv = Invitation.objects.filter(
            organization_id=self.org_id, email=self.invite_email
        ).first()
        self.assertIsNotNone(inv)
        self.assertIsNone(inv.accepted_at)

    def test_invite_sends_email(self):
        """Inviting sends an email to the invited address (console backend captured)."""
        from django.core import mail
        self._invite()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.invite_email, mail.outbox[0].to)
        self.assertIn("accept-invite", mail.outbox[0].body)

    def test_member_cannot_invite(self):
        """A member (not admin) cannot invite → 403."""
        self._login(self.member_user)
        r = self.client.post(
            f"/api/v1/organizations/{self.org_id}/invite/",
            {"email": "x@x.com", "role": "member"},
            format="json",
        )
        self.assertEqual(r.status_code, 403)

    def test_outside_user_cannot_invite(self):
        """An outside user (not a member at all) cannot invite → 403/404."""
        self._login(self.outside_user)
        r = self.client.post(
            f"/api/v1/organizations/{self.org_id}/invite/",
            {"email": "x@x.com", "role": "member"},
            format="json",
        )
        self.assertIn(r.status_code, (403, 404))

    def test_inviting_existing_active_member_returns_400(self):
        """Inviting an already-active member → 400."""
        r = self._invite(email=self.member_user.email)
        self.assertEqual(r.status_code, 400)

    def test_invite_creates_audit_log(self):
        """An AuditLog entry is created when an invitation is sent."""
        self._invite()
        log = AuditLog.objects.filter(
            organization_id=self.org_id, action="member.invited"
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.admin_user)

    def test_newbie_accepts_invitation_becomes_member(self):
        """Invited user accepts → active membership created, AuditLog added."""
        r = self._invite()
        token = r.data["token"]

        self._login(self.newbie)
        r = self.client.post(
            "/api/v1/invitations/accept/", {"token": token}, format="json"
        )
        self.assertEqual(r.status_code, 200, r.data)

        m = OrganizationMembership.objects.filter(
            organization_id=self.org_id, user=self.newbie
        ).first()
        self.assertIsNotNone(m)
        self.assertEqual(m.status, "active")

        log = AuditLog.objects.filter(
            organization_id=self.org_id, action="member.joined"
        ).first()
        self.assertIsNotNone(log)

    def test_accepted_member_sees_org_in_list(self):
        """After accepting, the org appears in the new member's /organizations/."""
        r = self._invite()
        token = r.data["token"]

        self._login(self.newbie)
        self.client.post("/api/v1/invitations/accept/", {"token": token}, format="json")

        r = self.client.get("/api/v1/organizations/")
        org_ids = [o["id"] for o in r.data]
        self.assertIn(self.org_id, org_ids)

    def test_wrong_email_user_accept_returns_403(self):
        """A user whose email doesn't match the invitation gets 403."""
        r = self._invite()
        token = r.data["token"]

        self._login(self.outside_user)
        r = self.client.post(
            "/api/v1/invitations/accept/", {"token": token}, format="json"
        )
        self.assertEqual(r.status_code, 403)

    def test_expired_token_returns_400(self):
        """An expired invitation returns 400."""
        self._invite()
        inv = Invitation.objects.filter(organization_id=self.org_id).first()
        inv.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        inv.save(update_fields=["expires_at"])

        self._login(self.newbie)
        r = self.client.post(
            "/api/v1/invitations/accept/",
            {"token": str(inv.token)},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_already_accepted_token_returns_400(self):
        """Re-accepting an already-accepted invitation → 400."""
        r = self._invite()
        token = r.data["token"]

        self._login(self.newbie)
        self.client.post("/api/v1/invitations/accept/", {"token": token}, format="json")
        # Second time:
        r = self.client.post("/api/v1/invitations/accept/", {"token": token}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_invalid_token_returns_400(self):
        """Garbage token → 400."""
        self._login(self.newbie)
        import uuid
        r = self.client.post(
            "/api/v1/invitations/accept/",
            {"token": str(uuid.uuid4())},
            format="json",
        )
        self.assertEqual(r.status_code, 400)


# ---------------------------------------------------------------------------
# S) Member list
# ---------------------------------------------------------------------------

class MemberListTests(_OrgMgmtBase):
    def test_admin_can_list_members(self):
        """Admin can GET /organizations/{id}/members/ → list of active memberships."""
        r = self.client.get(f"/api/v1/organizations/{self.org_id}/members/")
        self.assertEqual(r.status_code, 200)
        emails = [m["email"] for m in r.data]
        self.assertIn(self.admin_user.email, emails)
        self.assertIn(self.member_user.email, emails)

    def test_member_can_list_members(self):
        """A regular member can also list the members."""
        self._login(self.member_user)
        r = self.client.get(f"/api/v1/organizations/{self.org_id}/members/")
        self.assertEqual(r.status_code, 200)

    def test_outside_user_gets_403_or_404(self):
        """Non-member cannot list members."""
        self._login(self.outside_user)
        r = self.client.get(f"/api/v1/organizations/{self.org_id}/members/")
        self.assertIn(r.status_code, (403, 404))

    def test_nonexistent_org_returns_404(self):
        r = self.client.get("/api/v1/organizations/99999/members/")
        self.assertEqual(r.status_code, 404)


# ---------------------------------------------------------------------------
# T) Role changes + last-admin protection
# ---------------------------------------------------------------------------

class MemberRoleTests(_OrgMgmtBase):
    def test_admin_can_change_member_role(self):
        """Admin can promote member to admin via PATCH."""
        r = self.client.patch(
            f"/api/v1/organizations/{self.org_id}/members/{self.member_user.id}/",
            {"role": "admin"},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["role"], "admin")

        log = AuditLog.objects.filter(
            organization_id=self.org_id, action="member.role_changed"
        ).first()
        self.assertIsNotNone(log)

    def test_member_cannot_change_roles(self):
        """A member (not admin) cannot PATCH roles → 403."""
        self._login(self.member_user)
        r = self.client.patch(
            f"/api/v1/organizations/{self.org_id}/members/{self.admin_user.id}/",
            {"role": "member"},
            format="json",
        )
        self.assertEqual(r.status_code, 403)

    def test_cannot_demote_only_admin(self):
        """Cannot demote the sole admin to member → 400."""
        r = self.client.patch(
            f"/api/v1/organizations/{self.org_id}/members/{self.admin_user.id}/",
            {"role": "member"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        # Admin is still admin.
        m = OrganizationMembership.objects.get(
            organization_id=self.org_id, user=self.admin_user
        )
        self.assertEqual(m.role, "admin")

    def test_can_demote_admin_when_another_admin_exists(self):
        """Can demote admin when another admin exists."""
        # Promote member to admin first.
        self.client.patch(
            f"/api/v1/organizations/{self.org_id}/members/{self.member_user.id}/",
            {"role": "admin"},
            format="json",
        )
        # Now demote original admin.
        r = self.client.patch(
            f"/api/v1/organizations/{self.org_id}/members/{self.admin_user.id}/",
            {"role": "member"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)


# ---------------------------------------------------------------------------
# U) Remove member + last-admin protection
# ---------------------------------------------------------------------------

class MemberRemoveTests(_OrgMgmtBase):
    def test_admin_can_remove_member(self):
        """Admin can DELETE a member → status set to removed + audit log."""
        r = self.client.delete(
            f"/api/v1/organizations/{self.org_id}/members/{self.member_user.id}/"
        )
        self.assertEqual(r.status_code, 204)
        m = OrganizationMembership.objects.get(
            organization_id=self.org_id, user=self.member_user
        )
        self.assertEqual(m.status, "removed")

        log = AuditLog.objects.filter(
            organization_id=self.org_id, action="member.removed"
        ).first()
        self.assertIsNotNone(log)

    def test_member_cannot_remove_others(self):
        """A member cannot delete other members → 403."""
        self._login(self.member_user)
        r = self.client.delete(
            f"/api/v1/organizations/{self.org_id}/members/{self.admin_user.id}/"
        )
        self.assertEqual(r.status_code, 403)

    def test_cannot_remove_only_admin(self):
        """Cannot remove the sole active admin → 400."""
        r = self.client.delete(
            f"/api/v1/organizations/{self.org_id}/members/{self.admin_user.id}/"
        )
        self.assertEqual(r.status_code, 400)
        m = OrganizationMembership.objects.get(
            organization_id=self.org_id, user=self.admin_user
        )
        self.assertEqual(m.status, "active")

    def test_can_remove_admin_when_another_admin_exists(self):
        """Can remove admin when a second admin exists."""
        # Promote member to admin first.
        self.client.patch(
            f"/api/v1/organizations/{self.org_id}/members/{self.member_user.id}/",
            {"role": "admin"},
            format="json",
        )
        r = self.client.delete(
            f"/api/v1/organizations/{self.org_id}/members/{self.admin_user.id}/"
        )
        self.assertEqual(r.status_code, 204)

    def test_removed_member_no_longer_in_list(self):
        """After removal, the member no longer appears in the member list."""
        self.client.delete(
            f"/api/v1/organizations/{self.org_id}/members/{self.member_user.id}/"
        )
        r = self.client.get(f"/api/v1/organizations/{self.org_id}/members/")
        emails = [m["email"] for m in r.data]
        self.assertNotIn(self.member_user.email, emails)


# ---------------------------------------------------------------------------
# V) Audit log endpoint
# ---------------------------------------------------------------------------

class AuditLogEndpointTests(_OrgMgmtBase):
    def test_admin_can_get_audit_log(self):
        """Admin can GET /organizations/{id}/audit/ → list of AuditLog entries."""
        r = self.client.get(f"/api/v1/organizations/{self.org_id}/audit/")
        self.assertEqual(r.status_code, 200)
        # org.created was logged at creation time.
        results = r.data.get("results", r.data)
        actions = [entry["action"] for entry in results]
        self.assertIn("org.created", actions)

    def test_member_cannot_get_audit_log(self):
        """A plain member cannot see the audit log → 403."""
        self._login(self.member_user)
        r = self.client.get(f"/api/v1/organizations/{self.org_id}/audit/")
        self.assertEqual(r.status_code, 403)

    def test_outside_user_cannot_get_audit_log(self):
        """Non-member cannot get audit log → 403/404."""
        self._login(self.outside_user)
        r = self.client.get(f"/api/v1/organizations/{self.org_id}/audit/")
        self.assertIn(r.status_code, (403, 404))

    def test_audit_log_entries_newest_first(self):
        """Audit log is ordered newest-first."""
        # Trigger more entries.
        self.client.post(
            f"/api/v1/organizations/{self.org_id}/invite/",
            {"email": "x@x.com", "role": "member"},
            format="json",
        )
        r = self.client.get(f"/api/v1/organizations/{self.org_id}/audit/")
        results = r.data.get("results", r.data)
        if len(results) >= 2:
            from django.utils.dateparse import parse_datetime
            ts0 = parse_datetime(results[0]["created_at"])
            ts1 = parse_datetime(results[1]["created_at"])
            self.assertGreaterEqual(ts0, ts1)

    def test_nonexistent_org_audit_returns_404(self):
        r = self.client.get("/api/v1/organizations/99999/audit/")
        self.assertEqual(r.status_code, 404)


# ---------------------------------------------------------------------------
# W) Org branding endpoint (Phase 3c)
# ---------------------------------------------------------------------------

def _tiny_png_org():
    """Return a minimal valid 1x1 red PNG (67 bytes)."""
    import struct, zlib
    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


class OrgBrandingEndpointTests(_OrgMgmtBase):
    """GET + PUT /api/v1/organizations/<id>/branding/ — admin-only."""

    def test_admin_can_get_branding(self):
        """Admin can GET branding settings."""
        r = self.client.get(f"/api/v1/organizations/{self.org_id}/branding/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("default_sheet_heading", r.data)
        self.assertIn("logo", r.data)

    def test_admin_can_set_heading(self):
        """Admin can PUT a default_sheet_heading."""
        r = self.client.put(
            f"/api/v1/organizations/{self.org_id}/branding/",
            {"default_sheet_heading": "Sunrise Academy"},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["default_sheet_heading"], "Sunrise Academy")
        # Verify via GET
        r2 = self.client.get(f"/api/v1/organizations/{self.org_id}/branding/")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data["default_sheet_heading"], "Sunrise Academy")

    def test_admin_can_upload_logo(self):
        """Admin can PUT a logo image (multipart)."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        png = _tiny_png_org()
        logo = SimpleUploadedFile("org_logo.png", png, content_type="image/png")
        r = self.client.put(
            f"/api/v1/organizations/{self.org_id}/branding/",
            {"logo": logo, "default_sheet_heading": ""},
            format="multipart",
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(r.data.get("logo"), "Expected a non-empty logo URL")

    def test_non_admin_cannot_get_branding(self):
        """Plain member cannot access branding endpoint → 403."""
        self._login(self.member_user)
        r = self.client.get(f"/api/v1/organizations/{self.org_id}/branding/")
        self.assertEqual(r.status_code, 403)

    def test_non_admin_cannot_put_branding(self):
        """Plain member cannot update branding → 403."""
        self._login(self.member_user)
        r = self.client.put(
            f"/api/v1/organizations/{self.org_id}/branding/",
            {"default_sheet_heading": "Hack"},
            format="json",
        )
        self.assertEqual(r.status_code, 403)

    def test_non_member_cannot_access_branding(self):
        """Non-member → 403/404."""
        self._login(self.outside_user)
        r = self.client.get(f"/api/v1/organizations/{self.org_id}/branding/")
        self.assertIn(r.status_code, (403, 404))
