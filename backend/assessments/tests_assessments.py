from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from assessments.models import ClassGroup, Test, MarkingScheme, Question, Option

User = get_user_model()


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="t@example.com", password="Str0ng!pass")

    def test_scope_constraint_rejects_no_scope(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClassGroup.objects.create(created_by=self.user, name="C")  # no user/org → violates XOR

    def test_scope_constraint_rejects_both_scopes(self):
        from organizations.models import Organization
        org = Organization.objects.create(name="O", owner=self.user)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClassGroup.objects.create(created_by=self.user, name="C", user=self.user, organization=org)

    def test_create_class_test_question_option(self):
        c = ClassGroup.objects.create(created_by=self.user, name="Class 8", user=self.user)
        t = Test.objects.create(class_group=c, created_by=self.user, title="Test 1", subject="Math", user=self.user)
        MarkingScheme.objects.create(test=t, marks_per_correct=Decimal("2"))
        q = Question.objects.create(test=t, order_index=0, text="2+2?")
        Option.objects.create(question=q, label="A", text="3")
        Option.objects.create(question=q, label="B", text="4", is_correct=True)
        self.assertEqual(t.class_group, c)
        self.assertEqual(t.attempt_number, 1)
        self.assertEqual(q.options.count(), 2)
        self.assertEqual(t.marking_scheme.marks_per_correct, Decimal("2"))
