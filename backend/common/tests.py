from django.core.exceptions import ValidationError
from django.test import TestCase

from common.models import OwnerScopedModel
from common.permissions import IsInScope


class HealthEndpointTests(TestCase):
    def test_health_returns_ok(self):
        resp = self.client.get("/api/v1/health/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["db"], "ok")


class NativeLibImportTests(TestCase):
    """Phase 0 de-risk: confirm the OMR/CV native wheels import on Win + Py3.13.

    These libs are not USED until Phases 3-4, but a failed import then would block the
    riskiest phase. Importing here surfaces any native-DLL problem now.
    """

    def test_cv_and_pdf_libs_import(self):
        import cv2  # noqa: F401  (OpenCV)
        import numpy  # noqa: F401
        import pyzbar.pyzbar  # noqa: F401  (QR decode; bundles zbar DLL on Windows)
        import fitz  # noqa: F401  (PyMuPDF; multi-page PDF split)
        import reportlab  # noqa: F401  (OMR PDF generation)
        from PIL import Image  # noqa: F401
        import qrcode  # noqa: F401  (QR encode)


class OwnerScopeCleanTests(TestCase):
    """Tests the XOR scope rule in OwnerScopedModel.clean(). We call clean() against
    lightweight stand-ins because no concrete scoped model exists until Phase 2;
    clean() only reads self.user_id / self.organization_id."""

    def _row(self, user_id=None, organization_id=None):
        return type("Row", (), {"user_id": user_id, "organization_id": organization_id})()

    def test_clean_rejects_no_scope(self):
        with self.assertRaises(ValidationError):
            OwnerScopedModel.clean(self._row())

    def test_clean_rejects_both_scopes(self):
        with self.assertRaises(ValidationError):
            OwnerScopedModel.clean(self._row(user_id=1, organization_id=1))

    def test_clean_accepts_user_only(self):
        OwnerScopedModel.clean(self._row(user_id=1))  # must not raise

    def test_clean_accepts_org_only(self):
        OwnerScopedModel.clean(self._row(organization_id=1))  # must not raise


class IsInScopePermissionTests(TestCase):
    def _request(self, user_id):
        return type("Req", (), {"user": type("U", (), {"id": user_id, "is_authenticated": True})()})()

    def _obj(self, user_id=None, org_id=None):
        return type("Obj", (), {"user_id": user_id, "organization_id": org_id})()

    def test_solo_owner_allowed(self):
        perm = IsInScope()
        self.assertTrue(perm.has_object_permission(self._request(5), None, self._obj(user_id=5)))

    def test_other_user_denied(self):
        perm = IsInScope()
        self.assertFalse(perm.has_object_permission(self._request(5), None, self._obj(user_id=9)))
