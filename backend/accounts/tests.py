from django.contrib.auth import get_user_model
from django.test import TestCase


class UserModelTests(TestCase):
    def test_create_user_with_email(self):
        User = get_user_model()
        user = User.objects.create_user(email="teacher@example.com", password="Str0ng!pass")
        self.assertEqual(user.email, "teacher@example.com")
        self.assertTrue(user.check_password("Str0ng!pass"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_email_verified)

    def test_email_is_required(self):
        User = get_user_model()
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="x")

    def test_create_superuser(self):
        User = get_user_model()
        admin = User.objects.create_superuser(email="admin@example.com", password="Str0ng!pass")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
