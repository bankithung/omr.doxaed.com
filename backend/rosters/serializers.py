from rest_framework import serializers

from common.scope import parent_in_scope

from .models import Roster, Student


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ("id", "roster", "full_name", "roll_number", "external_ref")
        read_only_fields = ("id",)

    def validate_roster(self, value):
        request = self.context["request"]
        if not parent_in_scope(value, request):
            raise serializers.ValidationError("Roster not found in your account.")
        return value


class RosterSerializer(serializers.ModelSerializer):
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Roster
        fields = ("id", "name", "class_group", "student_count", "created_at", "updated_at")
        read_only_fields = ("id", "student_count", "created_at", "updated_at")

    def get_student_count(self, obj):
        return obj.students.count()

    def validate_class_group(self, value):
        if value is None:
            return value
        request = self.context["request"]
        if not parent_in_scope(value, request):
            raise serializers.ValidationError("Class group not found in your account.")
        return value
