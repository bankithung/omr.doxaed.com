from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.viewsets import ScopedModelViewSet

from .models import Roster, Student
from .serializers import RosterSerializer, StudentSerializer


class RosterViewSet(ScopedModelViewSet):
    queryset = Roster.objects.all()
    serializer_class = RosterSerializer
    owner_extra_fields = ("created_by",)

    @action(detail=True, methods=["post"], url_path="add_count")
    def add_count(self, request, pk=None):
        roster = self.get_object()  # already scoped to request.user via ScopedModelViewSet
        count = request.data.get("count")
        try:
            count = int(count)
        except (TypeError, ValueError):
            return Response({"count": "Must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
        if count < 1:
            return Response({"count": "Must be a positive integer."}, status=status.HTTP_400_BAD_REQUEST)

        students = [
            Student(roster=roster, roll_number=str(i))
            for i in range(1, count + 1)
        ]
        Student.objects.bulk_create(students)
        return Response({"created": count}, status=status.HTTP_201_CREATED)


class StudentViewSet(viewsets.ModelViewSet):
    """Child-scoped: filtered through roster__user; no IsInScope needed."""

    permission_classes = [IsAuthenticated]
    serializer_class = StudentSerializer

    def get_queryset(self):
        qs = Student.objects.filter(roster__user=self.request.user)
        roster_id = self.request.query_params.get("roster")
        if roster_id:
            qs = qs.filter(roster_id=roster_id)
        return qs
