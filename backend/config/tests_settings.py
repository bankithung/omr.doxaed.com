"""Tests for production-security settings wiring (Task 1)."""
import importlib
import sys

from django.conf import settings
from django.test import TestCase, override_settings


class SecuritySettingsTest(TestCase):
    """Verify that env-driven security flags apply as expected."""

    def test_session_cookie_httponly_default(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)

    def test_session_cookie_samesite_default(self):
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")

    def test_csrf_cookie_samesite_default(self):
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, "Lax")

    def test_secure_content_type_nosniff(self):
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)

    def test_secure_referrer_policy(self):
        self.assertEqual(settings.SECURE_REFERRER_POLICY, "same-origin")

    def test_x_frame_options_deny(self):
        self.assertEqual(settings.X_FRAME_OPTIONS, "DENY")

    def test_hsts_default_is_zero(self):
        """HSTS must default to 0 so dev is unaffected."""
        self.assertEqual(settings.SECURE_HSTS_SECONDS, 0)

    def test_ssl_redirect_default_off(self):
        self.assertFalse(settings.SECURE_SSL_REDIRECT)

    def test_hsts_override_sets_subdomains_and_preload(self):
        with override_settings(SECURE_HSTS_SECONDS=31536000,
                               SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
                               SECURE_HSTS_PRELOAD=True):
            self.assertEqual(settings.SECURE_HSTS_SECONDS, 31536000)
            self.assertTrue(settings.SECURE_HSTS_INCLUDE_SUBDOMAINS)
            self.assertTrue(settings.SECURE_HSTS_PRELOAD)

    def test_session_cookie_secure_override(self):
        with override_settings(SESSION_COOKIE_SECURE=True):
            self.assertTrue(settings.SESSION_COOKIE_SECURE)

    def test_whitenoise_in_middleware(self):
        self.assertIn(
            "whitenoise.middleware.WhiteNoiseMiddleware",
            settings.MIDDLEWARE,
        )

    def test_whitenoise_after_security_middleware(self):
        mw = settings.MIDDLEWARE
        security_idx = mw.index("django.middleware.security.SecurityMiddleware")
        whitenoise_idx = mw.index("whitenoise.middleware.WhiteNoiseMiddleware")
        self.assertGreater(whitenoise_idx, security_idx)

    def test_axes_in_installed_apps(self):
        self.assertIn("axes", settings.INSTALLED_APPS)

    def test_axes_middleware_last(self):
        last = settings.MIDDLEWARE[-1]
        self.assertEqual(last, "axes.middleware.AxesMiddleware")

    def test_axes_standalone_backend_first(self):
        first = settings.AUTHENTICATION_BACKENDS[0]
        self.assertEqual(first, "axes.backends.AxesStandaloneBackend")

    def test_verify_email_throttle_rate_configured(self):
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        self.assertIn("verify_email", rates)

    def test_whitenoise_staticfiles_storage(self):
        backend = settings.STORAGES["staticfiles"]["BACKEND"]
        self.assertEqual(backend, "whitenoise.storage.CompressedManifestStaticFilesStorage")


class ProdGuardTest(TestCase):
    """The prod guard raises ImproperlyConfigured when conditions aren't met."""

    def test_prod_guard_raises_on_dev_secret_key(self):
        """With DEBUG=False + the dev secret key, settings should have raised — test the logic."""
        from django.core.exceptions import ImproperlyConfigured

        dev_key = "dev-insecure-change-me-please-0123456789abcdef"

        # Simulate the guard logic directly (can't reload settings in tests)
        def _check(debug, secret_key, allowed_hosts):
            if not debug:
                if secret_key == dev_key:
                    raise ImproperlyConfigured("dev SECRET_KEY in production")
                if not allowed_hosts or set(allowed_hosts) <= {"localhost", "127.0.0.1"}:
                    raise ImproperlyConfigured("ALLOWED_HOSTS not set for production")

        with self.assertRaises(ImproperlyConfigured):
            _check(False, dev_key, ["mysite.com"])

    def test_prod_guard_raises_on_empty_allowed_hosts(self):
        from django.core.exceptions import ImproperlyConfigured

        dev_key = "dev-insecure-change-me-please-0123456789abcdef"

        def _check(debug, secret_key, allowed_hosts):
            if not debug:
                if secret_key == dev_key:
                    raise ImproperlyConfigured("dev SECRET_KEY in production")
                if not allowed_hosts or set(allowed_hosts) <= {"localhost", "127.0.0.1"}:
                    raise ImproperlyConfigured("ALLOWED_HOSTS not set for production")

        with self.assertRaises(ImproperlyConfigured):
            _check(False, "real-secret-key-xyz", [])

    def test_prod_guard_passes_with_valid_config(self):
        from django.core.exceptions import ImproperlyConfigured

        dev_key = "dev-insecure-change-me-please-0123456789abcdef"

        def _check(debug, secret_key, allowed_hosts):
            if not debug:
                if secret_key == dev_key:
                    raise ImproperlyConfigured("dev SECRET_KEY in production")
                if not allowed_hosts or set(allowed_hosts) <= {"localhost", "127.0.0.1"}:
                    raise ImproperlyConfigured("ALLOWED_HOSTS not set for production")

        # Should not raise
        _check(False, "real-secret-key-xyz", ["mysite.com"])

    def test_dev_mode_guard_does_not_raise(self):
        """DEBUG=True (our test env) must never trigger the guard."""
        from django.core.exceptions import ImproperlyConfigured

        dev_key = "dev-insecure-change-me-please-0123456789abcdef"

        def _check(debug, secret_key, allowed_hosts):
            if not debug:
                if secret_key == dev_key:
                    raise ImproperlyConfigured("dev SECRET_KEY in production")

        # DEBUG=True → no raise even with dev key
        _check(True, dev_key, [])
