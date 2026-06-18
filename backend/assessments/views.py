from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.scope import scope_filter, scope_kwargs
from common.viewsets import ScopedModelViewSet

from .models import ClassGroup, MarkingScheme, Option, Question, Section, SectionMarkingScheme, Test
from .serializers import ClassGroupSerializer, QuestionSerializer, SectionSerializer, TestSerializer


class ClassGroupViewSet(ScopedModelViewSet):
    queryset = ClassGroup.objects.all()
    serializer_class = ClassGroupSerializer
    owner_extra_fields = ("created_by",)


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
        qs = Question.objects.filter(scope_filter(self.request, "test__"))
        test_id = self.request.query_params.get("test")
        return qs.filter(test_id=test_id) if test_id else qs


class SectionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SectionSerializer

    def get_queryset(self):
        qs = Section.objects.filter(
            scope_filter(self.request, "test__")
        ).select_related("marking_scheme")
        test_id = self.request.query_params.get("test")
        return qs.filter(test_id=test_id) if test_id else qs
