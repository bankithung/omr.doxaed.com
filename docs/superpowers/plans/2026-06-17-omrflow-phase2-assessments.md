# OMRFlow Phase 2 (Assessments core, solo scope) Implementation Plan

> Standalone repo at `projects/omr.doxaed.com/` (own `.git`), branch `phase-2`. Paths RELATIVE TO
> REPO ROOT (`backend/...`, `frontend/...`). Commit to THIS repo. TDD; `- [ ]` steps.

**Goal:** A solo user can create a Class, a Test (with MCQs, options, marking scheme) and a Retest,
all strictly scoped to them, via DRF endpoints + a React test-creation wizard.

**Architecture:** New models in the `assessments` app inheriting the Phase-0 `OwnerScopedModel`
(first concrete scoped models). A reusable `ScopedModelViewSet` (in `common`) filters every
queryset to `request.user` and stamps the owner on create. Flat REST endpoints via a DRF router;
MarkingScheme is nested-writable 1:1 on Test; Options are nested-writable on Question. Retest is a
custom action that deep-copies the parent test.

**Tech:** Django 5 + DRF (routers, nested writable serializers). React (Vite, JS) + shadcn (Stepper
wizard, custom Select, forms) + the existing `api`/`authApi` client.

## Locked decisions
- **D1** Endpoints: `/api/v1/classes/`, `/api/v1/tests/` (nested `marking_scheme`; `?class_group=` filter;
  `POST {id}/retest/` action), `/api/v1/questions/` (nested `options`; `?test=` filter). DRF `DefaultRouter`.
- **D2** `ScopedModelViewSet` (common) — solo scope: `get_queryset` filters `user=request.user`,
  `perform_create` stamps `user` (+ optional `created_by`). Org scope deferred to Phase 6.
- **D3** Cross-scope protection: serializers validate that any FK parent (`class_group` on Test,
  `test` on Question) belongs to the requesting user; otherwise 400.
- **D4** `MarkingScheme` 1:1 created/updated with its Test via nested writable serializer.
  `Question` created with its `options` via nested writable serializer.
- **D5** Retest = deep-copy: new Test with `parent_test=<orig>`, `attempt_number=orig.attempt_number+1`,
  same `class_group/title/subject/status=draft`, a copied MarkingScheme, and deep-copied Questions+Options.
- **D6** This is the FIRST concrete `OwnerScopedModel` subclass — VERIFY the inherited
  `CheckConstraint` lands in the migration and the DB rejects a no-scope/both-scope row (IntegrityError test).
- **D7** Images on Question/Option are optional `ImageField` (MEDIA configured in Phase 0); the wizard
  is text-only for MVP (image upload deferred), but the fields exist.

## File structure
- `backend/assessments/models.py` — ClassGroup, Test, MarkingScheme, Question, Option.
- `backend/common/viewsets.py` — `ScopedModelViewSet`.
- `backend/assessments/serializers.py` — ClassGroup/Test/MarkingScheme/Question/Option serializers.
- `backend/assessments/views.py` — ClassGroupViewSet, TestViewSet (+ retest action), QuestionViewSet.
- `backend/assessments/urls.py` — router; included from `config/urls.py`.
- `backend/assessments/tests_assessments.py` — model/constraint, scope-isolation, CRUD, marking, retest.
- Frontend: `frontend/src/api/assessments.js` (api helpers); `routes/Classes.jsx`, `routes/TestList.jsx`,
  `routes/TestWizard.jsx`; small components for question authoring.

---

## Task 1: Models + migration + DB-constraint test (TDD)
**Files:** `backend/assessments/models.py`, `backend/assessments/tests_assessments.py`, migration.

- [ ] **Step 1 (red): constraint + relationship tests.** Create `backend/assessments/tests_assessments.py`:
```python
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
```
- [ ] **Step 2:** Run `.\.venv\Scripts\python.exe manage.py test assessments` → FAIL (no models).
- [ ] **Step 3 (impl):** `backend/assessments/models.py`:
```python
from django.conf import settings
from django.db import models

from common.models import OwnerScopedModel


class ClassGroup(OwnerScopedModel):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # No Meta here: Django inherits OwnerScopedModel.Meta (the scope CheckConstraint) and makes
    # this model concrete (abstract reset to False). Constraint name resolves to
    # assessments_classgroup_exactly_one_scope.
    def __str__(self):
        return self.name


class Test(OwnerScopedModel):
    DRAFT, READY, CLOSED = "draft", "ready", "closed"
    STATUS_CHOICES = [(DRAFT, "Draft"), (READY, "Ready"), (CLOSED, "Closed")]

    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name="tests")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    title = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True)
    parent_test = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="retests")
    attempt_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=DRAFT)

    def __str__(self):
        return self.title


class MarkingScheme(models.Model):
    test = models.OneToOneField(Test, on_delete=models.CASCADE, related_name="marking_scheme")
    marks_per_correct = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    negative_marks_per_wrong = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    partial_marking = models.BooleanField(default=False)
    multiple_correct_allowed = models.BooleanField(default=False)


class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="questions")
    order_index = models.PositiveIntegerField(default=0)
    text = models.TextField()
    image = models.ImageField(upload_to="questions/", null=True, blank=True)
    topic = models.CharField(max_length=255, blank=True)
    difficulty = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["order_index", "id"]


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    label = models.CharField(max_length=4)
    text = models.CharField(max_length=500, blank=True)
    image = models.ImageField(upload_to="options/", null=True, blank=True)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["label", "id"]
```
- [ ] **Step 4:** `makemigrations assessments` then INSPECT the generated migration — confirm it contains a `CheckConstraint` named `assessments_classgroup_exactly_one_scope` and `assessments_test_exactly_one_scope`. (If the models came out abstract / no constraint, add `class Meta(OwnerScopedModel.Meta): pass` to ClassGroup and Test and regenerate.) Then `migrate`.
- [ ] **Step 5:** `manage.py test assessments` → PASS (3 tests). **Step 6:** commit `feat(assessments): ClassGroup/Test/MarkingScheme/Question/Option models`.

## Task 2: ScopedModelViewSet + Classes CRUD + scope isolation (TDD)
**Files:** `backend/common/viewsets.py`, `backend/assessments/serializers.py`, `views.py`, `urls.py`, `config/urls.py`, tests.

- [ ] **Step 1 (red):** add to tests_assessments.py (use DRF APITestCase + a NoThrottle base if needed):
```python
from rest_framework.test import APITestCase


class ClassApiTests(APITestCase):
    def setUp(self):
        self.a = User.objects.create_user(email="a@example.com", password="Str0ng!pass")
        self.b = User.objects.create_user(email="b@example.com", password="Str0ng!pass")
        self._auth(self.a)

    def _auth(self, user):
        r = self.client.post("/api/v1/auth/login/", {"email": user.email, "password": "Str0ng!pass"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def test_create_and_list_own_classes(self):
        r = self.client.post("/api/v1/classes/", {"name": "Class 8"}, format="json")
        self.assertEqual(r.status_code, 201)
        r = self.client.get("/api/v1/classes/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 1)

    def test_scope_isolation(self):
        self.client.post("/api/v1/classes/", {"name": "A-class"}, format="json")
        self._auth(self.b)  # switch to user B
        r = self.client.get("/api/v1/classes/")
        self.assertEqual(len(r.data["results"]), 0)  # B sees none of A's

    def test_requires_auth(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/v1/classes/").status_code, 401)
```
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3 (impl):** `backend/common/viewsets.py`:
```python
from rest_framework import viewsets

from common.permissions import IsInScope


class ScopedModelViewSet(viewsets.ModelViewSet):
    """Tenant-owned resources, solo scope. Filters to request.user and stamps the owner on create.
    Org scope (membership) arrives in Phase 6."""

    permission_classes = [IsInScope]
    owner_extra_fields = ()  # e.g. ("created_by",)

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        extra = {f: self.request.user for f in self.owner_extra_fields}
        serializer.save(user=self.request.user, **extra)
```
`backend/assessments/serializers.py` (ClassGroup first; others appended in later tasks):
```python
from rest_framework import serializers

from .models import ClassGroup


class ClassGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassGroup
        fields = ("id", "name", "description", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")
```
`backend/assessments/views.py`:
```python
from common.viewsets import ScopedModelViewSet

from .models import ClassGroup
from .serializers import ClassGroupSerializer


class ClassGroupViewSet(ScopedModelViewSet):
    queryset = ClassGroup.objects.all()
    serializer_class = ClassGroupSerializer
    owner_extra_fields = ("created_by",)
```
`backend/assessments/urls.py`:
```python
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("classes", views.ClassGroupViewSet, basename="class")

urlpatterns = router.urls
```
In `backend/config/urls.py`, add `path("api/v1/", include("assessments.urls"))` (keep existing routes).
- [ ] **Step 4:** run → PASS (3). **Step 5:** commit `feat(assessments): ScopedModelViewSet + classes CRUD (scope-isolated)`.

## Task 3: Test CRUD (nested marking) + retest (TDD)
**Files:** serializers.py, views.py, urls.py, tests.
- [ ] **Step 1 (red):** tests: create a test with marking under one's own class (201); cannot attach to another user's class (400/404); retest action creates a linked copy.
```python
class TestApiTests(ClassApiTests):  # reuse _auth/setup
    def _make_class(self):
        return self.client.post("/api/v1/classes/", {"name": "C"}, format="json").data["id"]

    def test_create_test_with_marking(self):
        cid = self._make_class()
        r = self.client.post("/api/v1/tests/", {
            "class_group": cid, "title": "T1", "subject": "Math",
            "marking_scheme": {"marks_per_correct": "2", "negative_marks_per_wrong": "0.5"},
        }, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["marking_scheme"]["marks_per_correct"], "2.00")

    def test_cannot_use_others_class(self):
        cid = self._make_class()
        self._auth(self.b)
        r = self.client.post("/api/v1/tests/", {"class_group": cid, "title": "X"}, format="json")
        self.assertIn(r.status_code, (400, 404))

    def test_retest_links_and_increments(self):
        cid = self._make_class()
        tid = self.client.post("/api/v1/tests/", {"class_group": cid, "title": "T1"}, format="json").data["id"]
        r = self.client.post(f"/api/v1/tests/{tid}/retest/")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["parent_test"], tid)
        self.assertEqual(r.data["attempt_number"], 2)
```
- [ ] **Step 2:** FAIL. **Step 3 (impl):** add serializers:
```python
from .models import Test, MarkingScheme


class MarkingSchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarkingScheme
        fields = ("marks_per_correct", "negative_marks_per_wrong", "partial_marking", "multiple_correct_allowed")


class TestSerializer(serializers.ModelSerializer):
    marking_scheme = MarkingSchemeSerializer(required=False)

    class Meta:
        model = Test
        fields = ("id", "class_group", "title", "subject", "parent_test", "attempt_number", "status",
                  "marking_scheme", "created_at", "updated_at")
        read_only_fields = ("id", "parent_test", "attempt_number", "created_at", "updated_at")

    def validate_class_group(self, value):
        user = self.context["request"].user
        if value.user_id != user.id:
            raise serializers.ValidationError("Class not found in your account.")
        return value

    def create(self, validated_data):
        marking = validated_data.pop("marking_scheme", None)
        test = Test.objects.create(**validated_data)
        MarkingScheme.objects.create(test=test, **(marking or {}))
        return test

    def update(self, instance, validated_data):
        marking = validated_data.pop("marking_scheme", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if marking is not None:
            ms, _ = MarkingScheme.objects.get_or_create(test=instance)
            for k, v in marking.items():
                setattr(ms, k, v)
            ms.save()
        return instance
```
views.py — TestViewSet:
```python
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Test
from .serializers import TestSerializer


class TestViewSet(ScopedModelViewSet):
    queryset = Test.objects.all()
    serializer_class = TestSerializer
    owner_extra_fields = ("created_by",)

    def get_queryset(self):
        qs = super().get_queryset()
        cg = self.request.query_params.get("class_group")
        return qs.filter(class_group_id=cg) if cg else qs

    @action(detail=True, methods=["post"])
    def retest(self, request, pk=None):
        original = self.get_object()
        clone = Test.objects.create(
            user=request.user, created_by=request.user, class_group=original.class_group,
            title=original.title, subject=original.subject, parent_test=original,
            attempt_number=original.attempt_number + 1, status=Test.DRAFT,
        )
        ms = getattr(original, "marking_scheme", None)
        if ms:
            MarkingScheme.objects.create(
                test=clone, marks_per_correct=ms.marks_per_correct,
                negative_marks_per_wrong=ms.negative_marks_per_wrong,
                partial_marking=ms.partial_marking, multiple_correct_allowed=ms.multiple_correct_allowed)
        for q in original.questions.all():
            nq = Question.objects.create(test=clone, order_index=q.order_index, text=q.text,
                                         topic=q.topic, difficulty=q.difficulty)
            for o in q.options.all():
                Option.objects.create(question=nq, label=o.label, text=o.text, is_correct=o.is_correct)
        return Response(self.get_serializer(clone).data, status=201)
```
(Import Question/Option/MarkingScheme in views.) Register in urls.py router: `router.register("tests", views.TestViewSet, basename="test")`.
- [ ] **Step 4:** PASS. **Step 5:** commit `feat(assessments): test CRUD with marking scheme + retest deep-copy`.

## Task 4: Question + Option authoring (nested) + scope-by-test (TDD)
**Files:** serializers.py, views.py, urls.py, tests.
- [ ] **Step 1 (red):** create a question with options under one's own test; can't under another's test; list filtered by `?test=`.
```python
class QuestionApiTests(ClassApiTests):
    def _make_test(self):
        cid = self.client.post("/api/v1/classes/", {"name": "C"}, format="json").data["id"]
        return self.client.post("/api/v1/tests/", {"class_group": cid, "title": "T"}, format="json").data["id"]

    def test_create_question_with_options(self):
        tid = self._make_test()
        r = self.client.post("/api/v1/questions/", {
            "test": tid, "order_index": 0, "text": "2+2?",
            "options": [{"label": "A", "text": "3"}, {"label": "B", "text": "4", "is_correct": True}],
        }, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["options"]), 2)

    def test_cannot_add_to_others_test(self):
        tid = self._make_test()
        self._auth(self.b)
        r = self.client.post("/api/v1/questions/", {"test": tid, "text": "x", "options": []}, format="json")
        self.assertIn(r.status_code, (400, 404))
```
- [ ] **Step 2:** FAIL. **Step 3 (impl):** serializers:
```python
from .models import Question, Option


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ("id", "label", "text", "is_correct")
        read_only_fields = ("id",)


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True)

    class Meta:
        model = Question
        fields = ("id", "test", "order_index", "text", "topic", "difficulty", "options")
        read_only_fields = ("id",)

    def validate_test(self, value):
        user = self.context["request"].user
        if value.user_id != user.id:
            raise serializers.ValidationError("Test not found in your account.")
        return value

    def create(self, validated_data):
        options = validated_data.pop("options", [])
        q = Question.objects.create(**validated_data)
        for o in options:
            Option.objects.create(question=q, **o)
        return q

    def update(self, instance, validated_data):
        options = validated_data.pop("options", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if options is not None:
            instance.options.all().delete()
            for o in options:
                Option.objects.create(question=instance, **o)
        return instance
```
views.py:
```python
from rest_framework import viewsets
from .models import Question
from .serializers import QuestionSerializer


class QuestionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsInScope]   # import from common.permissions
    serializer_class = QuestionSerializer

    def get_queryset(self):
        qs = Question.objects.filter(test__user=self.request.user)
        test_id = self.request.query_params.get("test")
        return qs.filter(test_id=test_id) if test_id else qs
```
(import `from common.permissions import IsInScope` in views.) urls: `router.register("questions", views.QuestionViewSet, basename="question")`.
- [ ] **Step 4:** PASS. Run FULL backend suite (Phase 0+1+2). **Step 5:** commit `feat(assessments): question + option authoring (scope-by-test)`.

## Task 5: Frontend — Classes + Test list
**Files:** `frontend/src/api/assessments.js`, `routes/Classes.jsx`, `routes/TestList.jsx`, App.jsx routes (protected).
- `assessments.js`: helpers `listClasses/createClass/listTests({class_group})/createTest/retest/listQuestions/createQuestion` using `api`.
- **Classes.jsx** (protected): list user's classes (DataTable/cards), a "Create class" modal (shadcn Dialog + form). Click a class → `/classes/:id` test list.
- **TestList.jsx** (protected): tests in a class; "Create test" → navigates to the wizard; each test row shows status + a "Retest" action (calls retest, shows the new draft).
- Wire protected routes `/classes`, `/classes/:id`; add a nav link "Classes" when logged in.
- [ ] Build clean; commit `feat(assessments): classes + test list UI`.

## Task 6: Frontend — Test creation wizard + question authoring
**Files:** `routes/TestWizard.jsx`, a `QuestionEditor` component, App.jsx route.
- **TestWizard.jsx** (protected, route `/classes/:classId/tests/new`): a shadcn **Stepper** with 3 steps:
  1. Details — title, subject, marking scheme (marks per correct, negative marks, toggles for partial /
     multiple-correct using shadcn Switch). Creates the Test (draft) via `createTest`.
  2. Questions — add MCQs: each question has text + 2–6 options (add/remove), mark correct option(s)
     (radio if single-correct, checkboxes if multiple-correct allowed), via `createQuestion`.
  3. Review — list questions; "Finish" sets the test ready (PATCH status) and navigates to the test list.
- Custom components only (no native select/alert/confirm); errors via toast.
- [ ] Build clean; commit `feat(assessments): test creation wizard + question authoring`.

## Task 7: Phase 2 wrap-up + review + merge
- [ ] Full backend suite + check + frontend build green.
- [ ] Update memory (Phase 2 done, next Phase 3) + progress-log + MEMORY status; commit.
- [ ] Phase review (scope isolation holds; constraint enforced; retest correct); merge `phase-2` → `main`.

## Self-review
- Coverage: ClassGroup/Test/Question/Option/MarkingScheme models ✓(T1); scoped CRUD + isolation ✓(T2-4);
  retest ✓(T3); marking ✓(T3); first concrete scope-constraint validated ✓(T1,D6); wizard UI ✓(T5-6).
- Consistency: `ScopedModelViewSet`, `owner_extra_fields`, serializer `validate_class_group`/`validate_test`,
  nested `marking_scheme`/`options`, router basenames all consistent.
