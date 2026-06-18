from django.core import mail
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from unittest import mock

from django.test import override_settings

from accounts.tokens import make_uid_token

User = get_user_model()


# Base class that clears the Django cache before each test so DRF throttle
# counts and axes lockout state don't accumulate across test cases.
class NoThrottleTestCase(APITestCase):
    def _pre_setup(self):
        cache.clear()
        super()._pre_setup()

    def setUp(self):
        # Also reset axes access-attempt records between tests.
        try:
            from axes.utils import reset
            reset()
        except Exception:
            pass


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

    def test_register_duplicate_email_no_enumeration(self):
        """Duplicate email must NOT 400-leak. Returns same 201 + sends 'account exists' email."""
        User.objects.create_user(email="dup@example.com", password="x12345!!")
        mail.outbox.clear()
        resp = self.client.post("/api/v1/auth/register/", {
            "email": "dup@example.com", "password": "Str0ng!pass",
        }, format="json")
        # Same status code as a fresh signup (no enumeration)
        self.assertEqual(resp.status_code, 201)
        # No second user created
        self.assertEqual(User.objects.filter(email="dup@example.com").count(), 1)
        # Existing user receives a notification email
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("already have an OMRFlow account", mail.outbox[0].subject)

    def test_register_returns_detail_message(self):
        resp = self.client.post("/api/v1/auth/register/", {
            "email": "msg@example.com", "password": "Str0ng!pass",
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertIn("detail", resp.data)


class VerifyEmailTests(NoThrottleTestCase):
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

    def test_verify_email_throttle(self):
        """The 11th verify-email request in a minute must be rate-limited (429)."""
        u = User.objects.create_user(email="throttle@example.com", password="Str0ng!pass")
        uid, token = make_uid_token(u)
        cache.clear()
        for _ in range(10):
            self.client.post(
                "/api/v1/auth/verify-email/", {"uid": uid, "token": "bad"}, format="json"
            )
        resp = self.client.post(
            "/api/v1/auth/verify-email/", {"uid": uid, "token": "bad"}, format="json"
        )
        self.assertEqual(resp.status_code, 429)


class LoginTests(NoThrottleTestCase):
    def setUp(self):
        super().setUp()
        self.u = User.objects.create_user(email="l@example.com", password="Str0ng!pass", full_name="L")

    def test_login_ok(self):
        resp = self.client.post("/api/v1/auth/login/", {"email": "l@example.com", "password": "Str0ng!pass"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data); self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["user"]["email"], "l@example.com")

    def test_login_bad_creds_401(self):
        resp = self.client.post("/api/v1/auth/login/", {"email": "l@example.com", "password": "nope"}, format="json")
        self.assertEqual(resp.status_code, 401)


class AxesLockoutTests(NoThrottleTestCase):
    """django-axes locks out after AXES_FAILURE_LIMIT consecutive failures."""

    def setUp(self):
        super().setUp()
        self.u = User.objects.create_user(email="locked@example.com", password="Str0ng!pass")

    def test_axes_lockout_after_failure_limit(self):
        """After AXES_FAILURE_LIMIT bad logins, the account is locked out."""
        from django.test import override_settings
        from django.conf import settings as django_settings

        limit = getattr(django_settings, "AXES_FAILURE_LIMIT", 5)

        # Send `limit` failed login attempts
        for i in range(limit):
            resp = self.client.post(
                "/api/v1/auth/login/",
                {"email": "locked@example.com", "password": "wrongpass"},
                format="json",
                REMOTE_ADDR="10.0.0.1",
            )
            # Each attempt before lockout should be 401
            if i < limit - 1:
                self.assertEqual(resp.status_code, 401, f"Attempt {i+1} should be 401")

        # The next attempt (limit+1) should be locked
        resp = self.client.post(
            "/api/v1/auth/login/",
            {"email": "locked@example.com", "password": "wrongpass"},
            format="json",
            REMOTE_ADDR="10.0.0.1",
        )
        self.assertIn(
            resp.status_code,
            [403, 429],
            f"Expected lockout (403 or 429) after {limit} failures, got {resp.status_code}",
        )

    def test_axes_reset_on_success(self):
        """A successful login resets the failure counter (AXES_RESET_ON_SUCCESS=True)."""
        from axes.utils import reset
        reset()

        # Fail twice
        for _ in range(2):
            self.client.post(
                "/api/v1/auth/login/",
                {"email": "locked@example.com", "password": "wrongpass"},
                format="json",
                REMOTE_ADDR="10.0.0.2",
            )
        # Succeed (resets counter)
        ok = self.client.post(
            "/api/v1/auth/login/",
            {"email": "locked@example.com", "password": "Str0ng!pass"},
            format="json",
            REMOTE_ADDR="10.0.0.2",
        )
        self.assertEqual(ok.status_code, 200)

        # Should still be unlocked (2 prior failures < limit; reset on success)
        resp = self.client.post(
            "/api/v1/auth/login/",
            {"email": "locked@example.com", "password": "wrongpass"},
            format="json",
            REMOTE_ADDR="10.0.0.2",
        )
        self.assertEqual(resp.status_code, 401)


class LogoutTests(NoThrottleTestCase):
    def setUp(self):
        super().setUp()
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


class PasswordResetTests(NoThrottleTestCase):
    def test_request_sends_email_for_existing_user(self):
        User.objects.create_user(email="p@example.com", password="Str0ng!pass")
        resp = self.client.post("/api/v1/auth/password-reset/", {"email": "p@example.com"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_request_unknown_email_still_200_no_email(self):
        resp = self.client.post("/api/v1/auth/password-reset/", {"email": "nobody@example.com"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_confirm_sets_new_password(self):
        u = User.objects.create_user(email="c@example.com", password="OldPass!123")
        uid, token = make_uid_token(u)
        resp = self.client.post("/api/v1/auth/password-reset-confirm/",
            {"uid": uid, "token": token, "new_password": "Brand!New9"}, format="json")
        self.assertEqual(resp.status_code, 200)
        u.refresh_from_db()
        self.assertTrue(u.check_password("Brand!New9"))

    def test_confirm_invalid_token_400(self):
        from accounts.tokens import make_uid_token
        u = User.objects.create_user(email="badtok@example.com", password="OldPass!123")
        uid, _ = make_uid_token(u)
        resp = self.client.post("/api/v1/auth/password-reset-confirm/",
            {"uid": uid, "token": "not-a-valid-token", "new_password": "Brand!New9"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_confirm_weak_password_400(self):
        from accounts.tokens import make_uid_token
        u = User.objects.create_user(email="weakpw@example.com", password="OldPass!123")
        uid, token = make_uid_token(u)
        resp = self.client.post("/api/v1/auth/password-reset-confirm/",
            {"uid": uid, "token": token, "new_password": "password"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("new_password", resp.data)


class MeTests(NoThrottleTestCase):
    def setUp(self):
        super().setUp()
        self.u = User.objects.create_user(email="m@example.com", password="Str0ng!pass", full_name="Me")
        r = self.client.post("/api/v1/auth/login/", {"email": "m@example.com", "password": "Str0ng!pass"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def test_get_me(self):
        resp = self.client.get("/api/v1/auth/me/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["email"], "m@example.com")

    def test_patch_full_name(self):
        resp = self.client.patch("/api/v1/auth/me/", {"full_name": "Renamed"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.u.refresh_from_db()
        self.assertEqual(self.u.full_name, "Renamed")

    def test_me_requires_auth(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 401)


@override_settings(GOOGLE_CLIENT_ID="test-client-id.apps.googleusercontent.com")
class GoogleLoginTests(NoThrottleTestCase):
    """Sign in with Google — verify_oauth2_token is mocked so no network call."""

    URL = "/api/v1/auth/google/"
    PATCH = "accounts.views.google_id_token.verify_oauth2_token"

    def _idinfo(self, **over):
        info = {
            "email": "guser@example.com",
            "email_verified": True,
            "name": "Google User",
            "aud": "test-client-id.apps.googleusercontent.com",
            "iss": "accounts.google.com",
        }
        info.update(over)
        return info

    @override_settings(GOOGLE_CLIENT_ID="")
    def test_unconfigured_returns_503(self):
        resp = self.client.post(self.URL, {"id_token": "anything"}, format="json")
        self.assertEqual(resp.status_code, 503)
        self.assertIn("not configured", resp.data["detail"])

    def test_new_user_is_created_verified_and_gets_tokens(self):
        with mock.patch(self.PATCH, return_value=self._idinfo()):
            resp = self.client.post(self.URL, {"id_token": "valid"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["user"]["email"], "guser@example.com")
        user = User.objects.get(email="guser@example.com")
        self.assertTrue(user.is_email_verified)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.full_name, "Google User")

    def test_existing_user_is_linked_not_duplicated(self):
        existing = User.objects.create_user(
            email="guser@example.com", password="Str0ng!pass", full_name="Local Name"
        )
        with mock.patch(self.PATCH, return_value=self._idinfo()):
            resp = self.client.post(self.URL, {"id_token": "valid"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["user"]["email"], "guser@example.com")
        # No duplicate user, and the original password still works (link, not reset).
        self.assertEqual(User.objects.filter(email__iexact="guser@example.com").count(), 1)
        existing.refresh_from_db()
        self.assertTrue(existing.check_password("Str0ng!pass"))
        self.assertTrue(existing.is_email_verified)

    def test_existing_user_matched_case_insensitively(self):
        User.objects.create_user(email="MixedCase@Example.com", password="Str0ng!pass")
        with mock.patch(self.PATCH, return_value=self._idinfo(email="mixedcase@example.com")):
            resp = self.client.post(self.URL, {"id_token": "valid"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(User.objects.filter(email__iexact="mixedcase@example.com").count(), 1)

    def test_invalid_token_returns_400(self):
        with mock.patch(self.PATCH, side_effect=ValueError("bad token")):
            resp = self.client.post(self.URL, {"id_token": "bogus"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_unverified_google_email_returns_400(self):
        with mock.patch(self.PATCH, return_value=self._idinfo(email_verified=False)):
            resp = self.client.post(self.URL, {"id_token": "valid"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_missing_id_token_returns_400(self):
        resp = self.client.post(self.URL, {}, format="json")
        self.assertEqual(resp.status_code, 400)
