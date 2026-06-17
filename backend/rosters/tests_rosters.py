from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

User = get_user_model()


class RosterModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="model@example.com", password="Str0ng!pass")

    def test_full_name_encrypted_at_rest(self):
        from rosters.models import Roster, Student
        from django.db import connection
        r = Roster.objects.create(created_by=self.user, user=self.user, name="R")
        s = Student.objects.create(roster=r, full_name="Asha Devi", roll_number="12")
        with connection.cursor() as cur:
            cur.execute("SELECT full_name FROM rosters_student WHERE id=%s", [s.id])
            raw = cur.fetchone()[0]
        self.assertNotEqual(raw, "Asha Devi")          # stored ciphertext
        self.assertEqual(Student.objects.get(id=s.id).full_name, "Asha Devi")  # decrypts on read

    def test_roll_number_unique_within_roster(self):
        from rosters.models import Roster, Student
        r = Roster.objects.create(created_by=self.user, user=self.user, name="R2")
        Student.objects.create(roster=r, roll_number="01")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Student.objects.create(roster=r, roll_number="01")

    def test_same_roll_number_in_different_rosters_allowed(self):
        from rosters.models import Roster, Student
        r1 = Roster.objects.create(created_by=self.user, user=self.user, name="R3")
        r2 = Roster.objects.create(created_by=self.user, user=self.user, name="R4")
        Student.objects.create(roster=r1, roll_number="01")
        # Should not raise
        Student.objects.create(roster=r2, roll_number="01")

    def test_roster_scope_constraint_requires_scope(self):
        from rosters.models import Roster
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Roster.objects.create(created_by=self.user, name="NoScope")


class RosterApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.a = User.objects.create_user(email="a_roster@example.com", password="Str0ng!pass")
        self.b = User.objects.create_user(email="b_roster@example.com", password="Str0ng!pass")
        self._auth(self.a)

    def _auth(self, user):
        r = self.client.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": "Str0ng!pass"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    # ---- Roster CRUD ----

    def test_create_roster(self):
        r = self.client.post("/api/v1/rosters/", {"name": "Class 8 Math"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["name"], "Class 8 Math")

    def test_list_own_rosters(self):
        self.client.post("/api/v1/rosters/", {"name": "R1"}, format="json")
        self.client.post("/api/v1/rosters/", {"name": "R2"}, format="json")
        r = self.client.get("/api/v1/rosters/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 2)

    def test_roster_scope_isolation(self):
        cache.clear()
        self.client.post("/api/v1/rosters/", {"name": "A-roster"}, format="json")
        self._auth(self.b)
        r = self.client.get("/api/v1/rosters/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 0)

    def test_cross_tenant_roster_detail_404(self):
        cache.clear()
        rid = self.client.post("/api/v1/rosters/", {"name": "A"}, format="json").data["id"]
        self._auth(self.b)
        r = self.client.get(f"/api/v1/rosters/{rid}/")
        self.assertEqual(r.status_code, 404)

    def test_update_roster(self):
        rid = self.client.post("/api/v1/rosters/", {"name": "Old"}, format="json").data["id"]
        r = self.client.patch(f"/api/v1/rosters/{rid}/", {"name": "New"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["name"], "New")

    def test_delete_roster(self):
        rid = self.client.post("/api/v1/rosters/", {"name": "Temp"}, format="json").data["id"]
        r = self.client.delete(f"/api/v1/rosters/{rid}/")
        self.assertEqual(r.status_code, 204)

    def test_requires_auth(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/v1/rosters/").status_code, 401)

    # ---- Student CRUD ----

    def _make_roster(self, name="Roster"):
        return self.client.post("/api/v1/rosters/", {"name": name}, format="json").data["id"]

    def test_create_student(self):
        rid = self._make_roster()
        r = self.client.post(
            "/api/v1/students/",
            {"roster": rid, "full_name": "Alice", "roll_number": "01"},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["full_name"], "Alice")

    def test_list_students_filtered_by_roster(self):
        rid = self._make_roster()
        self.client.post("/api/v1/students/", {"roster": rid, "roll_number": "01"}, format="json")
        self.client.post("/api/v1/students/", {"roster": rid, "roll_number": "02"}, format="json")
        r = self.client.get(f"/api/v1/students/?roster={rid}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 2)

    def test_child_scope_student_detail_owner_200(self):
        rid = self._make_roster()
        sid = self.client.post(
            "/api/v1/students/",
            {"roster": rid, "roll_number": "01"},
            format="json",
        ).data["id"]
        r = self.client.get(f"/api/v1/students/{sid}/")
        self.assertEqual(r.status_code, 200)

    def test_child_scope_student_detail_cross_tenant_404(self):
        cache.clear()
        rid = self._make_roster()
        sid = self.client.post(
            "/api/v1/students/",
            {"roster": rid, "roll_number": "01"},
            format="json",
        ).data["id"]
        self._auth(self.b)
        r = self.client.get(f"/api/v1/students/{sid}/")
        self.assertEqual(r.status_code, 404)

    def test_cannot_create_student_for_other_users_roster(self):
        cache.clear()
        rid = self._make_roster("A-Roster")
        self._auth(self.b)
        r = self.client.post(
            "/api/v1/students/",
            {"roster": rid, "roll_number": "01"},
            format="json",
        )
        self.assertIn(r.status_code, (400, 403, 404))

    def test_duplicate_roll_number_in_same_roster_rejected(self):
        rid = self._make_roster()
        self.client.post("/api/v1/students/", {"roster": rid, "roll_number": "01"}, format="json")
        r = self.client.post("/api/v1/students/", {"roster": rid, "roll_number": "01"}, format="json")
        self.assertEqual(r.status_code, 400)

    # ---- add_count action ----

    def test_add_count_creates_n_students(self):
        rid = self._make_roster()
        r = self.client.post(f"/api/v1/rosters/{rid}/add_count/", {"count": 5}, format="json")
        self.assertEqual(r.status_code, 201)
        # Verify via student list
        rl = self.client.get(f"/api/v1/students/?roster={rid}")
        self.assertEqual(len(rl.data["results"]), 5)

    def test_add_count_roll_numbers_sequential(self):
        rid = self._make_roster()
        r = self.client.post(f"/api/v1/rosters/{rid}/add_count/", {"count": 3}, format="json")
        self.assertEqual(r.status_code, 201)
        rl = self.client.get(f"/api/v1/students/?roster={rid}")
        roll_numbers = sorted(s["roll_number"] for s in rl.data["results"])
        self.assertEqual(roll_numbers, ["1", "2", "3"])

    def test_add_count_cross_tenant_roster_404(self):
        cache.clear()
        rid = self._make_roster("A-count-roster")
        self._auth(self.b)
        r = self.client.post(f"/api/v1/rosters/{rid}/add_count/", {"count": 3}, format="json")
        self.assertEqual(r.status_code, 404)

    def test_add_count_requires_positive_count(self):
        rid = self._make_roster()
        r = self.client.post(f"/api/v1/rosters/{rid}/add_count/", {"count": 0}, format="json")
        self.assertEqual(r.status_code, 400)
