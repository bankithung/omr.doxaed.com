import json

from rest_framework import serializers

from common.logo_validators import validate_logo_image
from common.scope import parent_in_scope

from folders.models import Folder

from .models import (
    ClassGroup,
    MarkingScheme,
    Option,
    Question,
    Section,
    SectionMarkingScheme,
    Subject,
    Test,
)


class ClassGroupSerializer(serializers.ModelSerializer):
    folder = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ClassGroup
        fields = ("id", "name", "description", "folder", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_folder(self, value):
        if value is None:
            return value
        request = self.context["request"]
        # Folder must belong to the requester's active scope (solo or org).
        if not parent_in_scope(value, request):
            raise serializers.ValidationError("Folder not found in your account.")
        return value

    def _run_scope_match_clean(self, instance):
        """Enforce ClassGroup.clean() (folder ↔ class scope-match) on API writes.
        DRF does not call model.full_clean(); invoke the model's clean() so a
        folder/class scope mismatch is rejected (defence-in-depth on top of
        validate_folder + scope stamping)."""
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            )

    def create(self, validated_data):
        instance = ClassGroup(**validated_data)
        self._run_scope_match_clean(instance)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for k, v in validated_data.items():
            setattr(instance, k, v)
        self._run_scope_match_clean(instance)
        instance.save()
        return instance


class MarkingSchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarkingScheme
        fields = (
            "marks_per_correct",
            "negative_marks_per_wrong",
            "partial_marking",
            "multiple_correct_allowed",
            "multi_mark_policy",
        )


class SectionMarkingSchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionMarkingScheme
        fields = (
            "marks_per_correct",
            "negative_marks_per_wrong",
            "negative_kind",
            "partial_marking",
            "multiple_correct_allowed",
            "qualify_pct",
            "multi_mark_policy",
        )


class SectionSerializer(serializers.ModelSerializer):
    marking_scheme = SectionMarkingSchemeSerializer(required=False)

    class Meta:
        model = Section
        fields = (
            "id", "test", "key", "label", "order_index",
            "q_start", "q_end", "policy", "choose_k",
            "marking_scheme",
        )
        read_only_fields = ("id",)

    def validate(self, data):
        test = data.get("test") or (self.instance.test if self.instance else None)
        policy = data.get("policy", self.instance.policy if self.instance else "all")
        choose_k = data.get("choose_k", self.instance.choose_k if self.instance else None)
        q_start = data.get("q_start", self.instance.q_start if self.instance else None)
        q_end = data.get("q_end", self.instance.q_end if self.instance else None)

        if q_start and q_end and q_start > q_end:
            raise serializers.ValidationError("q_start must be <= q_end.")

        if policy == Section.POLICY_CHOOSE_K:
            if choose_k is None:
                raise serializers.ValidationError({"choose_k": "choose_k required when policy=choose_k."})
            if q_start and q_end:
                range_size = q_end - q_start + 1
                if not (1 <= choose_k <= range_size):
                    raise serializers.ValidationError({"choose_k": f"choose_k must be 1..{range_size}."})

        if test and q_start and q_end:
            siblings = Section.objects.filter(test=test)
            if self.instance:
                siblings = siblings.exclude(id=self.instance.id)
            for sib in siblings:
                if not (q_end < sib.q_start or q_start > sib.q_end):
                    raise serializers.ValidationError(
                        f"Range [{q_start},{q_end}] overlaps with section '{sib.key}' "
                        f"[{sib.q_start},{sib.q_end}]."
                    )
        return data

    def validate_test(self, value):
        request = self.context["request"]
        if not parent_in_scope(value, request):
            raise serializers.ValidationError("Test not found in your account.")
        return value

    def create(self, validated_data):
        ms_data = validated_data.pop("marking_scheme", None)
        section = Section.objects.create(**validated_data)
        if ms_data is not None:
            SectionMarkingScheme.objects.create(section=section, **ms_data)
        section.sync_question_membership()
        return section

    def update(self, instance, validated_data):
        ms_data = validated_data.pop("marking_scheme", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if ms_data is not None:
            sms, _ = SectionMarkingScheme.objects.get_or_create(section=instance)
            for k, v in ms_data.items():
                setattr(sms, k, v)
            sms.save()
        instance.sync_question_membership()
        return instance


class TestSerializer(serializers.ModelSerializer):
    marking_scheme = MarkingSchemeSerializer(required=False)
    mode = serializers.ChoiceField(
        choices=["standard", "roster_prebubbled", "competitive"],
        default="standard",
        required=False,
    )
    # Phase 3c: branding fields — all optional, multipart-safe
    sheet_heading = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    logo = serializers.ImageField(
        required=False,
        allow_null=True,
        validators=[validate_logo_image],
    )
    logo_position = serializers.ChoiceField(
        choices=["left", "center", "right"],
        required=False,
        default="left",
    )
    brand_inherit_org = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = Test
        fields = (
            "id",
            "class_group",
            "title",
            "subject",
            "parent_test",
            "attempt_number",
            "status",
            "mode",
            "default_options",
            "marking_scheme",
            # branding
            "sheet_heading",
            "logo",
            "logo_position",
            "brand_inherit_org",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "parent_test", "attempt_number", "created_at", "updated_at")

    def to_internal_value(self, data):
        # Multipart requests (logo upload) carry every field as a flat string,
        # so the nested `marking_scheme` object arrives JSON-encoded. Parse it
        # back to a dict AND rebuild `data` as a plain dict — DRF treats a
        # QueryDict as HTML input and would otherwise look for flattened
        # `marking_scheme.<field>` keys, ignoring the object we inject.
        ms = data.get("marking_scheme") if hasattr(data, "get") else None
        if isinstance(ms, str):
            if hasattr(data, "getlist"):  # QueryDict / MultiValueDict (multipart)
                plain = {k: data.get(k) for k in data.keys()}
            else:
                plain = dict(data)
            try:
                plain["marking_scheme"] = json.loads(ms)
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    {"marking_scheme": "marking_scheme must be valid JSON."}
                )
            data = plain
        return super().to_internal_value(data)

    def validate_class_group(self, value):
        # value is None for a class-less exam (allowed); only scope-check a class.
        request = self.context["request"]
        if value is not None and not parent_in_scope(value, request):
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


class OptionSerializer(serializers.ModelSerializer):
    # image is optional; allow_null=True so clients can clear it via JSON null
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Option
        fields = ("id", "label", "text", "image", "is_correct")
        read_only_fields = ("id",)


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True)
    # image is optional; allow_null=True so clients can clear it via JSON null
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Question
        fields = ("id", "test", "order_index", "text", "image", "topic", "difficulty", "options")
        read_only_fields = ("id",)

    def validate_test(self, value):
        request = self.context["request"]
        if not parent_in_scope(value, request):
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


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ("id", "class_group", "name", "order_index", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_class_group(self, value):
        request = self.context["request"]
        if not parent_in_scope(value, request):
            raise serializers.ValidationError("Class not found in your account.")
        return value
