from rest_framework import serializers

from common.scope import parent_in_scope

from .models import ClassGroup, MarkingScheme, Option, Question, Test


class ClassGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassGroup
        fields = ("id", "name", "description", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class MarkingSchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarkingScheme
        fields = (
            "marks_per_correct",
            "negative_marks_per_wrong",
            "partial_marking",
            "multiple_correct_allowed",
        )


class TestSerializer(serializers.ModelSerializer):
    marking_scheme = MarkingSchemeSerializer(required=False)

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
            "marking_scheme",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "parent_test", "attempt_number", "created_at", "updated_at")

    def validate_class_group(self, value):
        request = self.context["request"]
        if not parent_in_scope(value, request):
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
