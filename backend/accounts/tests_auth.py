from django.core import mail
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from accounts.tokens import make_uid_token

User = get_user_model()


class RegisterTests(APITestCase):
    def test_register_creates_unverified_user_and_sends_email(self):
        resp = self.client.post("/api/v1/auth/register/", {
            "email": "new@example.com", "password": "Str0ng!pass", "full_name": "New User",
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        user = User.objects.get(email="new@example.com")
        self.assertFalse(user.is_email_verified)
        self.assertTrue(user.check_password("Str0ng!pass"))
        self.assertEqual(len(mail.outbox), 1)

    def test_register_duplicate_email_rejected(self):
        User.objects.create_user(email="dup@example.com", password="x12345!!")
        resp = self.client.post("/api/v1/auth/register/", {
            "email": "dup@example.com", "password": "Str0ng!pass",
        }, format="json")
        self.assertEqual(resp.status_code, 400)


class VerifyEmailTests(APITestCase):
    def test_verify_marks_user_verified(self):
        u = User.objects.create_user(email="v@example.com", password="Str0ng!pass")
        uid, token = make_uid_token(u)
        resp = self.client.post("/api/v1/auth/verify-email/", {"uid": uid, "token": token}, format="json")
        self.assertEqual(resp.status_code, 200)
        u.refresh_from_db(); self.assertTrue(u.is_email_verified)

    def test_verify_bad_token_400(self):
        u = User.objects.create_user(email="v2@example.com", password="Str0ng!pass")
        uid, _ = make_uid_token(u)
        resp = self.client.post("/api/v1/auth/verify-email/", {"uid": uid, "token": "bad"}, format="json")
        self.assertEqual(resp.status_code, 400)


class LoginTests(APITestCase):
    def setUp(self):
        self.u = User.objects.create_user(email="l@example.com", password="Str0ng!pass", full_name="L")

    def test_login_ok(self):
        resp = self.client.post("/api/v1/auth/login/", {"email": "l@example.com", "password": "Str0ng!pass"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data); self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["user"]["email"], "l@example.com")

    def test_login_bad_creds_401(self):
        resp = self.client.post("/api/v1/auth/login/", {"email": "l@example.com", "password": "nope"}, format="json")
        self.assertEqual(resp.status_code, 401)


class LogoutTests(APITestCase):
    def setUp(self):
        self.u = User.objects.create_user(email="o@example.com", password="Str0ng!pass")
        r = self.client.post("/api/v1/auth/login/", {"email": "o@example.com", "password": "Str0ng!pass"}, format="json")
        self.access, self.refresh = r.data["access"], r.data["refresh"]

    def test_logout_blacklists_refresh(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        resp = self.client.post("/api/v1/auth/logout/", {"refresh": self.refresh}, format="json")
        self.assertEqual(resp.status_code, 205)
        self.client.credentials()
        again = self.client.post("/api/v1/auth/token/refresh/", {"refresh": self.refresh}, format="json")
        self.assertEqual(again.status_code, 401)
