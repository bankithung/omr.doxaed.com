from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.scope import can_edit_class, scope_filter, scope_kwargs, visibility_q
from common.viewsets import ScopedModelViewSet

from .models import ClassGroup, MarkingScheme, Option, Question, Section, SectionMarkingScheme, Test
from .serializers import ClassGroupSerializer, QuestionSerializer, SectionSerializer, TestSerializer

_EDIT_DENIED = "You have view-only access to this folder; editing is not permitted."


class ClassGroupViewSet(ScopedModelViewSet):
    queryset = ClassGroup.objects.all()
    serializer_class = ClassGroupSerializer
    owner_extra_fields = ("created_by",)

    def get_queryset(self):
        qs = super().get_queryset().filter(
            visibility_q(self.request, "", "created_by")
        ).distinct()
        folder = self.request.query_params.get("folder")
        return qs.filter(folder_id=folder) if folder else qs

    def perform_update(self, serializer):
        # EDIT-rights gate: the class is itself the governing class.
        if not can_edit_class(self.request, serializer.instance):
            raise PermissionDenied(_EDIT_DENIED)
        serializer.save()

    def perform_destroy(self, instance):
        if not can_edit_class(self.request, instance):
            raise PermissionDenied(_EDIT_DENIED)
        instance.delete()


class TestViewSet(ScopedModelViewSet):
    queryset = Test.objects.all()
    serializer_class = TestSerializer
    owner_extra_fields = ("created_by",)

    def get_queryset(self):
        qs = super().get_queryset().filter(
            visibility_q(self.request, "class_group__", "created_by")
        ).distinct()
        cg = self.request.query_params.get("class_group")
        return qs.filter(class_group_id=cg) if cg else qs

    def perform_create(self, serializer):
        # Creating a test under a class requires EDIT rights on that class.
        cg = serializer.validated_data.get("class_group")
        if not can_edit_class(self.request, cg):
            raise PermissionDenied(_EDIT_DENIED)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        if not can_edit_class(self.request, serializer.instance.class_group):
            raise PermissionDenied(_EDIT_DENIED)
        serializer.save()

    def perform_destroy(self, instance):
        if not can_edit_class(self.request, instance.class_group):
            raise PermissionDenied(_EDIT_DENIED)
        instance.delete()

    @action(detail=True, methods=["post"])
    def retest(self, request, pk=None):
        original = self.get_object()
        if not can_edit_class(request, original.class_group):
            raise PermissionDenied(_EDIT_DENIED)
        clone = Test.objects.create(
            **scope_kwargs(request),
            created_by=request.user,
            class_group=original.class_group,
            title=original.title,
            subject=original.subject,
            parent_test=original,
            attempt_number=original.attempt_number + 1,
            status=Test.DRAFT,
        )
        ms = getattr(original, "marking_scheme", None)
        if ms:
            MarkingScheme.objects.create(
                test=clone,
                marks_per_correct=ms.marks_per_correct,
                negative_marks_per_wrong=ms.negative_marks_per_wrong,
                partial_marking=ms.partial_marking,
                multiple_correct_allowed=ms.multiple_correct_allowed,
            )
        for q in original.questions.all():
            nq = Question.objects.create(
                test=clone,
                order_index=q.order_index,
                text=q.text,
                image=q.image,
                topic=q.topic,
                difficulty=q.difficulty,
            )
            for o in q.options.all():
                Option.objects.create(
                    question=nq,
                    label=o.label,
                    text=o.text,
                    image=o.image,
                    is_correct=o.is_correct,
                )
        # Clone sections + their marking schemes (C3)
        for sec in original.sections.all():
            new_sec = Section.objects.create(
                test=clone,
                key=sec.key,
                label=sec.label,
                order_index=sec.order_index,
                q_start=sec.q_start,
                q_end=sec.q_end,
                policy=sec.policy,
                choose_k=sec.choose_k,
            )
            sms = getattr(sec, "marking_scheme", None)
            if sms is not None:
                SectionMarkingScheme.objects.create(
                    section=new_sec,
                    marks_per_correct=sms.marks_per_correct,
                    negative_marks_per_wrong=sms.negative_marks_per_wrong,
                    negative_kind=sms.negative_kind,
                    partial_marking=sms.partial_marking,
                    multiple_correct_allowed=sms.multiple_correct_allowed,
                    qualify_pct=sms.qualify_pct,
                )
            new_sec.sync_question_membership()
        return Response(self.get_serializer(clone).data, status=status.HTTP_201_CREATED)


class QuestionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionSerializer

    def get_queryset(self):
        qs = Question.objects.filter(
            scope_filter(self.request, "test__")
            & visibility_q(self.request, "test__class_group__", "test__created_by")
        ).distinct()
        test_id = self.request.query_params.get("test")
        return qs.filter(test_id=test_id) if test_id else qs

    def _gate_edit(self, test):
        if not can_edit_class(self.request, test.class_group):
            raise PermissionDenied(_EDIT_DENIED)

    def perform_create(self, serializer):
        # Question.test is validated for scope by the serializer; gate EDIT here.
        self._gate_edit(serializer.validated_data["test"])
        serializer.save()

    def perform_update(self, serializer):
        # Gate BOTH the source parent (existing) AND the destination parent: a
        # writable `test` FK would otherwise let a member with EDIT on the source
        # test re-parent this row into a test they can only VIEW (or cannot see).
        self._gate_edit(serializer.instance.test)
        new_test = serializer.validated_data.get("test", serializer.instance.test)
        self._gate_edit(new_test)
        serializer.save()

    def perform_destroy(self, instance):
        self._gate_edit(instance.test)
        instance.delete()


class SectionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SectionSerializer

    def get_queryset(self):
        qs = Section.objects.filter(
            scope_filter(self.request, "test__")
            & visibility_q(self.request, "test__class_group__", "test__created_by")
        ).select_related("marking_scheme").distinct()
        test_id = self.request.query_params.get("test")
        return qs.filter(test_id=test_id) if test_id else qs

    def _gate_edit(self, test):
        if not can_edit_class(self.request, test.class_group):
            raise PermissionDenied(_EDIT_DENIED)

    def perform_create(self, serializer):
        self._gate_edit(serializer.validated_data["test"])
        serializer.save()

    def perform_update(self, serializer):
        # Gate BOTH the source parent (existing) AND the destination parent: a
        # writable `test` FK would otherwise let a member with EDIT on the source
        # test re-parent this row into a test they can only VIEW (or cannot see).
        self._gate_edit(serializer.instance.test)
        new_test = serializer.validated_data.get("test", serializer.instance.test)
        self._gate_edit(new_test)
        serializer.save()

    def perform_destroy(self, instance):
        self._gate_edit(instance.test)
        instance.delete()
